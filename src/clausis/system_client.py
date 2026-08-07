"""Fail-closed client for the isolated system confirmation service."""

from __future__ import annotations

import asyncio
import json
from typing import Mapping, Optional, Protocol

from .models import ActionRequest, ActionResult


class BrokerLike(Protocol):
    def submit(self, request: ActionRequest) -> ActionResult:
        ...


class ConfirmationLike(Protocol):
    def confirm_and_submit(self, request: ActionRequest) -> ActionResult:
        ...


class ConfirmationAwareBroker:
    """Route only broker-declared risky actions to trusted confirmation."""

    def __init__(
        self,
        broker: BrokerLike,
        confirmer: Optional[ConfirmationLike] = None,
    ) -> None:
        self._broker = broker
        self._confirmer = confirmer

    def submit(self, request: ActionRequest) -> ActionResult:
        result = self._broker.submit(request)
        if result.status != "confirmation_required" or self._confirmer is None:
            return result
        try:
            return self._confirmer.confirm_and_submit(request)
        except Exception:
            return ActionResult(
                "denied",
                "Die geschützte lokale Bestätigung ist nicht verfügbar.",
                request.action,
            )


class SystemTrustedConfirmation:
    """One request per system-bus connection; no secrets cross this client."""

    BUS_NAME = "org.clausis.TrustedConfirm1"
    PATH = "/org/clausis/TrustedConfirm1"
    INTERFACE = "org.clausis.TrustedConfirm1"

    def confirm_and_submit(self, request: ActionRequest) -> ActionResult:
        return asyncio.run(self._confirm(request))

    async def _confirm(self, request: ActionRequest) -> ActionResult:
        try:
            from dbus_next import BusType
            from dbus_next.aio import MessageBus
        except ImportError as exc:
            raise RuntimeError("system D-Bus support is not installed") from exc

        bus = await MessageBus(bus_type=BusType.SYSTEM).connect()
        try:
            node = await bus.introspect(self.BUS_NAME, self.PATH)
            interface = bus.get_proxy_object(
                self.BUS_NAME, self.PATH, node
            ).get_interface(self.INTERFACE)
            raw = await interface.call_confirm_and_submit(
                json.dumps(request.to_dict(), ensure_ascii=False)
            )
            return _parse_result(raw, expected_action=request.action)
        finally:
            bus.disconnect()


def _parse_result(raw: str, *, expected_action: str) -> ActionResult:
    if not isinstance(raw, str) or len(raw.encode("utf-8")) > 32_768:
        raise ValueError("invalid confirmation response")
    decoded = json.loads(raw)
    if not isinstance(decoded, Mapping):
        raise ValueError("confirmation response must be an object")
    allowed = {"status", "message", "action", "confirmation_id", "details"}
    if set(decoded) - allowed:
        raise ValueError("confirmation response contains unknown fields")
    status = decoded.get("status")
    message = decoded.get("message")
    action = decoded.get("action")
    details = decoded.get("details", {})
    if not isinstance(status, str) or not isinstance(message, str):
        raise ValueError("confirmation response has invalid text fields")
    if status not in {
        "completed", "denied", "dry_run", "failed", "confirmation_required"
    }:
        raise ValueError("confirmation response has an invalid status")
    if action not in {expected_action, "invalid"}:
        raise ValueError("confirmation response action mismatch")
    if not isinstance(details, Mapping):
        raise ValueError("confirmation response details must be an object")
    confirmation_id = decoded.get("confirmation_id")
    if confirmation_id is not None and not isinstance(confirmation_id, str):
        raise ValueError("confirmation response ID is invalid")
    if len(message) > 2048:
        raise ValueError("confirmation response message is too long")
    return ActionResult(
        status=status,
        message=message,
        action=action,
        confirmation_id=confirmation_id,
        details=dict(details),
    )
