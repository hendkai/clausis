"""Clipboard actions and the accessibility switches.

Pasting reuses the dictation refusals on purpose: clipboard content can be
placed there by any other process, so a hijacked clipboard must not become a
command line.
"""

from __future__ import annotations

import unittest

from clausis.broker import ActionBroker, SafeExecutor
from clausis.capabilities import CapabilityAuthority
from clausis.executors import SessionExecutor
from clausis.gnome_adapter import (
    CLIPBOARD_READ_METHOD,
    GnomeAdapterError,
    GnomeSemanticExecutor,
    PyAtSpiDesktop,
)
from clausis.models import ActionRequest
from clausis.policy import ACTION_POLICIES, evaluate
from clausis.router import OfflineRouter
from tests.test_dictation import (
    STATE_EDITABLE,
    STATE_FOCUSED,
    STATE_PROTECTED,
    STATE_SHOWING,
    DesktopHarness,
    FakeNode,
    build_desktop,
    build_terminal,
)


class ActionNode(FakeNode):
    """A node that publishes the accessible actions given to it."""

    def __init__(self, name, role, states, actions, content="", **kwargs):
        super().__init__(name, role, states, content=content, **kwargs)
        self.available = tuple(actions)
        self.performed = []

    def queryAction(self):
        node = self

        class Action:
            nActions = len(node.available)

            def getName(self, index):
                return node.available[index]

            def doAction(self, index):
                node.performed.append(node.available[index])
                return True

        return Action()


class ClipboardAdapterTests(DesktopHarness):
    def test_copy_uses_the_widget_action(self):
        field = ActionNode(
            "Notiz", "text", {STATE_SHOWING, STATE_FOCUSED, STATE_EDITABLE}, ("copy", "paste")
        )
        desktop = self.desktop_for(build_desktop(field))
        self.assertEqual(desktop.copy_selection(), "Notiz")
        self.assertEqual(field.performed, ["copy"])

    def test_copy_from_a_password_field_is_refused(self):
        field = ActionNode(
            "Passwort", "password text", {STATE_SHOWING, STATE_FOCUSED, STATE_EDITABLE}, ("copy",)
        )
        desktop = self.desktop_for(build_desktop(field))
        with self.assertRaisesRegex(GnomeAdapterError, "Passwortfeld"):
            desktop.copy_selection()
        self.assertEqual(field.performed, [])

    def test_copy_from_a_protected_widget_is_refused(self):
        field = ActionNode(
            "PIN", "text", {STATE_SHOWING, STATE_FOCUSED, STATE_EDITABLE, STATE_PROTECTED}, ("copy",)
        )
        desktop = self.desktop_for(build_desktop(field))
        with self.assertRaises(GnomeAdapterError):
            desktop.copy_selection()
        self.assertEqual(field.performed, [])

    def test_paste_into_a_terminal_is_refused(self):
        field = ActionNode(
            "", "terminal", {STATE_SHOWING, STATE_FOCUSED, STATE_EDITABLE}, ("paste",)
        )
        desktop = self.desktop_for(build_terminal(field))
        with self.assertRaisesRegex(GnomeAdapterError, "Terminal"):
            desktop.paste()
        self.assertEqual(field.performed, [])

    def test_paste_into_a_password_field_is_refused(self):
        field = ActionNode(
            "Passwort", "password text", {STATE_SHOWING, STATE_FOCUSED, STATE_EDITABLE}, ("paste",)
        )
        desktop = self.desktop_for(build_desktop(field))
        with self.assertRaisesRegex(GnomeAdapterError, "Passwortfeld"):
            desktop.paste()
        self.assertEqual(field.performed, [])

    def test_paste_reports_the_resulting_field_content(self):
        field = ActionNode(
            "Notiz",
            "text",
            {STATE_SHOWING, STATE_FOCUSED, STATE_EDITABLE},
            ("paste",),
            content="eingefügter Text",
        )
        desktop = self.desktop_for(build_desktop(field))
        self.assertEqual(desktop.paste(), "eingefügter Text")
        self.assertEqual(field.performed, ["paste"])

    def test_widget_without_a_paste_action_is_reported(self):
        field = ActionNode(
            "Notiz", "text", {STATE_SHOWING, STATE_FOCUSED, STATE_EDITABLE}, ("copy",)
        )
        desktop = self.desktop_for(build_desktop(field))
        with self.assertRaisesRegex(GnomeAdapterError, "Einfügen"):
            desktop.paste()

    def test_german_action_names_are_accepted(self):
        field = ActionNode(
            "Notiz", "text", {STATE_SHOWING, STATE_FOCUSED, STATE_EDITABLE}, ("Kopieren",)
        )
        desktop = self.desktop_for(build_desktop(field))
        desktop.copy_selection()
        self.assertEqual(field.performed, ["Kopieren"])


class ClipboardReadTests(unittest.TestCase):
    class FakeShell:
        def __init__(self, text):
            self.text = text
            self.calls = []

        def invoke(self, method):
            self.calls.append(method)
            return self.text

    def _broker(self, shell):
        return ActionBroker(
            CapabilityAuthority(b"c" * 32),
            SessionExecutor(SafeExecutor(dry_run=False), GnomeSemanticExecutor(None, shell)),
        )

    def test_clipboard_content_is_spoken(self):
        shell = self.FakeShell("Termin am Freitag")
        result = self._broker(shell).submit(ActionRequest("clipboard.read"))
        self.assertEqual(result.status, "completed")
        self.assertIn("Termin am Freitag", result.message)
        self.assertEqual(shell.calls, [CLIPBOARD_READ_METHOD])

    def test_empty_clipboard_is_announced(self):
        result = self._broker(self.FakeShell("   ")).submit(ActionRequest("clipboard.read"))
        self.assertIn("leer", result.message)

    def test_read_needs_no_confirmation(self):
        self.assertFalse(evaluate(ActionRequest("clipboard.read")).confirmation_required)


class AccessibilitySwitchTests(unittest.TestCase):
    SWITCHES = (
        ("a11y.keyboard.enable", "screen-keyboard-enabled", "true"),
        ("a11y.keyboard.disable", "screen-keyboard-enabled", "false"),
        ("a11y.magnifier.enable", "screen-magnifier-enabled", "true"),
        ("a11y.magnifier.disable", "screen-magnifier-enabled", "false"),
        ("a11y.screenreader.enable", "screen-reader-enabled", "true"),
        ("a11y.screenreader.disable", "screen-reader-enabled", "false"),
    )

    def test_each_switch_is_a_fully_specified_fixed_vector(self):
        for action, key, value in self.SWITCHES:
            with self.subTest(action=action):
                command = ACTION_POLICIES[action].command
                self.assertEqual(
                    list(command),
                    ["gsettings", "set", "org.gnome.desktop.a11y.applications", key, value],
                )

    def test_switches_take_no_target(self):
        for action, _key, _value in self.SWITCHES:
            with self.subTest(action=action):
                with self.assertRaises(ValueError):
                    evaluate(ActionRequest(action, "org.gnome.desktop.interface"))

    def test_switches_need_no_confirmation(self):
        for action, _key, _value in self.SWITCHES:
            with self.subTest(action=action):
                self.assertFalse(evaluate(ActionRequest(action)).confirmation_required)

    def test_spoken_commands_reach_the_switches(self):
        router = OfflineRouter()
        expected = {
            "Bildschirmtastatur an": "a11y.keyboard.enable",
            "Bildschirmtastatur aus": "a11y.keyboard.disable",
            "Lupe an": "a11y.magnifier.enable",
            "Bildschirmlupe aus": "a11y.magnifier.disable",
            "Orca an": "a11y.screenreader.enable",
            "screen reader off": "a11y.screenreader.disable",
        }
        for transcript, action in expected.items():
            with self.subTest(transcript=transcript):
                self.assertEqual(router.route(transcript).action, action)

    def test_clipboard_commands_route(self):
        router = OfflineRouter()
        self.assertEqual(router.route("kopieren").action, "clipboard.copy")
        self.assertEqual(router.route("einfügen").action, "clipboard.paste")
        self.assertEqual(router.route("was ist in der Zwischenablage").action, "clipboard.read")


class ClipboardActionNameTests(unittest.TestCase):
    def test_action_names_stay_lower_case_for_matching(self):
        for name in PyAtSpiDesktop.COPY_ACTIONS | PyAtSpiDesktop.PASTE_ACTIONS:
            self.assertEqual(name, name.casefold())


if __name__ == "__main__":
    unittest.main()
