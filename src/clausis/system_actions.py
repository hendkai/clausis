"""Read-only local adapters for status, update and file-search actions.

These actions were allowlisted in :mod:`clausis.policy` without a platform
adapter, so every routed voice command failed with ``action requires a platform
adapter``.  The executor below answers them locally: it reads ``/proc`` and
``/sys``, simulates an APT upgrade without locking or writing, and searches a
bounded set of user directories.  No action here changes system state, so the
executor also answers while the session runs in dry-run mode, exactly like the
read-only semantic GNOME actions.
"""

from __future__ import annotations

from dataclasses import dataclass
import os
from pathlib import Path
import re
import subprocess
from typing import Callable, List, Optional, Sequence, Tuple

from .models import ActionRequest, ActionResult
from .policy import ActionPolicy


LOCAL_QUERY_ACTIONS = frozenset(
    {"system.status", "update.check", "file.search", "system.report"}
)

APT_SIMULATE_COMMAND: Tuple[str, ...] = (
    "apt-get",
    "--simulate",
    "--quiet",
    "-o",
    "Debug::NoLocking=true",
    "dist-upgrade",
)

CommandRunner = Callable[[Sequence[str]], "subprocess.CompletedProcess[str]"]


def _run(command: Sequence[str]) -> "subprocess.CompletedProcess[str]":
    return subprocess.run(
        list(command),
        shell=False,
        check=False,
        capture_output=True,
        text=True,
        timeout=60.0,
        env={"PATH": "/usr/local/bin:/usr/bin:/bin", "LC_ALL": "C", "DEBIAN_FRONTEND": "noninteractive"},
    )


@dataclass(frozen=True)
class SystemStatus:
    uptime_seconds: Optional[float]
    load_1m: Optional[float]
    memory_available_percent: Optional[float]
    root_free_gib: Optional[float]
    battery_percent: Optional[int]
    battery_charging: Optional[bool]

    def spoken(self) -> str:
        parts = []
        if self.uptime_seconds is not None:
            hours, minutes = divmod(int(self.uptime_seconds) // 60, 60)
            parts.append(f"Das System läuft seit {hours} Stunden und {minutes} Minuten.")
        if self.load_1m is not None:
            parts.append(f"Die Systemlast beträgt {self.load_1m:.1f}.")
        if self.memory_available_percent is not None:
            parts.append(f"{self.memory_available_percent:.0f} Prozent Arbeitsspeicher sind frei.")
        if self.root_free_gib is not None:
            parts.append(f"Auf dem Systemdatenträger sind {self.root_free_gib:.0f} Gigabyte frei.")
        if self.battery_percent is not None:
            state = "wird geladen" if self.battery_charging else "läuft im Akkubetrieb"
            parts.append(f"Der Akku steht bei {self.battery_percent} Prozent und {state}.")
        if not parts:
            return "Ich konnte den Systemzustand gerade nicht auslesen."
        return " ".join(parts)


def read_system_status(root: Path = Path("/")) -> SystemStatus:
    """Collect a spoken-summary status without running any external program."""

    proc = root / "proc"
    uptime: Optional[float]
    load: Optional[float]
    try:
        uptime = float((proc / "uptime").read_text(encoding="utf-8").split()[0])
    except (OSError, IndexError, ValueError):
        uptime = None
    try:
        load = float((proc / "loadavg").read_text(encoding="utf-8").split()[0])
    except (OSError, IndexError, ValueError):
        load = None

    memory: Optional[float] = None
    try:
        values = {}
        for line in (proc / "meminfo").read_text(encoding="utf-8").splitlines():
            name, _, rest = line.partition(":")
            fields = rest.split()
            if fields:
                values[name] = float(fields[0])
        total = values.get("MemTotal", 0.0)
        if total > 0:
            memory = 100.0 * values.get("MemAvailable", 0.0) / total
    except (OSError, ValueError):
        memory = None

    free_gib: Optional[float] = None
    try:
        stats = os.statvfs(str(root))
        free_gib = stats.f_bavail * stats.f_frsize / (1024 ** 3)
    except OSError:
        free_gib = None

    percent: Optional[int] = None
    charging: Optional[bool] = None
    try:
        supplies = sorted((root / "sys/class/power_supply").iterdir())
    except OSError:
        supplies = []
    for supply in supplies:
        if not supply.name.upper().startswith("BAT"):
            continue
        try:
            percent = int((supply / "capacity").read_text(encoding="utf-8").strip())
            charging = (supply / "status").read_text(encoding="utf-8").strip().casefold() != "discharging"
        except (OSError, ValueError):
            percent = None
            charging = None
        break
    return SystemStatus(uptime, load, memory, free_gib, percent, charging)


@dataclass(frozen=True)
class UpgradeSummary:
    total: int
    security: int
    available: bool

    def spoken(self) -> str:
        if not self.available:
            return "Die Paketverwaltung ist gerade nicht erreichbar. Bitte versuchen Sie es später erneut."
        if self.total == 0:
            return "Das System ist auf dem aktuellen Stand. Es sind keine Aktualisierungen verfügbar."
        security = (
            f" Davon sind {self.security} Sicherheitsaktualisierungen." if self.security else ""
        )
        return f"Es sind {self.total} Aktualisierungen verfügbar.{security}"


_INSTALL_LINE = re.compile(r"^Inst\s+(?P<name>\S+)\s+(?P<rest>.*)$")


def parse_apt_simulation(output: str) -> Tuple[int, int]:
    """Count planned upgrades and the security subset of an ``apt-get -s`` run."""

    total = 0
    security = 0
    for line in output.splitlines():
        match = _INSTALL_LINE.match(line.strip())
        if match is None:
            continue
        total += 1
        if "security" in match.group("rest").casefold():
            security += 1
    return total, security


def check_updates(runner: CommandRunner = _run) -> UpgradeSummary:
    try:
        completed = runner(APT_SIMULATE_COMMAND)
    except (OSError, subprocess.SubprocessError):
        return UpgradeSummary(0, 0, False)
    if completed.returncode != 0:
        return UpgradeSummary(0, 0, False)
    total, security = parse_apt_simulation(completed.stdout or "")
    return UpgradeSummary(total, security, True)


SEARCH_DIRECTORIES = (
    "Dokumente", "Documents", "Downloads", "Schreibtisch", "Desktop",
    "Bilder", "Pictures", "Musik", "Music", "Videos", "Öffentlich", "Public",
)
MAX_SEARCH_RESULTS = 5
MAX_SEARCH_ENTRIES = 20_000
MAX_SEARCH_DEPTH = 6


def search_files(
    query: str,
    *,
    home: Optional[Path] = None,
    limit: int = MAX_SEARCH_RESULTS,
) -> List[Path]:
    """Search a bounded set of user directories for a case-insensitive name.

    The walk never follows symlinks, never leaves the listed directories and
    stops after a fixed number of entries so a deep or hostile tree cannot make
    the assistant unresponsive.
    """

    needle = " ".join(query.split()).casefold()
    if not needle:
        raise ValueError("search query is empty")
    base = home or Path.home()
    roots = [base / name for name in SEARCH_DIRECTORIES]
    matches: List[Path] = []
    visited = 0
    for root in roots:
        if not root.is_dir() or root.is_symlink():
            continue
        for directory, subdirectories, files in os.walk(root, followlinks=False):
            depth = len(Path(directory).relative_to(root).parts)
            if depth >= MAX_SEARCH_DEPTH:
                subdirectories[:] = []
            subdirectories[:] = [name for name in subdirectories if not name.startswith(".")]
            for name in files:
                visited += 1
                if visited > MAX_SEARCH_ENTRIES:
                    return matches
                if name.startswith("."):
                    continue
                if needle in name.casefold():
                    matches.append(Path(directory) / name)
                    if len(matches) >= limit:
                        return matches
    return matches


def spoken_search_result(query: str, matches: Sequence[Path]) -> str:
    if not matches:
        return f"Ich habe keine Datei gefunden, die zu {query} passt."
    names = ". ".join(
        f"Nummer {index}: {path.name} in {path.parent.name}"
        for index, path in enumerate(matches, start=1)
    )
    return f"Ich habe {len(matches)} Treffer für {query} gefunden. {names}."


class LocalQueryExecutor:
    """Answer the read-only local actions without spawning a shell."""

    def __init__(
        self,
        *,
        root: Path = Path("/"),
        home: Optional[Path] = None,
        runner: CommandRunner = _run,
    ) -> None:
        self.root = root
        self.home = home
        self.runner = runner

    def execute(self, request: ActionRequest, policy: ActionPolicy) -> ActionResult:
        del policy
        try:
            if request.action == "system.status":
                status = read_system_status(self.root)
                uptime = status.uptime_seconds
                return ActionResult(
                    "completed",
                    status.spoken(),
                    request.action,
                    details={"uptime_seconds": None if uptime is None else int(uptime)},
                )
            if request.action == "update.check":
                summary = check_updates(self.runner)
                status = "completed" if summary.available else "failed"
                return ActionResult(
                    status,
                    summary.spoken(),
                    request.action,
                    details={"total": summary.total, "security": summary.security},
                )
            if request.action == "system.report":
                from .report import build_report

                report = build_report()
                destination = (self.home or Path.home()) / "clausis-bericht.json"
                destination.write_text(report.to_json() + "\n", encoding="utf-8")
                destination.chmod(0o600)
                return ActionResult(
                    "completed",
                    f"{report.spoken()} Er liegt als clausis-bericht.json in Ihrem "
                    "persönlichen Ordner.",
                    request.action,
                    details={"path": str(destination)},
                )
            if request.action == "file.search":
                matches = search_files(request.target, home=self.home)
                return ActionResult(
                    "completed",
                    spoken_search_result(request.target, matches),
                    request.action,
                    details={"matches": [str(path) for path in matches]},
                )
        except (OSError, ValueError) as exc:
            return ActionResult("failed", str(exc), request.action)
        return ActionResult("failed", "Keine lokale Abfrage verfügbar.", request.action)
