"""Local audio capability and activation-state handling.

The controller deliberately stays independent from cloud or agent code.  A
transcript must pass this local gate before Hermes or GPT Live can see it.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
import json
import math
from pathlib import Path
import re
import time
from typing import Callable, Optional


class AudioMode(str, Enum):
    FULL_DUPLEX = "full_duplex"
    HALF_DUPLEX = "half_duplex"
    OUTPUT_ONLY = "output_only"
    UNAVAILABLE = "unavailable"


class ListeningState(str, Enum):
    SLEEPING = "sleeping"
    AWAKE = "awake"
    STOPPED = "stopped"


@dataclass(frozen=True)
class AudioCapabilities:
    microphone: bool
    speaker: bool
    shared_clock: bool = False
    echo_cancellation: bool = False
    hardware_certified: bool = False


@dataclass(frozen=True)
class AudioDecision:
    mode: AudioMode
    announcement: str
    barge_in: bool


@dataclass(frozen=True)
class ActivationResult:
    command: Optional[str]
    announcement: str = ""
    stopped: bool = False


def choose_audio_mode(capabilities: AudioCapabilities) -> AudioDecision:
    if not capabilities.speaker and not capabilities.microphone:
        return AudioDecision(AudioMode.UNAVAILABLE, "Audio ist nicht verfügbar. Tastatur und Orca bleiben aktiv.", False)
    if not capabilities.microphone:
        return AudioDecision(AudioMode.OUTPUT_ONLY, "Kein Mikrofon erkannt. Spracheingabe ist ausgeschaltet.", False)
    if not capabilities.speaker:
        return AudioDecision(AudioMode.HALF_DUPLEX, "Kein Lautsprecher erkannt. Antworten werden nur angezeigt.", False)
    if capabilities.hardware_certified and capabilities.shared_clock and capabilities.echo_cancellation:
        return AudioDecision(
            AudioMode.HALF_DUPLEX,
            "Vollduplex-Hardware wurde erkannt. Bis der lokale Unterbrechungsdetektor geprüft ist, verwendet Clausis sicheren Halbduplexbetrieb.",
            False,
        )
    return AudioDecision(
        AudioMode.HALF_DUPLEX,
        "Echounterdrückung ist nicht zertifiziert. Das System verwendet sicheren Halbduplexbetrieb.",
        False,
    )


def probe_audio_capabilities(
    certification_path: Path = Path("/etc/clausis/audio-certified.json"),
) -> AudioCapabilities:
    """Inspect local devices and accept duplex guarantees only from a marker.

    Device enumeration is best effort.  The certification marker is installed
    only for a tested hardware profile; detecting a microphone alone never
    upgrades a machine to full duplex.
    """

    microphone = False
    speaker = False
    try:
        import sounddevice as sd

        devices = sd.query_devices()
        microphone = any(int(device.get("max_input_channels", 0)) > 0 for device in devices)
        speaker = any(int(device.get("max_output_channels", 0)) > 0 for device in devices)
    except Exception:
        pass

    certified = False
    shared_clock = False
    echo_cancellation = False
    try:
        record = json.loads(certification_path.read_text(encoding="utf-8"))
        certified = record.get("certified") is True
        shared_clock = record.get("shared_clock") is True
        echo_cancellation = record.get("echo_cancellation") is True
    except (OSError, ValueError, TypeError):
        pass
    return AudioCapabilities(
        microphone=microphone,
        speaker=speaker,
        shared_clock=shared_clock,
        echo_cancellation=echo_cancellation,
        hardware_certified=certified,
    )


_SPOKEN_PUNCTUATION = re.compile(r"[,.:;!?-]+")


class LocalActivationController:
    """Deterministic wake, sleep and emergency-stop gate.

    The controller sees only local STT output.  Stop phrases work in every
    state, while arbitrary speech is discarded until a wake phrase is heard.
    """

    WAKE_PHRASES = ("clausis", "hallo clausis", "hey clausis", "hello clausis")
    STOP_PHRASES = (
        "stopp clausis",
        "clausis stopp",
        "stop clausis",
        "stopp hermes",
        "hermes stopp",
        "stop hermes",
    )
    SLEEP_PHRASES = (
        "geh schlafen",
        "nicht mehr zuhören",
        "stop listening",
        "go to sleep",
    )

    def __init__(
        self,
        *,
        active_seconds: float = 25.0,
        clock: Callable[[], float] = time.monotonic,
    ) -> None:
        if active_seconds <= 0:
            raise ValueError("active_seconds must be positive")
        self.active_seconds = active_seconds
        self._clock = clock
        self._deadline = 0.0
        self.state = ListeningState.SLEEPING

    @staticmethod
    def normalize(text: str) -> str:
        return " ".join(_SPOKEN_PUNCTUATION.sub(" ", text.casefold()).split())

    def ingest(self, transcript: str, *, bypass_wake: bool = False) -> ActivationResult:
        normalized = self.normalize(transcript)
        if not normalized:
            return ActivationResult(None)
        if normalized in self.STOP_PHRASES:
            self.state = ListeningState.STOPPED
            return ActivationResult("stopp hermes", "Clausis wurde lokal gestoppt.", True)
        if self.state is ListeningState.STOPPED:
            return ActivationResult(None)
        if self.state is ListeningState.AWAKE and self._clock() >= self._deadline:
            self.state = ListeningState.SLEEPING
        if normalized in self.SLEEP_PHRASES:
            self.sleep()
            return ActivationResult(None, "Clausis hört nur noch auf das Aktivierungswort.")
        if bypass_wake:
            self._activate()
            return ActivationResult(transcript.strip())

        wake_command = self._after_wake_phrase(normalized)
        if wake_command is not None:
            self._activate()
            if wake_command:
                return ActivationResult(wake_command)
            return ActivationResult(None, "Ja, ich höre zu.")
        if self.state is ListeningState.SLEEPING:
            return ActivationResult(None)
        self._activate()
        return ActivationResult(transcript.strip())

    def _activate(self) -> None:
        self.state = ListeningState.AWAKE
        self._deadline = self._clock() + self.active_seconds

    def extend_awake_for(self, seconds: float) -> None:
        """Keep the local gate awake for one bounded trusted follow-up window."""

        try:
            duration = float(seconds)
        except (TypeError, ValueError) as exc:
            raise ValueError("follow-up duration must be numeric") from exc
        if not math.isfinite(duration) or not 0.0 < duration <= 125.0:
            raise ValueError("follow-up duration must be between 0 and 125 seconds")
        if self.state is ListeningState.STOPPED:
            return
        now = self._clock()
        self.state = ListeningState.AWAKE
        self._deadline = max(self._deadline, now + duration)

    def sleep(self) -> None:
        """Close the local gate without reviving a controller that already stopped."""

        if self.state is ListeningState.STOPPED:
            return
        self.state = ListeningState.SLEEPING
        self._deadline = 0.0

    def _after_wake_phrase(self, normalized: str) -> Optional[str]:
        for phrase in sorted(self.WAKE_PHRASES, key=len, reverse=True):
            if normalized == phrase:
                return ""
            prefix = phrase + " "
            if normalized.startswith(prefix):
                return normalized[len(prefix):]
        return None
