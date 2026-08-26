"""Offline neural speech output via Piper as a speech-dispatcher module.

Clausis speaks through speech-dispatcher contracts only (``spd-say -w`` for
say-all, cancel via ``spd-say -C``).  Piper therefore enters the system as a
generic speech-dispatcher output module (``sd_generic`` ships with Debian's
speech-dispatcher package): a ``piper-generic.conf`` in
``/etc/speech-dispatcher/modules/`` plus pinned artifacts installed at image
build time.  There is deliberately no second parallel TTS stack — that would
duplicate and break the say-all cancel mechanics.

Debian 13 (trixie) has no Piper TTS package (the ``piper`` package there is an
unrelated GTK mouse-configuration app), so both the static Piper release
tarball and the German voice model are fetched during image build with pinned
SHA-256 checksums — never at runtime.  See DESIGN in this module and
docs/BLIND_USE_GAP_ANALYSIS.md §6.
"""

from __future__ import annotations

import argparse
from dataclasses import dataclass
from pathlib import Path
from typing import Sequence


PIPER_RELEASE = "2023.11.14-2"
#: Static upstream release tarball (piper binary + bundled espeak-ng-data).
PIPER_TARBALL_URL = (
    "https://github.com/rhasspy/piper/releases/download/"
    f"{PIPER_RELEASE}/piper_linux_x86_64.tar.gz"
)
PIPER_TARBALL_SHA256 = (
    "a50cb45f355b7af1f6d758c1b360717877ba0a398cc8cbe6d2a7a3a26e225992"
)
#: Piper itself is MIT-licensed (rhasspy/piper).
PIPER_LICENSE = "MIT"
#: The German voice model and its training dataset are CC0 (Thorsten-Voice).
MODEL_LICENSE = "CC0"

MODEL_NAME = "de_DE-thorsten-medium"
MODEL_URL = (
    "https://huggingface.co/rhasspy/piper-voices/resolve/main/"
    f"de/de_DE/thorsten/medium/{MODEL_NAME}.onnx"
)
MODEL_SHA256 = (
    "7e64762d8e5118bb578f2eea6207e1a35a8e0c30595010b666f983fc87bb7819"
)
MODEL_CONFIG_URL = f"{MODEL_URL}.json"
#: Hash of the small .onnx.json sidecar (speech-dispatcher never reads it;
#: piper refuses to start without it, so it is shipped and pinned as well).
MODEL_CONFIG_SHA256 = (
    "974adee790533adb273a1ac88f49027d2a1b8f0f2cf4905954a4791e79264e85"
)
MODEL_CARD_URL = (
    "https://huggingface.co/rhasspy/piper-voices/raw/main/"
    "de/de_DE/thorsten/medium/MODEL_CARD"
)

#: Where the build hook unpacks the piper tree (binary + libs + espeak-ng-data).
PIPER_HOME = Path("/opt/piper")
#: Where the build hook installs the voice model files.
MODEL_DIR = Path("/usr/share/clausis/models/piper")
#: speech-dispatcher looks for module configs here (Debian trixie layout).
SPEECHD_MODULES_DIR = Path("/etc/speech-dispatcher/modules")
#: System-wide client/server defaults (DefaultModule line lands here).
SPEECHD_CONF = Path("/etc/speech-dispatcher/speechd.conf")

#: The generic module registers under this name; spd-say -o piper-generic.
MODULE_NAME = "piper-generic"
#: The documented fallback when piper or its model is unavailable.
FALLBACK_MODULE = "espeak-ng"

#: speechd passes the SSIP rate (-100..100) through
#: ``rate * GenericRateMultiply + GenericRateAdd`` into ``$RATE``.
#: GenericRateAdd is a raw integer, GenericRateMultiply is written in
#: hundredths (module_utils.h divides by 100), so the finest slope is 0.01:
#: length-scale = 1 - 0.01 * rate.  rate 0 → 1.0 (model default), +50 → 0.5
#: (fast), -50 → 1.5 (slow); the command line clamps the ends to [0.5, 1.5]
#: so the unreachable-slope corner (rate +100 → 0.0) can never reach piper.
#: ForceInteger stays off — $RATE must remain a float string.
RATE_ADD = 1
RATE_MULTIPLY = -1
RATE_FORCE_INTEGER = 0
#: Hard limits for --length-scale applied inside GenericExecuteSynth.
RATE_MIN = 0.5
RATE_MAX = 1.5


@dataclass(frozen=True)
class Artifact:
    """One downloadable, checksum-pinned build-time artifact."""

    url: str
    sha256: str
    destination: Path
    license_ref: str


def artifacts() -> tuple[Artifact, ...]:
    """The pinned artifacts the image build must fetch and verify."""

    return (
        Artifact(PIPER_TARBALL_URL, PIPER_TARBALL_SHA256, PIPER_HOME, PIPER_LICENSE),
        Artifact(
            MODEL_URL,
            MODEL_SHA256,
            MODEL_DIR / f"{MODEL_NAME}.onnx",
            MODEL_LICENSE,
        ),
        Artifact(
            MODEL_CONFIG_URL,
            MODEL_CONFIG_SHA256,
            MODEL_DIR / f"{MODEL_NAME}.onnx.json",
            MODEL_LICENSE,
        ),
    )


def module_config(*, piper_home: Path = PIPER_HOME, model_dir: Path = MODEL_DIR) -> str:
    """Render the speech-dispatcher generic module configuration.

    ``sd_generic`` substitutes ``$DATA`` (already shell-escaped), ``$RATE``,
    ``$PITCH`` and ``$PLAY_COMMAND`` (the audio backend's player, e.g.
    ``paplay -n speech-dispatcher-generic`` under PipeWire/PulseAudio).
    Piper writes raw PCM to stdout; $PLAY_COMMAND consumes it.  The command
    must die with SIGKILL on stop — a plain pipe chain does.
    """

    piper = (piper_home / "piper").as_posix()
    model = (model_dir / f"{MODEL_NAME}.onnx").as_posix()
    return f"""\
# Piper neural speech output as a speech-dispatcher generic module.
# Generated by Clausis (src/clausis/piper_tts.py) — do not edit by hand;
# regenerate with: python3 -m clausis.piper_tts --write-module-config
#
# Piper: MIT license, https://github.com/rhasspy/piper (release {PIPER_RELEASE})
# Voice de_DE-thorsten-medium: CC0, https://github.com/thorstenMueller/Thorsten-Voice
# Docs: docs/BLIND_USE_GAP_ANALYSIS.md §6, docs/licenses/piper.md

Debug 0

GenericExecuteSynth \\
"printf %s '$DATA' | {piper} --model {model} --output-raw --length-scale `awk -v r=$RATE 'BEGIN {{ if (r < {RATE_MIN}) print {RATE_MIN}; else if (r > {RATE_MAX}) print {RATE_MAX}; else print r }}'` | $PLAY_COMMAND"

GenericCmdDependency "piper"
GenericCmdDependency "paplay"

GenericLanguage "de" "de"

# VoiceFileDependency must come BEFORE AddVoice (dotconf is sequential):
# with the model file missing, AddVoice is skipped, the module exposes no
# German voice and speech-dispatcher falls back to another module.
VoiceFileDependency "{model}"

AddVoice "de" "MALE1" "{MODEL_NAME}"
DefaultVoice "{MODEL_NAME}"

# SSIP rate -100..100 → length-scale 1 - 0.01*rate, clamped to [0.5, 1.5]
# in the command line; rate 0 keeps the model default.  GenericRateAdd is a
# raw integer, GenericRateMultiply is hundredths (-1 → -0.01).  Piper has no
# pitch/volume controls.
GenericRateAdd {RATE_ADD}
GenericRateMultiply {RATE_MULTIPLY}
GenericRateForceInteger {RATE_FORCE_INTEGER}
"""


def speechd_conf_lines(
    *, module: str = MODULE_NAME, fallback: str = FALLBACK_MODULE
) -> list[str]:
    """Lines to append to /etc/speech-dispatcher/speechd.conf.

    ``LanguageDefaultModule "de" "piper-generic"`` makes German clients
    (spd-say -l de, Orca) prefer Piper without touching other languages.
    There is deliberately no ``DefaultModule`` line: speech-dispatcher
    0.12 does not fall back from a dead DefaultModule to other modules for
    already-connected clients, so pinning the default to piper-generic would
    risk silence; language-default plus the server's own module fallback
    (any working module, then always-loaded espeak-ng-fallback, then dummy)
    keeps espeak-ng the honest fallback (design decision 4).
    """

    return [
        "# Clausis: prefer the Piper neural voice for German; fall back to",
        f"# {fallback} (speech-dispatcher module fallback, espeak-ng-fallback",
        "# is always force-loaded by the server).",
        f'LanguageDefaultModule "{module_language(module)}" "{module}"',
    ]


def module_language(module: str) -> str:
    """Language key used with LanguageDefaultModule for a module name."""

    return "de"


def speechd_conf_removals() -> list[str]:
    """speechd.conf lines that must not survive (stale directives)."""

    return ["DefaultModule piper-generic"]


def main(argv: Sequence[str] = ()) -> int:
    """Print or write the generated module configuration (build tooling)."""

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--write-module-config", action="store_true")
    args = parser.parse_args(list(argv) or None)
    if args.write_module_config:
        print(module_config(), end="")
        return 0
    parser.print_help()
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
