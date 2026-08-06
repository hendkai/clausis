"""Action allowlist, argument validation and confirmation policy."""

from __future__ import annotations

from dataclasses import dataclass
import re
from typing import Any, Callable, Dict, Mapping, Optional

from .models import ActionRequest, Origin, Risk


Validator = Callable[[ActionRequest], None]


@dataclass(frozen=True)
class ActionPolicy:
    minimum_risk: Risk
    reversible: bool
    command: Optional[tuple] = None
    validator: Optional[Validator] = None
    privileged: bool = False


SAFE_IDENTIFIER = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._+@:-]{0,127}$")
SAFE_SETTING = re.compile(r"^[a-z][a-z0-9-]{0,63}$")


def _target_required(request: ActionRequest) -> None:
    if not request.target:
        raise ValueError("target is required")


def _safe_identifier(request: ActionRequest) -> None:
    _target_required(request)
    if not SAFE_IDENTIFIER.fullmatch(request.target):
        raise ValueError("target is not an allowed identifier")


def _path(request: ActionRequest) -> None:
    _target_required(request)
    if not request.target.startswith("/") or "\x00" in request.target:
        raise ValueError("target must be an absolute path")


def _percentage(request: ActionRequest) -> None:
    value = request.arguments.get("percent")
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not 0 <= value <= 150:
        raise ValueError("percent must be between 0 and 150")


def _setting(request: ActionRequest) -> None:
    if request.target and not SAFE_SETTING.fullmatch(request.target):
        raise ValueError("invalid settings panel")


ACTION_POLICIES: Mapping[str, ActionPolicy] = {
    "app.launch": ActionPolicy(Risk.LOW, True, ("gtk-launch",), _safe_identifier),
    "app.close": ActionPolicy(Risk.MEDIUM, True, None, _safe_identifier),
    "desktop.overview": ActionPolicy(Risk.LOW, True),
    "desktop.window.next": ActionPolicy(Risk.LOW, True),
    "desktop.window.previous": ActionPolicy(Risk.LOW, True),
    "desktop.settings.open": ActionPolicy(Risk.LOW, True, ("gnome-control-center",), _setting),
    "file.open": ActionPolicy(Risk.LOW, True, ("gio", "open"), _path),
    "file.search": ActionPolicy(Risk.LOW, True, None, _target_required),
    "file.move_to_trash": ActionPolicy(Risk.HIGH, True, ("gio", "trash"), _path),
    "file.delete": ActionPolicy(Risk.CRITICAL, False, None, _path),
    "audio.volume.set": ActionPolicy(Risk.LOW, True, ("wpctl", "set-volume", "@DEFAULT_AUDIO_SINK@"), _percentage),
    "audio.volume.up": ActionPolicy(Risk.LOW, True, ("wpctl", "set-volume", "@DEFAULT_AUDIO_SINK@", "5%+")),
    "audio.volume.down": ActionPolicy(Risk.LOW, True, ("wpctl", "set-volume", "@DEFAULT_AUDIO_SINK@", "5%-")),
    "audio.mute.toggle": ActionPolicy(Risk.LOW, True, ("wpctl", "set-mute", "@DEFAULT_AUDIO_SINK@", "toggle")),
    "network.status": ActionPolicy(Risk.LOW, True, ("nmcli", "general", "status")),
    "network.wifi.enable": ActionPolicy(Risk.MEDIUM, True, ("nmcli", "radio", "wifi", "on")),
    "network.wifi.disable": ActionPolicy(Risk.MEDIUM, True, ("nmcli", "radio", "wifi", "off")),
    "system.status": ActionPolicy(Risk.LOW, True),
    "system.lock": ActionPolicy(Risk.LOW, True, ("loginctl", "lock-session")),
    "system.logout": ActionPolicy(Risk.HIGH, True, ("gnome-session-quit", "--logout", "--no-prompt")),
    "system.reboot": ActionPolicy(Risk.CRITICAL, False, ("systemctl", "reboot"), privileged=True),
    "system.poweroff": ActionPolicy(Risk.CRITICAL, False, ("systemctl", "poweroff"), privileged=True),
    "package.install": ActionPolicy(Risk.HIGH, True, None, _safe_identifier, privileged=True),
    "package.remove": ActionPolicy(Risk.CRITICAL, False, None, _safe_identifier, privileged=True),
    "update.check": ActionPolicy(Risk.LOW, True),
    "update.install_security": ActionPolicy(Risk.HIGH, True, None, privileged=True),
}


class PolicyDecision:
    def __init__(self, *, allowed: bool, confirmation_required: bool, reason: str, policy: ActionPolicy) -> None:
        self.allowed = allowed
        self.confirmation_required = confirmation_required
        self.reason = reason
        self.policy = policy


def evaluate(request: ActionRequest) -> PolicyDecision:
    policy = ACTION_POLICIES.get(request.action)
    if policy is None:
        raise ValueError("action is not allowlisted")
    if policy.validator:
        policy.validator(request)
    if request.risk.rank < policy.minimum_risk.rank:
        raise ValueError("caller attempted to understate action risk")
    if request.reversible and not policy.reversible:
        raise ValueError("caller incorrectly marked an irreversible action reversible")
    tainted = request.origin in {Origin.EXTERNAL_CONTENT, Origin.HERMES}
    needs_confirmation = (
        policy.minimum_risk.rank >= Risk.MEDIUM.rank
        or not policy.reversible
        or policy.privileged
        or tainted
    )
    reason = "confirmation required by risk and provenance policy" if needs_confirmation else "safe local action"
    return PolicyDecision(
        allowed=True,
        confirmation_required=needs_confirmation,
        reason=reason,
        policy=policy,
    )

