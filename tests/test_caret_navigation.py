"""Cursor navigation inside the focused field, driven against a fake tree.

The point of these tests is the honesty of the after-state check: a caret move
the field refused or silently ignored must surface as a failure, never as a
silent no-op that leaves a voice-only user disoriented.
"""

from __future__ import annotations

import unittest

from clausis.broker import ActionBroker, SafeExecutor
from clausis.capabilities import CapabilityAuthority
from clausis.executors import SessionExecutor
from clausis.gnome_adapter import GnomeAdapterError, GnomeSemanticExecutor, PyAtSpiDesktop
from clausis.models import ActionRequest
from clausis.policy import ACTION_POLICIES, evaluate
from clausis.router import OfflineRouter

from tests.test_dictation import (
    STATE_ACTIVE,
    STATE_EDITABLE,
    STATE_FOCUSED,
    STATE_SHOWING,
    DesktopHarness,
    FakeNode,
    build_desktop,
)


def field(content="", caret=None, **kwargs):
    return FakeNode(
        "Notiz",
        "text",
        {STATE_SHOWING, STATE_FOCUSED, STATE_EDITABLE},
        content=content,
        caret=caret,
        **kwargs,
    )


class CaretMovementTests(DesktopHarness):
    def test_caret_moves_to_start_and_end(self):
        node = field("Guten Tag Welt", caret=10)
        desktop = self.desktop_for(build_desktop(node))
        desktop.move_caret("start")
        self.assertEqual(node.caret, 0)
        desktop.move_caret("end")
        self.assertEqual(node.caret, len("Guten Tag Welt"))

    def test_word_steps_move_over_words_and_spaces(self):
        node = field("eins zwei drei", caret=0)
        desktop = self.desktop_for(build_desktop(node))
        desktop.move_caret("word_next")
        self.assertEqual(node.caret, 5)
        desktop.move_caret("word_next")
        self.assertEqual(node.caret, 10)
        desktop.move_caret("word_previous")
        self.assertEqual(node.caret, 5)
        desktop.move_caret("word_previous")
        self.assertEqual(node.caret, 0)

    def test_word_steps_clamp_at_both_ends(self):
        node = field("kurz", caret=0)
        desktop = self.desktop_for(build_desktop(node))
        desktop.move_caret("word_previous")
        self.assertEqual(node.caret, 0)
        desktop.move_caret("word_next")
        self.assertEqual(node.caret, 4)
        desktop.move_caret("word_next")
        self.assertEqual(node.caret, 4)

    def test_word_step_over_leading_spaces(self):
        node = field("  eins", caret=0)
        desktop = self.desktop_for(build_desktop(node))
        desktop.move_caret("word_next")
        self.assertEqual(node.caret, 2)

    def test_unknown_direction_is_refused(self):
        desktop = self.desktop_for(build_desktop(field("Text")))
        with self.assertRaisesRegex(GnomeAdapterError, "Cursorrichtung"):
            desktop.move_caret("sideways")

    def test_rejected_caret_move_is_reported_not_assumed(self):
        node = field("Hallo", caret=2, caret_accepts=False)
        desktop = self.desktop_for(build_desktop(node))
        with self.assertRaisesRegex(GnomeAdapterError, "abgelehnt"):
            desktop.move_caret("start")
        self.assertEqual(node.caret, 2)

    def test_field_without_focus_support_is_refused(self):
        node = field("Hallo", caret=2, focus_accepts=False)
        desktop = self.desktop_for(build_desktop(node))
        with self.assertRaisesRegex(GnomeAdapterError, "fokussieren"):
            desktop.move_caret("end")

    def test_position_is_spoken_with_total(self):
        node = field("abc", caret=0)
        desktop = self.desktop_for(build_desktop(node))
        spoken = desktop.move_caret("end")
        self.assertIn("Position 3", spoken)
        self.assertIn("von 3", spoken)

    def test_password_field_never_gets_a_caret_move(self):
        node = FakeNode(
            "Passwort", "password text", {STATE_SHOWING, STATE_FOCUSED, STATE_EDITABLE}, content="x" * 8
        )
        desktop = self.desktop_for(build_desktop(node))
        with self.assertRaisesRegex(GnomeAdapterError, "Passwortfeld"):
            desktop.move_caret("end")


class ReadFromCaretTests(DesktopHarness):
    def test_reads_from_the_caret_to_the_end(self):
        node = field("Guten Tag Welt", caret=6)
        desktop = self.desktop_for(build_desktop(node))
        self.assertEqual(desktop.read_from_caret(), "Tag Welt")

    def test_caret_at_start_reads_everything(self):
        node = field("Alles", caret=0)
        desktop = self.desktop_for(build_desktop(node))
        self.assertEqual(desktop.read_from_caret(), "Alles")

    def test_caret_at_end_reads_nothing(self):
        node = field("Alles", caret=5)
        desktop = self.desktop_for(build_desktop(node))
        self.assertEqual(desktop.read_from_caret(), "")


class NewlineParagraphTests(DesktopHarness):
    def test_newline_inserts_one_break_at_the_caret(self):
        node = field("Zeile eins", caret=None)
        desktop = self.desktop_for(build_desktop(node))
        content = desktop.insert_newline()
        self.assertEqual(node.content, "Zeile eins\n")
        self.assertIn("\n", content)

    def test_paragraph_inserts_a_blank_line(self):
        node = field("Erster Absatz", caret=None)
        desktop = self.desktop_for(build_desktop(node))
        desktop.insert_paragraph()
        self.assertEqual(node.content, "Erster Absatz\n\n")

    def test_newline_in_the_middle_of_the_field(self):
        node = field("eins zwei", caret=4)
        desktop = self.desktop_for(build_desktop(node))
        desktop.insert_newline()
        self.assertIn("\n", node.content)
        self.assertTrue(node.content.startswith("eins\n"))

    def test_newline_is_read_back_from_the_tree_not_assumed(self):
        node = field("Zeile", caret=None, accept=False)
        desktop = self.desktop_for(build_desktop(node))
        with self.assertRaisesRegex(GnomeAdapterError, "abgelehnt"):
            desktop.insert_newline()
        self.assertEqual(node.content, "Zeile")

    def test_terminal_still_refuses_a_newline(self):
        node = FakeNode("", "terminal", {STATE_SHOWING, STATE_FOCUSED, STATE_EDITABLE})
        window = FakeNode("Terminal", "frame", {STATE_SHOWING, STATE_ACTIVE}, [node])
        application = FakeNode("GNOME Terminal", "application", set(), [window])
        desktop = self.desktop_for(FakeNode("desktop", "desktop frame", set(), [application]))
        with self.assertRaisesRegex(GnomeAdapterError, "Terminal"):
            desktop.insert_newline()


class CaretPolicyAndRoutingTests(unittest.TestCase):
    def test_caret_actions_stay_low_risk_and_immediate(self):
        for action in (
            "text.caret.start",
            "text.caret.end",
            "text.caret.word_next",
            "text.caret.word_previous",
            "text.read_from_caret",
            "text.newline",
            "text.paragraph",
        ):
            with self.subTest(action=action):
                decision = evaluate(ActionRequest(action))
                self.assertFalse(decision.confirmation_required)

    def test_caret_actions_accept_no_target(self):
        for action in (
            "text.caret.start",
            "text.caret.end",
            "text.caret.word_next",
            "text.caret.word_previous",
            "text.newline",
            "text.paragraph",
        ):
            with self.subTest(action=action):
                with self.assertRaises(ValueError):
                    evaluate(ActionRequest(action, "egal"))

    def test_spoken_commands_route_to_the_caret_actions(self):
        router = OfflineRouter()
        cases = {
            "cursor an den anfang": "text.caret.start",
            "cursor ans ende": "text.caret.end",
            "cursor ein wort weiter": "text.caret.word_next",
            "cursor ein wort zurück": "text.caret.word_previous",
            "lies ab dem cursor": "text.read_from_caret",
            "neue zeile": "text.newline",
            "absatz": "text.paragraph",
            "caret to the start": "text.caret.start",
            "caret to the end": "text.caret.end",
            "next word": "text.caret.word_next",
            "previous word": "text.caret.word_previous",
            "read from the caret": "text.read_from_caret",
        }
        for spoken, action in cases.items():
            with self.subTest(spoken=spoken):
                request = router.route(spoken)
                self.assertTrue(request is not None and request.action == action, spoken)

    def test_caret_move_reaches_the_adapter_through_the_broker(self):
        class Recorder:
            def __init__(self):
                self.moves = []

            def move_caret(self, direction):
                self.moves.append(direction)
                return "Der Cursor steht auf Position 0 von 3."

        recorder = Recorder()
        broker = ActionBroker(
            CapabilityAuthority(b"c" * 32),
            SessionExecutor(SafeExecutor(dry_run=False), GnomeSemanticExecutor(recorder)),
        )
        result = broker.submit(ActionRequest("text.caret.start"))
        self.assertEqual(result.status, "completed")
        self.assertEqual(recorder.moves, ["start"])
        self.assertIn("Position 0", result.message)

    def test_newline_reaches_the_adapter_through_the_broker(self):
        class Recorder:
            def __init__(self):
                self.newlines = 0

            def insert_newline(self):
                self.newlines += 1
                return "Zeile\n"

        recorder = Recorder()
        broker = ActionBroker(
            CapabilityAuthority(b"c" * 32),
            SessionExecutor(SafeExecutor(dry_run=False), GnomeSemanticExecutor(recorder)),
        )
        result = broker.submit(ActionRequest("text.newline"))
        self.assertEqual(result.status, "completed")
        self.assertEqual(recorder.newlines, 1)
        self.assertIn("Neue Zeile", result.message)

    def test_caret_actions_are_wired_into_the_adapted_action_table(self):
        from clausis.executors import unadapted_actions

        self.assertEqual(unadapted_actions(), frozenset())
        for action in ("text.caret.start", "text.newline", "dialog.file.list"):
            self.assertIn(action, ACTION_POLICIES)


if __name__ == "__main__":
    unittest.main()
