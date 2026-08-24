"""Voice text editing — selection, replacement, undo/redo, granular reading.

Driven against a fake accessibility tree, like dictation and caret navigation.
The property under test is the same honesty rule: every mutation is read back
from the tree, and a widget that refused or ignored the operation is reported
as a failure instead of a success.
"""

from __future__ import annotations

import unittest

from clausis.broker import ActionBroker, SafeExecutor
from clausis.capabilities import CapabilityAuthority
from clausis.executors import SessionExecutor
from clausis.gnome_adapter import GnomeAdapterError, GnomeSemanticExecutor, PyAtSpiDesktop
from clausis.models import ActionRequest
from clausis.policy import evaluate
from clausis.router import OfflineRouter

from tests.test_dictation import (
    STATE_ACTIVE,
    STATE_EDITABLE,
    STATE_FOCUSED,
    STATE_SHOWING,
    DesktopHarness,
    FakeEditableText,
    FakeNode,
    FakeText,
    build_desktop,
)


class SelectableFakeText(FakeText):
    """Text interface that reads and writes the field's selection slot.

    The selection lives on the node (not on this object) because the adapter
    calls ``queryText()`` twice — set, then verify — and the verify call must
    observe what ``addSelection`` actually wrote.
    """

    def __init__(self, node):
        super().__init__(node)
        if not hasattr(node, "selection"):
            node.selection = (self.caretOffset, self.caretOffset)

    def getSelection(self, index):
        return tuple(self.node.selection)

    def addSelection(self, start, end):
        if not getattr(self.node, "selection_accepts", True):
            return False
        self.node.selection = (start, end)
        self.node.caret = end
        return True


class SelectableField(FakeNode):
    """An editable field with selection support and optional named actions."""

    def __init__(self, content="", caret=None, *, named_actions=(), **kwargs):
        super().__init__(
            "Notiz",
            "text",
            {STATE_SHOWING, STATE_FOCUSED, STATE_EDITABLE},
            content=content,
            caret=caret,
            **kwargs,
        )
        self.selection = (caret if caret is not None else len(content),
                          caret if caret is not None else len(content))
        self.selection_accepts = True
        self.named_actions = dict(named_actions)
        self.invoked = []

    def queryText(self):
        text = SelectableFakeText(self)
        # Keep the object alive beyond the call for the selection state.
        self._text = text
        return text

    def queryAction(self):
        field = self

        class Action:
            nActions = len(field.named_actions)

            def getName(self, index):
                return list(field.named_actions)[index]

            def doAction(self, index):
                name = list(field.named_actions)[index]
                field.invoked.append(name)
                return field.named_actions[name]

        return Action()


def selectable_desktop(field):
    return build_desktop(field)


class SelectionTests(DesktopHarness):
    def _desktop(self, field):
        return self.desktop_for(selectable_desktop(field))

    def test_select_word_selects_the_word_at_the_caret(self):
        field = SelectableField("Guten Tag Welt", caret=10)
        spoken = self._desktop(field).select_word()
        self.assertEqual(spoken, "Welt")
        self.assertEqual(field.selection, (10, 14))
        # A caret inside "Tag" selects "Tag".
        field2 = SelectableField("Guten Tag Welt", caret=7)
        self.assertEqual(self._desktop(field2).select_word(), "Tag")
        self.assertEqual(field2.selection, (6, 9))

    def test_select_sentence_selects_the_current_sentence(self):
        content = "Erster Satz. Zweiter Satz danebena. Dritter."
        field = SelectableField(content, caret=14)
        spoken = self._desktop(field).select_sentence()
        self.assertEqual(spoken, "Zweiter Satz danebena.")
        start, end = field.selection
        self.assertEqual(content[start:end], "Zweiter Satz danebena.")

    def test_select_all_uses_the_widget_action_when_published(self):
        field = SelectableField("Alles markieren", named_actions={"select all": True})
        # A real widget's select-all action changes the selection itself.
        def fake_do(name):
            field.selection = (0, len(field.content))
            return True
        field.named_actions = {"select all": True}
        desktop = self._desktop(field)
        original = desktop._invoke_named_action

        def invoke_with_effect(node, names):
            if "select all" in names and "select all" in field.named_actions:
                field.selection = (0, len(field.content))
                field.invoked.append("select all")
                return True
            return original(node, names)

        desktop._invoke_named_action = invoke_with_effect
        content = desktop.select_all()
        self.assertEqual(field.invoked, ["select all"])
        self.assertEqual(content, "Alles markieren")

    def test_select_all_falls_back_to_the_text_interface(self):
        field = SelectableField("Inhalt hier")
        content = self._desktop(field).select_all()
        self.assertEqual(content, "Inhalt hier")
        self.assertEqual(field.selection, (0, len("Inhalt hier")))

    def test_rejected_selection_is_reported_not_assumed(self):
        field = SelectableField("Ein Wort", caret=4)
        field.selection_accepts = False
        with self.assertRaisesRegex(GnomeAdapterError, "abgelehnt"):
            self._desktop(field).select_word()

    def test_password_field_never_gets_a_selection(self):
        field = FakeNode(
            "Passwort", "password text", {STATE_SHOWING, STATE_FOCUSED, STATE_EDITABLE}
        )
        desktop = self.desktop_for(build_desktop(field))
        with self.assertRaisesRegex(GnomeAdapterError, "Passwortfeld"):
            desktop.select_word()


class ReplaceAndDeleteTests(DesktopHarness):
    def _desktop(self, field):
        return self.desktop_for(selectable_desktop(field))

    def test_replace_selection_rewrites_the_selected_span(self):
        field = SelectableField("Frau Meier schreibt", caret=5)
        field.selection = (5, 10)
        content = self._desktop(field).replace_selection("Maier")
        self.assertEqual(field.content, "Frau Maier schreibt")
        self.assertIn("Frau Maier schreibt", content)

    def test_replace_without_a_selection_is_refused(self):
        field = SelectableField("Text", caret=4)
        field.selection = (4, 4)
        with self.assertRaisesRegex(GnomeAdapterError, "nichts ausgewählt|Ersetzung"):
            self._desktop(field).replace_selection("Ersatz")

    def test_rejected_replacement_is_reported(self):
        field = SelectableField("Alt", caret=0, accept=False)
        field.selection = (0, 3)
        with self.assertRaisesRegex(GnomeAdapterError, "abgelehnt"):
            self._desktop(field).replace_selection("Neu")

    def test_delete_selection_removes_the_span(self):
        field = SelectableField("Guten Tag Welt", caret=6)
        field.selection = (6, 10)
        remaining = self._desktop(field).delete_selection()
        self.assertEqual(field.content, "Guten Welt")
        self.assertIn("Guten Welt", remaining)

    def test_delete_without_a_selection_is_refused(self):
        field = SelectableField("Text", caret=2)
        field.selection = (2, 2)
        with self.assertRaisesRegex(GnomeAdapterError, "nichts ausgewählt"):
            self._desktop(field).delete_selection()


class UndoRedoTests(DesktopHarness):
    def _desktop(self, field):
        return self.desktop_for(selectable_desktop(field))

    def test_undo_invokes_the_widgets_own_action(self):
        field = SelectableField("Text", named_actions={"undo": True})
        result = self._desktop(field).edit_undo()
        self.assertEqual(field.invoked, ["undo"])
        self.assertEqual(result, "rückgängig")

    def test_redo_invokes_the_widgets_own_action(self):
        field = SelectableField("Text", named_actions={"redo": True})
        result = self._desktop(field).edit_redo()
        self.assertEqual(field.invoked, ["redo"])
        self.assertEqual(result, "wiederhergestellt")

    def test_field_without_an_undo_action_is_refused_honestly(self):
        field = SelectableField("Text")
        with self.assertRaisesRegex(GnomeAdapterError, "Rückgängig"):
            self._desktop(field).edit_undo()


class GranularReadTests(DesktopHarness):
    def _desktop(self, field):
        return self.desktop_for(selectable_desktop(field))

    def test_reads_the_unit_at_the_caret(self):
        field = SelectableField("Erster Satz. Zweiter Satz.", caret=14)
        desktop = self._desktop(field)
        self.assertEqual(desktop.read_granular("word"), "Zweiter")
        self.assertEqual(desktop.read_granular("sentence"), "Zweiter Satz.")
        # Position 14 is the 'w' of 'Zweiter'.
        self.assertEqual(desktop.read_granular("character"), "w")

    def test_line_and_paragraph_granularity(self):
        content = "Zeile eins\nZeile zwei\n\nZweiter Absatz."
        field = SelectableField(content, caret=12)
        desktop = self._desktop(field)
        self.assertEqual(desktop.read_granular("line"), "Zeile zwei")
        # A paragraph spans its lines; the blank line ends it.
        self.assertEqual(desktop.read_granular("paragraph"), "Zeile eins\nZeile zwei")
        field2 = SelectableField(content, caret=25)
        self.assertEqual(
            self._desktop(field2).read_granular("paragraph"), "Zweiter Absatz."
        )

    def test_unknown_granularity_is_refused(self):
        desktop = self._desktop(SelectableField("Text"))
        with self.assertRaisesRegex(GnomeAdapterError, "Granularität"):
            desktop.read_granular("page")

    def test_empty_field_reads_nothing(self):
        desktop = self._desktop(SelectableField(""))
        self.assertEqual(desktop.read_granular("word"), "")


class TextEditingPolicyTests(unittest.TestCase):
    def test_editing_actions_stay_low_risk_and_immediate(self):
        granular = ActionRequest("text.read_granular", arguments={"granularity": "word"})
        self.assertFalse(evaluate(granular).confirmation_required)
        for action in (
            "text.select_word",
            "text.select_sentence",
            "text.select_all",
            "text.delete_selection",
            "text.undo",
            "text.redo",
        ):
            with self.subTest(action=action):
                decision = evaluate(ActionRequest(action))
                self.assertFalse(decision.confirmation_required)

    def test_replace_selection_needs_dictatable_text(self):
        request = ActionRequest("text.replace_selection", "Maier")
        self.assertFalse(evaluate(request).confirmation_required)
        for invalid in ("", "   ", "x" * 513):
            with self.subTest(target=invalid):
                with self.assertRaises(ValueError):
                    evaluate(ActionRequest("text.replace_selection", invalid))

    def test_read_granular_validates_the_unit(self):
        request = ActionRequest(
            "text.read_granular", arguments={"granularity": "sentence"}
        )
        self.assertFalse(evaluate(request).confirmation_required)
        with self.assertRaises(ValueError):
            evaluate(ActionRequest("text.read_granular", arguments={"granularity": "page"}))
        with self.assertRaises(ValueError):
            evaluate(ActionRequest("text.read_granular", "satze"))

    def test_spoken_commands_route_to_the_editing_actions(self):
        router = OfflineRouter()
        cases = {
            "markiere das wort": "text.select_word",
            "markiere den satz": "text.select_sentence",
            "alles markieren": "text.select_all",
            "lösche die auswahl": "text.delete_selection",
            "rückgängig": "text.undo",
            "wiederherstellen": "text.redo",
            "select the word": "text.select_word",
            "select all": "text.select_all",
            "delete the selection": "text.delete_selection",
            "undo": "text.undo",
            "redo": "text.redo",
        }
        for spoken, action in cases.items():
            with self.subTest(spoken=spoken):
                request = router.route(spoken)
                self.assertTrue(request is not None and request.action == action, spoken)

    def test_replace_selection_takes_the_dictated_replacement(self):
        request = OfflineRouter().route("ersetze die auswahl durch Maier")
        self.assertIsNotNone(request)
        self.assertEqual(request.action, "text.replace_selection")
        self.assertEqual(request.target, "Maier")
        request = OfflineRouter().route("replace the selection with Maier")
        self.assertEqual(request.target, "Maier")

    def test_granular_reading_routes_with_the_unit(self):
        router = OfflineRouter()
        for spoken, unit in (
            ("lies das zeichen vor", "character"),
            ("lies das wort vor", "word"),
            ("lies die zeile vor", "line"),
            ("lies den satz vor", "sentence"),
            ("lies den absatz vor", "paragraph"),
            ("read the sentence", "sentence"),
        ):
            with self.subTest(spoken=spoken):
                request = router.route(spoken)
                self.assertIsNotNone(request, spoken)
                self.assertEqual(request.action, "text.read_granular")
                self.assertEqual(request.arguments["granularity"], unit)


class TextEditingEndToEndTests(unittest.TestCase):
    """Router → broker → executor → fake field, the full spoken workflow."""

    def test_select_then_replace_through_the_broker(self):
        from tests.test_dictation import fake_pyatspi
        import sys

        field = SelectableField("Vielen Dank Frau Meier.", caret=19)
        desktop_root = selectable_desktop(field)
        original = sys.modules.get("pyatspi")
        sys.modules["pyatspi"] = fake_pyatspi(desktop_root)
        try:
            broker = ActionBroker(
                CapabilityAuthority(b"d" * 32),
                SessionExecutor(SafeExecutor(dry_run=False), GnomeSemanticExecutor()),
            )
            select = OfflineRouter().route("markiere den satz")
            self.assertEqual(select.action, "text.select_sentence")
            result = broker.submit(select)
            self.assertEqual(result.status, "completed", result.message)
            replace = OfflineRouter().route("ersetze die auswahl durch Frau Maier")
            self.assertIsNotNone(replace)
            result = broker.submit(replace)
            self.assertEqual(result.status, "completed", result.message)
            self.assertIn("Frau Maier", field.content)
        finally:
            if original is not None:
                sys.modules["pyatspi"] = original
            else:
                sys.modules.pop("pyatspi", None)


if __name__ == "__main__":
    unittest.main()
