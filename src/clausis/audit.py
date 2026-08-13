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
        request_data = request.to_dict()
        if request.action in {
            "desktop.text.set",
            "desktop.text.insert_at_caret",
            "desktop.text.replace_selection",
            "desktop.text.replace_previous_word",
            "desktop.text.replace_next_word",
            "desktop.text.replace_current_line",
            "desktop.text.insert_line_above",
            "desktop.text.insert_line_below",
            "desktop.clipboard.write_text",
        }:
            labels = {
                "desktop.text.set": "dictated text",
                "desktop.text.insert_at_caret": "inserted text",
                "desktop.text.replace_selection": "selection replacement text",
                "desktop.text.replace_previous_word": "previous word replacement text",
                "desktop.text.replace_next_word": "next word replacement text",
                "desktop.text.replace_current_line": "current line replacement text",
                "desktop.text.insert_line_above": "inserted line above text",
                "desktop.text.insert_line_below": "inserted line below text",
                "desktop.clipboard.write_text": "clipboard write text",
            }
            label = labels[request.action]
            request_data["target"] = f"[REDACTED: {label}]"
        result_data = result.to_dict()
        if request.action in {
            "desktop.text.read_focused",
            "desktop.text.read_selection",
            "desktop.clipboard.read_text",
            "desktop.text.read_previous_character",
            "desktop.text.read_next_character",
            "desktop.text.read_previous_word",
            "desktop.text.read_next_word",
            "desktop.text.read_current_line",
            "desktop.standard_dialog.read",
            "desktop.notifications.read",
        }:
            labels = {
                "desktop.text.read_focused": "focused text",
                "desktop.text.read_selection": "selected text",
                "desktop.clipboard.read_text": "clipboard text",
                "desktop.text.read_previous_character": "previous character",
                "desktop.text.read_next_character": "next character",
                "desktop.text.read_previous_word": "previous word",
                "desktop.text.read_next_word": "next word",
                "desktop.text.read_current_line": "current line",
                "desktop.standard_dialog.read": "standard dialog text",
                "desktop.notifications.read": "notification text",
            }
            label = labels[request.action]
            result_data["message"] = f"[REDACTED: {label}]"
            result_data["details"] = {}
        entry: Dict[str, Any] = {
            "timestamp": utc_now().isoformat(),
            "request": redact(request_data),
            "result": redact(result_data),
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
