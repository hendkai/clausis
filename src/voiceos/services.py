"""D-Bus service entry points.

The optional ``dbus-next`` dependency is imported only on Debian.  Unit tests
exercise the same broker and confirmation objects without needing a bus.
"""

from __future__ import annotations

import asyncio
import json
import os
from pathlib import Path
from typing import Any

from .audit import AuditLog
from .broker import ActionBroker, SafeExecutor
from .capabilities import CapabilityAuthority
from .confirmation import PinVerifier, TrustedConfirmer
from .models import ActionRequest
from .policy import ACTION_POLICIES


def _credential(name: str, *, minimum: int = 32) -> bytes:
    directory = os.environ.get("CREDENTIALS_DIRECTORY")
    path = Path(directory, name) if directory else Path("/etc/voiceos", name)
    data = path.read_bytes()
    if len(data) < minimum:
        raise RuntimeError(f"credential {name} is too short")
    return data


async def _run_broker() -> None:
    try:
        from dbus_next.aio import MessageBus
        from dbus_next.service import ServiceInterface, method
    except ImportError as exc:
        raise SystemExit("install voiceos-core[dbus] to run the D-Bus services") from exc

    authority = CapabilityAuthority(_credential("capability.key"))
    audit = AuditLog(Path("/var/log/voiceos/actions.jsonl"), _credential("audit.key"))
    execute = os.environ.get("VOICEOS_EXECUTE") == "1"
    broker = ActionBroker(authority, SafeExecutor(dry_run=not execute), audit_log=audit)

    class BrokerInterface(ServiceInterface):
        def __init__(self) -> None:
            super().__init__("org.voiceos.ActionBroker1")

        @method()
        def Submit(self, request_json: "s") -> "s":
            try:
                request = ActionRequest.from_dict(json.loads(request_json))
                result = broker.submit(request).to_dict()
            except (ValueError, json.JSONDecodeError) as exc:
                result = {"status": "denied", "message": str(exc), "action": "invalid"}
            return json.dumps(result, ensure_ascii=False)

        @method()
        def GetCapabilities(self) -> "s":
            return json.dumps(sorted(ACTION_POLICIES))

    bus = await MessageBus().connect()
    bus.export("/org/voiceos/ActionBroker1", BrokerInterface())
    await bus.request_name("org.voiceos.ActionBroker1")
    await asyncio.get_running_loop().create_future()


async def _run_confirm() -> None:
    try:
        from dbus_next.aio import MessageBus
        from dbus_next.service import ServiceInterface, method
    except ImportError as exc:
        raise SystemExit("install voiceos-core[dbus] to run the D-Bus services") from exc

    authority = CapabilityAuthority(_credential("capability.key"))
    pin_data = json.loads(_credential("voice-pin.json", minimum=8).decode("utf-8"))
    pin = PinVerifier.from_hex(pin_data["salt"], pin_data["digest"])
    confirmer = TrustedConfirmer(authority, pin)

    class ConfirmInterface(ServiceInterface):
        def __init__(self) -> None:
            super().__init__("org.voiceos.TrustedConfirm1")

        @method()
        def Begin(self, request_json: "s") -> "s":
            request = ActionRequest.from_dict(json.loads(request_json))
            pending = confirmer.begin(request)
            return json.dumps({
                "confirmation_id": pending.confirmation_id,
                "summary": confirmer.canonical_summary(pending),
                "expires_at": pending.expires_at.isoformat(),
            }, ensure_ascii=False)

        @method()
        def Approve(self, confirmation_id: "s", phrase: "s", pin: "s") -> "s":
            # Prototype transport only. Release builds replace this string with
            # a protected memfd/portal and direct audio verification.
            return confirmer.approve(confirmation_id, phrase, pin)

        @method()
        def Deny(self, confirmation_id: "s") -> "":
            confirmer.deny(confirmation_id)

    bus = await MessageBus().connect()
    bus.export("/org/voiceos/TrustedConfirm1", ConfirmInterface())
    await bus.request_name("org.voiceos.TrustedConfirm1")
    await asyncio.get_running_loop().create_future()


def broker_main() -> None:
    asyncio.run(_run_broker())


def confirm_main() -> None:
    asyncio.run(_run_confirm())

