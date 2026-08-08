"""Dedicated low-load wake-word detection.

Until now the wake phrase was recognised by running full speech-to-text on
everything the microphone heard and matching the transcript.  That works, but
it keeps a transcription model busy around the clock, which is the opposite of
"niedrige Dauerlast", and it cannot react before a whole utterance has ended.

This module adds the cheap first stage: an energy gate that costs almost
nothing per frame, and behind it a small keyword model that only runs on frames
that could plausibly contain speech.  Everything degrades honestly — without a
configured model, :class:`WakeWordGate` reports itself unavailable and the
caller keeps using the existing transcript gate rather than silently listening
for nothing.
"""

from __future__ import annotations

import array
from dataclasses import dataclass
import math
from pathlib import Path
from typing import Optional, Protocol


MODEL_DIR = Path("/usr/share/clausis/models/wake")
PLACEHOLDER_MARKER = "CLAUSIS-PLACEHOLDER-NO-WAKE-MODEL"
#: 16 kHz mono int16 is what both the energy gate and the keyword models expect.
SAMPLE_RATE = 16_000
FRAME_MS = 80
DEFAULT_THRESHOLD = 0.6
#: Consecutive speech-like frames required before the model is consulted.  One
#: frame of noise is not speech; three in a row usually is.
SPEECH_FRAMES = 3


def frame_rms(frame: bytes) -> float:
    """Return the RMS of a mono int16 frame, normalised to 0..1."""

    if not frame:
        return 0.0
    samples = array.array("h")
    usable = len(frame) - (len(frame) % 2)
    samples.frombytes(frame[:usable])
    if not samples:
        return 0.0
    total = 0
    for sample in samples:
        total += sample * sample
    return math.sqrt(total / len(samples)) / 32768.0


class EnergyGate:
    """Reject silence before any model runs.

    This is the part that keeps the permanent listener cheap: a multiply and an
    add per sample, and no inference at all while the room is quiet.
    """

    def __init__(self, *, threshold: float = 0.012, speech_frames: int = SPEECH_FRAMES) -> None:
        if not 0.0 < threshold < 1.0:
            raise ValueError("threshold must be between 0 and 1")
        self.threshold = threshold
        self.speech_frames = max(1, speech_frames)
        self._consecutive = 0

    def reset(self) -> None:
        self._consecutive = 0

    def accepts(self, frame: bytes) -> bool:
        if frame_rms(frame) < self.threshold:
            self._consecutive = 0
            return False
        self._consecutive += 1
        return self._consecutive >= self.speech_frames


class WakeWordDetector(Protocol):
    def score(self, frame: bytes) -> float:
        ...


def wake_model_is_configured(directory: Path = MODEL_DIR) -> bool:
    """Return whether a real keyword model, not the placeholder, is installed."""

    try:
        if not directory.is_dir():
            return False
        entries = sorted(directory.iterdir())
    except OSError:
        return False
    models = [item for item in entries if item.suffix in {".onnx", ".tflite"}]
    if not models:
        return False
    readme = directory / "README"
    try:
        if readme.is_file() and PLACEHOLDER_MARKER in readme.read_text(
            encoding="utf-8", errors="replace"
        ):
            return False
    except OSError:
        return False
    return True


class OpenWakeWordDetector:
    """Adapter for an openWakeWord model, imported lazily.

    The model weights are not bundled: they carry their own licence and have to
    be chosen for the actual wake phrase.  A missing runtime or model is not an
    error here, it simply means the gate stays unavailable.
    """

    def __init__(self, directory: Path = MODEL_DIR) -> None:
        try:
            from openwakeword.model import Model
        except ImportError as exc:  # pragma: no cover - depends on live image
            raise RuntimeError("openWakeWord ist nicht installiert") from exc
        if not wake_model_is_configured(directory):
            raise RuntimeError("kein Wake-Word-Modell konfiguriert")
        paths = [
            str(item)
            for item in sorted(directory.iterdir())
            if item.suffix in {".onnx", ".tflite"}
        ]
        self._model = Model(wakeword_models=paths)

    def score(self, frame: bytes) -> float:
        samples = array.array("h")
        usable = len(frame) - (len(frame) % 2)
        samples.frombytes(frame[:usable])
        predictions = self._model.predict(samples)
        try:
            return float(max(predictions.values())) if predictions else 0.0
        except (AttributeError, TypeError, ValueError):
            return 0.0


@dataclass(frozen=True)
class WakeEvent:
    detected: bool
    score: float


class WakeWordGate:
    """Energy gate plus keyword model, with an honest unavailable state."""

    def __init__(
        self,
        detector: Optional[WakeWordDetector] = None,
        *,
        threshold: float = DEFAULT_THRESHOLD,
        energy: Optional[EnergyGate] = None,
    ) -> None:
        if not 0.0 < threshold <= 1.0:
            raise ValueError("threshold must be between 0 and 1")
        self.detector = detector
        self.threshold = threshold
        self.energy = energy or EnergyGate()

    @classmethod
    def from_model(cls, directory: Path = MODEL_DIR, **kwargs) -> "WakeWordGate":
        """Build a gate, or an unavailable one when no model is configured."""

        try:
            return cls(OpenWakeWordDetector(directory), **kwargs)
        except RuntimeError:
            return cls(None, **kwargs)

    def available(self) -> bool:
        return self.detector is not None

    def push(self, frame: bytes) -> WakeEvent:
        """Feed one frame and report whether the wake word was heard."""

        if self.detector is None:
            return WakeEvent(False, 0.0)
        if not self.energy.accepts(frame):
            return WakeEvent(False, 0.0)
        try:
            score = float(self.detector.score(frame))
        except Exception:
            # A failing model must not take the voice session with it; the
            # caller falls back to the transcript gate.
            return WakeEvent(False, 0.0)
        if score >= self.threshold:
            self.energy.reset()
            return WakeEvent(True, score)
        return WakeEvent(False, score)


class WakeListener:
    """Wait for the wake word on a stream of frames.

    The frame source is injected so the same logic runs against a microphone in
    the live image and against a fixed sequence in the tests.  Returning
    ``False`` on an exhausted or failing source is deliberate: the caller then
    falls back to the transcript gate instead of blocking forever.
    """

    def __init__(
        self,
        gate: WakeWordGate,
        read_frame,
        *,
        on_detect=None,
        clock=None,
    ) -> None:
        self.gate = gate
        self.read_frame = read_frame
        self.on_detect = on_detect
        import time as _time

        self.clock = clock or _time.monotonic

    def wait(self, *, timeout: Optional[float] = None) -> bool:
        if not self.gate.available():
            return False
        deadline = None if timeout is None else self.clock() + timeout
        while deadline is None or self.clock() < deadline:
            try:
                frame = self.read_frame()
            except Exception:
                return False
            if not frame:
                return False
            if self.gate.push(frame).detected:
                if self.on_detect is not None:
                    self.on_detect()
                return True
        return False


def microphone_frames(sample_rate: int = SAMPLE_RATE, frame_ms: int = FRAME_MS):
    """Yield a callable that reads one int16 frame from the default microphone.

    Imported lazily, so a machine without the audio stack still imports this
    module and simply reports the gate as unavailable.
    """

    import numpy as np
    import sounddevice as sd

    blocksize = int(sample_rate * frame_ms / 1000)
    stream = sd.InputStream(
        samplerate=sample_rate, channels=1, dtype="float32", blocksize=blocksize
    )
    stream.start()

    def read() -> bytes:
        data, overflowed = stream.read(blocksize)
        if overflowed:
            return bytes(blocksize * 2)
        mono = np.clip(data[:, 0], -1.0, 1.0)
        return (mono * 32767.0).astype("<i2").tobytes()

    return read, stream
