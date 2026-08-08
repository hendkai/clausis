import unittest
from dataclasses import replace

from clausis.broker import ActionBroker, SafeExecutor
from clausis.capabilities import CapabilityAuthority
from clausis.executors import SessionExecutor
from clausis.gnome_adapter import (
    DesktopContext,
    GnomeAdapterError,
    GnomeSemanticExecutor,
    PyAtSpiDesktop,
    SemanticControl,
)
from clausis.models import ActionRequest, Risk


class FakeDesktop:
    def __init__(self):
        self.activated = []
        self.cycled = []
        self.closed = []

    def context(self):
        return DesktopContext(
            "Dateien",
            "Persönlicher Ordner",
            "Dokumente",
            "folder",
            (
                SemanticControl(1, "Öffnen", "push button", ("click",)),
                SemanticControl(2, "Abbrechen", "push button", ("click",)),
            ),
        )

    def activate(self, number):
        self.activated.append(number)
        return "Öffnen"

    def cycle_window(self, direction):
        self.cycled.append(direction)
        return "Einstellungen"

    def navigate_back(self):
        return "Zurück"

    def close_application(self, name):
        self.closed.append(name)
        if name == "unbekannt":
            raise GnomeAdapterError("Ich habe kein offenes Fenster für unbekannt gefunden.")
        return "Dateien"


class FakeShell:
    def __init__(self):
        self.calls = []

    def invoke(self, method):
        self.calls.append(method)
        return method


class GnomeAdapterTests(unittest.TestCase):
    def setUp(self):
        self.desktop = FakeDesktop()
        self.shell = FakeShell()
        self.authority = CapabilityAuthority(b"g" * 32)
        executor = SessionExecutor(
            SafeExecutor(dry_run=False), GnomeSemanticExecutor(self.desktop, self.shell)
        )
        self.broker = ActionBroker(self.authority, executor)

    def test_describes_real_semantic_context(self):
        result = self.broker.submit(ActionRequest("desktop.context.describe"))
        self.assertEqual(result.status, "completed")
        self.assertIn("Dateien", result.message)
        self.assertIn("Dokumente", result.message)

    def test_lists_numbered_controls(self):
        result = self.broker.submit(ActionRequest("desktop.controls.list"))
        self.assertIn("Nummer 1: Öffnen", result.message)
        self.assertIn("Nummer 2: Abbrechen", result.message)

    def test_arbitrary_control_activation_requires_confirmation(self):
        request = ActionRequest(
            "desktop.control.activate", target="1", risk=Risk.MEDIUM
        )
        self.assertEqual(self.broker.submit(request).status, "confirmation_required")
        approved = replace(request, capability_token=self.authority.issue(request))
        self.assertEqual(self.broker.submit(approved).status, "completed")
        self.assertEqual(self.desktop.activated, [1])

    def test_invalid_control_number_fails_before_adapter(self):
        request = ActionRequest(
            "desktop.control.activate", target="31", risk=Risk.MEDIUM
        )
        self.assertEqual(self.broker.submit(request).status, "denied")
        self.assertEqual(self.desktop.activated, [])

    def test_window_cycle_uses_semantic_adapter(self):
        result = self.broker.submit(ActionRequest("desktop.window.next"))
        self.assertEqual(result.status, "completed")
        self.assertEqual(self.desktop.cycled, [1])

    def test_non_semantic_action_still_uses_fixed_command_executor(self):
        broker = ActionBroker(
            self.authority,
            SessionExecutor(
                SafeExecutor(dry_run=True), GnomeSemanticExecutor(self.desktop)
            ),
        )
        result = broker.submit(ActionRequest("audio.volume.up"))
        self.assertEqual(result.status, "dry_run")
        self.assertEqual(result.details["argv"][0], "wpctl")

    def test_semantic_mutation_respects_developer_dry_run(self):
        broker = ActionBroker(
            self.authority,
            SessionExecutor(
                SafeExecutor(dry_run=True), GnomeSemanticExecutor(self.desktop)
            ),
        )
        result = broker.submit(ActionRequest("desktop.window.next"))
        self.assertEqual(result.status, "dry_run")
        self.assertEqual(self.desktop.cycled, [])
    def test_closing_an_application_requires_confirmation(self):
        request = ActionRequest("app.close", target="firefox", risk=Risk.MEDIUM)
        self.assertEqual(self.broker.submit(request).status, "confirmation_required")
        self.assertEqual(self.desktop.closed, [])
        approved = replace(request, capability_token=self.authority.issue(request))
        result = self.broker.submit(approved)
        self.assertEqual(result.status, "completed")
        self.assertEqual(self.desktop.closed, ["firefox"])
        self.assertIn("geschlossen", result.message)

    def test_closing_an_unknown_application_fails_honestly(self):
        request = ActionRequest("app.close", target="unbekannt", risk=Risk.MEDIUM)
        approved = replace(request, capability_token=self.authority.issue(request))
        result = self.broker.submit(approved)
        self.assertEqual(result.status, "failed")
        self.assertIn("unbekannt", result.message)

    def test_overview_uses_the_shell_bridge(self):
        result = self.broker.submit(ActionRequest("desktop.overview"))
        self.assertEqual(result.status, "completed")
        self.assertEqual(self.shell.calls, ["ShowOverview"])

    def test_every_shell_action_maps_to_one_extension_method(self):
        from clausis.gnome_adapter import SHELL_ACTIONS

        for action, (method, spoken) in SHELL_ACTIONS.items():
            with self.subTest(action=action):
                self.shell.calls.clear()
                result = self.broker.submit(ActionRequest(action))
                self.assertEqual(result.status, "completed")
                self.assertEqual(self.shell.calls, [method])
                self.assertEqual(result.message, spoken)

    def test_shell_actions_reject_a_target(self):
        from clausis.gnome_adapter import SHELL_ACTIONS

        for action in SHELL_ACTIONS:
            with self.subTest(action=action):
                result = self.broker.submit(ActionRequest(action, target="beliebig"))
                self.assertEqual(result.status, "denied")

    def test_missing_shell_extension_is_reported_and_not_faked(self):
        class BrokenShell:
            def invoke(self, method):
                raise GnomeAdapterError("Die Clausis-Erweiterung für die GNOME-Shell ist nicht aktiv.")

        broker = ActionBroker(
            self.authority,
            SessionExecutor(
                SafeExecutor(dry_run=False), GnomeSemanticExecutor(self.desktop, BrokenShell())
            ),
        )
        result = broker.submit(ActionRequest("desktop.overview"))
        self.assertEqual(result.status, "failed")
        self.assertIn("Erweiterung", result.message)


class CloseActionSafetyTests(unittest.TestCase):
    def test_close_labels_never_include_a_destructive_control(self):
        for label in PyAtSpiDesktop.CLOSE_LABELS | PyAtSpiDesktop.CLOSE_ACTIONS:
            self.assertNotIn("löschen", label)
            self.assertNotIn("delete", label)
            self.assertNotIn("remove", label)


if __name__ == "__main__":
    unittest.main()
