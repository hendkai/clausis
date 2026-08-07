import unittest

from clausis.capabilities import CapabilityAuthority
from clausis.confirmation import (
    ConfirmationResponse,
    PinVerifier,
    TrustedConfirmer,
    canonicalize_untrusted_request,
)
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

    def test_trusted_input_is_the_only_production_approval_path(self):
        class LocalInput:
            seen_summary = ""
            seen_challenge = ""

            def collect(inner_self, summary, challenge):
                inner_self.seen_summary = summary
                inner_self.seen_challenge = challenge
                return ConfirmationResponse(challenge + ".", "123456")

        local_input = LocalInput()
        approved = self.confirmer.approve_from_trusted_input(
            self.request, local_input
        )
        self.assertIn(local_input.seen_challenge, local_input.seen_summary)
        self.assertIsNotNone(approved.capability_token)
        self.authority.verify(approved.capability_token, self.request)

    def test_caller_cannot_smuggle_a_capability_into_confirmation(self):
        forged = ActionRequest(
            "system.reboot",
            origin=Origin.LOCAL_VOICE,
            risk=Risk.CRITICAL,
            reversible=False,
            capability_token="forged",
        )
        with self.assertRaisesRegex(ValueError, "caller-supplied"):
            canonicalize_untrusted_request(forged)

    def test_public_bus_origin_is_never_trusted_local_input(self):
        canonical = canonicalize_untrusted_request(self.request)
        self.assertEqual(canonical.origin, Origin.HERMES)

    def test_low_risk_action_cannot_misuse_confirmation_endpoint(self):
        class UnusedInput:
            def collect(self, summary, challenge):
                raise AssertionError("must not ask the user")

        with self.assertRaisesRegex(ValueError, "does not require"):
            self.confirmer.approve_from_trusted_input(
                ActionRequest("audio.volume.up"), UnusedInput()
            )


if __name__ == "__main__":
    unittest.main()
