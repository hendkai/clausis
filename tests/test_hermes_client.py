from __future__ import annotations

import json
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest.mock import patch

from clausis.hermes_client import HermesOneShot, hermes_is_configured


class HermesClientTests(unittest.TestCase):
    def _configured_home(self, directory: str) -> Path:
        home = Path(directory)
        target = home / ".hermes" / "config.yaml"
        target.parent.mkdir(parents=True)
        target.write_text(json.dumps({"clausis": {"setup_complete": True}}))
        return home

    def test_only_clausis_managed_ready_config_enables_fallback(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            home = Path(directory)
            self.assertFalse(hermes_is_configured(home))
            self._configured_home(directory)
            self.assertTrue(hermes_is_configured(home))

    def test_one_shot_forces_narrow_toolset_and_never_uses_a_shell(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            home = self._configured_home(directory)
            completed = subprocess.CompletedProcess([], 0, "Eine sichere Antwort.\n", "")
            with patch("clausis.hermes_client.subprocess.run", return_value=completed) as run:
                result = HermesOneShot(home=home)("  Erkläre   mir Linux  ")
            self.assertEqual(result.status, "hermes_response")
            args, kwargs = run.call_args
            self.assertEqual(
                args[0],
                [
                    "/usr/local/bin/hermes",
                    "--toolsets",
                    "todo",
                    "-z",
                    "Erkläre mir Linux",
                ],
            )
            self.assertFalse(kwargs["shell"])

    def test_unconfigured_hermes_does_not_start_a_process(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            with patch("clausis.hermes_client.subprocess.run") as run:
                result = HermesOneShot(home=Path(directory))("Hallo")
            self.assertEqual(result.status, "offline_unmatched")
            run.assert_not_called()

    def test_provider_errors_are_not_returned_for_speech(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            home = self._configured_home(directory)
            completed = subprocess.CompletedProcess(
                [], 1, "", "request failed with secret-token-123"
            )
            with patch("clausis.hermes_client.subprocess.run", return_value=completed):
                result = HermesOneShot(home=home)("Hallo")
            self.assertEqual(result.status, "failed")
            self.assertNotIn("secret-token-123", result.message)
            self.assertIn("nicht vorgelesen", result.message)


if __name__ == "__main__":
    unittest.main()
