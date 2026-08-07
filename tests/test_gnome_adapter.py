import unittest
from dataclasses import replace

from clausis.broker import ActionBroker, SafeExecutor
from clausis.capabilities import CapabilityAuthority
from clausis.gnome_adapter import (
    DesktopContext,
    GnomeSemanticExecutor,
    SemanticControl,
    SessionExecutor,
)
from clausis.models import ActionRequest, Risk


class FakeDesktop:
    def __init__(self):
        self.activated = []
        self.cycled = []

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


class GnomeAdapterTests(unittest.TestCase):
    def setUp(self):
        self.desktop = FakeDesktop()
        self.authority = CapabilityAuthority(b"g" * 32)
        executor = SessionExecutor(
            SafeExecutor(dry_run=False), GnomeSemanticExecutor(self.desktop)
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


if __name__ == "__main__":
    unittest.main()
