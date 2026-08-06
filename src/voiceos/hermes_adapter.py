"""Strict adapter for Hermes tool calls.

The adapter never accepts shell commands.  Hermes can only submit the same
typed requests as the offline router, and Hermes-originated requests are always
tainted so policy requires a trusted confirmation.
"""

from __future__ import annotations

import json
from typing import Any, Mapping

from .models import ActionRequest, Origin


MAX_MESSAGE_BYTES = 32_768


def parse_tool_call(payload: str) -> ActionRequest:
    if len(payload.encode("utf-8")) > MAX_MESSAGE_BYTES:
        raise ValueError("Hermes tool call exceeds 32 KiB")
    try:
        decoded: Any = json.loads(payload)
    except json.JSONDecodeError as exc:
        raise ValueError("Hermes tool call is not valid JSON") from exc
    if not isinstance(decoded, Mapping):
        raise ValueError("Hermes tool call must be an object")
    request = ActionRequest.from_dict(decoded)
    if request.capability_token:
        raise ValueError("Hermes must not supply capability tokens")
    return ActionRequest(
        action=request.action,
        target=request.target,
        arguments=request.arguments,
        origin=Origin.HERMES,
        risk=request.risk,
        reversible=request.reversible,
        expires_at=request.expires_at,
    )


HERMES_DENYLIST_CONFIG = {
    "approvals": {"mode": "manual"},
    "tools": {
        "terminal": False,
        "execute_code": False,
        "write_file": False,
        "patch": False,
        "skill_manage": False,
    },
    "skills": {"write_approval": True, "guard_agent_created": True},
}

