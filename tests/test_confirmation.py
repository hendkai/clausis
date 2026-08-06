import unittest

from clausis.capabilities import CapabilityAuthority
from clausis.confirmation import PinVerifier, TrustedConfirmer
from clausis.models import ActionRequest, Origin, Risk


class ConfirmationTests(unittest.TestCase):
    def setUp(self):
        self.authority = CapabilityAuthority(b"b" * 32)
        self.pin = PinVerifier.enroll("123456")
        self.confirmer = TrustedConfirmer(
            self.authority,
            self.pin,
            words=("eins", "zwei", "drei", "vier", "fuenf", "sechs", "sieben", "acht"),
        )
        self.request = ActionRequest(
            "system.reboot", origin=Origin.HERMES, risk=Risk.CRITICAL, reversible=False
        )

    def test_approval_issues_valid_token(self):
        pending = self.confirmer.begin(self.request)
        token = self.confirmer.approve(pending.confirmation_id, pending.phrase, "123456")
        self.authority.verify(token, self.request)

    def test_wrong_phrase_rejected(self):
        pending = self.confirmer.begin(self.request)
        with self.assertRaisesRegex(ValueError, "phrase"):
            self.confirmer.approve(pending.confirmation_id, "wrong phrase", "123456")

    def test_wrong_pin_rejected(self):
        pending = self.confirmer.begin(self.request)
        with self.assertRaisesRegex(ValueError, "PIN"):
            self.confirmer.approve(pending.confirmation_id, pending.phrase, "654321")

    def test_three_attempt_limit(self):
        pending = self.confirmer.begin(self.request)
        for _ in range(3):
            with self.assertRaises(ValueError):
                self.confirmer.approve(pending.confirmation_id, "wrong", "123456")
        with self.assertRaisesRegex(ValueError, "too many"):
            self.confirmer.approve(pending.confirmation_id, "wrong", "123456")

    def test_pin_export_round_trip(self):
        exported = self.pin.export()
        restored = PinVerifier.from_hex(exported["salt"], exported["digest"])
        self.assertTrue(restored.verify("123456"))
        self.assertFalse(restored.verify("000000"))

    def test_short_pin_rejected(self):
        with self.assertRaises(ValueError):
            PinVerifier.enroll("1234")


if __name__ == "__main__":
    unittest.main()

