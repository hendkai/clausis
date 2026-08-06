import unittest

from voiceos.broker import ActionBroker, SafeExecutor
from voiceos.capabilities import CapabilityAuthority
from voiceos.router import OfflineRouter
from voiceos.runtime import RuntimeState, VoiceRuntime


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

    def test_local_command_routes(self):
        result = self.runtime.handle_transcript("Lauter")
        self.assertEqual(result.status, "dry_run")


if __name__ == "__main__":
    unittest.main()

