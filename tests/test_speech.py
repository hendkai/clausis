from __future__ import annotations

import subprocess
import sys
import tempfile
from pathlib import Path
from types import SimpleNamespace
import unittest
from unittest.mock import patch

from clausis.speech import LocalWhisper, SpeechError, SystemSpeaker


class SystemSpeakerTests(unittest.TestCase):
    def test_timed_out_backend_fails_closed_without_replaying_secret(self) -> None:
        with (
            patch("clausis.speech.shutil.which", return_value="/usr/bin/speaker"),
            patch(
                "clausis.speech.subprocess.run",
                side_effect=subprocess.TimeoutExpired(["spd-say"], 120),
            ) as run,
        ):
            with self.assertRaisesRegex(SpeechError, "nicht rechtzeitig"):
                SystemSpeaker().speak("protected recovery key")

        self.assertEqual(run.call_count, 1)
        self.assertEqual(run.call_args.kwargs["timeout"], 120)
        self.assertFalse(run.call_args.kwargs["shell"])


class LocalWhisperTests(unittest.TestCase):
    def test_initial_prompt_is_forwarded_only_to_local_model(self) -> None:
        calls = []

        class Model:
            def __init__(self, *args, **kwargs):
                pass

            def transcribe(self, path, **kwargs):
                calls.append((path, kwargs))
                return ([SimpleNamespace(text=" sieben zwei neun ")], None)

        with (
            tempfile.TemporaryDirectory() as temporary,
            patch.dict(sys.modules, {"faster_whisper": SimpleNamespace(WhisperModel=Model)}),
        ):
            audio = Path(temporary) / "private.wav"
            audio.touch()
            result = LocalWhisper(
                "local-model", language="de", initial_prompt="Ziffern"
            ).transcribe(audio)

        self.assertEqual(result, "sieben zwei neun")
        self.assertEqual(calls[0][1]["initial_prompt"], "Ziffern")
        self.assertEqual(calls[0][1]["language"], "de")


if __name__ == "__main__":
    unittest.main()
