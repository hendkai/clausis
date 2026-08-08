"""The snapshot guard around system-changing privileged actions.

The health check could already recommend a rollback; these tests cover the part
that acts on it, including the deliberate decision that a machine without
snapshots still receives its security updates.
"""

from __future__ import annotations

import io
import json
import subprocess
import tempfile
import unittest
from dataclasses import replace
from pathlib import Path

from clausis.capabilities import CapabilityAuthority
from clausis.models import ActionRequest, Risk
from clausis.privileged import ReplayGuard, helper_main
from clausis.rollback import (
    SNAPSHOT_GUARDED,
    SnapshotError,
    SnapshotManager,
    UpdateGuard,
)


def _completed(returncode=0, stdout="", stderr=""):
    return subprocess.CompletedProcess(["fake"], returncode, stdout, stderr)


class FakeSnapper:
    """Record snapper calls and answer them like a configured system."""

    def __init__(self, *, configured=True, pre=7, post=8, undo_ok=True):
        self.configured = configured
        self.pre = pre
        self.post = post
        self.undo_ok = undo_ok
        self.calls = []

    def __call__(self, command):
        self.calls.append(list(command))
        if "list-configs" in command:
            return _completed(0, "root\n" if self.configured else "")
        if "create" in command and "pre" in command:
            return _completed(0, f"{self.pre}\n")
        if "create" in command and "post" in command:
            return _completed(0, f"{self.post}\n")
        if "undochange" in command:
            return _completed(0 if self.undo_ok else 1)
        return _completed(0)

    @property
    def undone(self):
        return [c for c in self.calls if "undochange" in c]


class SnapshotManagerTests(unittest.TestCase):
    def _manager(self, snapper, **kwargs):
        return SnapshotManager(runner=snapper, which=lambda name: "/usr/bin/snapper", **kwargs)

    def test_available_requires_the_root_config(self):
        self.assertTrue(self._manager(FakeSnapper()).available())
        self.assertFalse(self._manager(FakeSnapper(configured=False)).available())

    def test_missing_binary_is_unavailable(self):
        manager = SnapshotManager(runner=FakeSnapper(), which=lambda name: None)
        self.assertFalse(manager.available())

    def test_snapshot_numbers_are_parsed(self):
        manager = self._manager(FakeSnapper(pre=12, post=13))
        self.assertEqual(manager.create_pre(), 12)
        self.assertEqual(manager.create_post(12), 13)

    def test_unparsable_output_is_an_error(self):
        manager = self._manager(lambda command: _completed(0, "no number here"))
        with self.assertRaises(SnapshotError):
            manager.create_pre()

    def test_failed_creation_is_an_error(self):
        manager = self._manager(lambda command: _completed(1))
        with self.assertRaises(SnapshotError):
            manager.create_pre()

    def test_undo_uses_the_snapshot_range(self):
        snapper = FakeSnapper()
        self._manager(snapper).undo(7, 8)
        self.assertIn(["snapper", "-c", "root", "undochange", "7..8"], snapper.calls)

    def test_snapshot_numbers_are_coerced_to_integers(self):
        snapper = FakeSnapper()
        manager = self._manager(snapper)
        manager.undo(True, 8)
        self.assertIn("1..8", snapper.calls[-1])

    def test_every_call_is_a_fixed_vector_without_a_shell(self):
        snapper = FakeSnapper()
        manager = self._manager(snapper)
        manager.available()
        manager.create_post(manager.create_pre())
        manager.undo(7, 8)
        for call in snapper.calls:
            self.assertEqual(call[0], "snapper")
            self.assertNotIn(";", " ".join(call))
            self.assertNotIn("|", " ".join(call))


class UpdateGuardTests(unittest.TestCase):
    def _guard(self, snapper, *, update_ok=True, healthy=True):
        self.updates = []

        def runner(command):
            self.updates.append(list(command))
            return _completed(0 if update_ok else 100, stderr="E: broken\n")

        return UpdateGuard(
            manager=SnapshotManager(runner=snapper, which=lambda name: "/usr/bin/snapper"),
            health=lambda: {"rollback_recommended": not healthy},
            runner=runner,
        )

    def test_successful_update_keeps_the_new_state(self):
        snapper = FakeSnapper()
        outcome = self._guard(snapper).run(["apt-get", "install", "nano"])
        self.assertTrue(outcome.succeeded)
        self.assertFalse(outcome.rolled_back)
        self.assertTrue(outcome.snapshotted)
        self.assertEqual(snapper.undone, [])

    def test_failed_update_is_rolled_back(self):
        snapper = FakeSnapper()
        outcome = self._guard(snapper, update_ok=False).run(["apt-get", "install", "nano"])
        self.assertFalse(outcome.succeeded)
        self.assertTrue(outcome.rolled_back)
        self.assertEqual(len(snapper.undone), 1)
        self.assertIn("wiederhergestellt", outcome.message)

    def test_update_that_breaks_speech_is_rolled_back(self):
        # The update itself succeeded; the health check is what condemns it.
        snapper = FakeSnapper()
        outcome = self._guard(snapper, healthy=False).run(["unattended-upgrade"])
        self.assertFalse(outcome.succeeded)
        self.assertTrue(outcome.rolled_back)
        self.assertIn("sprachfähig", outcome.message)

    def test_missing_snapshots_do_not_block_a_security_update(self):
        # Refusing security updates because snapper is absent would trade a
        # real risk for a hypothetical one.
        snapper = FakeSnapper(configured=False)
        outcome = self._guard(snapper).run(["unattended-upgrade"])
        self.assertTrue(outcome.succeeded)
        self.assertFalse(outcome.snapshotted)
        self.assertIn("kein Systemabbild", outcome.message)
        self.assertEqual(self.updates, [["unattended-upgrade"]])

    def test_failed_rollback_is_reported_honestly(self):
        snapper = FakeSnapper(undo_ok=False)
        outcome = self._guard(snapper, update_ok=False).run(["apt-get", "install", "nano"])
        self.assertFalse(outcome.succeeded)
        self.assertFalse(outcome.rolled_back)
        self.assertIn("ebenfalls fehlgeschlagen", outcome.message)
        self.assertIn("Tastatur", outcome.message)

    def test_unusable_health_check_does_not_trigger_a_rollback(self):
        def exploding():
            raise RuntimeError("no health data")

        snapper = FakeSnapper()
        guard = UpdateGuard(
            manager=SnapshotManager(runner=snapper, which=lambda name: "/usr/bin/snapper"),
            health=exploding,
            runner=lambda command: _completed(0),
        )
        outcome = guard.run(["apt-get", "install", "nano"])
        self.assertTrue(outcome.succeeded)
        self.assertEqual(snapper.undone, [])

    def test_missing_post_snapshot_leaves_the_system_untouched(self):
        class NoPost(FakeSnapper):
            def __call__(self, command):
                if "create" in command and "post" in command:
                    self.calls.append(list(command))
                    return _completed(1)
                return super().__call__(command)

        snapper = NoPost()
        outcome = self._guard(snapper).run(["apt-get", "install", "nano"])
        self.assertEqual(snapper.undone, [])
        self.assertIn("nichts zurückgenommen", outcome.message)


class HelperIntegrationTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        root = Path(self.directory.name)
        self.key_path = root / "capability.key"
        self.key_path.write_bytes(b"k" * 32)
        self.authority = CapabilityAuthority(b"k" * 32)
        self.replay = ReplayGuard(root / "store")

    def _run(self, request, update_guard=None, runner=None):
        import contextlib

        stream = io.StringIO(json.dumps(request.to_dict()))
        buffer = io.StringIO()
        with contextlib.redirect_stdout(buffer):
            helper_main(
                [],
                stdin=stream,
                key_path=self.key_path,
                guard=self.replay,
                runner=runner or (lambda command: _completed(0)),
                update_guard=update_guard,
            )
        return json.loads(buffer.getvalue())

    def _approved(self, request):
        return replace(request, capability_token=self.authority.issue(request))

    def test_software_changing_actions_are_guarded(self):
        self.assertEqual(
            SNAPSHOT_GUARDED,
            {"package.install", "package.remove", "update.install_security"},
        )

    def test_security_update_runs_through_the_guard(self):
        seen = []

        class RecordingGuard:
            def run(self, command):
                seen.append(list(command))
                from clausis.rollback import GuardOutcome

                return GuardOutcome(True, False, True, "Die Aktion wurde ausgeführt.")

        request = self._approved(
            ActionRequest("update.install_security", risk=Risk.HIGH)
        )
        reply = self._run(request, update_guard=RecordingGuard())
        self.assertEqual(reply["status"], "completed")
        self.assertEqual(seen, [["unattended-upgrade", "--verbose"]])

    def test_rolled_back_update_is_reported_as_failed(self):
        class RollingBackGuard:
            def run(self, command):
                from clausis.rollback import GuardOutcome

                return GuardOutcome(False, True, True, "Der vorherige Systemstand wurde wiederhergestellt.")

        request = self._approved(ActionRequest("package.install", "nano", risk=Risk.HIGH))
        reply = self._run(request, update_guard=RollingBackGuard())
        self.assertEqual(reply["status"], "failed")
        self.assertIn("wiederhergestellt", reply["message"])

    def test_reboot_is_not_snapshotted(self):
        commands = []

        request = self._approved(
            ActionRequest("system.reboot", risk=Risk.CRITICAL, reversible=False)
        )
        reply = self._run(
            request, runner=lambda command: (commands.append(list(command)), _completed(0))[1]
        )
        self.assertEqual(reply["status"], "completed")
        self.assertEqual(commands, [["systemctl", "reboot"]])


if __name__ == "__main__":
    unittest.main()
