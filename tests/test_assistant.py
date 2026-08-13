import unittest

from clausis.assistant import (
    CORRECTION_EXPIRY_GRACE_SECONDS,
    _synchronize_correction_gate,
)
from clausis.audio import ListeningState, LocalActivationController
from clausis.broker import ActionBroker, SafeExecutor
from clausis.capabilities import CapabilityAuthority
from clausis.router import OfflineRouter
from clausis.runtime import RuntimeState, VoiceRuntime


class AssistantCorrectionGateTests(unittest.TestCase):
    def setUp(self):
        self.now = 100.0
        clock = lambda: self.now
        self.activation = LocalActivationController(active_seconds=25, clock=clock)
        self.runtime = VoiceRuntime(
            OfflineRouter(),
            ActionBroker(CapabilityAuthority(b"z" * 32), SafeExecutor(dry_run=True)),
            correction_ttl_seconds=30,
            clock=clock,
        )
        self.activation.ingest("Hallo Clausis")

    def test_correction_keeps_gate_open_through_runtime_ttl_and_grace(self):
        self.runtime.handle_transcript("korrigieren")
        _synchronize_correction_gate(self.runtime, self.activation)
        self.now += 29.5
        gated = self.activation.ingest("lauter")
        self.assertEqual(gated.command, "lauter")
        result = self.runtime.handle_transcript(gated.command)
        self.assertEqual(result.status, "dry_run")
        self.assertFalse(self.runtime.correction_pending)

    def test_repeat_does_not_extend_beyond_original_deadline_plus_grace(self):
        self.runtime.handle_transcript("korrigieren")
        _synchronize_correction_gate(self.runtime, self.activation)
        self.now += 20
        self.runtime.handle_transcript("wiederholen")
        _synchronize_correction_gate(self.runtime, self.activation)

        self.now = 134.9
        self.assertEqual(self.activation.ingest("lauter").command, "lauter")
        result = self.runtime.handle_transcript("lauter")
        self.assertEqual(result.status, "correction_expired")
        self.activation.sleep()
        _synchronize_correction_gate(self.runtime, self.activation)

        self.now = 135.1
        self.assertIsNone(self.activation.ingest("leiser").command)

    def test_sleeping_gate_clears_runtime_correction(self):
        self.runtime.handle_transcript("korrigieren")
        _synchronize_correction_gate(self.runtime, self.activation)
        self.activation.ingest("geh schlafen")
        _synchronize_correction_gate(self.runtime, self.activation)
        self.assertEqual(self.activation.state, ListeningState.SLEEPING)
        self.assertFalse(self.runtime.correction_pending)
        self.assertEqual(self.runtime.state, RuntimeState.IDLE)

    def test_grace_constant_is_small_and_fixed(self):
        self.assertEqual(CORRECTION_EXPIRY_GRACE_SECONDS, 5.0)


if __name__ == "__main__":
    unittest.main()
