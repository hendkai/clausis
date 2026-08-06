"""Audio mode selection independent from a concrete PipeWire binding."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class AudioMode(str, Enum):
    FULL_DUPLEX = "full_duplex"
    HALF_DUPLEX = "half_duplex"
    OUTPUT_ONLY = "output_only"
    UNAVAILABLE = "unavailable"


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


def choose_audio_mode(capabilities: AudioCapabilities) -> AudioDecision:
    if not capabilities.speaker and not capabilities.microphone:
        return AudioDecision(AudioMode.UNAVAILABLE, "Audio ist nicht verfügbar. Tastatur und Orca bleiben aktiv.", False)
    if not capabilities.microphone:
        return AudioDecision(AudioMode.OUTPUT_ONLY, "Kein Mikrofon erkannt. Spracheingabe ist ausgeschaltet.", False)
    if not capabilities.speaker:
        return AudioDecision(AudioMode.HALF_DUPLEX, "Kein Lautsprecher erkannt. Antworten werden nur angezeigt.", False)
    if capabilities.hardware_certified and capabilities.shared_clock and capabilities.echo_cancellation:
        return AudioDecision(AudioMode.FULL_DUPLEX, "Vollduplex-Sprache ist aktiv.", True)
    return AudioDecision(
        AudioMode.HALF_DUPLEX,
        "Echounterdrückung ist nicht zertifiziert. Das System verwendet sicheren Halbduplexbetrieb.",
        True,
    )

