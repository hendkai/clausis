import io
import json
import subprocess
import tempfile
import unittest
from dataclasses import replace
from pathlib import Path

from clausis.capabilities import CapabilityAuthority, CapabilityError
from clausis.models import ActionRequest, Origin, Risk
from clausis.policy import ACTION_POLICIES
from clausis.privileged import (
    HELPER_PATH,
    PRIVILEGED_ACTIONS,
    PRIVILEGED_COMMANDS,
    PrivilegedExecutor,
    ReplayGuard,
    build_privileged_command,
    helper_main,
)


REBOOT = ActionRequest("system.reboot", risk=Risk.CRITICAL, reversible=False)
INSTALL = ActionRequest("package.install", "gnome-calculator", risk=Risk.HIGH)


def _completed(returncode=0, stdout="", stderr=""):
    return subprocess.CompletedProcess(["fake"], returncode, stdout, stderr)


class PrivilegedCommandTests(unittest.TestCase):
    def test_every_privileged_policy_has_a_root_command(self):
        self.assertEqual(set(PRIVILEGED_ACTIONS), set(PRIVILEGED_COMMANDS))

    def test_privileged_policies_carry_no_session_command(self):
        for action in PRIVILEGED_ACTIONS:
            self.assertIsNone(ACTION_POLICIES[action].command)

    def test_package_name_is_appended_after_a_double_dash(self):
        command = build_privileged_command(INSTALL)
        self.assertEqual(command[-2:], ["--", "gnome-calculator"])

    def test_option_like_package_name_is_rejected(self):
        for target in ("--reinstall", "-y", "gnome calculator", "pkg;rm", "../etc"):
            with self.subTest(target=target):
                with self.assertRaises(ValueError):
                    build_privileged_command(replace(INSTALL, target=target))

    def test_target_on_a_targetless_action_is_rejected(self):
        with self.assertRaises(ValueError):
            build_privileged_command(replace(REBOOT, target="now"))

    def test_unknown_action_has_no_adapter(self):
        with self.assertRaises(ValueError):
            build_privileged_command(ActionRequest("audio.volume.up"))


class ReplayGuardTests(unittest.TestCase):
    def test_second_use_of_a_capability_is_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            guard = ReplayGuard(Path(directory) / "store")
            guard.consume("abc", "2999-01-01T00:00:00+00:00")
            with self.assertRaises(CapabilityError):
                guard.consume("abc", "2999-01-01T00:00:00+00:00")

    def test_expired_entries_are_pruned(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "store"
            guard = ReplayGuard(path)
            guard.consume("old", "2000-01-01T00:00:00+00:00")
            guard.consume("new", "2999-01-01T00:00:00+00:00")
            self.assertFalse((path / "old").exists())
            self.assertTrue((path / "new").exists())

    def test_store_is_written_root_only(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "run" / "store"
            ReplayGuard(path).consume("abc", "2999-01-01T00:00:00+00:00")
            self.assertEqual(path.stat().st_mode & 0o077, 0)
            self.assertEqual((path / "abc").stat().st_mode & 0o077, 0)

    def test_identifier_cannot_escape_the_store_directory(self):
        with tempfile.TemporaryDirectory() as directory:
            guard = ReplayGuard(Path(directory) / "store")
            for identifier in ("", "../escape", "a/b", "." * 200):
                with self.subTest(identifier=identifier):
                    with self.assertRaises(CapabilityError):
                        guard.consume(identifier, "2999-01-01T00:00:00+00:00")


class HelperTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        root = Path(self.directory.name)
        self.key_path = root / "capability.key"
        self.key_path.write_bytes(b"k" * 32)
        self.authority = CapabilityAuthority(b"k" * 32)
        self.guard = ReplayGuard(root / "store")
        self.commands = []

    def _run(self, request, *, returncode=0, stderr=""):
        def runner(command):
            self.commands.append(list(command))
            return _completed(returncode, stderr=stderr)

        stream = io.StringIO(json.dumps(request.to_dict()))
        buffer = io.StringIO()
        import contextlib

        with contextlib.redirect_stdout(buffer):
            code = helper_main(
                [],
                stdin=stream,
                key_path=self.key_path,
                guard=self.guard,
                runner=runner,
            )
        return code, json.loads(buffer.getvalue())

    def _approved(self, request):
        return replace(request, capability_token=self.authority.issue(request))

    def test_confirmed_reboot_runs_the_fixed_vector(self):
        code, reply = self._run(self._approved(REBOOT))
        self.assertEqual(code, 0)
        self.assertEqual(reply["status"], "completed")
        self.assertEqual(self.commands, [["systemctl", "reboot"]])

    def test_request_without_capability_is_denied(self):
        _, reply = self._run(REBOOT)
        self.assertEqual(reply["status"], "denied")
        self.assertEqual(self.commands, [])

    def test_forged_capability_is_denied(self):
        _, reply = self._run(replace(REBOOT, capability_token="forged.token"))
        self.assertEqual(reply["status"], "denied")
        self.assertEqual(self.commands, [])

    def test_capability_for_another_action_is_denied(self):
        token = self.authority.issue(INSTALL)
        _, reply = self._run(replace(REBOOT, capability_token=token))
        self.assertEqual(reply["status"], "denied")
        self.assertEqual(self.commands, [])

    def test_replayed_capability_is_denied_by_the_helper(self):
        approved = self._approved(REBOOT)
        self.assertEqual(self._run(approved)[1]["status"], "completed")
        self.assertEqual(self._run(approved)[1]["status"], "denied")
        self.assertEqual(len(self.commands), 1)

    def test_unprivileged_action_is_refused(self):
        request = ActionRequest("audio.volume.up")
        _, reply = self._run(self._approved(request))
        self.assertEqual(reply["status"], "denied")
        self.assertEqual(self.commands, [])

    def test_helper_rejects_arguments(self):
        import contextlib

        buffer = io.StringIO()
        with contextlib.redirect_stdout(buffer):
            helper_main(["system.reboot"], stdin=io.StringIO("{}"), key_path=self.key_path)
        self.assertEqual(json.loads(buffer.getvalue())["status"], "denied")

    def test_invalid_json_is_denied(self):
        import contextlib

        buffer = io.StringIO()
        with contextlib.redirect_stdout(buffer):
            helper_main([], stdin=io.StringIO("not json"), key_path=self.key_path)
        self.assertEqual(json.loads(buffer.getvalue())["status"], "denied")

    def test_oversized_request_is_denied(self):
        import contextlib

        buffer = io.StringIO()
        with contextlib.redirect_stdout(buffer):
            helper_main([], stdin=io.StringIO("x" * 40_000), key_path=self.key_path)
        self.assertEqual(json.loads(buffer.getvalue())["status"], "denied")

    def test_failing_command_reports_the_last_stderr_line(self):
        _, reply = self._run(
            self._approved(INSTALL), returncode=100, stderr="E: Unable to locate package\n"
        )
        self.assertEqual(reply["status"], "failed")
        self.assertIn("Unable to locate package", reply["message"])


class PrivilegedExecutorTests(unittest.TestCase):
    def setUp(self):
        self.authority = CapabilityAuthority(b"p" * 32)
        self.calls = []

    def _executor(self, *, dry_run=False, reply=None, returncode=0):
        def runner(argv, payload):
            self.calls.append((list(argv), payload))
            body = reply if reply is not None else json.dumps(
                {"status": "completed", "message": "ok", "action": "system.reboot"}
            )
            return _completed(returncode, stdout=body)

        return PrivilegedExecutor(dry_run=dry_run, runner=runner)

    def test_unconfirmed_action_never_reaches_pkexec(self):
        result = self._executor().execute(REBOOT, ACTION_POLICIES["system.reboot"])
        self.assertEqual(result.status, "confirmation_required")
        self.assertEqual(self.calls, [])

    def test_dry_run_reports_the_launcher_without_executing(self):
        approved = replace(REBOOT, capability_token=self.authority.issue(REBOOT))
        result = self._executor(dry_run=True).execute(approved, ACTION_POLICIES["system.reboot"])
        self.assertEqual(result.status, "dry_run")
        self.assertEqual(result.details["argv"], ["pkexec", HELPER_PATH])
        self.assertEqual(self.calls, [])

    def test_capability_travels_on_stdin_and_never_in_argv(self):
        token = self.authority.issue(REBOOT)
        approved = replace(REBOOT, capability_token=token)
        self._executor().execute(approved, ACTION_POLICIES["system.reboot"])
        argv, payload = self.calls[0]
        self.assertEqual(argv, ["pkexec", HELPER_PATH])
        self.assertNotIn(token, " ".join(argv))
        self.assertEqual(json.loads(payload)["capability_token"], token)

    def test_polkit_refusal_is_reported_as_denied(self):
        approved = replace(REBOOT, capability_token=self.authority.issue(REBOOT))
        result = self._executor(reply="", returncode=126).execute(
            approved, ACTION_POLICIES["system.reboot"]
        )
        self.assertEqual(result.status, "denied")

    def test_mismatched_helper_answer_is_rejected(self):
        approved = replace(REBOOT, capability_token=self.authority.issue(REBOOT))
        forged = json.dumps({"status": "completed", "message": "ok", "action": "system.poweroff"})
        result = self._executor(reply=forged).execute(approved, ACTION_POLICIES["system.reboot"])
        self.assertEqual(result.status, "failed")

    def test_invalid_package_name_fails_before_polkit(self):
        request = replace(INSTALL, target="--reinstall")
        approved = replace(request, capability_token=self.authority.issue(request))
        result = self._executor().execute(approved, ACTION_POLICIES["package.install"])
        self.assertEqual(result.status, "failed")
        self.assertEqual(self.calls, [])

    def test_tainted_origin_still_requires_a_capability(self):
        request = replace(REBOOT, origin=Origin.HERMES)
        result = self._executor().execute(request, ACTION_POLICIES["system.reboot"])
        self.assertEqual(result.status, "confirmation_required")
        self.assertEqual(self.calls, [])


if __name__ == "__main__":
    unittest.main()
