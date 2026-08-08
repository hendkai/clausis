"""Pre-rendered spoken prompts for the initramfs.

There is no speech-dispatcher, no PipeWire and no Python in an initramfs, so
the disk-unlock prompt cannot be synthesised at the moment it is needed.  It
has to exist as a plain WAV file before the system ever boots.

This module renders those files once, at package configuration time, with the
same offline voice the desktop uses.  When no synthesiser is available it still
writes the non-speech earcons, because a distinguishable tone at the passphrase
prompt is far better than a silent black screen for someone who cannot read it.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import shutil
import subprocess
from typing import Callable, Dict, List, Optional, Sequence

from .earcons import Earcon, write_wav


PROMPT_DIR = Path("/usr/share/clausis/boot-audio")
#: 22.05 kHz mono matches the earcons and is what a plain ALSA player in an
#: initramfs handles without resampling.
SAMPLE_RATE = 22_050

PROMPTS: Dict[str, str] = {
    "unlock": (
        "Clausis. Bitte geben Sie jetzt Ihr Festplatten-Passwort über die "
        "Tastatur ein und bestätigen Sie mit der Eingabetaste. "
        "Die Eingabe wird aus Sicherheitsgründen nicht vorgelesen."
    ),
    "unlock-retry": (
        "Das Passwort war nicht richtig. Bitte versuchen Sie es erneut. "
        "Mit dem notierten Wiederherstellungsschlüssel können Sie ebenfalls "
        "entsperren."
    ),
    "unlocked": "Der Datenträger ist entsperrt. Das System startet jetzt.",
    "recovery": (
        "Der Start ist fehlgeschlagen. Wählen Sie im Menü den "
        "Wiederherstellungseintrag, oder halten Sie die Umschalttaste beim "
        "Start gedrückt."
    ),
}

#: The earcon that accompanies each prompt, so the state is audible even when
#: no synthesiser was available at build time.
PROMPT_EARCONS: Dict[str, Earcon] = {
    "unlock": Earcon.WAKE,
    "unlock-retry": Earcon.ERROR,
    "unlocked": Earcon.CONFIRM,
    "recovery": Earcon.ERROR,
}

SYNTHESISERS = (
    ("espeak-ng", ("-v", "de", "-s", "150", "-w")),
    ("espeak", ("-v", "de", "-s", "150", "-w")),
)


@dataclass(frozen=True)
class RenderResult:
    spoken: List[str]
    earcons: List[str]
    synthesiser: Optional[str]

    @property
    def has_speech(self) -> bool:
        return bool(self.spoken)


def _synthesiser(which: Callable[[str], Optional[str]]) -> Optional[Sequence[str]]:
    for name, arguments in SYNTHESISERS:
        if which(name):
            return (name, *arguments)
    return None


def _run(command: Sequence[str]) -> "subprocess.CompletedProcess[str]":
    return subprocess.run(
        list(command),
        shell=False,
        check=False,
        capture_output=True,
        text=True,
        timeout=60.0,
        env={"PATH": "/usr/local/bin:/usr/bin:/bin", "LC_ALL": "C"},
    )


def render_prompts(
    destination: Path = PROMPT_DIR,
    *,
    which: Callable[[str], Optional[str]] = shutil.which,
    runner: Callable[[Sequence[str]], object] = _run,
) -> RenderResult:
    """Render every boot prompt to ``destination``; never raise on a failure.

    A missing synthesiser must not fail package configuration: the earcons are
    written regardless, and the caller can see from the result what was
    produced.
    """

    destination.mkdir(parents=True, exist_ok=True)
    spoken: List[str] = []
    earcons: List[str] = []

    for name, earcon in PROMPT_EARCONS.items():
        try:
            write_wav(earcon, destination / f"{name}-tone.wav")
            earcons.append(name)
        except OSError:
            continue

    command = _synthesiser(which)
    if command is None:
        return RenderResult(spoken, earcons, None)

    for name, text in PROMPTS.items():
        target = destination / f"{name}.wav"
        try:
            completed = runner([*command, str(target), text])
        except (OSError, subprocess.SubprocessError):
            continue
        if getattr(completed, "returncode", 1) == 0 and target.is_file() and target.stat().st_size:
            spoken.append(name)
    return RenderResult(spoken, earcons, command[0])


def main(argv: Sequence[str] = ()) -> int:
    import argparse

    parser = argparse.ArgumentParser(description="Render Clausis boot prompts")
    parser.add_argument("--destination", type=Path, default=PROMPT_DIR)
    args = parser.parse_args(list(argv) or None)
    result = render_prompts(args.destination)
    if result.has_speech:
        print(f"rendered {len(result.spoken)} spoken prompts with {result.synthesiser}")
    else:
        print("no speech synthesiser available; wrote earcons only")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
