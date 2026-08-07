#!/usr/bin/env python3
"""Exercise the real dbus-next service interfaces on a private system bus."""

from __future__ import annotations

import asyncio
import json

from dbus_next import BusType
from dbus_next.aio import MessageBus


async def proxy(bus, name: str, path: str, interface: str):
    for _ in range(100):
        try:
            node = await bus.introspect(name, path)
            return bus.get_proxy_object(name, path, node).get_interface(interface), node
        except Exception:
            await asyncio.sleep(0.05)
    raise RuntimeError(f"service {name} did not appear")


async def main() -> None:
    bus = await MessageBus(bus_type=BusType.SYSTEM).connect()
    broker, _ = await proxy(
        bus,
        "org.clausis.ActionBroker1",
        "/org/clausis/ActionBroker1",
        "org.clausis.ActionBroker1",
    )
    confirmer, confirm_node = await proxy(
        bus,
        "org.clausis.TrustedConfirm1",
        "/org/clausis/TrustedConfirm1",
        "org.clausis.TrustedConfirm1",
    )
    methods = {
        method.name
        for interface in confirm_node.interfaces
        if interface.name == "org.clausis.TrustedConfirm1"
        for method in interface.methods
    }
    assert methods == {"ConfirmAndSubmit"}, methods

    malformed = json.loads(await confirmer.call_confirm_and_submit("[]"))
    assert malformed["status"] == "denied", malformed
    assert "pin" not in json.dumps(malformed).casefold(), malformed
    assert "capability" not in json.dumps(malformed).casefold(), malformed

    request = json.dumps({"action": "audio.volume.up", "origin": "local_voice"})
    result = json.loads(await broker.call_submit(request))
    assert result["status"] == "confirmation_required", result
    print("real system-bus interfaces reject automation and local-origin spoofing")
    bus.disconnect()


if __name__ == "__main__":
    asyncio.run(main())
