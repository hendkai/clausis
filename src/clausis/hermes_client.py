"""Narrow, non-interactive Hermes reply adapter for the voice runtime."""

from __future__ import annotations

import json
import os
from pathlib import Path
import subprocess
from typing import Mapping, Optional

from .models import ActionResult
from .recovery import Failure, recovery_for


MAX_PROMPT_CHARACTERS = 4096
MAX_RESPONSE_CHARACTERS = 16_000


def hermes_is_configured(home: Path) -> bool:
    """Return whether the Clausis setup marked Hermes ready for cloud/local chat."""
    try:
        payload = json.loads((home / ".hermes" / "config.yaml").read_text(encoding="utf-8"))
    except (OSError, ValueError, TypeError):
        return False
    clausis = payload.get("clausis")
    return isinstance(clausis, dict) and clausis.get("setup_complete") is True


class HermesOneShot:
    """Ask Hermes for one plain-text reply with a minimal toolset forced on.

    System actions do not cross this adapter. Deterministic Clausis commands
    are routed before this fallback and continue to use the typed broker. The
    invocation exposes only Hermes' local ``todo`` toolset; the user's provider
    configuration is still loaded for the model and credentials.
    """

    def __init__(
        self,
        executable: str = "/usr/local/bin/hermes",
        *,
        timeout: float = 45.0,
        home: Optional[Path] = None,
    ) -> None:
        self.executable = executable
        self.timeout = timeout
        self.home = home or Path.home()

    def __call__(self, prompt: str) -> ActionResult:
        cleaned = " ".join(prompt.strip().split())
        if not cleaned:
            return ActionResult("failed", "Die Hermes-Anfrage ist leer.", "hermes.chat")
        if len(cleaned) > MAX_PROMPT_CHARACTERS:
            return ActionResult("failed", "Die Hermes-Anfrage ist zu lang.", "hermes.chat")
        if not hermes_is_configured(self.home):
            return ActionResult(
                "offline_unmatched",
                "Hermes ist noch nicht mit einem Anbieter verbunden.",
                "hermes.chat",
            )
        try:
            completed = subprocess.run(
                [self.executable, "--toolsets", "todo", "-z", cleaned],
                shell=False,
                check=False,
                capture_output=True,
                text=True,
                timeout=self.timeout,
                env=_child_environment(self.home),
            )
        except (OSError, subprocess.SubprocessError):
            # Name the equal keyboard path instead of leaving the user with a
            # dead end when network or agent is gone.
            return ActionResult(
                "failed",
                recovery_for(Failure.AGENT_UNAVAILABLE).message(),
                "hermes.chat",
            )
        response = completed.stdout.strip()
        if completed.returncode != 0 or not response:
            return ActionResult(
                "failed",
                "Hermes konnte nicht antworten. Technische Fehlermeldungen werden aus "
                "Datenschutzgründen nicht vorgelesen. "
                + recovery_for(Failure.AGENT_UNAVAILABLE).keyboard,
                "hermes.chat",
            )
        return ActionResult(
            "hermes_response", response[:MAX_RESPONSE_CHARACTERS], "hermes.chat"
        )


def _child_environment(home: Path) -> Mapping[str, str]:
    environment = {
        "HOME": str(home),
        "PATH": "/usr/local/bin:/usr/bin:/bin",
        "PYTHONUNBUFFERED": "1",
    }
    for name in (
        "DBUS_SESSION_BUS_ADDRESS",
        "LANG",
        "LC_ALL",
        "WAYLAND_DISPLAY",
        "XDG_RUNTIME_DIR",
    ):
        if name in os.environ:
            environment[name] = os.environ[name]
    return environment
