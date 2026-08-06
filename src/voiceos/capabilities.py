"""Short-lived, action-bound capability tokens.

Tokens are signed by TrustedConfirm and verified by ActionBroker.  The key is
provided by a root-owned credential file in production.  Hermes never receives
the signing key and cannot broaden a token to another action or target.
"""

from __future__ import annotations

import base64
import hashlib
import hmac
import json
import secrets
from datetime import timedelta
from typing import Any, Dict, Optional, Set

from .models import ActionRequest, parse_timestamp, utc_now


class CapabilityError(ValueError):
    pass


def _b64(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).decode("ascii").rstrip("=")


def _unb64(data: str) -> bytes:
    return base64.urlsafe_b64decode(data + "=" * (-len(data) % 4))


class CapabilityAuthority:
    def __init__(self, key: bytes, *, consumed: Optional[Set[str]] = None) -> None:
        if len(key) < 32:
            raise ValueError("capability key must contain at least 32 bytes")
        self._key = key
        self._consumed = consumed if consumed is not None else set()

    @classmethod
    def generate(cls) -> "CapabilityAuthority":
        return cls(secrets.token_bytes(32))

    def issue(self, request: ActionRequest, ttl_seconds: int = 30) -> str:
        if ttl_seconds < 1 or ttl_seconds > 120:
            raise ValueError("capability TTL must be between 1 and 120 seconds")
        payload: Dict[str, Any] = {
            "v": 1,
            "jti": secrets.token_urlsafe(18),
            "action": request.action,
            "target": request.target,
            "arguments_sha256": self.arguments_digest(request),
            "origin": request.origin.value,
            "expires_at": (utc_now() + timedelta(seconds=ttl_seconds)).isoformat(),
        }
        body = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()
        signature = hmac.new(self._key, body, hashlib.sha256).digest()
        return _b64(body) + "." + _b64(signature)

    def verify(self, token: str, request: ActionRequest, *, consume: bool = True) -> Dict[str, Any]:
        try:
            body_part, signature_part = token.split(".", 1)
            body = _unb64(body_part)
            signature = _unb64(signature_part)
            payload = json.loads(body)
        except (ValueError, TypeError, json.JSONDecodeError) as exc:
            raise CapabilityError("malformed capability") from exc
        expected = hmac.new(self._key, body, hashlib.sha256).digest()
        if not hmac.compare_digest(signature, expected):
            raise CapabilityError("invalid capability signature")
        if payload.get("v") != 1:
            raise CapabilityError("unsupported capability version")
        if parse_timestamp(payload["expires_at"]) <= utc_now():
            raise CapabilityError("capability expired")
        expected_fields = {
            "action": request.action,
            "target": request.target,
            "arguments_sha256": self.arguments_digest(request),
            "origin": request.origin.value,
        }
        if any(payload.get(key) != value for key, value in expected_fields.items()):
            raise CapabilityError("capability is not valid for this request")
        jti = str(payload.get("jti", ""))
        if not jti or jti in self._consumed:
            raise CapabilityError("capability was already consumed")
        if consume:
            self._consumed.add(jti)
        return payload

    @staticmethod
    def arguments_digest(request: ActionRequest) -> str:
        encoded = json.dumps(
            dict(request.arguments), sort_keys=True, separators=(",", ":"), ensure_ascii=False
        ).encode("utf-8")
        return hashlib.sha256(encoded).hexdigest()

