"""Action broker and safe executor."""

from __future__ import annotations

import os
import subprocess
from typing import Dict, List, Optional, Protocol

from .audit import AuditLog
from .capabilities import CapabilityAuthority, CapabilityError
from .models import ActionRequest, ActionResult, parse_timestamp, utc_now
from .policy import ActionPolicy, evaluate


class Executor(Protocol):
    def execute(self, request: ActionRequest, policy: ActionPolicy) -> ActionResult:
        ...


class SafeExecutor:
    """Executes fixed argv vectors only; shell interpretation is never used."""

    def __init__(self, *, dry_run: bool = True, timeout: float = 15.0) -> None:
        self.dry_run = dry_run
        self.timeout = timeout

    def command_for(self, request: ActionRequest, policy: ActionPolicy) -> List[str]:
        if policy.command is None:
            raise ValueError("action requires a platform adapter")
        command = list(policy.command)
        if request.action in {"app.launch", "desktop.settings.open", "file.open", "file.move_to_trash"}:
            command.append(request.target)
        elif request.action == "audio.volume.set":
            command.append(f"{float(request.arguments['percent']):g}%")
        elif request.action in {
            "accessibility.screen_magnifier.set_percent",
            "accessibility.screen_magnifier.set_saturation",
            "accessibility.screen_magnifier.cross_hairs.set_opacity",
        }:
            factor = request.arguments["percent"] / 100
            command.append(f"{factor:.2f}")
        elif request.action == "accessibility.screen_magnifier.set_screen_position":
            command.append(request.arguments["position"])
        elif request.action in {
            "accessibility.screen_magnifier.cross_hairs.set_length",
            "accessibility.screen_magnifier.cross_hairs.set_thickness",
        }:
            command.append(str(request.arguments["pixels"]))
        elif request.action == "accessibility.screen_magnifier.cross_hairs.set_color":
            command.append(
                "#{red:02x}{green:02x}{blue:02x}".format(**request.arguments)
            )
        elif request.action in {
            "accessibility.screen_magnifier.set_brightness",
            "accessibility.screen_magnifier.set_contrast",
        }:
            command.append(f"{request.arguments['percent'] / 100:.2f}")
        elif request.action in {
            "accessibility.screen_magnifier.set_focus_tracking",
            "accessibility.screen_magnifier.set_caret_tracking",
            "accessibility.screen_magnifier.set_mouse_tracking",
        }:
            command.append(request.arguments["mode"])
        return command

    def execute(self, request: ActionRequest, policy: ActionPolicy) -> ActionResult:
        command = self.command_for(request, policy)
        if self.dry_run:
            return ActionResult("dry_run", "validated; execution disabled", request.action, details={"argv": command})
        child_env = {"PATH": "/usr/local/bin:/usr/bin:/bin"}
        for name in (
            "DBUS_SESSION_BUS_ADDRESS", "DISPLAY", "HOME", "LANG", "LC_ALL",
            "WAYLAND_DISPLAY", "XDG_RUNTIME_DIR",
        ):
            if name in os.environ:
                child_env[name] = os.environ[name]
        completed = subprocess.run(
            command,
            shell=False,
            check=False,
            capture_output=True,
            text=True,
            timeout=self.timeout,
            env=child_env,
        )
        status = "completed" if completed.returncode == 0 else "failed"
        return ActionResult(
            status,
            "action completed" if completed.returncode == 0 else "action failed",
            request.action,
            details={"returncode": completed.returncode, "stderr": completed.stderr[-1000:]},
        )


class ActionBroker:
    def __init__(
        self,
        authority: CapabilityAuthority,
        executor: Executor,
        *,
        audit_log: Optional[AuditLog] = None,
    ) -> None:
        self._authority = authority
        self._executor = executor
        self._audit = audit_log

    def submit(self, request: ActionRequest) -> ActionResult:
        if request.expires_at is not None and parse_timestamp(request.expires_at) <= utc_now():
            result = ActionResult("denied", "request expired", request.action)
            self._record(request, result)
            return result
        try:
            decision = evaluate(request)
        except ValueError as exc:
            result = ActionResult("denied", str(exc), request.action)
            self._record(request, result)
            return result
        if decision.confirmation_required:
            if not request.capability_token:
                result = ActionResult("confirmation_required", decision.reason, request.action)
                self._record(request, result)
                return result
            try:
                self._authority.verify(request.capability_token, request)
            except CapabilityError as exc:
                result = ActionResult("denied", str(exc), request.action)
                self._record(request, result)
                return result
        try:
            result = self._executor.execute(request, decision.policy)
        except (OSError, ValueError, subprocess.SubprocessError) as exc:
            result = ActionResult("failed", str(exc), request.action)
        self._record(request, result)
        return result

    def _record(self, request: ActionRequest, result: ActionResult) -> None:
        if self._audit:
            self._audit.append(request, result)
