"""Typed messages crossing Clausis trust boundaries.

The data structures deliberately accept JSON-compatible values only.  This
keeps D-Bus, Hermes and audit-log representations equivalent and prevents an
adapter from smuggling executable Python objects into the broker.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from enum import Enum
import json
import re
from typing import Any, Dict, Mapping, Optional


ACTION_RE = re.compile(r"^[a-z][a-z0-9_]*(?:\.[a-z][a-z0-9_]*)+$")
TARGET_RE = re.compile(r"^[^\x00-\x1f]{0,512}$")


class Origin(str, Enum):
    LOCAL_VOICE = "local_voice"
    LOCAL_UI = "local_ui"
    HERMES = "hermes"
    EXTERNAL_CONTENT = "external_content"
    INSTALLER = "installer"


class Risk(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"

    @property
    def rank(self) -> int:
        return (Risk.LOW, Risk.MEDIUM, Risk.HIGH, Risk.CRITICAL).index(self)


@dataclass(frozen=True)
class ActionRequest:
    action: str
    target: str = ""
    arguments: Mapping[str, Any] = field(default_factory=dict)
    origin: Origin = Origin.LOCAL_VOICE
    risk: Risk = Risk.LOW
    reversible: bool = True
    capability_token: Optional[str] = None
    expires_at: Optional[str] = None

    def __post_init__(self) -> None:
        if not ACTION_RE.fullmatch(self.action):
            raise ValueError("action must be a dotted lower-case identifier")
        if not TARGET_RE.fullmatch(self.target):
            raise ValueError("target contains control characters or is too long")
        if not isinstance(self.arguments, Mapping):
            raise ValueError("arguments must be an object")
        try:
            encoded = json.dumps(dict(self.arguments), ensure_ascii=False)
        except (TypeError, ValueError) as exc:
            raise ValueError("arguments must be JSON-compatible") from exc
        if len(encoded.encode("utf-8")) > 16_384:
            raise ValueError("arguments exceed 16 KiB")
        if self.expires_at is not None:
            parse_timestamp(self.expires_at)

    def to_dict(self) -> Dict[str, Any]:
        data = asdict(self)
        data["origin"] = self.origin.value
        data["risk"] = self.risk.value
        return data

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> "ActionRequest":
        allowed = {
            "action", "target", "arguments", "origin", "risk", "reversible",
            "capability_token", "expires_at",
        }
        unknown = set(data) - allowed
        if unknown:
            raise ValueError("unknown action fields: " + ", ".join(sorted(unknown)))
        if not isinstance(data.get("action"), str):
            raise ValueError("action must be a string")
        if "target" in data and not isinstance(data["target"], str):
            raise ValueError("target must be a string")
        if "arguments" in data and not isinstance(data["arguments"], Mapping):
            raise ValueError("arguments must be an object")
        if "reversible" in data and not isinstance(data["reversible"], bool):
            raise ValueError("reversible must be a boolean")
        if data.get("capability_token") is not None and not isinstance(data["capability_token"], str):
            raise ValueError("capability_token must be a string or null")
        if data.get("expires_at") is not None and not isinstance(data["expires_at"], str):
            raise ValueError("expires_at must be a string or null")
        return cls(
            action=data["action"],
            target=data.get("target", ""),
            arguments=dict(data.get("arguments", {})),
            origin=Origin(data.get("origin", Origin.LOCAL_VOICE.value)),
            risk=Risk(data.get("risk", Risk.LOW.value)),
            reversible=data.get("reversible", True),
            capability_token=data.get("capability_token"),
            expires_at=data.get("expires_at"),
        )


@dataclass(frozen=True)
class ActionResult:
    status: str
    message: str
    action: str
    confirmation_id: Optional[str] = None
    details: Mapping[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def parse_timestamp(value: str) -> datetime:
    if not isinstance(value, str):
        raise ValueError("timestamp must be a string")
    normalized = value[:-1] + "+00:00" if value.endswith("Z") else value
    parsed = datetime.fromisoformat(normalized)
    if parsed.tzinfo is None:
        raise ValueError("timestamp requires a timezone")
    return parsed.astimezone(timezone.utc)
