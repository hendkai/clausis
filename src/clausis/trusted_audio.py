"""Direct local audio path for the isolated trusted confirmation service."""

from __future__ import annotations

import re
from pathlib import Path
from typing import Optional

from .confirmation import ConfirmationResponse
from .installer import InstallConfirmationChallenge
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


class DirectInstallConfirmation:
    """One-shot installer approval held entirely inside the pre-write process.

    The generated phrase and local transcript never cross D-Bus, Calamares'
    global storage, stdout or the desktop accessibility tree.
    """

    def __init__(
        self,
        model: str = "/usr/share/clausis/models/faster-whisper-base",
        *,
        language: str = "de",
        recorder: Optional[MicrophoneRecorder] = None,
        transcriber: Optional[LocalWhisper] = None,
        speaker: Optional[SystemSpeaker] = None,
        challenge: Optional[InstallConfirmationChallenge] = None,
    ) -> None:
        self.language = language
        self.recorder = recorder or MicrophoneRecorder()
        self.transcriber = transcriber or LocalWhisper(model, language=language)
        self.speaker = speaker or SystemSpeaker()
        self.challenge = challenge or InstallConfirmationChallenge()

    def _listen(self) -> str:
        path: Optional[Path] = None
        try:
            path = record_temporary(self.recorder)
            return self.transcriber.transcribe(path).strip()
        finally:
            if path is not None:
                path.unlink(missing_ok=True)

    def authorize(self, summary: str) -> bool:
        phrase = self.challenge.issue()
        self.speaker.speak(
            f"{summary} Zum Bestätigen sagen Sie jetzt exakt: {phrase}.",
            language=self.language,
        )
        approved = self.challenge.confirm(self._listen())
        if approved:
            self.speaker.speak(
                "Bestätigung erkannt. Die Installation beginnt jetzt.",
                language=self.language,
            )
            return True
        self.speaker.speak(
            "Die Bestätigung war nicht eindeutig. Die Installation wurde abgebrochen.",
            language=self.language,
        )
        return False
