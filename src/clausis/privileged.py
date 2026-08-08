"""Privileged system actions behind Polkit and a fixed argument vector.

``ACTION_POLICIES`` marks reboot, power-off, package management and security
updates as privileged.  The session broker runs unprivileged, so those actions
had no execution path at all: the Polkit policy already pointed at
``/usr/libexec/clausis-system-action`` but that helper did not exist.

This module implements both halves.  The session side (:class:`PrivilegedExecutor`)
hands the typed request to ``pkexec`` **on standard input**, so neither the
capability token nor the target ever appears in a process argument list.  The
root side (:func:`helper_main`) re-parses the request, re-evaluates the policy,
re-verifies the action-bound capability, rejects a replayed capability using its
own store and only then runs a fixed argument vector without a shell.  The
helper never trusts a command supplied by the caller.
"""

from __future__ import annotations

import json
import os
from pathlib import Path
import re
import subprocess
import sys
from typing import Callable, Dict, List, Optional, Sequence, Tuple

from .capabilities import CapabilityAuthority, CapabilityError
from .models import ActionRequest, ActionResult, parse_timestamp, utc_now
from .policy import ACTION_POLICIES, ActionPolicy, evaluate
from .rollback import SNAPSHOT_GUARDED, UpdateGuard


HELPER_PATH = "/usr/libexec/clausis-system-action"
CAPABILITY_KEY_PATH = Path("/etc/clausis/capability.key")
REPLAY_STORE_PATH = Path("/run/clausis/privileged-capabilities.d")
MAX_HELPER_REQUEST_BYTES = 32_768

PRIVILEGED_ACTIONS = frozenset(
    name for name, policy in ACTION_POLICIES.items() if policy.privileged
)

#: Root-side argument vectors.  The caller never supplies a command; it can only
#: name an action from this table and, where the policy allows it, one validated
#: package identifier.
PRIVILEGED_COMMANDS: Dict[str, Tuple[str, ...]] = {
    "system.reboot": ("systemctl", "reboot"),
    "system.poweroff": ("systemctl", "poweroff"),
    "package.install": ("apt-get", "--yes", "--no-install-recommends", "install", "--"),
    "package.remove": ("apt-get", "--yes", "remove", "--"),
    "update.install_security": ("unattended-upgrade", "--verbose"),
}
TARGET_ACTIONS = frozenset({"package.install", "package.remove"})

#: Debian binary package name grammar; deliberately stricter than the generic
#: ``SAFE_IDENTIFIER`` so a value can never look like an ``apt-get`` option.
DEBIAN_PACKAGE = re.compile(r"^[a-z0-9][a-z0-9+.-]{1,62}$")

HelperRunner = Callable[[Sequence[str], str], "subprocess.CompletedProcess[str]"]


def build_privileged_command(request: ActionRequest) -> List[str]:
    """Map an action to its fixed root-side argument vector."""

    command = PRIVILEGED_COMMANDS.get(request.action)
    if command is None:
        raise ValueError("action has no privileged adapter")
    argv = list(command)
    if request.action in TARGET_ACTIONS:
        if not DEBIAN_PACKAGE.fullmatch(request.target):
            raise ValueError("target is not a Debian package name")
        argv.append(request.target)
    elif request.target:
        raise ValueError("action does not accept a target")
    return argv


CAPABILITY_ID = re.compile(r"^[A-Za-z0-9_-]{1,64}$")


class ReplayGuard:
    """Root-only single-use store for capability IDs seen by the helper.

    The broker consumes a capability in its own memory, but the helper is a
    separate short-lived process.  Without this store a capability that is still
    inside its short lifetime could be handed to ``pkexec`` twice.

    Each capability is one file created with ``O_EXCL``, so claiming an ID is a
    single atomic step: two helpers racing on the same capability cannot both
    win, which a read-modify-write of a shared file could not guarantee.
    """

    def __init__(self, path: Path = REPLAY_STORE_PATH) -> None:
        self.path = path

    def consume(self, identifier: str, expires_at: str) -> None:
        """Claim a capability ID or raise when it was already used."""

        if not CAPABILITY_ID.fullmatch(identifier or ""):
            raise CapabilityError("capability has no usable identifier")
        try:
            self.path.mkdir(parents=True, exist_ok=True)
            os.chmod(self.path, 0o700)
            self._prune()
            descriptor = os.open(
                str(self.path / identifier),
                os.O_CREAT | os.O_EXCL | os.O_WRONLY,
                0o600,
            )
        except FileExistsError as exc:
            raise CapabilityError("capability was already consumed") from exc
        except OSError as exc:
            raise CapabilityError(f"the replay store is unavailable: {exc}") from exc
        with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
            handle.write(expires_at)

    def _prune(self) -> None:
        now = utc_now()
        for entry in self.path.iterdir():
            try:
                if not _expiry_in_future(entry.read_text(encoding="utf-8").strip(), now):
                    entry.unlink()
            except OSError:
                continue


def _expiry_in_future(value: str, now) -> bool:
    try:
        return parse_timestamp(value) > now
    except ValueError:
        return False


def _run_helper(argv: Sequence[str], payload: str) -> "subprocess.CompletedProcess[str]":
    return subprocess.run(
        list(argv),
        input=payload,
        shell=False,
        check=False,
        capture_output=True,
        text=True,
        timeout=900.0,
    )


class PrivilegedExecutor:
    """Session-side client for the Polkit-gated helper."""

    def __init__(
        self,
        *,
        dry_run: bool = True,
        helper: str = HELPER_PATH,
        launcher: Sequence[str] = ("pkexec",),
        runner: HelperRunner = _run_helper,
    ) -> None:
        self.dry_run = dry_run
        self.helper = helper
        self.launcher = tuple(launcher)
        self.runner = runner

    def command_for(self, request: ActionRequest, policy: ActionPolicy) -> List[str]:
        if not policy.privileged:
            raise ValueError("action is not privileged")
        # Validate the root-side vector here as well so an unsupported action
        # fails before Polkit ever prompts the user.
        build_privileged_command(request)
        return [*self.launcher, self.helper]

    def execute(self, request: ActionRequest, policy: ActionPolicy) -> ActionResult:
        try:
            argv = self.command_for(request, policy)
        except ValueError as exc:
            return ActionResult("failed", str(exc), request.action)
        if not request.capability_token:
            return ActionResult(
                "confirmation_required",
                "Privilegierte Aktionen benötigen eine vertrauenswürdige Bestätigung.",
                request.action,
            )
        if self.dry_run:
            return ActionResult(
                "dry_run",
                "validated privileged action; execution disabled",
                request.action,
                details={"argv": argv},
            )
        payload = json.dumps(request.to_dict(), ensure_ascii=False)
        try:
            completed = self.runner(argv, payload)
        except (OSError, subprocess.SubprocessError) as exc:
            return ActionResult("failed", f"Der privilegierte Helfer war nicht erreichbar: {exc}", request.action)
        return _parse_helper_result(completed, request)


def _parse_helper_result(
    completed: "subprocess.CompletedProcess[str]", request: ActionRequest
) -> ActionResult:
    try:
        decoded = json.loads(completed.stdout or "")
        status = decoded["status"]
        message = decoded["message"]
        action = decoded["action"]
    except (KeyError, TypeError, ValueError):
        if completed.returncode == 126:
            return ActionResult(
                "denied",
                "Die Autorisierung für die privilegierte Aktion wurde abgelehnt.",
                request.action,
            )
        return ActionResult(
            "failed",
            "Der privilegierte Helfer hat keine gültige Antwort geliefert.",
            request.action,
        )
    if not isinstance(status, str) or not isinstance(message, str) or action != request.action:
        return ActionResult("failed", "Die Antwort des Helfers war ungültig.", request.action)
    if status not in {"completed", "denied", "failed"}:
        return ActionResult("failed", "Die Antwort des Helfers hatte einen unbekannten Status.", request.action)
    return ActionResult(status, message[:2048], request.action)


def _helper_reply(status: str, message: str, action: str) -> int:
    print(json.dumps({"status": status, "message": message, "action": action}, ensure_ascii=False))
    return 0 if status == "completed" else 1


def helper_main(
    argv: Optional[Sequence[str]] = None,
    *,
    stdin=None,
    key_path: Path = CAPABILITY_KEY_PATH,
    guard: Optional[ReplayGuard] = None,
    runner: Optional[Callable[[Sequence[str]], "subprocess.CompletedProcess[str]"]] = None,
    update_guard: Optional[UpdateGuard] = None,
) -> int:
    """Root-side entry point invoked through ``pkexec``.

    Nothing from the request is ever passed to a shell, and no capability,
    transcript or PIN is echoed back to the caller.
    """

    if argv:
        return _helper_reply("denied", "Der Helfer akzeptiert keine Argumente.", "invalid")
    stream = sys.stdin if stdin is None else stdin
    raw = stream.read(MAX_HELPER_REQUEST_BYTES + 1)
    if len(raw.encode("utf-8")) > MAX_HELPER_REQUEST_BYTES:
        return _helper_reply("denied", "Die Anfrage ist zu groß.", "invalid")
    try:
        decoded = json.loads(raw)
        if not isinstance(decoded, dict):
            raise ValueError("request must be a JSON object")
        request = ActionRequest.from_dict(decoded)
    except (TypeError, ValueError) as exc:
        return _helper_reply("denied", f"Ungültige Anfrage: {exc}", "invalid")

    try:
        decision = evaluate(request)
    except ValueError as exc:
        return _helper_reply("denied", str(exc), request.action)
    if not decision.policy.privileged:
        return _helper_reply("denied", "Diese Aktion ist nicht privilegiert.", request.action)
    if not decision.confirmation_required:
        return _helper_reply("denied", "Privilegierte Aktionen erfordern eine Bestätigung.", request.action)

    try:
        command = build_privileged_command(request)
    except ValueError as exc:
        return _helper_reply("denied", str(exc), request.action)

    try:
        key = key_path.read_bytes()
        authority = CapabilityAuthority(key)
        payload = authority.verify(request.capability_token or "", request, consume=False)
        (guard or ReplayGuard()).consume(str(payload.get("jti", "")), str(payload.get("expires_at", "")))
    except (OSError, ValueError, CapabilityError) as exc:
        return _helper_reply("denied", f"Die Berechtigung wurde abgelehnt: {exc}", request.action)

    execute = runner or _run_root_command

    # Software changes run inside the snapshot guard so a broken update is
    # undone instead of leaving a system that can no longer speak.
    if request.action in SNAPSHOT_GUARDED:
        try:
            outcome = (update_guard or UpdateGuard(runner=execute)).run(command)
        except (OSError, subprocess.SubprocessError) as exc:
            return _helper_reply(
                "failed", f"Die Aktion konnte nicht ausgeführt werden: {exc}", request.action
            )
        return _helper_reply(
            "completed" if outcome.succeeded else "failed", outcome.message, request.action
        )

    try:
        completed = execute(command)
    except (OSError, subprocess.SubprocessError) as exc:
        return _helper_reply("failed", f"Die Aktion konnte nicht ausgeführt werden: {exc}", request.action)
    if completed.returncode != 0:
        detail = (completed.stderr or "").strip().splitlines()
        reason = detail[-1][:200] if detail else f"Rückgabewert {completed.returncode}"
        return _helper_reply("failed", f"Die Aktion ist fehlgeschlagen: {reason}", request.action)
    return _helper_reply("completed", "Die privilegierte Aktion wurde ausgeführt.", request.action)


def _run_root_command(command: Sequence[str]) -> "subprocess.CompletedProcess[str]":
    return subprocess.run(
        list(command),
        shell=False,
        check=False,
        capture_output=True,
        text=True,
        timeout=880.0,
        env={
            "PATH": "/usr/sbin:/usr/bin:/sbin:/bin",
            "LC_ALL": "C",
            "DEBIAN_FRONTEND": "noninteractive",
        },
    )


if __name__ == "__main__":
    raise SystemExit(helper_main(sys.argv[1:]))
