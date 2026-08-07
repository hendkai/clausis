"""Direct local audio path for the isolated trusted confirmation service."""

from __future__ import annotations

import re
from pathlib import Path
from typing import Optional

from .confirmation import ConfirmationResponse
from .speech import (
    LocalWhisper,
    MicrophoneRecorder,
    SpeechError,
    SystemSpeaker,
    record_temporary,
)


_DIGITS = {
    "null": "0", "zero": "0", "oh": "0",
    "eins": "1", "ein": "1", "one": "1",
    "zwei": "2", "two": "2",
    "drei": "3", "three": "3",
    "vier": "4", "four": "4",
    "fünf": "5", "funf": "5", "five": "5",
    "sechs": "6", "six": "6",
    "sieben": "7", "seven": "7",
    "acht": "8", "eight": "8",
    "neun": "9", "nine": "9",
}


def normalize_spoken_pin(transcript: str) -> str:
    """Convert a locally transcribed digit sequence without retaining audio."""

    compact = re.sub(r"[\s,.;:_-]+", "", transcript)
    if compact.isdigit():
        return compact
    words = re.findall(r"[\wäöüß]+", transcript.casefold(), flags=re.UNICODE)
    try:
        pin = "".join(_DIGITS[word] for word in words)
    except KeyError as exc:
        raise SpeechError("Die PIN enthielt ein unbekanntes Wort.") from exc
    if not pin.isdigit():
        raise SpeechError("Keine PIN erkannt.")
    return pin


class DirectAudioConfirmation:
    """Speak and capture secrets entirely inside ``clausis-confirm``.

    No transcript is printed, returned over D-Bus or persisted.  Temporary WAV
    files live in the service's PrivateTmp and are unlinked after each pass.
    """

    def __init__(
        self,
        model: str = "/usr/share/clausis/models/faster-whisper-base",
        *,
        language: str = "de",
        recorder: Optional[MicrophoneRecorder] = None,
        transcriber: Optional[LocalWhisper] = None,
        speaker: Optional[SystemSpeaker] = None,
    ) -> None:
        self.language = language
        self.recorder = recorder or MicrophoneRecorder()
        self.transcriber = transcriber or LocalWhisper(model, language=language)
        self.speaker = speaker or SystemSpeaker()

    def _listen(self) -> str:
        path: Optional[Path] = None
        try:
            path = record_temporary(self.recorder)
            return self.transcriber.transcribe(path).strip()
        finally:
            if path is not None:
                path.unlink(missing_ok=True)

    def collect(self, summary: str, challenge: str) -> ConfirmationResponse:
        self.speaker.speak(summary, language=self.language)
        phrase = self._listen()
        self.speaker.speak(
            "Sagen Sie jetzt Ihre PIN. Sie wird nicht vorgelesen oder gespeichert.",
            language=self.language,
        )
        pin = normalize_spoken_pin(self._listen())
        return ConfirmationResponse(phrase=phrase, pin=pin)
