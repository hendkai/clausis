"""Boot health checks used by snapshot rollback integration.

The check separates two questions that a single "healthy" flag used to blur:
whether an update broke something a rollback can repair, and whether this
machine currently lacks a capability such as a microphone.  A missing
microphone is a degraded capability with a documented recovery path, not a
reason to roll the system back.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import shutil
from typing import Callable, Dict, List, Optional, Sequence

from .recovery import Failure, recovery_for
from .subvolumes import mounted_subvolumes, validate_present


REQUIRED = ("wpctl", "systemctl", "loginctl", "gio")
OPTIONAL = ("nmcli", "gtk-launch", "gnome-control-center", "orca")
#: Any one of these is enough to speak.
SPEECH_BINARIES = ("spd-say", "espeak-ng", "espeak")
STT_MODEL = Path("/usr/share/clausis/models/faster-whisper-base")
#: Piper neural voice (image-build-time artifacts); missing files degrade
#: the voice quality to the espeak-ng fallback, they never break speech.
TTS_MODEL = Path("/usr/share/clausis/models/piper")


def _microphone(probe: Optional[Callable[[], object]] = None) -> bool:
    try:
        from .audio import probe_audio_capabilities

        capabilities = (probe or probe_audio_capabilities)()
        return bool(getattr(capabilities, "microphone", False))
    except Exception:
        return False


def _layout(mounts_path: Path) -> Dict[str, object]:
    try:
        mounts = mounts_path.read_text(encoding="utf-8")
    except OSError:
        return {"complete": False, "missing": [], "rollback_safe": False, "exposed": []}
    return validate_present(mounted_subvolumes(mounts))


def collect(
    *,
    model_path: Path = STT_MODEL,
    tts_model_path: Path = TTS_MODEL,
    probe: Optional[Callable[[], object]] = None,
    which: Callable[[str], Optional[str]] = shutil.which,
    mounts_path: Path = Path("/proc/self/mounts"),
) -> Dict[str, object]:
    required = {name: bool(which(name)) for name in REQUIRED}
    optional = {name: bool(which(name)) for name in OPTIONAL}
    speech = any(which(name) for name in SPEECH_BINARIES)
    model = model_path.is_dir()
    tts_model = (tts_model_path / "de_DE-thorsten-medium.onnx").is_file()
    microphone = _microphone(probe)

    # Only components an update can break drive the rollback recommendation.
    # A missing Piper voice model is NOT one: speech-dispatcher falls back
    # to espeak-ng, so speech keeps working (documented in BLIND §6).
    repairable = all(required.values()) and speech and model
    failures: List[str] = []
    if not speech:
        failures.append(Failure.NO_SPEECH_OUTPUT.value)
    if not model:
        failures.append(Failure.STT_UNAVAILABLE.value)
    if not microphone:
        failures.append(Failure.NO_MICROPHONE.value)
    if not tts_model:
        failures.append(Failure.NEURAL_VOICE_UNAVAILABLE.value)

    # Layout drift is reported, never used to recommend a rollback: a machine
    # installed by an older image is not a broken update.
    layout = _layout(mounts_path)

    return {
        "subvolumes": layout,
        "healthy": repairable and microphone,
        "required": required,
        "optional": optional,
        "speech_output": speech,
        "stt_model": model,
        "microphone": microphone,
        "rollback_recommended": not repairable,
        "failures": failures,
        "recovery": [recovery_for(Failure(name)).message() for name in failures],
    }


def main(argv: Sequence[str] = ()) -> int:
    parser = argparse.ArgumentParser(description="Check Clausis boot health")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args(list(argv) or None)
    result = collect()
    if args.json:
        print(json.dumps(result, sort_keys=True))
    else:
        print("healthy" if result["healthy"] else "degraded")
        for line in result["recovery"]:
            print(line)
    return 0 if result["healthy"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
