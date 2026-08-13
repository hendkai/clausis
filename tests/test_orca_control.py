import subprocess
import unittest
from unittest.mock import patch

from clausis.orca_control import main, restart_orca


class FakeProcess:
    def __init__(self, returncode=None):
        self.returncode = returncode

    def poll(self):
        return self.returncode


class OrcaControlTests(unittest.TestCase):
    def test_restart_uses_only_fixed_speech_recovery_argv(self):
        calls = []
        waits = []

        def popen(argv, **kwargs):
            calls.append((argv, kwargs))
            return FakeProcess()

        restart_orca(popen=popen, wait=waits.append)
        self.assertEqual(calls[0][0], ["orca", "--replace", "--enable", "speech"])
        self.assertIs(calls[0][1]["stdin"], subprocess.DEVNULL)
        self.assertIs(calls[0][1]["stdout"], subprocess.DEVNULL)
        self.assertIs(calls[0][1]["stderr"], subprocess.DEVNULL)
        self.assertTrue(calls[0][1]["start_new_session"])
        self.assertTrue(calls[0][1]["close_fds"])
        self.assertEqual(waits, [1.0])

    def test_immediate_exit_is_reported_as_failure(self):
        with self.assertRaisesRegex(RuntimeError, "status 1"):
            restart_orca(popen=lambda *args, **kwargs: FakeProcess(1), wait=lambda _: None)

    def test_main_rejects_all_unbounded_options(self):
        for argv in ([], ["enable", "mouse-review"], ["restart", "speech"]):
            with self.subTest(argv=argv):
                self.assertEqual(main(argv), 2)

    def test_main_reports_spawn_failure_without_details(self):
        with patch("clausis.orca_control.restart_orca", side_effect=OSError("secret")):
            self.assertEqual(main(["restart"]), 1)
