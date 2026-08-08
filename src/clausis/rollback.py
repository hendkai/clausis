"""Snapshot guard around system-changing privileged actions.

The health check can already tell that an update broke something a rollback
would repair, but nothing acted on it.  This module closes that loop: a
package or security update runs between a ``pre`` and a ``post`` snapshot, the
health check runs afterwards, and a failed update is undone automatically.

Two deliberate choices:

* ``snapper undochange`` is used rather than ``snapper rollback``.  It reverts
  the file changes of exactly that update without switching the default
  subvolume, so no reboot is required and a running voice session survives.
* A missing or unconfigured snapper does **not** block the update.  Refusing
  security updates on a machine without snapshots would trade a real,
  immediate risk for a hypothetical one; the answer says plainly that no
  snapshot exists.

Every snapper invocation is a fixed argument vector.  Snapshot numbers are the
only caller-influenced values and are validated as integers before use.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import shutil
import subprocess
from typing import Callable, List, Optional, Sequence


SNAPPER = "snapper"
CONFIG = "root"
DESCRIPTION = "clausis system action"
#: Privileged actions that change installed software and therefore run inside
#: the snapshot guard.  Reboot and power-off change nothing to snapshot.
SNAPSHOT_GUARDED = frozenset(
    {"package.install", "package.remove", "update.install_security"}
)

CommandRunner = Callable[[Sequence[str]], "subprocess.CompletedProcess[str]"]


class SnapshotError(RuntimeError):
    """Snapshots are unavailable; the caller decides whether that is fatal."""


@dataclass(frozen=True)
class GuardOutcome:
    succeeded: bool
    rolled_back: bool
    snapshotted: bool
    message: str


def _run(command: Sequence[str]) -> "subprocess.CompletedProcess[str]":
    return subprocess.run(
        list(command),
        shell=False,
        check=False,
        capture_output=True,
        text=True,
        timeout=600.0,
        env={"PATH": "/usr/sbin:/usr/bin:/sbin:/bin", "LC_ALL": "C"},
    )


class SnapshotManager:
    """Thin, fixed-argv wrapper around the snapper commands Clausis needs."""

    def __init__(
        self,
        *,
        config: str = CONFIG,
        runner: CommandRunner = _run,
        which: Callable[[str], Optional[str]] = shutil.which,
    ) -> None:
        self.config = config
        self.runner = runner
        self.which = which

    def available(self) -> bool:
        if not self.which(SNAPPER):
            return False
        completed = self.runner([SNAPPER, "-c", self.config, "list-configs"])
        return completed.returncode == 0 and self.config in (completed.stdout or "")

    def _base(self) -> List[str]:
        return [SNAPPER, "-c", self.config]

    @staticmethod
    def _number(output: str) -> int:
        digits = (output or "").strip().splitlines()
        for line in reversed(digits):
            candidate = line.strip()
            if candidate.isdigit():
                return int(candidate)
        raise SnapshotError("snapper did not report a snapshot number")

    def create_pre(self, description: str = DESCRIPTION) -> int:
        completed = self.runner(
            [
                *self._base(), "create", "--type", "pre",
                "--cleanup-algorithm", "number",
                "--print-number", "--description", description,
            ]
        )
        if completed.returncode != 0:
            raise SnapshotError("the pre snapshot could not be created")
        return self._number(completed.stdout)

    def create_post(self, pre: int, description: str = DESCRIPTION) -> int:
        completed = self.runner(
            [
                *self._base(), "create", "--type", "post",
                "--pre-number", str(int(pre)),
                "--cleanup-algorithm", "number",
                "--print-number", "--description", description,
            ]
        )
        if completed.returncode != 0:
            raise SnapshotError("the post snapshot could not be created")
        return self._number(completed.stdout)

    def undo(self, pre: int, post: int) -> bool:
        completed = self.runner(
            [*self._base(), "undochange", f"{int(pre)}..{int(post)}"]
        )
        return completed.returncode == 0


class UpdateGuard:
    """Run a system-changing command between snapshots and undo a bad result."""

    def __init__(
        self,
        *,
        manager: Optional[SnapshotManager] = None,
        health: Optional[Callable[[], dict]] = None,
        runner: CommandRunner = _run,
    ) -> None:
        self.manager = manager or SnapshotManager()
        self.health = health
        self.runner = runner

    def _layout_safe(self) -> bool:
        try:
            from .subvolumes import mounted_subvolumes, validate_present

            mounts = Path("/proc/self/mounts").read_text(encoding="utf-8")
            return bool(validate_present(mounted_subvolumes(mounts))["rollback_safe"])
        except Exception:
            return False

    def _healthy(self) -> bool:
        probe = self.health
        if probe is None:
            from .healthcheck import collect

            probe = collect
        try:
            return not probe().get("rollback_recommended", False)
        except Exception:
            # A health check that cannot run is not evidence of breakage.
            return True

    def run(self, command: Sequence[str]) -> GuardOutcome:
        try:
            snapshotted = self.manager.available()
        except Exception:
            snapshotted = False

        pre: Optional[int] = None
        if snapshotted:
            try:
                pre = self.manager.create_pre()
            except SnapshotError:
                snapshotted = False

        completed = self.runner(list(command))
        succeeded = completed.returncode == 0

        if not snapshotted or pre is None:
            note = (
                "Es konnte kein Systemabbild angelegt werden, die Aktion wurde "
                "trotzdem ausgeführt."
            )
            if succeeded:
                return GuardOutcome(True, False, False, note)
            return GuardOutcome(False, False, False, self._failure(completed) + " " + note)

        try:
            post = self.manager.create_post(pre)
        except SnapshotError:
            return GuardOutcome(
                succeeded,
                False,
                True,
                "Das Systemabbild nach der Aktion fehlt, es wurde nichts zurückgenommen.",
            )

        if succeeded and self._healthy():
            return GuardOutcome(True, False, True, "Die Aktion wurde ausgeführt.")

        reason = (
            "Die Aktion ist fehlgeschlagen."
            if not succeeded
            else "Das System war nach der Aktion nicht mehr sprachfähig."
        )
        if self.manager.undo(pre, post):
            note = ""
            if not self._layout_safe():
                # Saying this plainly matters: on a flat filesystem the undo
                # also reverted the audit chain that records what happened.
                note = (
                    " Achtung: Auf diesem System liegt das Protokoll im "
                    "zurückgenommenen Bereich, die Aufzeichnung kann unvollständig sein."
                )
            return GuardOutcome(
                False,
                True,
                True,
                f"{reason} Der vorherige Systemstand wurde wiederhergestellt. "
                "Starten Sie den Rechner neu, wenn etwas ungewohnt wirkt." + note,
            )
        return GuardOutcome(
            False,
            False,
            True,
            f"{reason} Die Rücknahme ist ebenfalls fehlgeschlagen. Bitte prüfen "
            "Sie das System mit Tastatur und Orca.",
        )

    @staticmethod
    def _failure(completed: "subprocess.CompletedProcess[str]") -> str:
        detail = (completed.stderr or "").strip().splitlines()
        reason = detail[-1][:200] if detail else f"Rückgabewert {completed.returncode}"
        return f"Die Aktion ist fehlgeschlagen: {reason}"
