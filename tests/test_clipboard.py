import subprocess
import sys
import unittest

from clausis.clipboard import read_text, write_text


class ClipboardTests(unittest.TestCase):
    @staticmethod
    def _process_factory(payload: bytes, *, returncode: int = 0):
        def factory(argv, **kwargs):
            factory.argv = argv
            expression = "b'x' * 400001" if len(payload) == 400_001 else repr(payload)
            code = "import os,sys; os.write(1, " + expression + "); sys.exit(" + str(returncode) + ")"
            return subprocess.Popen(
                [sys.executable, "-c", code],
                stdin=kwargs["stdin"],
                stdout=kwargs["stdout"],
                stderr=kwargs["stderr"],
                close_fds=True,
            )

        factory.argv = None
        return factory

    def test_write_uses_fixed_wayland_argv_and_stdin_only(self):
        calls = []

        def fake_run(argv, **kwargs):
            calls.append((argv, kwargs))
            return subprocess.CompletedProcess(argv, 0, "", "")

        write_text("first\nsecond", run=fake_run)
        argv, kwargs = calls[0]
        self.assertEqual(argv, ["wl-copy", "--type", "text/plain;charset=utf-8"])
        self.assertEqual(kwargs["input"], "first\nsecond")
        self.assertFalse(kwargs["shell"])
        self.assertTrue(kwargs["capture_output"])
        self.assertNotIn("first", " ".join(argv))

    def test_write_rejects_empty_nul_and_oversized_text_before_spawn(self):
        calls = []
        for value in ("", "a\x00b", "x" * 100_001):
            with self.subTest(length=len(value)), self.assertRaises(ValueError):
                write_text(value, run=lambda *args, **kwargs: calls.append(args))
        self.assertEqual(calls, [])

    def test_write_reports_failure_without_exposing_content(self):
        def failed(argv, **kwargs):
            return subprocess.CompletedProcess(argv, 1, "", "sensitive provider detail")

        with self.assertRaisesRegex(RuntimeError, "clipboard write failed") as raised:
            write_text("private value", run=failed)
        self.assertNotIn("private", str(raised.exception))
        self.assertNotIn("provider", str(raised.exception))

    def test_read_uses_fixed_argv_and_preserves_exact_utf8(self):
        factory = self._process_factory("first\n  zweite".encode("utf-8"))
        self.assertEqual(read_text(popen=factory), "first\n  zweite")
        self.assertEqual(factory.argv, ["wl-paste", "--type", "text"])

    def test_read_rejects_empty_invalid_nul_and_oversized_output(self):
        for payload in (b"", b"\xff", b"a\x00b", b"x" * 400_001):
            with self.subTest(size=len(payload)), self.assertRaises(ValueError):
                read_text(popen=self._process_factory(payload))

    def test_read_reports_provider_failure_without_stderr_or_content(self):
        with self.assertRaisesRegex(RuntimeError, "clipboard read failed") as raised:
            read_text(popen=self._process_factory(b"private", returncode=2))
        self.assertNotIn("private", str(raised.exception))


if __name__ == "__main__":
    unittest.main()
