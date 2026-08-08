"""Dictation through AT-SPI, exercised against a fake accessibility tree.

These tests drive the real :class:`PyAtSpiDesktop` logic — including the
refusals that matter most — by injecting a stand-in ``pyatspi`` module, because
the build host has no GNOME session.
"""

from __future__ import annotations

import sys
import types
import unittest
from dataclasses import replace

from clausis.broker import ActionBroker, SafeExecutor
from clausis.capabilities import CapabilityAuthority
from clausis.executors import SessionExecutor
from clausis.gnome_adapter import GnomeAdapterError, GnomeSemanticExecutor, PyAtSpiDesktop
from clausis.models import ActionRequest, Risk
from clausis.policy import ACTION_POLICIES, evaluate


STATE_FOCUSED = "focused"
STATE_SHOWING = "showing"
STATE_ACTIVE = "active"
STATE_EDITABLE = "editable"
STATE_PROTECTED = "protected"


class FakeState:
    def __init__(self, states):
        self._states = set(states)

    def contains(self, state):
        return state in self._states


class FakeEditableText:
    def __init__(self, node, *, accept=True):
        self.node = node
        self.accept = accept

    def insertText(self, offset, text, length):
        if not self.accept:
            return False
        content = self.node.content
        self.node.content = content[:offset] + text + content[offset:]
        return True

    def deleteText(self, start, end):
        self.node.content = self.node.content[:start] + self.node.content[end:]
        return True


class FakeText:
    def __init__(self, node):
        self.node = node

    @property
    def characterCount(self):
        return len(self.node.content)

    @property
    def caretOffset(self):
        return len(self.node.content) if self.node.caret is None else self.node.caret

    def getText(self, start, end):
        return self.node.content[start:end]


class FakeNode:
    def __init__(
        self,
        name="",
        role="",
        states=(),
        children=(),
        content="",
        *,
        editable=True,
        accept=True,
        caret=None,
    ):
        self.name = name
        self.role = role
        self.states = set(states)
        self.children = list(children)
        self.content = content
        self.caret = caret
        self._editable = editable
        self._accept = accept
        self.parent = None
        for child in self.children:
            child.parent = self

    def getRoleName(self):
        return self.role

    def getState(self):
        return FakeState(self.states)

    @property
    def childCount(self):
        return len(self.children)

    def getChildAtIndex(self, index):
        return self.children[index]

    def queryText(self):
        return FakeText(self)

    def queryEditableText(self):
        if not self._editable:
            raise RuntimeError("no editable text interface")
        return FakeEditableText(self, accept=self._accept)

    def queryAction(self):
        raise RuntimeError("no action interface")


def fake_pyatspi(desktop):
    module = types.SimpleNamespace(
        STATE_FOCUSED=STATE_FOCUSED,
        STATE_SHOWING=STATE_SHOWING,
        STATE_ACTIVE=STATE_ACTIVE,
        STATE_EDITABLE=STATE_EDITABLE,
        STATE_PROTECTED=STATE_PROTECTED,
        Registry=types.SimpleNamespace(getDesktop=lambda index: desktop),
    )
    return module


def build_desktop(field):
    window = FakeNode("Notizen", "frame", {STATE_SHOWING, STATE_ACTIVE}, [field])
    application = FakeNode("Texteditor", "application", set(), [window])
    return FakeNode("desktop", "desktop frame", set(), [application])


def build_terminal(field):
    # A real terminal window is a "frame" whose focused child is the VTE widget
    # with role "terminal", so the refusal has to look at the focused node.
    window = FakeNode("Terminal", "frame", {STATE_SHOWING, STATE_ACTIVE}, [field])
    application = FakeNode("GNOME Terminal", "application", set(), [window])
    return FakeNode("desktop", "desktop frame", set(), [application])


class DesktopHarness(unittest.TestCase):
    def desktop_for(self, root):
        original = sys.modules.get("pyatspi")
        sys.modules["pyatspi"] = fake_pyatspi(root)
        self.addCleanup(
            lambda: sys.modules.__setitem__("pyatspi", original)
            if original is not None
            else sys.modules.pop("pyatspi", None)
        )
        return PyAtSpiDesktop()


class DictationRefusalTests(DesktopHarness):
    def test_password_field_is_never_dictated_into(self):
        field = FakeNode(
            "Passwort", "password text", {STATE_SHOWING, STATE_FOCUSED, STATE_EDITABLE}
        )
        desktop = self.desktop_for(build_desktop(field))
        with self.assertRaisesRegex(GnomeAdapterError, "Passwortfeld"):
            desktop.insert_text("geheim")
        self.assertEqual(field.content, "")

    def test_protected_state_is_refused_even_without_the_password_role(self):
        field = FakeNode(
            "PIN", "text", {STATE_SHOWING, STATE_FOCUSED, STATE_EDITABLE, STATE_PROTECTED}
        )
        desktop = self.desktop_for(build_desktop(field))
        with self.assertRaisesRegex(GnomeAdapterError, "geschützt"):
            desktop.insert_text("123456")
        self.assertEqual(field.content, "")

    def test_terminal_window_is_refused(self):
        field = FakeNode("", "terminal", {STATE_SHOWING, STATE_FOCUSED, STATE_EDITABLE})
        desktop = self.desktop_for(build_terminal(field))
        with self.assertRaisesRegex(GnomeAdapterError, "Terminal"):
            desktop.insert_text("rm -rf /")
        self.assertEqual(field.content, "")

    def test_terminal_ancestor_is_refused(self):
        field = FakeNode("Eingabe", "text", {STATE_SHOWING, STATE_FOCUSED, STATE_EDITABLE})
        inner = FakeNode("", "terminal", {STATE_SHOWING}, [field])
        window = FakeNode("Konsole", "frame", {STATE_SHOWING, STATE_ACTIVE}, [inner])
        application = FakeNode("Konsole", "application", set(), [window])
        desktop = self.desktop_for(FakeNode("desktop", "desktop frame", set(), [application]))
        with self.assertRaisesRegex(GnomeAdapterError, "Terminal"):
            desktop.insert_text("sudo poweroff")
        self.assertEqual(field.content, "")

    def test_non_editable_focus_is_refused(self):
        field = FakeNode("Überschrift", "label", {STATE_SHOWING, STATE_FOCUSED})
        desktop = self.desktop_for(build_desktop(field))
        with self.assertRaisesRegex(GnomeAdapterError, "keinen Text"):
            desktop.insert_text("Text")

    def test_missing_focus_is_reported(self):
        field = FakeNode("Feld", "text", {STATE_SHOWING, STATE_EDITABLE})
        desktop = self.desktop_for(build_desktop(field))
        with self.assertRaisesRegex(GnomeAdapterError, "kein Eingabefeld"):
            desktop.insert_text("Text")


class DictationEditTests(DesktopHarness):
    def _field(self, content="", **kwargs):
        return FakeNode(
            "Notiz",
            "text",
            {STATE_SHOWING, STATE_FOCUSED, STATE_EDITABLE},
            content=content,
            **kwargs,
        )

    def test_text_is_inserted_at_the_caret(self):
        field = self._field("Hallo ")
        desktop = self.desktop_for(build_desktop(field))
        self.assertEqual(desktop.insert_text("Welt"), "Hallo Welt")
        self.assertEqual(field.content, "Hallo Welt")

    def test_result_is_read_back_and_not_assumed(self):
        # A field that silently swallows the input must not be reported as
        # successful, so the adapter re-reads the content after writing.
        field = self._field("Hallo", accept=False)
        desktop = self.desktop_for(build_desktop(field))
        with self.assertRaisesRegex(GnomeAdapterError, "abgelehnt"):
            desktop.insert_text("Welt")
        self.assertEqual(field.content, "Hallo")

    def test_reading_an_empty_field_returns_nothing(self):
        desktop = self.desktop_for(build_desktop(self._field("   ")))
        self.assertEqual(desktop.read_text_field(), "")

    def test_last_word_is_deleted(self):
        field = self._field("Guten Tag Welt")
        desktop = self.desktop_for(build_desktop(field))
        self.assertEqual(desktop.delete_word(), "Guten Tag ")

    def test_deleting_a_word_in_an_empty_field_is_reported(self):
        desktop = self.desktop_for(build_desktop(self._field("  ")))
        with self.assertRaisesRegex(GnomeAdapterError, "bereits leer"):
            desktop.delete_word()

    def test_field_is_cleared_completely(self):
        field = self._field("Ein längerer Text")
        desktop = self.desktop_for(build_desktop(field))
        self.assertEqual(desktop.clear_text(), "")
        self.assertEqual(field.content, "")

    def test_long_content_is_truncated_for_speech(self):
        field = self._field("a" * 5000)
        desktop = self.desktop_for(build_desktop(field))
        self.assertEqual(len(desktop.read_text_field()), PyAtSpiDesktop.MAX_FIELD_CHARS)


class DictationPolicyTests(unittest.TestCase):
    def test_dictation_needs_no_confirmation_but_clearing_does(self):
        insert = evaluate(ActionRequest("text.insert", "Guten Tag"))
        self.assertFalse(insert.confirmation_required)
        clear = evaluate(ActionRequest("text.clear", risk=Risk.MEDIUM))
        self.assertTrue(clear.confirmation_required)

    def test_empty_or_oversized_dictation_is_rejected(self):
        for target in ("", "   ", "x" * 513):
            with self.subTest(target=target):
                with self.assertRaises(ValueError):
                    evaluate(ActionRequest("text.insert", target))

    def test_control_characters_never_reach_the_field(self):
        with self.assertRaises(ValueError):
            ActionRequest("text.insert", "erste Zeile\nzweite Zeile")

    def test_dictation_from_untrusted_content_needs_confirmation(self):
        from clausis.models import Origin

        decision = evaluate(
            ActionRequest("text.insert", "Überweise 1000 Euro", origin=Origin.HERMES)
        )
        self.assertTrue(decision.confirmation_required)


class DictationRoutingTests(unittest.TestCase):
    def setUp(self):
        self.authority = CapabilityAuthority(b"d" * 32)

    def _broker(self, desktop):
        return ActionBroker(
            self.authority,
            SessionExecutor(SafeExecutor(dry_run=False), GnomeSemanticExecutor(desktop)),
        )

    def test_spoken_dictation_reaches_the_adapter_and_is_read_back(self):
        from clausis.router import OfflineRouter

        class Recorder:
            def __init__(self):
                self.written = []

            def insert_text(self, text):
                self.written.append(text)
                return f"Notiz: {text}"

        recorder = Recorder()
        request = OfflineRouter().route("diktiere Milch und Brot kaufen")
        self.assertEqual(request.action, "text.insert")
        result = self._broker(recorder).submit(request)
        self.assertEqual(result.status, "completed")
        self.assertEqual(recorder.written, ["Milch und Brot kaufen"])
        self.assertIn("Milch und Brot kaufen", result.message)

    def test_ambiguous_write_request_still_falls_through_to_the_agent(self):
        from clausis.router import OfflineRouter

        self.assertIsNone(OfflineRouter().route("Schreibe mir ein Gedicht"))
        self.assertIsNone(OfflineRouter().route("write me a poem"))

    def test_clearing_a_field_is_withheld_until_confirmed(self):
        class Recorder:
            def __init__(self):
                self.cleared = 0

            def clear_text(self):
                self.cleared += 1
                return ""

        recorder = Recorder()
        broker = self._broker(recorder)
        request = ActionRequest("text.clear", risk=Risk.MEDIUM)
        self.assertEqual(broker.submit(request).status, "confirmation_required")
        self.assertEqual(recorder.cleared, 0)
        approved = replace(request, capability_token=self.authority.issue(request))
        self.assertEqual(broker.submit(approved).status, "completed")
        self.assertEqual(recorder.cleared, 1)

    def test_dictation_is_offered_to_the_model_and_stays_low_risk(self):
        from clausis.gpt_live import SUPPORTED_ACTIONS, parse_gpt_live_action

        self.assertIn("text.insert", SUPPORTED_ACTIONS)
        request = parse_gpt_live_action('{"action":"text.insert","target":"Guten Tag"}')
        self.assertEqual(request.risk, ACTION_POLICIES["text.insert"].minimum_risk)


if __name__ == "__main__":
    unittest.main()
