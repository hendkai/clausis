import unittest

from clausis.audio import (
    AudioCapabilities,
    AudioMode,
    ListeningState,
    LocalActivationController,
    choose_audio_mode,
)
from clausis.installer import InstallerPlan


class AudioTests(unittest.TestCase):
    def test_certified_hardware_stays_half_duplex_without_interrupt_detector(self):
        result = choose_audio_mode(AudioCapabilities(True, True, True, True, True))
        self.assertEqual(result.mode, AudioMode.HALF_DUPLEX)
        self.assertFalse(result.barge_in)
        self.assertIn("Unterbrechungsdetektor", result.announcement)

    def test_unknown_hardware_degrades(self):
        result = choose_audio_mode(AudioCapabilities(True, True))
        self.assertEqual(result.mode, AudioMode.HALF_DUPLEX)
        self.assertIn("Halbduplex", result.announcement)
        self.assertFalse(result.barge_in)

    def test_no_audio_has_non_voice_fallback(self):
        result = choose_audio_mode(AudioCapabilities(False, False))
        self.assertIn("Tastatur", result.announcement)


class LocalActivationTests(unittest.TestCase):
    def setUp(self):
        self.now = 100.0
        self.controller = LocalActivationController(
            active_seconds=10.0, clock=lambda: self.now
        )

    def test_discards_background_speech_until_wake_word(self):
        result = self.controller.ingest("Lösche bitte alle Dateien")
        self.assertIsNone(result.command)
        self.assertEqual(self.controller.state, ListeningState.SLEEPING)

    def test_wake_word_and_command_can_share_one_utterance(self):
        result = self.controller.ingest("Hallo Clausis, Lauter!")
        self.assertEqual(result.command, "lauter")
        self.assertEqual(self.controller.state, ListeningState.AWAKE)

    def test_follow_up_is_accepted_only_inside_activation_window(self):
        self.controller.ingest("Clausis")
        self.assertEqual(self.controller.ingest("öffne firefox").command, "öffne firefox")
        self.now += 11.0
        self.assertIsNone(self.controller.ingest("öffne terminal").command)

    def test_stop_is_local_and_works_while_sleeping(self):
        result = self.controller.ingest("Stopp Clausis")
        self.assertTrue(result.stopped)
        self.assertEqual(result.command, "stopp hermes")
        self.assertEqual(self.controller.state, ListeningState.STOPPED)

    def test_sleep_phrase_closes_activation_window(self):
        self.controller.ingest("Hallo Clausis")
        result = self.controller.ingest("geh schlafen")
        self.assertIsNone(result.command)
        self.assertEqual(self.controller.state, ListeningState.SLEEPING)

    def test_text_fallback_can_bypass_wake_word(self):
        result = self.controller.ingest("systemstatus", bypass_wake=True)
        self.assertEqual(result.command, "systemstatus")


class InstallerPlanTests(unittest.TestCase):
    def valid_plan(self, **changes):
        values = dict(
            locale="de_DE.UTF-8",
            timezone="Europe/Berlin",
            username="anna",
            disk_id="/dev/nvme0n1",
            erase_disk=True,
            recovery_key_exported=True,
        )
        values.update(changes)
        return InstallerPlan(**values)

    def test_valid_plan_summary(self):
        self.assertIn("vollständig gelöscht", self.valid_plan().spoken_summary())

    def test_cloud_requires_consent(self):
        with self.assertRaisesRegex(ValueError, "consent"):
            self.valid_plan(hermes_provider="nous").validate()

    def test_encryption_requires_recovery_export(self):
        with self.assertRaisesRegex(ValueError, "recovery"):
            self.valid_plan(recovery_key_exported=False).validate()

    def test_secret_metadata_rejected(self):
        with self.assertRaisesRegex(ValueError, "secrets"):
            self.valid_plan(metadata={"password": "bad"}).validate()


if __name__ == "__main__":
    unittest.main()
