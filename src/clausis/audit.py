"""Tamper-evident, privacy-filtered audit logging."""

from __future__ import annotations

import hashlib
import hmac
import json
from pathlib import Path
from typing import Any, Dict, Mapping

from .models import ActionRequest, ActionResult, utc_now


SENSITIVE_KEYS = {
    "pin", "password", "passphrase", "secret", "token", "api_key",
    "voiceprint", "capability_token", "access_token", "refresh_token",
}


def redact(value: Any) -> Any:
    if isinstance(value, Mapping):
        return {
            str(key): "[REDACTED]" if _sensitive_key(str(key)) else redact(item)
            for key, item in value.items()
        }
    if isinstance(value, list):
        return [redact(item) for item in value]
    return value


def _sensitive_key(key: str) -> bool:
    normalized = key.casefold()
    return normalized in SENSITIVE_KEYS or normalized.endswith(("_token", "_secret", "_password"))


class AuditLog:
    def __init__(self, path: Path, key: bytes) -> None:
        if len(key) < 32:
            raise ValueError("audit key must contain at least 32 bytes")
        self.path = path
        self._key = key
        self._previous = self._load_tail_hash()

    def append(self, request: ActionRequest, result: ActionResult) -> str:
        entry: Dict[str, Any] = {
            "timestamp": utc_now().isoformat(),
            "request": redact(request.to_dict()),
            "result": redact(result.to_dict()),
            "previous": self._previous,
        }
        body = json.dumps(entry, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
        digest = hmac.new(self._key, body.encode("utf-8"), hashlib.sha256).hexdigest()
        entry["chain_hmac"] = digest
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self.path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(entry, sort_keys=True, ensure_ascii=False) + "\n")
        self._previous = digest
        return digest

    def verify(self) -> bool:
        previous = "0" * 64
        if not self.path.exists():
            return True
        for line in self.path.read_text(encoding="utf-8").splitlines():
            entry = json.loads(line)
            signature = entry.pop("chain_hmac")
            if entry.get("previous") != previous:
                return False
            body = json.dumps(entry, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
            expected = hmac.new(self._key, body.encode("utf-8"), hashlib.sha256).hexdigest()
            if not hmac.compare_digest(signature, expected):
                return False
            previous = signature
        return True

    def _load_tail_hash(self) -> str:
        if not self.path.exists():
            return "0" * 64
        lines = self.path.read_text(encoding="utf-8").splitlines()
        if not lines:
            return "0" * 64
        return str(json.loads(lines[-1]).get("chain_hmac", ""))
