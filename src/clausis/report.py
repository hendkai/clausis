"""A diagnostic report a blind tester can produce without seeing the screen.

Community feedback is the project's chosen validation path, and a report that
says only "it did not work" cannot be acted on.  This builds the report
instead: what the machine is, which capabilities were detected, which
components are degraded, and what Clausis last did — with a spoken summary so
the person filing it knows what they are about to share.

Privacy is the constraint that shapes everything here.  A report leaves the
machine, so it must never contain what the user said, what they wrote, which
files they have, or any secret.  The audit log is summarised by action name and
status only; transcripts, targets and arguments are dropped, not redacted,
because a redacted field still tells an attacker that it existed.
"""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
import json
import os
from pathlib import Path
import platform
import shutil
from typing import Callable, Dict, Optional, Sequence

from . import __version__
from .subvolumes import mounted_subvolumes, validate_present


AUDIT_LOG = Path("/var/log/clausis/actions.jsonl")
MAX_AUDIT_LINES = 2000
#: Only these fields of an audit record may ever appear in a report.
AUDIT_FIELDS = ("action", "status")


@dataclass(frozen=True)
class Report:
    payload: Dict[str, object]

    def to_json(self) -> str:
        return json.dumps(self.payload, indent=2, sort_keys=True, ensure_ascii=False)

    def spoken(self) -> str:
        """A summary the tester hears before deciding whether to share it."""

        system = self.payload.get("system", {})
        health = self.payload.get("health", {})
        actions = self.payload.get("recent_actions", {})
        parts = [
            f"Clausis Version {self.payload.get('clausis_version', 'unbekannt')} "
            f"auf {system.get('distribution', 'unbekanntem System')}.",
        ]
        failures = health.get("failures") or []
        if failures:
            parts.append(
                "Eingeschränkt: " + ", ".join(str(item) for item in failures) + "."
            )
        else:
            parts.append("Es wurden keine eingeschränkten Komponenten gefunden.")
        total = sum(actions.values()) if isinstance(actions, dict) else 0
        parts.append(
            f"Der Bericht enthält {total} zusammengefasste Aktionen, "
            "aber keine Aufnahmen, keine Texte und keine Dateinamen."
        )
        return " ".join(parts)


def _distribution() -> str:
    try:
        for line in Path("/etc/os-release").read_text(encoding="utf-8").splitlines():
            if line.startswith("PRETTY_NAME="):
                return line.partition("=")[2].strip().strip('"')[:120]
    except OSError:
        pass
    return platform.system()


def summarise_audit(
    path: Path = AUDIT_LOG, *, limit: int = MAX_AUDIT_LINES
) -> Dict[str, int]:
    """Count recent actions by name and status; never quote their contents.

    A voice assistant's log is a record of someone's day.  Counting is enough
    to see that, say, every ``desktop.control.activate`` failed, which is what a
    maintainer needs; the target it was aimed at is not.
    """

    counter: Counter = Counter()
    try:
        lines = path.read_text(encoding="utf-8", errors="replace").splitlines()[-limit:]
    except OSError:
        return {}
    for line in lines:
        try:
            record = json.loads(line)
        except ValueError:
            continue
        if not isinstance(record, dict):
            continue
        request = record.get("request") if isinstance(record.get("request"), dict) else record
        result = record.get("result") if isinstance(record.get("result"), dict) else record
        action = request.get("action") if isinstance(request, dict) else None
        status = result.get("status") if isinstance(result, dict) else None
        if isinstance(action, str) and isinstance(status, str):
            counter[f"{action}:{status}"] += 1
    return dict(sorted(counter.items()))


def build_report(
    *,
    health: Optional[Callable[[], dict]] = None,
    audit_path: Path = AUDIT_LOG,
    mounts_path: Path = Path("/proc/self/mounts"),
    which: Callable[[str], Optional[str]] = shutil.which,
) -> Report:
    if health is None:
        from .healthcheck import collect

        health = collect
    try:
        health_report = dict(health())
    except Exception as exc:
        health_report = {"error": type(exc).__name__}
    # Drop the spoken recovery sentences: they are for the user, not for a bug
    # tracker, and they make the report needlessly long.
    health_report.pop("recovery", None)
    # Reported once, at the top level, from the injectable mounts path.
    health_report.pop("subvolumes", None)

    try:
        layout = validate_present(
            mounted_subvolumes(mounts_path.read_text(encoding="utf-8"))
        )
    except OSError:
        layout = {"complete": False, "missing": [], "rollback_safe": False, "exposed": []}

    return Report(
        {
            "clausis_version": __version__,
            "system": {
                "distribution": _distribution(),
                "kernel": platform.release(),
                "architecture": platform.machine(),
                "python": platform.python_version(),
                "desktop": os.environ.get("XDG_CURRENT_DESKTOP", "unknown"),
                "session_type": os.environ.get("XDG_SESSION_TYPE", "unknown"),
            },
            "components": {
                name: bool(which(name))
                for name in ("orca", "espeak-ng", "spd-say", "snapper", "pkexec", "aplay")
            },
            "health": health_report,
            "subvolumes": layout,
            "recent_actions": summarise_audit(audit_path),
            "privacy": (
                "Dieser Bericht enthält keine Aufnahmen, keine Transkripte, keine "
                "Dateinamen, keine Zugangsdaten und keine Aktionsziele."
            ),
        }
    )


def main(argv: Sequence[str] = ()) -> int:
    import argparse

    parser = argparse.ArgumentParser(
        description="Erzeuge einen datensparsamen Clausis-Diagnosebericht"
    )
    parser.add_argument("--output", type=Path, help="Datei statt Standardausgabe")
    parser.add_argument("--quiet", action="store_true", help="nichts vorlesen")
    args = parser.parse_args(list(argv) or None)

    report = build_report()
    if not args.quiet:
        from .recovery import Announcer

        try:
            from .speech import SystemSpeaker

            speaker = SystemSpeaker()
        except Exception:
            speaker = None
        Announcer(speaker).announce(report.spoken())
        print(report.spoken(), flush=True)

    if args.output:
        args.output.write_text(report.to_json() + "\n", encoding="utf-8")
        args.output.chmod(0o600)
        print(f"Bericht gespeichert: {args.output}", flush=True)
    else:
        print(report.to_json())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
