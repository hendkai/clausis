"""Concrete local speech input and output adapters.

Optional native dependencies are imported lazily so the security core and the
installer recovery console continue to work without audio hardware.
"""

from __future__ import annotations

from dataclasses import dataclass
import shutil
import subprocess
import tempfile
import time
import wave
from pathlib import Path
from typing import Optional


class SpeechError(RuntimeError):
    """A recoverable microphone, transcription or speech-output failure."""


@dataclass(frozen=True)
class RecordingOptions:
    sample_rate: int = 16_000
    block_ms: int = 100
    start_timeout: float = 12.0
    silence_seconds: float = 1.2
    max_seconds: float = 25.0
    minimum_rms: float = 0.012


class MicrophoneRecorder:
    """Record one utterance with adaptive energy detection."""

    def __init__(self, options: RecordingOptions = RecordingOptions()) -> None:
        self.options = options

    def record(self, destination: Path) -> Path:
        try:
            import numpy as np
            import sounddevice as sd
        except ImportError as exc:  # pragma: no cover - depends on live image
            raise SpeechError("Audio-Pakete fehlen. Bitte Clausis-Audio reparieren.") from exc

        blocksize = int(self.options.sample_rate * self.options.block_ms / 1000)
        start_deadline = time.monotonic() + self.options.start_timeout
        max_blocks = int(self.options.max_seconds * 1000 / self.options.block_ms)
        silence_blocks = max(1, int(self.options.silence_seconds * 1000 / self.options.block_ms))
        frames = []
        noise_samples = []
        speaking = False
        quiet = 0

        try:
            with sd.InputStream(
                samplerate=self.options.sample_rate,
                channels=1,
                dtype="float32",
                blocksize=blocksize,
            ) as stream:
                for _ in range(max_blocks):
                    data, overflowed = stream.read(blocksize)
                    if overflowed:
                        continue
                    mono = data[:, 0].copy()
                    rms = float(np.sqrt(np.mean(np.square(mono), dtype=np.float64)))
                    if not speaking:
                        noise_samples.append(rms)
                        baseline = float(np.median(noise_samples[-20:]))
                        threshold = max(self.options.minimum_rms, baseline * 3.0)
                        if rms >= threshold:
                            speaking = True
                            frames.extend([mono])
                        elif time.monotonic() >= start_deadline:
                            raise SpeechError("Keine Sprache erkannt.")
                        continue
                    frames.append(mono)
                    if rms < threshold:
                        quiet += 1
                        if quiet >= silence_blocks:
                            break
                    else:
                        quiet = 0
        except SpeechError:
            raise
        except Exception as exc:  # sounddevice uses backend-specific errors
            raise SpeechError(f"Mikrofon nicht verfügbar: {exc}") from exc

        if not frames:
            raise SpeechError("Keine Sprache aufgenommen.")
        samples = np.clip(np.concatenate(frames), -1.0, 1.0)
        pcm = (samples * 32767.0).astype("<i2").tobytes()
        destination.parent.mkdir(parents=True, exist_ok=True)
        with wave.open(str(destination), "wb") as output:
            output.setnchannels(1)
            output.setsampwidth(2)
            output.setframerate(self.options.sample_rate)
            output.writeframes(pcm)
        return destination


class LocalWhisper:
    """Lazy Faster-Whisper transcription using a bundled or cached model."""

    def __init__(self, model: str, *, language: Optional[str] = None) -> None:
        self.model_name = model
        self.language = language
        self._model = None

    def transcribe(self, audio_path: Path) -> str:
        try:
            from faster_whisper import WhisperModel
        except ImportError as exc:  # pragma: no cover - depends on live image
            raise SpeechError("Lokale Spracherkennung ist nicht installiert.") from exc
        if self._model is None:
            self._model = WhisperModel(self.model_name, device="cpu", compute_type="int8")
        segments, _ = self._model.transcribe(
            str(audio_path), language=self.language, beam_size=3, vad_filter=True
        )
        return " ".join(segment.text.strip() for segment in segments).strip()


class SystemSpeaker:
    """Speak with the local speech service; never use a shell.

    ``speak`` blocks until the utterance is done (``spd-say -w``), which is
    right for short confirmations.  ``speak_async`` returns a handle whose
    ``wait`` blocks; long-running speech (say-all) uses it together with
    ``cancel`` so a spoken "Stopp" can end the audio at a chunk boundary.
    """

    def speak(self, text: str, *, language: str = "de") -> None:
        if not text.strip():
            return
        commands = []
        if shutil.which("spd-say"):
            commands.append(["spd-say", "-w", "-l", language, text])
        if shutil.which("espeak-ng"):
            commands.append(["espeak-ng", "-v", language, text])
        if shutil.which("say"):
            commands.append(["say", text])
        for command in commands:
            try:
                completed = subprocess.run(command, shell=False, check=False, timeout=120)
            except (OSError, subprocess.SubprocessError):
                continue
            if completed.returncode == 0:
                return
        raise SpeechError("Keine lokale Sprachausgabe verfügbar.")

    def speak_async(self, text: str, *, language: str = "de"):
        """Speak without blocking the caller; return an utterance handle.

        The handle's ``wait()`` blocks until the utterance finished (or was
        cancelled); ``is_done`` reports the same without blocking.  Only the
        speech-dispatcher path supports cancellation, so it is the only one
        offered asynchronously: falling back to a blocking engine for a
        say-all would mute the stop command for minutes.
        """

        if not text.strip():
            return _CompletedUtterance()
        if not shutil.which("spd-say"):
            raise SpeechError("Keine lokale Sprachausgabe verfügbar.")
        try:
            # -w makes spd-say block until speech-dispatcher finished (or the
            # output was cancelled), so process exit is the utterance signal.
            process = subprocess.Popen(
                ["spd-say", "-w", "-l", language, text],
                shell=False,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
        except OSError as exc:
            raise SpeechError("Keine lokale Sprachausgabe verfügbar.") from exc
        return _AsyncUtterance(process)

    def cancel(self) -> None:
        """Stop the current speech output (speech-dispatcher cancel).

        Fixed vector, no shell.  Silently a no-op when speech-dispatcher is
        not installed; on the live image it always is.
        """

        if not shutil.which("spd-say"):
            return
        try:
            subprocess.run(
                ["spd-say", "-C"],
                shell=False,
                check=False,
                timeout=15,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
        except (OSError, subprocess.SubprocessError):
            return


class _CompletedUtterance:
    """Handle of an empty utterance: already finished."""

    is_done = True

    def wait(self, timeout: Optional[float] = None) -> None:
        del timeout


class _AsyncUtterance:
    """Handle of a running ``spd-say -w`` process."""

    def __init__(self, process: subprocess.Popen) -> None:
        self._process = process

    @property
    def is_done(self) -> bool:
        return self._process.poll() is not None

    def wait(self, timeout: Optional[float] = None) -> None:
        try:
            self._process.wait(timeout=timeout)
        except subprocess.TimeoutExpired:
            pass


def record_temporary(recorder: MicrophoneRecorder) -> Path:
    """Record into a private temporary file that the caller must delete."""
    handle = tempfile.NamedTemporaryFile(prefix="clausis-", suffix=".wav", delete=False)
    handle.close()
    path = Path(handle.name)
    try:
        path.chmod(0o600)
        return recorder.record(path)
    except Exception:
        path.unlink(missing_ok=True)
        raise
