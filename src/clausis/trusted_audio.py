"""Direct local audio path for the isolated trusted confirmation service."""

from __future__ import annotations

import re
import secrets
from pathlib import Path
from typing import Optional

from .confirmation import ConfirmationResponse
from .installer import InstallConfirmationChallenge
from .speech import (
    LocalWhisper,
    MicrophoneRecorder,
    RecordingOptions,
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

_ABORT_PHRASES = frozenset({
    "abbrechen",
    "abbruch",
    "cancel",
    "stopp clausis",
    "stopp hermes",
    "stop clausis",
    "stop hermes",
})

_RECOVERY_TRANSCRIPTION_PROMPT = (
    "LUKS Recovery Schlüssel. Zwölf Vierergruppen aus den Ziffern null, eins, "
    "zwei, drei, vier, fünf, sechs, sieben, acht und neun."
)


class ConfirmationAborted(SpeechError):
    """An exact local abort phrase stopped a protected audio ceremony."""


def is_spoken_abort(transcript: str) -> bool:
    """Recognize only complete, explicit abort utterances in German or English."""

    normalized = " ".join(
        re.findall(r"[\wäöüß]+", transcript.casefold(), flags=re.UNICODE)
    )
    return normalized in _ABORT_PHRASES


def _require_not_aborted(transcript: str) -> str:
    if is_spoken_abort(transcript):
        raise ConfirmationAborted("Bestätigung lokal abgebrochen.")
    return transcript


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


def normalize_spoken_recovery_key(transcript: str) -> str:
    """Normalize a locally spoken 12-by-4 digit LUKS recovery key."""

    words = re.findall(r"\d+|[\wäöüß]+", transcript.casefold(), flags=re.UNICODE)
    digits: list[str] = []
    for word in words:
        if word.isdigit():
            digits.extend(word)
            continue
        digit = _DIGITS.get(word)
        if digit is None:
            raise SpeechError("Der Recovery-Schlüssel enthielt ein unbekanntes Wort.")
        digits.append(digit)
    if len(digits) != 48:
        raise SpeechError("Der Recovery-Schlüssel muss genau 48 Ziffern enthalten.")
    return "-".join("".join(digits[index:index + 4]) for index in range(0, 48, 4))


def format_recovery_key_for_speech(recovery_key: str) -> str:
    """Speak every recovery digit separately while preserving group pauses."""

    groups = recovery_key.split("-")
    if len(groups) != 12 or any(len(group) != 4 or not group.isdigit() for group in groups):
        raise ValueError("invalid recovery-key format")
    return "; ".join(" ".join(group) for group in groups)


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
            return _require_not_aborted(self.transcriber.transcribe(path).strip())
        finally:
            if path is not None:
                path.unlink(missing_ok=True)

    def collect(self, summary: str, challenge: str) -> ConfirmationResponse:
        try:
            self.speaker.speak(summary, language=self.language)
            self.speaker.speak(
                "Zum sofortigen lokalen Abbruch sagen Sie Abbrechen oder Stopp Clausis.",
                language=self.language,
            )
            phrase = self._listen()
            self.speaker.speak(
                "Sagen Sie jetzt Ihre PIN. Sie wird nicht vorgelesen oder gespeichert. "
                "Zum Abbrechen sagen Sie Abbrechen oder Stopp Clausis.",
                language=self.language,
            )
            pin = normalize_spoken_pin(self._listen())
            return ConfirmationResponse(phrase=phrase, pin=pin)
        except ConfirmationAborted:
            self.speaker.speak(
                "Die Bestätigung wurde lokal abgebrochen.", language=self.language
            )
            raise


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
        self.recorder = recorder or MicrophoneRecorder(
            RecordingOptions(max_seconds=90.0, silence_seconds=1.8)
        )
        self.transcriber = transcriber or LocalWhisper(
            model,
            language=language,
            initial_prompt=_RECOVERY_TRANSCRIPTION_PROMPT,
        )
        self.speaker = speaker or SystemSpeaker()
        self.challenge = challenge or InstallConfirmationChallenge()

    def _listen(self) -> str:
        path: Optional[Path] = None
        try:
            path = record_temporary(self.recorder)
            return _require_not_aborted(self.transcriber.transcribe(path).strip())
        finally:
            if path is not None:
                path.unlink(missing_ok=True)

    def authorize(self, summary: str, recovery_key: str) -> bool:
        spoken_key = format_recovery_key_for_speech(recovery_key)
        self.speaker.speak(
            f"{summary} Notieren Sie jetzt den einmaligen LUKS Recovery Schlüssel. "
            "Er wird nach dieser Installation nicht erneut angezeigt. "
            "Der Schlüssel folgt jetzt.",
            language=self.language,
        )
        self.speaker.speak(spoken_key, language=self.language)
        self.speaker.speak(
            "Ich wiederhole den Recovery Schlüssel jetzt.",
            language=self.language,
        )
        self.speaker.speak(spoken_key, language=self.language)
        self.speaker.speak(
            "Lesen Sie jetzt alle zwölf Vierergruppen von Ihrer Notiz vor. "
            "Zum sofortigen lokalen Abbruch sagen Sie Abbrechen oder Stopp Clausis.",
            language=self.language,
        )
        try:
            noted_key = normalize_spoken_recovery_key(self._listen())
        except ConfirmationAborted:
            self.speaker.speak(
                "Die Installation wurde lokal abgebrochen.", language=self.language
            )
            return False
        except SpeechError:
            noted_key = ""
        if not secrets.compare_digest(noted_key, recovery_key):
            self.speaker.speak(
                "Der notierte Recovery-Schlüssel stimmt nicht überein. "
                "Die Installation wurde abgebrochen.",
                language=self.language,
            )
            return False
        phrase = self.challenge.issue()
        self.speaker.speak(
            f"Der Recovery-Schlüssel wurde geprüft. Zum Bestätigen sagen Sie jetzt exakt: {phrase}. "
            "Zum lokalen Abbruch sagen Sie Abbrechen oder Stopp Clausis.",
            language=self.language,
        )
        try:
            approved = self.challenge.confirm(self._listen())
        except ConfirmationAborted:
            self.speaker.speak(
                "Die Installation wurde lokal abgebrochen.", language=self.language
            )
            return False
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
