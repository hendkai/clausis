"""The Btrfs layout that keeps a rollback from erasing its own evidence.

The property these tests protect is narrow and important: undoing a failed
update must not revert the tamper-evident audit chain, the record of which
Hermes release is installed, or the user's documents.
"""

from __future__ import annotations

import unittest
from pathlib import Path

from clausis.healthcheck import collect
from clausis.subvolumes import (
    MUST_SURVIVE_ROLLBACK,
    SUBVOLUMES,
    Subvolume,
    calamares_subvolumes,
    excluded,
    mounted_subvolumes,
    rollback_safety_report,
    snapshotted,
    validate_present,
)


ROOT = Path(__file__).resolve().parents[1]
PARTITION_CONF = ROOT / "packaging/calamares/partition.conf"


class LayoutTests(unittest.TestCase):
    def test_only_the_system_root_is_inside_the_rollback_boundary(self):
        self.assertEqual(snapshotted(), ("/",))

    def test_the_audit_log_is_outside_the_rollback_boundary(self):
        # Rolling back the record of what an update did would destroy exactly
        # the evidence needed to understand the failure.
        report = rollback_safety_report()
        self.assertTrue(report["safe"])
        self.assertEqual(report["unprotected"], [])
        self.assertIn("/var/log", excluded())

    def test_every_path_that_must_survive_is_covered(self):
        for path in MUST_SURVIVE_ROLLBACK:
            with self.subTest(path=path):
                self.assertTrue(
                    any(path == point or path.startswith(point + "/") for point in excluded())
                )

    def test_a_flat_layout_is_reported_as_unsafe(self):
        flat = (Subvolume("@", "/", True, "everything in one volume"),)
        report = rollback_safety_report(flat)
        self.assertFalse(report["safe"])
        self.assertEqual(sorted(report["unprotected"]), sorted(MUST_SURVIVE_ROLLBACK))

    def test_every_subvolume_states_why_it_exists(self):
        for item in SUBVOLUMES:
            with self.subTest(name=item.name):
                self.assertTrue(item.reason.strip().endswith("."))
                self.assertGreater(len(item.reason), 30)

    def test_mount_points_and_names_are_unique(self):
        self.assertEqual(len({item.name for item in SUBVOLUMES}), len(SUBVOLUMES))
        self.assertEqual(len({item.mount_point for item in SUBVOLUMES}), len(SUBVOLUMES))

    def test_snapshot_store_is_not_inside_the_snapshot(self):
        # Otherwise every snapshot would contain the previous ones.
        self.assertIn("/.snapshots", excluded())


class CalamaresConfigurationTests(unittest.TestCase):
    def setUp(self):
        self.source = PARTITION_CONF.read_text(encoding="utf-8")

    def test_installer_declares_a_subvolume_layout_at_all(self):
        self.assertIn("btrfsSubvolumes:", self.source)

    def test_installer_matches_the_authoritative_definition(self):
        for entry in calamares_subvolumes():
            with self.subTest(subvolume=entry["subvolume"]):
                self.assertIn(f'subvolume: "{entry["subvolume"]}"', self.source)
                self.assertIn(f'mountPoint: "{entry["mountPoint"]}"', self.source)

    def test_layout_order_puts_the_root_first(self):
        entries = calamares_subvolumes()
        self.assertEqual(entries[0]["mountPoint"], "/")

    def test_root_filesystem_is_still_btrfs(self):
        self.assertIn('defaultFileSystemType: "btrfs"', self.source)


class MountParsingTests(unittest.TestCase):
    MOUNTS = (
        "/dev/mapper/root / btrfs rw,relatime,subvol=/@ 0 0\n"
        "/dev/mapper/root /home btrfs rw,relatime,subvol=/@home 0 0\n"
        "/dev/mapper/root /var/log btrfs rw,relatime,subvol=/@var-log 0 0\n"
        "/dev/mapper/root /var/lib/clausis btrfs rw,subvol=/@var-lib-clausis 0 0\n"
        "/dev/mapper/root /.snapshots btrfs rw,subvol=/@snapshots 0 0\n"
        "/dev/mapper/root /var/cache btrfs rw,subvol=/@var-cache 0 0\n"
        "/dev/mapper/root /var/tmp btrfs rw,subvol=/@var-tmp 0 0\n"
        "/dev/mapper/root /swap btrfs rw,subvol=/@swap 0 0\n"
        "proc /proc proc rw 0 0\n"
        "/dev/sda1 /boot ext4 rw 0 0\n"
    )

    def test_only_btrfs_subvolume_mounts_are_reported(self):
        points = mounted_subvolumes(self.MOUNTS)
        self.assertIn("/var/log", points)
        self.assertNotIn("/proc", points)
        self.assertNotIn("/boot", points)

    def test_a_complete_installation_validates(self):
        report = validate_present(mounted_subvolumes(self.MOUNTS))
        self.assertTrue(report["complete"])
        self.assertTrue(report["rollback_safe"])
        self.assertEqual(report["exposed"], [])

    def test_a_flat_installation_is_reported_as_exposed(self):
        report = validate_present(["/"])
        self.assertFalse(report["complete"])
        self.assertFalse(report["rollback_safe"])
        self.assertIn("/var/log/clausis", report["exposed"])

    def test_a_partial_installation_names_what_is_missing(self):
        partial = "/dev/mapper/root / btrfs rw,subvol=/@ 0 0\n"
        report = validate_present(mounted_subvolumes(partial))
        self.assertIn("/var/log", report["missing"])
        self.assertIn("/home", report["missing"])

    def test_malformed_mount_lines_are_ignored(self):
        self.assertEqual(mounted_subvolumes("garbage\n\nalso garbage here\n"), [])


class HealthcheckLayoutTests(unittest.TestCase):
    def _collect(self, mounts, tmp_path):
        path = tmp_path / "mounts"
        path.write_text(mounts, encoding="utf-8")
        voice = tmp_path / "voice"
        voice.mkdir()
        (voice / "de_DE-thorsten-medium.onnx").write_bytes(b"")
        return collect(
            model_path=Path("/"),
            tts_model_path=voice,
            probe=lambda: type("C", (), {"microphone": True})(),
            which=lambda name: f"/usr/bin/{name}",
            mounts_path=path,
        )

    def test_layout_is_reported_in_the_health_check(self):
        import tempfile

        with tempfile.TemporaryDirectory() as directory:
            report = self._collect(MountParsingTests.MOUNTS, Path(directory))
        self.assertTrue(report["subvolumes"]["rollback_safe"])

    def test_layout_drift_never_recommends_a_rollback(self):
        # A machine installed by an older image is not a broken update.
        import tempfile

        with tempfile.TemporaryDirectory() as directory:
            report = self._collect(
                "/dev/mapper/root / btrfs rw,subvol=/@ 0 0\n", Path(directory)
            )
        self.assertFalse(report["subvolumes"]["rollback_safe"])
        self.assertFalse(report["rollback_recommended"])

    def test_unreadable_mounts_do_not_crash_the_check(self):
        import tempfile

        with tempfile.TemporaryDirectory() as directory:
            voice = Path(directory) / "voice"
            voice.mkdir()
            (voice / "de_DE-thorsten-medium.onnx").write_bytes(b"")
            report = collect(
                model_path=Path("/"),
                tts_model_path=voice,
                probe=lambda: type("C", (), {"microphone": True})(),
                which=lambda name: f"/usr/bin/{name}",
                mounts_path=Path("/nonexistent-clausis-mounts"),
            )
        self.assertFalse(report["subvolumes"]["rollback_safe"])


class RollbackWarningTests(unittest.TestCase):
    def test_rollback_on_an_unsafe_layout_says_so(self):
        import subprocess

        from clausis.rollback import SnapshotManager, UpdateGuard

        def snapper(command):
            if "list-configs" in command:
                return subprocess.CompletedProcess(command, 0, "root\n", "")
            if "create" in command:
                return subprocess.CompletedProcess(command, 0, "7\n", "")
            return subprocess.CompletedProcess(command, 0, "", "")

        guard = UpdateGuard(
            manager=SnapshotManager(runner=snapper, which=lambda name: "/usr/bin/snapper"),
            health=lambda: {"rollback_recommended": True},
            runner=lambda command: subprocess.CompletedProcess(command, 0, "", ""),
        )
        # This host has no Clausis subvolume layout, so the warning must appear.
        outcome = guard.run(["unattended-upgrade"])
        self.assertTrue(outcome.rolled_back)
        self.assertIn("Protokoll", outcome.message)


if __name__ == "__main__":
    unittest.main()
