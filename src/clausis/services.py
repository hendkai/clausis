"""D-Bus service entry points.

The optional ``dbus-next`` dependency is imported only on Debian.  Unit tests
exercise the same broker and confirmation objects without needing a bus.
"""

from __future__ import annotations

import asyncio
from dataclasses import replace
import json
import os
from pathlib import Path
from typing import Mapping

from .audit import AuditLog
from .broker import ActionBroker, SafeExecutor
from .capabilities import CapabilityAuthority
from .confirmation import (
    PinVerifier,
    TrustedConfirmer,
    canonicalize_untrusted_request,
)
from .models import ActionRequest, ActionResult, Origin
from .policy import ACTION_POLICIES


MAX_DBUS_REQUEST_BYTES = 32_768


def parse_dbus_request(request_json: str) -> ActionRequest:
    if not isinstance(request_json, str):
        raise ValueError("request must be a JSON string")
    if len(request_json.encode("utf-8")) > MAX_DBUS_REQUEST_BYTES:
        raise ValueError("request exceeds 32 KiB")
    decoded = json.loads(request_json)
    if not isinstance(decoded, Mapping):
        raise ValueError("request must be a JSON object")
    return ActionRequest.from_dict(decoded)


def _credential(name: str, *, minimum: int = 32) -> bytes:
    directory = os.environ.get("CREDENTIALS_DIRECTORY")
    path = Path(directory, name) if directory else Path("/etc/clausis", name)
    data = path.read_bytes()
    if len(data) < minimum:
        raise RuntimeError(f"credential {name} is too short")
    return data


async def _run_broker() -> None:
    try:
        from dbus_next import BusType
        from dbus_next.aio import MessageBus
        from dbus_next.service import ServiceInterface, method
    except ImportError as exc:
        raise SystemExit("install clausis-core[dbus] to run the D-Bus services") from exc

    authority = CapabilityAuthority(_credential("capability.key"))
    audit = AuditLog(Path("/var/log/clausis/actions.jsonl"), _credential("audit.key"))
    execute = os.environ.get("CLAUSIS_EXECUTE") == "1"
    broker = ActionBroker(authority, SafeExecutor(dry_run=not execute), audit_log=audit)

    class BrokerInterface(ServiceInterface):
        def __init__(self) -> None:
            super().__init__("org.clausis.ActionBroker1")

        @method()
        def Submit(self, request_json: "s") -> "s":
            try:
                request = parse_dbus_request(request_json)
                # An unconfirmed public-bus caller cannot claim trusted local
                # provenance. A valid action-bound token retains the exact
                # request that the isolated confirmer approved.
                if request.capability_token is None:
                    request = replace(request, origin=Origin.HERMES)
                result = broker.submit(request).to_dict()
            except (ValueError, json.JSONDecodeError) as exc:
                result = {"status": "denied", "message": str(exc), "action": "invalid"}
            return json.dumps(result, ensure_ascii=False)

        @method()
        def GetCapabilities(self) -> "s":
            return json.dumps(sorted(ACTION_POLICIES))

    bus = await MessageBus(bus_type=BusType.SYSTEM).connect()
    bus.export("/org/clausis/ActionBroker1", BrokerInterface())
    await bus.request_name("org.clausis.ActionBroker1")
    await asyncio.get_running_loop().create_future()


async def _run_confirm() -> None:
    try:
        from dbus_next import BusType
        from dbus_next.aio import MessageBus
        from dbus_next.service import ServiceInterface, method
    except ImportError as exc:
        raise SystemExit("install clausis-core[dbus] to run the D-Bus services") from exc

    authority = CapabilityAuthority(_credential("capability.key"))
    pin_data = json.loads(_credential("voice-pin.json", minimum=8).decode("utf-8"))
    pin = PinVerifier.from_export(pin_data)
    confirmer = TrustedConfirmer(authority, pin)

    from .trusted_audio import DirectAudioConfirmation

    trusted_input = DirectAudioConfirmation(
        os.environ.get(
            "CLAUSIS_STT_MODEL", "/usr/share/clausis/models/faster-whisper-base"
        ),
        language=os.environ.get("CLAUSIS_LANGUAGE", "de"),
    )

    bus = await MessageBus(bus_type=BusType.SYSTEM).connect()
    broker_node = await bus.introspect(
        "org.clausis.ActionBroker1", "/org/clausis/ActionBroker1"
    )
    broker_proxy = bus.get_proxy_object(
        "org.clausis.ActionBroker1", "/org/clausis/ActionBroker1", broker_node
    ).get_interface("org.clausis.ActionBroker1")

    class ConfirmInterface(ServiceInterface):
        def __init__(self) -> None:
            super().__init__("org.clausis.TrustedConfirm1")

        @method()
        async def ConfirmAndSubmit(self, request_json: "s") -> "s":
            try:
                request = canonicalize_untrusted_request(
                    parse_dbus_request(request_json)
                )
                approved = await asyncio.to_thread(
                    confirmer.approve_from_trusted_input, request, trusted_input
                )
                # The capability is never returned to the desktop client. The
                # isolated service consumes it immediately at ActionBroker.
                return await broker_proxy.call_submit(
                    json.dumps(approved.to_dict(), ensure_ascii=False)
                )
            except Exception:
                # Do not return challenge, PIN, transcript or capability data.
                result = ActionResult(
                    "denied", "Vertrauenswürdige Bestätigung fehlgeschlagen.", "invalid"
                )
                return json.dumps(result.to_dict(), ensure_ascii=False)

    bus.export("/org/clausis/TrustedConfirm1", ConfirmInterface())
    await bus.request_name("org.clausis.TrustedConfirm1")
    await asyncio.get_running_loop().create_future()


def broker_main() -> None:
    asyncio.run(_run_broker())


def confirm_main() -> None:
    asyncio.run(_run_confirm())
