import unittest

from clausis.broker import ActionBroker, SafeExecutor
from clausis.capabilities import CapabilityAuthority
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
        self.assertIn(
            "korrigierten", self.runtime.handle_transcript("korrigieren").message
        )

    def test_local_command_routes(self):
        result = self.runtime.handle_transcript("Lauter")
        self.assertEqual(result.status, "dry_run")


if __name__ == "__main__":
    unittest.main()
