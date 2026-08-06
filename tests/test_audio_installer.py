import unittest

from voiceos.audio import AudioCapabilities, AudioMode, choose_audio_mode
from voiceos.installer import InstallerPlan


class AudioTests(unittest.TestCase):
    def test_certified_hardware_gets_full_duplex(self):
        result = choose_audio_mode(AudioCapabilities(True, True, True, True, True))
        self.assertEqual(result.mode, AudioMode.FULL_DUPLEX)

    def test_unknown_hardware_degrades(self):
        result = choose_audio_mode(AudioCapabilities(True, True))
        self.assertEqual(result.mode, AudioMode.HALF_DUPLEX)
        self.assertIn("Halbduplex", result.announcement)

    def test_no_audio_has_non_voice_fallback(self):
        result = choose_audio_mode(AudioCapabilities(False, False))
        self.assertIn("Tastatur", result.announcement)


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

