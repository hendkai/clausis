import unittest

from clausis.capabilities import CapabilityAuthority, CapabilityError
from clausis.models import ActionRequest, Origin, Risk


class CapabilityTests(unittest.TestCase):
    def setUp(self):
        self.authority = CapabilityAuthority(b"a" * 32)
        self.request = ActionRequest(
            "network.wifi.disable", origin=Origin.HERMES, risk=Risk.MEDIUM
        )

    def test_issue_and_verify_once(self):
        token = self.authority.issue(self.request)
        self.authority.verify(token, self.request)
        with self.assertRaisesRegex(CapabilityError, "consumed"):
            self.authority.verify(token, self.request)

    def test_token_cannot_change_target(self):
        request = ActionRequest("file.move_to_trash", "/tmp/a", origin=Origin.HERMES, risk=Risk.HIGH)
        token = self.authority.issue(request)
        changed = ActionRequest("file.move_to_trash", "/tmp/b", origin=Origin.HERMES, risk=Risk.HIGH)
        with self.assertRaisesRegex(CapabilityError, "not valid"):
            self.authority.verify(token, changed)

    def test_token_cannot_change_arguments(self):
        request = ActionRequest("audio.volume.set", arguments={"percent": 20}, origin=Origin.HERMES)
        token = self.authority.issue(request)
        changed = ActionRequest("audio.volume.set", arguments={"percent": 100}, origin=Origin.HERMES)
        with self.assertRaises(CapabilityError):
            self.authority.verify(token, changed)

    def test_tamper_rejected(self):
        token = self.authority.issue(self.request)
        tampered = ("A" if token[0] != "A" else "B") + token[1:]
        with self.assertRaises(CapabilityError):
            self.authority.verify(tampered, self.request)

    def test_ttl_bounds(self):
        with self.assertRaises(ValueError):
            self.authority.issue(self.request, ttl_seconds=121)


if __name__ == "__main__":
    unittest.main()

