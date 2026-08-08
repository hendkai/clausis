"""Local interruption detection for real barge-in.

Barge-in means the user can talk over Clausis and be heard.  The hard part is
not detecting speech, it is not detecting *Clausis itself*: without echo
cancellation the microphone hears the speaker, and the assistant interrupts its
own sentence forever.

So the detector refuses to arm unless the machine actually has certified echo
cancellation.  On everything else Clausis keeps the honest half-duplex
behaviour it already announces, instead of promising full duplex it cannot
deliver.  The decision is local and needs no cloud, which is why an
interruption also works with no network at all.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Optional

from .audio import AudioCapabilities
from .wake import frame_rms


#: How far above the measured room noise a frame must be to count as speech
#: while Clausis is talking.  Deliberately higher than the wake-word gate: the
#: room is loud during playback, so the bar for "someone is talking over me"
#: has to be correspondingly higher.
INTERRUPT_MARGIN = 3.0
MIN_INTERRUPT_LEVEL = 0.03
#: Consecutive loud frames before speech is accepted as an interruption. At the
#: 80 ms frame size that is roughly a quarter of a second of continuous speech,
#: which a cough or a door does not produce.
INTERRUPT_FRAMES = 3


class BargeInUnavailable(RuntimeError):
    """The machine cannot support barge-in without hearing itself."""


@dataclass(frozen=True)
class InterruptEvent:
    interrupted: bool
    level: float


def barge_in_supported(capabilities: AudioCapabilities) -> bool:
    """Barge-in needs a microphone, echo cancellation and a certified profile."""

    return bool(
        capabilities.microphone
        and capabilities.speaker
        and capabilities.echo_cancellation
        and capabilities.hardware_certified
    )


class BargeInDetector:
    """Detect the user talking over the assistant, or refuse to try."""

    def __init__(
        self,
        capabilities: AudioCapabilities,
        *,
        noise_floor: float = 0.01,
        frames: int = INTERRUPT_FRAMES,
    ) -> None:
        if not barge_in_supported(capabilities):
            raise BargeInUnavailable(
                "Ohne zertifizierte Echounterdrückung würde Clausis sich selbst "
                "unterbrechen. Es bleibt beim sicheren Halbduplexbetrieb."
            )
        self.capabilities = capabilities
        self.noise_floor = max(noise_floor, 1e-6)
        self.frames = max(1, frames)
        self._consecutive = 0

    @property
    def level(self) -> float:
        return max(self.noise_floor * INTERRUPT_MARGIN, MIN_INTERRUPT_LEVEL)

    def reset(self) -> None:
        self._consecutive = 0

    def observe_noise(self, frame: bytes) -> None:
        """Track the quiet-room level so the threshold follows the room."""

        measured = frame_rms(frame)
        self.noise_floor = max(1e-6, 0.9 * self.noise_floor + 0.1 * measured)

    def push(self, frame: bytes) -> InterruptEvent:
        measured = frame_rms(frame)
        if measured < self.level:
            self._consecutive = 0
            return InterruptEvent(False, measured)
        self._consecutive += 1
        if self._consecutive >= self.frames:
            self._consecutive = 0
            return InterruptEvent(True, measured)
        return InterruptEvent(False, measured)


class InterruptibleSpeaker:
    """Speak, and stop immediately when the user talks over the assistant.

    Without a detector this is a plain speaker, so the same call site works on
    every machine and half-duplex hardware simply never interrupts.
    """

    def __init__(
        self,
        speaker,
        *,
        detector: Optional[BargeInDetector] = None,
        read_frame: Optional[Callable[[], bytes]] = None,
        stop: Optional[Callable[[], None]] = None,
    ) -> None:
        self.speaker = speaker
        self.detector = detector
        self.read_frame = read_frame
        self.stop = stop
        self.interrupted = False

    def speak(self, text: str, *, language: str = "de") -> bool:
        """Return whether the utterance completed without being interrupted."""

        self.interrupted = False
        if self.detector is None or self.read_frame is None:
            self.speaker.speak(text, language=language)
            return True

        self.detector.reset()
        self.speaker.speak(text, language=language)
        while True:
            frame = self.read_frame()
            if not frame:
                return not self.interrupted
            if self.detector.push(frame).interrupted:
                self.interrupted = True
                if self.stop is not None:
                    self.stop()
                return False
