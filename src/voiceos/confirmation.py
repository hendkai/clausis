"""Trusted confirmation state machine.

This service must run outside the desktop accessibility tree in production.
It generates the challenge itself, speaks the canonical action summary, and
issues a capability only after an exact, time-bounded response and PIN check.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import timedelta
import hashlib
import hmac
import secrets
from typing import Dict, Optional, Sequence

from .capabilities import CapabilityAuthority
from .models import ActionRequest, utc_now


DEFAULT_WORDS = (
    "anker", "birke", "dachs", "eule", "feder", "garten", "hafen", "insel",
    "kerze", "lampe", "mond", "nuss", "quelle", "regen", "sonne", "wolke",
)


@dataclass
class PendingConfirmation:
    confirmation_id: str
    request: ActionRequest
    phrase: str
    expires_at: object
    attempts: int = 0


class PinVerifier:
    """PBKDF2 PIN verifier; plaintext PINs are never persisted.

    PBKDF2-HMAC-SHA-256 is available in every supported Python/OpenSSL build,
    including the minimal installer environment.  The format is deliberately
    versioned so a future Argon2 migration can happen without guessing.
    """

    ALGORITHM = "pbkdf2-sha256-v1"
    ITERATIONS = 600_000

    def __init__(self, salt: bytes, digest: bytes) -> None:
        self._salt = salt
        self._digest = digest

    @classmethod
    def enroll(cls, pin: str) -> "PinVerifier":
        cls._validate_pin(pin)
        salt = secrets.token_bytes(16)
        return cls(salt, cls._derive(pin, salt))

    @classmethod
    def from_hex(cls, salt: str, digest: str) -> "PinVerifier":
        return cls(bytes.fromhex(salt), bytes.fromhex(digest))

    def export(self) -> Dict[str, str]:
        return {
            "algorithm": self.ALGORITHM,
            "iterations": str(self.ITERATIONS),
            "salt": self._salt.hex(),
            "digest": self._digest.hex(),
        }

    def verify(self, pin: str) -> bool:
        try:
            candidate = self._derive(pin, self._salt)
        except (TypeError, ValueError):
            return False
        return hmac.compare_digest(candidate, self._digest)

    @classmethod
    def _derive(cls, pin: str, salt: bytes) -> bytes:
        return hashlib.pbkdf2_hmac(
            "sha256", pin.encode("utf-8"), salt, cls.ITERATIONS, dklen=32
        )

    @staticmethod
    def _validate_pin(pin: str) -> None:
        if not isinstance(pin, str) or not pin.isdigit() or not 6 <= len(pin) <= 12:
            raise ValueError("PIN must contain 6 to 12 digits")


class TrustedConfirmer:
    def __init__(
        self,
        authority: CapabilityAuthority,
        pin_verifier: PinVerifier,
        *,
        words: Sequence[str] = DEFAULT_WORDS,
        ttl_seconds: int = 30,
    ) -> None:
        if len(words) < 8:
            raise ValueError("challenge vocabulary is too small")
        self._authority = authority
        self._pin = pin_verifier
        self._words = tuple(words)
        self._ttl_seconds = ttl_seconds
        self._pending: Dict[str, PendingConfirmation] = {}

    def begin(self, request: ActionRequest) -> PendingConfirmation:
        confirmation_id = secrets.token_urlsafe(18)
        phrase = " ".join(secrets.choice(self._words) for _ in range(3))
        pending = PendingConfirmation(
            confirmation_id=confirmation_id,
            request=request,
            phrase=phrase,
            expires_at=utc_now() + timedelta(seconds=self._ttl_seconds),
        )
        self._pending[confirmation_id] = pending
        return pending

    def canonical_summary(self, pending: PendingConfirmation) -> str:
        request = pending.request
        irreversible = "nicht rückgängig" if not request.reversible else "rückgängig machbar"
        target = request.target or "das System"
        return (
            f"Geplante Aktion: {request.action}. Ziel: {target}. "
            f"Risiko: {request.risk.value}. Die Aktion ist {irreversible}. "
            f"Zum Bestätigen sagen Sie: {pending.phrase}."
        )

    def approve(self, confirmation_id: str, phrase: str, pin: str) -> str:
        pending = self._pending.get(confirmation_id)
        if pending is None:
            raise ValueError("unknown confirmation")
        if pending.expires_at <= utc_now():
            self._pending.pop(confirmation_id, None)
            raise ValueError("confirmation expired")
        pending.attempts += 1
        if pending.attempts > 3:
            self._pending.pop(confirmation_id, None)
            raise ValueError("too many confirmation attempts")
        normalized = " ".join(phrase.casefold().split())
        if not hmac.compare_digest(normalized, pending.phrase.casefold()):
            raise ValueError("challenge phrase did not match")
        if not self._pin.verify(pin):
            raise ValueError("PIN verification failed")
        self._pending.pop(confirmation_id, None)
        return self._authority.issue(pending.request, ttl_seconds=self._ttl_seconds)

    def deny(self, confirmation_id: str) -> None:
        self._pending.pop(confirmation_id, None)
