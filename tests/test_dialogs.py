"""Standard GNOME dialogs, driven against a fake accessibility tree.

The refusal for permission and authentication prompts is the point of these
tests: it is the one dialog class that a misheard or injected utterance must
never be able to approve.
"""

from __future__ import annotations

import unittest
from dataclasses import replace

from clausis.broker import ActionBroker, SafeExecutor
from clausis.capabilities import CapabilityAuthority
from clausis.executors import SessionExecutor
from clausis.gnome_adapter import (
    DialogKind,
    GnomeAdapterError,
    GnomeSemanticExecutor,
    PyAtSpiDesktop,
)
from clausis.models import ActionRequest, Origin, Risk
from clausis.policy import evaluate
from clausis.router import OfflineRouter
from tests.test_dictation import (
    STATE_ACTIVE,
    STATE_EDITABLE,
    STATE_FOCUSED,
    STATE_SHOWING,
    DesktopHarness,
    FakeNode,
)


class FakeButton(FakeNode):
    def __init__(self, label, *, accept=True):
        super().__init__(label, "push button", {STATE_SHOWING})
        self.pressed = 0
        self._accepts = accept

    def queryAction(self):
        button = self

        class Action:
            nActions = 1

            def getName(self, index):
                return "click"

            def doAction(self, index):
                if not button._accepts:
                    return False
                button.pressed += 1
                return True

        return Action()


def dialog_tree(title, children, role="dialog"):
    window = FakeNode(title, role, {STATE_SHOWING, STATE_ACTIVE}, children)
    application = FakeNode("Anwendung", "application", set(), [window])
    return FakeNode("desktop", "desktop frame", set(), [application])


class DialogClassificationTests(DesktopHarness):
    def test_save_dialog_is_recognized(self):
        desktop = self.desktop_for(
            dialog_tree(
                "Dokument speichern",
                [
                    FakeNode("Name", "text", {STATE_SHOWING, STATE_FOCUSED, STATE_EDITABLE}),
                    FakeButton("Speichern"),
                    FakeButton("Abbrechen"),
                ],
            )
        )
        context = desktop.describe_dialog()
        self.assertIs(context.kind, DialogKind.FILE_SAVE)
        self.assertEqual(context.affirmative, "Speichern")
        self.assertEqual(context.negative, "Abbrechen")
        self.assertIn("Dateinamen", context.spoken())

    def test_open_dialog_is_recognized(self):
        desktop = self.desktop_for(
            dialog_tree(
                "Datei öffnen",
                [FakeButton("Öffnen"), FakeButton("Abbrechen")],
                role="file chooser",
            )
        )
        context = desktop.describe_dialog()
        self.assertIs(context.kind, DialogKind.FILE_OPEN)
        self.assertIn("Öffnen", context.buttons)

    def test_plain_message_dialog_is_recognized(self):
        desktop = self.desktop_for(
            dialog_tree("Änderungen verwerfen?", [FakeButton("Ja"), FakeButton("Nein")])
        )
        self.assertIs(desktop.describe_dialog().kind, DialogKind.MESSAGE)

    def test_permission_dialog_is_recognized_by_wording(self):
        for title in (
            "Authentifizierung erforderlich",
            "Zugriff erlauben?",
            "Administrator-Kennwort",
            "Authentication Required",
            "Allow access to your location?",
        ):
            with self.subTest(title=title):
                desktop = self.desktop_for(
                    dialog_tree(title, [FakeButton("OK"), FakeButton("Abbrechen")])
                )
                self.assertIs(desktop.describe_dialog().kind, DialogKind.PERMISSION)

    def test_password_field_marks_a_dialog_as_permission(self):
        desktop = self.desktop_for(
            dialog_tree(
                "Weiter",
                [
                    FakeNode("Eingabe", "password text", {STATE_SHOWING}),
                    FakeButton("OK"),
                ],
            )
        )
        self.assertIs(desktop.describe_dialog().kind, DialogKind.PERMISSION)

    def test_no_open_dialog_is_reported(self):
        window = FakeNode("Editor", "frame", {STATE_SHOWING, STATE_ACTIVE}, [])
        application = FakeNode("Editor", "application", set(), [window])
        desktop = self.desktop_for(FakeNode("desktop", "desktop frame", set(), [application]))
        with self.assertRaisesRegex(GnomeAdapterError, "kein Dialog"):
            desktop.describe_dialog()


class DialogActionTests(DesktopHarness):
    def test_affirmative_button_is_pressed(self):
        save = FakeButton("Speichern")
        desktop = self.desktop_for(
            dialog_tree("Dokument speichern", [save, FakeButton("Abbrechen")])
        )
        self.assertEqual(desktop.accept_dialog(), "Speichern")
        self.assertEqual(save.pressed, 1)

    def test_negative_button_is_pressed(self):
        cancel = FakeButton("Abbrechen")
        desktop = self.desktop_for(dialog_tree("Datei öffnen", [FakeButton("Öffnen"), cancel]))
        self.assertEqual(desktop.cancel_dialog(), "Abbrechen")
        self.assertEqual(cancel.pressed, 1)

    def test_permission_dialog_is_never_accepted_by_voice(self):
        allow = FakeButton("OK")
        desktop = self.desktop_for(
            dialog_tree("Authentifizierung erforderlich", [allow, FakeButton("Abbrechen")])
        )
        with self.assertRaisesRegex(GnomeAdapterError, "Tastatur oder Orca"):
            desktop.accept_dialog()
        self.assertEqual(allow.pressed, 0)

    def test_permission_dialog_may_still_be_cancelled(self):
        # Declining is always safe and must stay reachable by voice, otherwise
        # a permission prompt would trap a voice-only user.
        cancel = FakeButton("Abbrechen")
        desktop = self.desktop_for(
            dialog_tree("Zugriff erlauben?", [FakeButton("Erlauben"), cancel])
        )
        self.assertEqual(desktop.cancel_dialog(), "Abbrechen")
        self.assertEqual(cancel.pressed, 1)

    def test_missing_button_is_reported_honestly(self):
        desktop = self.desktop_for(dialog_tree("Hinweis", [FakeButton("Mehr erfahren")]))
        with self.assertRaisesRegex(GnomeAdapterError, "Zustimmen"):
            desktop.accept_dialog()
        with self.assertRaisesRegex(GnomeAdapterError, "Abbrechen"):
            desktop.cancel_dialog()

    def test_rejected_button_press_is_not_reported_as_success(self):
        desktop = self.desktop_for(
            dialog_tree("Dokument speichern", [FakeButton("Speichern", accept=False)])
        )
        with self.assertRaisesRegex(GnomeAdapterError, "abgelehnt"):
            desktop.accept_dialog()


class DialogPolicyTests(unittest.TestCase):
    def setUp(self):
        self.authority = CapabilityAuthority(b"q" * 32)

    def test_accepting_needs_confirmation_but_cancelling_does_not(self):
        self.assertTrue(evaluate(ActionRequest("dialog.accept", risk=Risk.MEDIUM)).confirmation_required)
        self.assertFalse(evaluate(ActionRequest("dialog.cancel")).confirmation_required)
        self.assertFalse(evaluate(ActionRequest("dialog.describe")).confirmation_required)

    def test_agent_cannot_accept_a_dialog_without_confirmation(self):
        decision = evaluate(ActionRequest("dialog.accept", risk=Risk.MEDIUM, origin=Origin.HERMES))
        self.assertTrue(decision.confirmation_required)

    def test_dialog_actions_accept_no_target(self):
        for action in ("dialog.describe", "dialog.accept", "dialog.cancel"):
            with self.subTest(action=action):
                with self.assertRaises(ValueError):
                    evaluate(ActionRequest(action, "Speichern", risk=Risk.MEDIUM))

    def test_spoken_commands_route_to_the_dialog_actions(self):
        router = OfflineRouter()
        self.assertEqual(router.route("was fragt der Dialog").action, "dialog.describe")
        self.assertEqual(router.route("Dialog bestätigen").action, "dialog.accept")
        self.assertEqual(router.route("Dialog abbrechen").action, "dialog.cancel")
        # A bare "abbrechen" must stay the voice-dialog cancel, not a click.
        self.assertEqual(router.route("abbrechen").action, "voice.cancel")

    def test_accept_is_withheld_until_confirmed(self):
        class Recorder:
            def __init__(self):
                self.accepted = 0

            def accept_dialog(self):
                self.accepted += 1
                return "Speichern"

        recorder = Recorder()
        broker = ActionBroker(
            self.authority,
            SessionExecutor(SafeExecutor(dry_run=False), GnomeSemanticExecutor(recorder)),
        )
        request = ActionRequest("dialog.accept", risk=Risk.MEDIUM)
        self.assertEqual(broker.submit(request).status, "confirmation_required")
        self.assertEqual(recorder.accepted, 0)
        approved = replace(request, capability_token=self.authority.issue(request))
        self.assertEqual(broker.submit(approved).status, "completed")
        self.assertEqual(recorder.accepted, 1)


class PermissionWordCoverageTests(unittest.TestCase):
    def test_permission_words_cover_both_languages(self):
        words = PyAtSpiDesktop.PERMISSION_WORDS
        for expected in ("passwort", "password", "authentifiz", "authentic", "polkit"):
            self.assertIn(expected, words)

    def test_permission_words_are_lower_case_for_casefold_matching(self):
        for word in PyAtSpiDesktop.PERMISSION_WORDS:
            self.assertEqual(word, word.casefold())


if __name__ == "__main__":
    unittest.main()
