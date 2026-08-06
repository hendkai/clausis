import tempfile
import unittest
from dataclasses import replace
from datetime import timedelta
from pathlib import Path

from clausis.audit import AuditLog
from clausis.broker import ActionBroker, SafeExecutor
from clausis.capabilities import CapabilityAuthority
from clausis.models import ActionRequest, Origin, Risk, utc_now


class BrokerTests(unittest.TestCase):
    def setUp(self):
        self.authority = CapabilityAuthority(b"c" * 32)
        self.broker = ActionBroker(self.authority, SafeExecutor(dry_run=True))

    def test_safe_action_dry_runs(self):
        result = self.broker.submit(ActionRequest("audio.volume.up"))
        self.assertEqual(result.status, "dry_run")
        self.assertEqual(result.details["argv"][-1], "5%+")

    def test_risky_action_requires_confirmation(self):
        request = ActionRequest("network.wifi.disable", risk=Risk.MEDIUM)
        result = self.broker.submit(request)
        self.assertEqual(result.status, "confirmation_required")

    def test_confirmed_action_runs(self):
        request = ActionRequest("network.wifi.disable", origin=Origin.HERMES, risk=Risk.MEDIUM)
        token = self.authority.issue(request)
        result = self.broker.submit(replace(request, capability_token=token))
        self.assertEqual(result.status, "dry_run")

    def test_replayed_action_denied(self):
        request = ActionRequest("network.wifi.disable", origin=Origin.HERMES, risk=Risk.MEDIUM)
        approved = replace(request, capability_token=self.authority.issue(request))
        self.assertEqual(self.broker.submit(approved).status, "dry_run")
        self.assertEqual(self.broker.submit(approved).status, "denied")

    def test_unsupported_platform_adapter_fails_closed(self):
        request = ActionRequest("app.close", "firefox", risk=Risk.MEDIUM)
        approved = replace(request, capability_token=self.authority.issue(request))
        self.assertEqual(self.broker.submit(approved).status, "failed")

    def test_audit_is_written_and_valid(self):
        with tempfile.TemporaryDirectory() as directory:
            audit = AuditLog(Path(directory) / "audit.jsonl", b"d" * 32)
            broker = ActionBroker(self.authority, SafeExecutor(dry_run=True), audit_log=audit)
            broker.submit(ActionRequest("audio.volume.up"))
            self.assertTrue(audit.verify())

    def test_expired_low_risk_request_is_denied(self):
        request = ActionRequest(
            "audio.volume.up",
            expires_at=(utc_now() - timedelta(seconds=1)).isoformat(),
        )
        self.assertEqual(self.broker.submit(request).status, "denied")


if __name__ == "__main__":
    unittest.main()
