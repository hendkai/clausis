"""Non-speech audio signals.

Speech is a poor way to say "I am listening now": it is slow, it talks over the
user, and after the tenth time it is noise.  Short distinguishable tones carry
the state instead, which is also what a user who has turned the speech rate up
needs.

The tones are synthesised locally with the standard library — no asset ships,
nothing is downloaded — and played through a fixed argument vector.  A machine
without a player simply stays silent here; an earcon is a hint, never the only
carrier of information, so every state it marks is also available as speech or
as a notification through :mod:`clausis.recovery`.
"""

from __future__ import annotations

import array
from enum import Enum
import math
from pathlib import Path
import shutil
import subprocess
import tempfile
from typing import Callable, Dict, Optional, Sequence, Tuple
import wave


SAMPLE_RATE = 22_050
PLAYERS = (("paplay",), ("aplay", "-q"))


class Earcon(str, Enum):
    WAKE = "wake"
    CONFIRM = "confirm"
    ERROR = "error"
    SLEEP = "sleep"


#: (frequency Hz, duration seconds) pairs.  Rising for attention, falling for
#: closing, a low double tone for failure: distinguishable without perfect
#: pitch and without hearing the difference between two similar beeps.
TONES: Dict[Earcon, Tuple[Tuple[float, float], ...]] = {
    Earcon.WAKE: ((660.0, 0.09), (880.0, 0.11)),
    Earcon.CONFIRM: ((880.0, 0.08), (1174.0, 0.10)),
    Earcon.ERROR: ((300.0, 0.13), (220.0, 0.17)),
    Earcon.SLEEP: ((660.0, 0.09), (440.0, 0.13)),
}


def render(earcon: Earcon, *, amplitude: float = 0.22) -> bytes:
    """Render one earcon as mono 16-bit PCM with short fades."""

    if not 0.0 < amplitude <= 1.0:
        raise ValueError("amplitude must be between 0 and 1")
    samples = array.array("h")
    for frequency, duration in TONES[earcon]:
        count = int(SAMPLE_RATE * duration)
        # A few milliseconds of fade at each end; a hard edge clicks, and a
        # click is exactly the kind of noise a hearing aid amplifies badly.
        fade = max(1, int(SAMPLE_RATE * 0.005))
        for index in range(count):
            envelope = min(1.0, index / fade, (count - index) / fade)
            value = math.sin(2.0 * math.pi * frequency * index / SAMPLE_RATE)
            samples.append(int(max(-1.0, min(1.0, value * envelope * amplitude)) * 32767))
    return samples.tobytes()


def write_wav(earcon: Earcon, path: Path) -> Path:
    with wave.open(str(path), "wb") as handle:
        handle.setnchannels(1)
        handle.setsampwidth(2)
        handle.setframerate(SAMPLE_RATE)
        handle.writeframes(render(earcon))
    return path


def _player(which: Callable[[str], Optional[str]] = shutil.which) -> Optional[Sequence[str]]:
    for candidate in PLAYERS:
        if which(candidate[0]):
            return candidate
    return None


class EarconPlayer:
    """Play earcons, or stay silent when no player exists."""

    def __init__(
        self,
        *,
        which: Callable[[str], Optional[str]] = shutil.which,
        runner: Optional[Callable[[Sequence[str]], object]] = None,
        directory: Optional[Path] = None,
    ) -> None:
        self.command = _player(which)
        self.runner = runner or self._run
        self._directory = directory
        self._temporary: Optional[tempfile.TemporaryDirectory] = None
        self._rendered: Dict[Earcon, Path] = {}

    @staticmethod
    def _run(command: Sequence[str]) -> object:
        return subprocess.run(
            list(command),
            shell=False,
            check=False,
            capture_output=True,
            timeout=10.0,
        )

    @property
    def available(self) -> bool:
        return self.command is not None

    def _path(self, earcon: Earcon) -> Path:
        if earcon in self._rendered:
            return self._rendered[earcon]
        if self._directory is None:
            self._temporary = tempfile.TemporaryDirectory(prefix="clausis-earcons-")
            self._directory = Path(self._temporary.name)
        path = write_wav(earcon, self._directory / f"{earcon.value}.wav")
        self._rendered[earcon] = path
        return path

    def close(self) -> None:
        """Remove the rendered tones; safe to call more than once."""

        if self._temporary is not None:
            self._temporary.cleanup()
            self._temporary = None
            self._directory = None
        self._rendered.clear()

    def __enter__(self) -> "EarconPlayer":
        return self

    def __exit__(self, *exc_info) -> None:
        self.close()

    def play(self, earcon: Earcon) -> bool:
        """Return whether the earcon was handed to a player."""

        if self.command is None:
            return False
        try:
            self.runner([*self.command, str(self._path(earcon))])
        except (OSError, subprocess.SubprocessError, ValueError):
            return False
        return True
