import unittest

from clausis.models import ActionRequest, Origin, Risk
from clausis.policy import evaluate


class PolicyTests(unittest.TestCase):
    def test_safe_local_action_needs_no_confirmation(self):
        decision = evaluate(ActionRequest("audio.volume.up"))
        self.assertFalse(decision.confirmation_required)

    def test_hermes_action_is_tainted(self):
        decision = evaluate(ActionRequest("audio.volume.up", origin=Origin.HERMES))
        self.assertTrue(decision.confirmation_required)

    def test_external_content_action_is_tainted(self):
        decision = evaluate(ActionRequest("file.open", "/tmp/a", origin=Origin.EXTERNAL_CONTENT))
        self.assertTrue(decision.confirmation_required)

    def test_risk_cannot_be_understated(self):
        with self.assertRaisesRegex(ValueError, "understate"):
            evaluate(ActionRequest("system.reboot", risk=Risk.LOW, reversible=False))

    def test_irreversible_cannot_be_marked_reversible(self):
        with self.assertRaisesRegex(ValueError, "irreversible"):
            evaluate(ActionRequest("system.reboot", risk=Risk.CRITICAL, reversible=True))

    def test_shell_like_app_identifier_rejected(self):
        with self.assertRaises(ValueError):
            evaluate(ActionRequest("app.launch", "firefox;rm"))

    def test_relative_path_rejected(self):
        with self.assertRaisesRegex(ValueError, "absolute"):
            evaluate(ActionRequest("file.open", "relative.txt"))

    def test_unknown_action_rejected(self):
        with self.assertRaisesRegex(ValueError, "allowlisted"):
            evaluate(ActionRequest("shell.execute"))

    def test_volume_range(self):
        with self.assertRaises(ValueError):
            evaluate(ActionRequest("audio.volume.set", arguments={"percent": 999}))


if __name__ == "__main__":
    unittest.main()

