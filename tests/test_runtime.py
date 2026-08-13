import unittest

from clausis.broker import ActionBroker, SafeExecutor
from clausis.capabilities import CapabilityAuthority
from clausis.models import ActionResult
from clausis.router import OfflineRouter
from clausis.runtime import RuntimeState, VoiceRuntime


class RuntimeTests(unittest.TestCase):
    def setUp(self):
        self.runtime = VoiceRuntime(
            OfflineRouter(),
            ActionBroker(CapabilityAuthority(b"r" * 32), SafeExecutor(dry_run=True)),
        )

    def test_stop_never_calls_broker(self):
        result = self.runtime.handle_transcript("Stopp Hermes")
        self.assertEqual(result.status, "stopped")
        self.assertEqual(self.runtime.state, RuntimeState.STOPPED)

    def test_unmatched_offline_is_explicit(self):
        result = self.runtime.handle_transcript("Erkläre Quantenphysik")
        self.assertEqual(result.status, "offline_unmatched")

    def test_repeat_returns_last_actual_result_without_broker_call(self):
        first = self.runtime.handle_transcript("lauter")
        repeated = self.runtime.handle_transcript("wiederholen")
        self.assertEqual(repeated.status, "repeated")
        self.assertEqual(repeated.message, first.message)

    def test_cancel_and_correct_are_local(self):
        self.assertIn(
            "abgebrochen", self.runtime.handle_transcript("abbrechen").message
        )
        result = self.runtime.handle_transcript("korrigieren")
        self.assertEqual(result.status, "correction_requested")
        self.assertIn("korrigierten", result.message)
        self.assertIn("nicht automatisch rückgängig", result.message)
        self.assertTrue(self.runtime.correction_pending)
        self.assertEqual(self.runtime.state, RuntimeState.CORRECTING)

    def test_correction_slot_dispatches_exactly_one_replacement_normally(self):
        self.runtime.handle_transcript("korrigieren")
        result = self.runtime.handle_transcript("lauter")
        self.assertEqual(result.status, "dry_run")
        self.assertEqual(result.action, "audio.volume.up")
        self.assertFalse(self.runtime.correction_pending)
        self.assertEqual(self.runtime.state, RuntimeState.IDLE)

        unmatched = self.runtime.handle_transcript("das ist weiter unbekannt")
        self.assertEqual(unmatched.status, "offline_unmatched")
        self.assertFalse(self.runtime.correction_pending)

    def test_repeat_keeps_correction_slot_and_cancel_clears_it(self):
        prompt = self.runtime.handle_transcript("korrigieren")
        repeated = self.runtime.handle_transcript("wiederholen")
        self.assertEqual(repeated.status, "repeated")
        self.assertEqual(repeated.message, prompt.message)
        self.assertTrue(self.runtime.correction_pending)
        self.assertEqual(self.runtime.state, RuntimeState.CORRECTING)

        cancelled = self.runtime.handle_transcript("abbrechen")
        self.assertIn("abgebrochen", cancelled.message)
        self.assertFalse(self.runtime.correction_pending)
        self.assertEqual(self.runtime.state, RuntimeState.IDLE)

    def test_repeated_correct_reprompts_without_nesting_and_stop_clears_slot(self):
        first = self.runtime.handle_transcript("korrigieren")
        second = self.runtime.handle_transcript("korrigieren")
        self.assertEqual(second.status, "correction_requested")
        self.assertEqual(second.message, first.message)
        self.assertTrue(self.runtime.correction_pending)

        stopped = self.runtime.handle_transcript("Stopp Hermes")
        self.assertEqual(stopped.status, "stopped")
        self.assertFalse(self.runtime.correction_pending)
        self.assertEqual(self.runtime.state, RuntimeState.STOPPED)

    def test_unmatched_replacement_consumes_slot_before_optional_fallback(self):
        seen = []
        runtime = VoiceRuntime(
            OfflineRouter(),
            ActionBroker(CapabilityAuthority(b"s" * 32), SafeExecutor(dry_run=True)),
            hermes_fallback=lambda text: (
                seen.append(text)
                or ActionResult("completed", "fallback", "hermes.reply")
            ),
        )
        runtime.handle_transcript("korrigieren")
        result = runtime.handle_transcript("eine freie frage")
        self.assertEqual(result.action, "hermes.reply")
        self.assertEqual(seen, ["eine freie frage"])
        self.assertFalse(runtime.correction_pending)

    def test_correction_slot_expires_and_discards_first_late_command(self):
        now = [100.0]
        runtime = VoiceRuntime(
            OfflineRouter(),
            ActionBroker(CapabilityAuthority(b"t" * 32), SafeExecutor(dry_run=True)),
            correction_ttl_seconds=10,
            clock=lambda: now[0],
        )
        prompt = runtime.handle_transcript("korrigieren")
        self.assertIn("10 Sekunden", prompt.message)
        now[0] = 110.0
        expired = runtime.handle_transcript("lauter")
        self.assertEqual(expired.status, "correction_expired")
        self.assertIn("nicht ausgeführt", expired.message)
        self.assertFalse(runtime.correction_pending)
        self.assertEqual(runtime.state, RuntimeState.IDLE)

        # The discarded utterance is not replayed; a new normal command is
        # required after the expiry notification.
        self.assertEqual(runtime.handle_transcript("lauter").status, "dry_run")

    def test_correction_replacement_just_before_deadline_is_accepted(self):
        now = [50.0]
        runtime = VoiceRuntime(
            OfflineRouter(),
            ActionBroker(CapabilityAuthority(b"u" * 32), SafeExecutor(dry_run=True)),
            correction_ttl_seconds=5,
            clock=lambda: now[0],
        )
        runtime.handle_transcript("korrigieren")
        now[0] = 54.999
        result = runtime.handle_transcript("lauter")
        self.assertEqual(result.status, "dry_run")
        self.assertFalse(runtime.correction_pending)

    def test_stop_cancel_and_new_correction_take_priority_after_expiry(self):
        def make_runtime(key):
            now = [0.0]
            runtime = VoiceRuntime(
                OfflineRouter(),
                ActionBroker(CapabilityAuthority(key * 32), SafeExecutor(dry_run=True)),
                correction_ttl_seconds=5,
                clock=lambda: now[0],
            )
            runtime.handle_transcript("korrigieren")
            now[0] = 6.0
            return runtime

        stopped = make_runtime(b"v")
        self.assertEqual(stopped.handle_transcript("Stopp Hermes").status, "stopped")
        self.assertFalse(stopped.correction_pending)

        cancelled = make_runtime(b"w")
        self.assertEqual(cancelled.handle_transcript("abbrechen").action, "voice.cancel")
        self.assertFalse(cancelled.correction_pending)

        restarted = make_runtime(b"x")
        result = restarted.handle_transcript("korrigieren")
        self.assertEqual(result.status, "correction_requested")
        self.assertTrue(restarted.correction_pending)
        self.assertEqual(restarted.state, RuntimeState.CORRECTING)

    def test_correction_ttl_is_finite_and_bounded(self):
        for ttl in (None, "invalid", float("nan"), float("inf"), 4.9, 120.1):
            with self.assertRaises(ValueError):
                VoiceRuntime(
                    OfflineRouter(),
                    ActionBroker(
                        CapabilityAuthority(b"y" * 32), SafeExecutor(dry_run=True)
                    ),
                    correction_ttl_seconds=ttl,
                )

    def test_local_command_routes(self):
        result = self.runtime.handle_transcript("Lauter")
        self.assertEqual(result.status, "dry_run")


if __name__ == "__main__":
    unittest.main()
