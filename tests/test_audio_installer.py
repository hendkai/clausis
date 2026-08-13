from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from clausis.audio import (
    AudioCapabilities,
    AudioMode,
    ListeningState,
    LocalActivationController,
    choose_audio_mode,
)
from clausis.installer import (
    InstallConfirmationChallenge,
    InstallDisk,
    InstallerPlan,
    calamares_prewrite_summary,
    discard_staged_recovery_key,
    eligible_install_disks,
    generate_recovery_key,
    guard_calamares_erase_transaction,
    parse_lsblk_inventory,
    stage_recovery_key,
)


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

    def test_bounded_follow_up_extension_does_not_shorten_existing_window(self):
        self.controller.ingest("Hallo Clausis")
        self.controller.extend_awake_for(30)
        self.now += 29
        self.assertEqual(self.controller.ingest("lauter").command, "lauter")

        # A shorter extension cannot pull an existing deadline backwards.
        self.controller.extend_awake_for(1)
        self.now += 1.5
        self.assertEqual(self.controller.ingest("leiser").command, "leiser")

    def test_follow_up_extension_is_finite_bounded_and_never_revives_stop(self):
        for duration in (None, "bad", float("nan"), float("inf"), 0, 125.1):
            with self.assertRaises(ValueError):
                self.controller.extend_awake_for(duration)

        self.controller.ingest("Stopp Clausis")
        self.controller.extend_awake_for(30)
        self.assertEqual(self.controller.state, ListeningState.STOPPED)


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
        summary = self.valid_plan().spoken_summary()
        self.assertIn("dauerhaft gelöscht", summary)
        self.assertIn("LUKS 2", summary)

    def test_cloud_requires_consent(self):
        with self.assertRaisesRegex(ValueError, "consent"):
            self.valid_plan(hermes_provider="nous").validate()

    def test_encryption_requires_recovery_export(self):
        with self.assertRaisesRegex(ValueError, "recovery"):
            self.valid_plan(recovery_key_exported=False).validate()

    def test_secret_metadata_rejected(self):
        with self.assertRaisesRegex(ValueError, "secrets"):
            self.valid_plan(metadata={"password": "bad"}).validate()

    def test_non_destructive_mode_is_not_falsely_claimed_as_voice_native(self):
        with self.assertRaisesRegex(ValueError, "whole-disk"):
            self.valid_plan(erase_disk=False).validate()

    def test_plan_rebinds_exact_stable_disk_identity(self):
        disk = InstallDisk(
            path="/dev/sda",
            stable_id="/dev/disk/by-id/ata-VBOX_HARDDISK_123456",
            size_bytes=64 * 1024**3,
            model="VBOX HARDDISK",
            serial="VB123456",
        )
        plan = self.valid_plan(
            disk_id=disk.stable_id,
            disk_bytes=disk.size_bytes,
            disk_model=disk.model,
            disk_serial_suffix=disk.serial_suffix,
        )
        self.assertIs(plan.bind_to((disk,)), disk)

    def test_plan_refuses_disk_identity_change(self):
        disk = InstallDisk(
            path="/dev/sda",
            stable_id="/dev/disk/by-id/ata-VBOX_HARDDISK_123456",
            size_bytes=64 * 1024**3,
            serial="VB123456",
        )
        plan = self.valid_plan(
            disk_id=disk.stable_id,
            disk_bytes=disk.size_bytes + 1,
            disk_serial_suffix=disk.serial_suffix,
        )
        with self.assertRaisesRegex(ValueError, "size changed"):
            plan.bind_to((disk,))


class DiskInventoryTests(unittest.TestCase):
    def test_inventory_excludes_live_medium_removable_and_mounted_disks(self):
        payload = {
            "blockdevices": [
                {
                    "path": "/dev/sda",
                    "type": "disk",
                    "size": 64 * 1024**3,
                    "model": "Safe Disk",
                    "serial": "SAFE123456",
                    "rm": False,
                    "ro": False,
                    "mountpoints": [None],
                    "children": [{"mountpoints": [None]}],
                },
                {
                    "path": "/dev/sdb",
                    "type": "disk",
                    "size": 64 * 1024**3,
                    "model": "Live USB",
                    "rm": True,
                    "ro": False,
                    "children": [{"mountpoints": ["/run/live/medium"]}],
                },
                {
                    "path": "/dev/nvme0n1",
                    "type": "disk",
                    "size": 128 * 1024**3,
                    "model": "Mounted",
                    "rm": False,
                    "ro": False,
                    "children": [{"mountpoints": ["/media/clausis/Data"]}],
                },
            ]
        }
        inventory = parse_lsblk_inventory(
            payload,
            stable_ids={
                "/dev/sda": "/dev/disk/by-id/ata-Safe_Disk_SAFE123456",
                "/dev/sdb": "/dev/disk/by-id/usb-Live_USB",
                "/dev/nvme0n1": "/dev/disk/by-id/nvme-Mounted",
            },
        )
        eligible = eligible_install_disks(inventory)
        self.assertEqual([disk.path for disk in eligible], ["/dev/sda"])
        self.assertIn("gestartete Live-System", " ".join(inventory[1].rejection_reasons()))
        self.assertIn("eingehängt", " ".join(inventory[2].rejection_reasons()))

    def test_unstable_device_name_is_never_eligible(self):
        disk = InstallDisk(path="/dev/vda", stable_id="/dev/vda", size_bytes=64 * 1024**3)
        self.assertFalse(disk.eligible)
        self.assertIn("stabile Gerätekennung", " ".join(disk.rejection_reasons()))

    def test_small_disk_is_rejected(self):
        disk = InstallDisk(
            path="/dev/sda",
            stable_id="/dev/disk/by-id/ata-small",
            size_bytes=16 * 1024**3,
        )
        self.assertIn("32 GiB", " ".join(disk.rejection_reasons()))

    def test_lsblk_string_false_is_not_treated_as_true(self):
        inventory = parse_lsblk_inventory(
            {
                "blockdevices": [
                    {
                        "path": "/dev/vda",
                        "type": "disk",
                        "size": str(64 * 1024**3),
                        "rm": "false",
                        "ro": "0",
                    }
                ]
            },
            stable_ids={"/dev/vda": "/dev/disk/by-id/virtio-clausis-test"},
        )
        self.assertTrue(inventory[0].eligible)

    def test_calamares_guard_binds_exact_encrypted_btrfs_target(self):
        disk = InstallDisk(
            path="/dev/vda",
            stable_id="/dev/disk/by-id/virtio-clausis-test",
            size_bytes=64 * 1024**3,
        )
        result = guard_calamares_erase_transaction(
            (disk,), device_node="/dev/vda", encrypted="true", filesystem="btrfs"
        )
        self.assertIs(result, disk)

    def test_calamares_guard_rejects_changed_target_or_weakened_profile(self):
        disk = InstallDisk(
            path="/dev/vda",
            stable_id="/dev/disk/by-id/virtio-clausis-test",
            size_bytes=64 * 1024**3,
        )
        for values in (
            {"device_node": "/dev/sda", "encrypted": "true", "filesystem": "btrfs"},
            {"device_node": "/dev/vda", "encrypted": "false", "filesystem": "btrfs"},
            {"device_node": "/dev/vda", "encrypted": "true", "filesystem": "ext4"},
        ):
            with self.subTest(values=values), self.assertRaises(ValueError):
                guard_calamares_erase_transaction((disk,), **values)

    def test_prewrite_summary_binds_destructive_profile_and_disk_identity(self):
        disk = InstallDisk(
            path="/dev/vda",
            stable_id="/dev/disk/by-id/virtio-clausis-test",
            size_bytes=64 * 1024**3,
            model="VIRTUAL DISK",
            serial="ABC123456",
        )
        summary = calamares_prewrite_summary(disk)
        self.assertIn("VIRTUAL DISK", summary)
        self.assertIn("64.0 GiB", summary)
        self.assertIn("123456", summary)
        self.assertIn("dauerhaft gelöscht", summary)
        self.assertIn("LUKS 2", summary)
        self.assertIn("Btrfs", summary)


class InstallConfirmationChallengeTests(unittest.TestCase):
    def test_phrase_is_exact_single_use_and_not_reusable(self):
        challenge = InstallConfirmationChallenge()
        with patch("clausis.installer.secrets.SystemRandom.sample", return_value=["anker", "mond"]), patch(
            "clausis.installer.secrets.randbelow", return_value=23
        ):
            phrase = challenge.issue()
        self.assertEqual(phrase, "anker mond 123")
        self.assertTrue(challenge.confirm("  ANKER,   Mond 123. "))
        self.assertFalse(challenge.confirm(phrase))

    def test_ambiguous_or_expired_response_fails_closed(self):
        now = [10.0]
        challenge = InstallConfirmationChallenge(ttl_seconds=5, clock=lambda: now[0])
        phrase = challenge.issue()
        self.assertFalse(challenge.confirm("ja"))
        phrase = challenge.issue()
        now[0] = 16.0
        self.assertFalse(challenge.confirm(phrase))


class RecoveryKeyTests(unittest.TestCase):
    def test_generated_key_has_twelve_fixed_groups(self):
        values = iter(range(12))
        key = generate_recovery_key(lambda _limit: next(values))
        self.assertEqual(
            key,
            "0000-0001-0002-0003-0004-0005-0006-0007-0008-0009-0010-0011",
        )

    def test_root_only_staging_replaces_stale_key_and_deletes_cleanly(self):
        with tempfile.TemporaryDirectory() as temporary:
            directory = Path(temporary) / "run"
            path = directory / "recovery.key"
            first = "0000-0001-0002-0003-0004-0005-0006-0007-0008-0009-0010-0011"
            second = "9999-9998-9997-9996-9995-9994-9993-9992-9991-9990-9989-9988"
            stage_recovery_key(first, directory=directory, path=path)
            self.assertEqual(path.read_text(encoding="ascii").strip(), first)
            self.assertEqual(path.stat().st_mode & 0o777, 0o600)
            self.assertEqual(directory.stat().st_mode & 0o777, 0o700)
            stage_recovery_key(second, directory=directory, path=path)
            self.assertEqual(path.read_text(encoding="ascii").strip(), second)
            discard_staged_recovery_key(path)
            self.assertFalse(path.exists())

    def test_invalid_or_symlinked_staging_is_rejected(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            real_directory = root / "real"
            real_directory.mkdir()
            link = root / "link"
            link.symlink_to(real_directory, target_is_directory=True)
            with self.assertRaises(ValueError):
                stage_recovery_key(
                    "not-a-key", directory=real_directory, path=real_directory / "key"
                )
            valid = "0000-0001-0002-0003-0004-0005-0006-0007-0008-0009-0010-0011"
            with self.assertRaises(ValueError):
                stage_recovery_key(valid, directory=link, path=link / "recovery.key")

    def test_insecure_existing_staging_directory_is_rejected(self):
        with tempfile.TemporaryDirectory() as temporary:
            directory = Path(temporary) / "run"
            directory.mkdir(mode=0o755)
            directory.chmod(0o755)
            with self.assertRaises(ValueError):
                stage_recovery_key(
                    "0000-0001-0002-0003-0004-0005-0006-0007-0008-0009-0010-0011",
                    directory=directory,
                    path=directory / "recovery.key",
                )

if __name__ == "__main__":
    unittest.main()
