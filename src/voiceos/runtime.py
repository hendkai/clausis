"""Offline-first orchestration loop.

Production audio frontends feed final transcripts into this object.  Keeping
the orchestration independent of microphone libraries makes it usable by the
Calamares installer, speech-dispatcher, tests and recovery console.
"""

from __future__ import annotations

import argparse
import json
import sys
from enum import Enum
from typing import Callable, Optional, Sequence

from .broker import ActionBroker
from .models import ActionResult
from .router import OfflineRouter


class RuntimeState(str, Enum):
    IDLE = "idle"
    LISTENING = "listening"
    PROCESSING = "processing"
    SPEAKING = "speaking"
    STOPPED = "stopped"


class VoiceRuntime:
    def __init__(
        self,
        router: OfflineRouter,
        broker: ActionBroker,
        *,
        hermes_fallback: Optional[Callable[[str], ActionResult]] = None,
    ) -> None:
        self.router = router
        self.broker = broker
        self.hermes_fallback = hermes_fallback
        self.state = RuntimeState.IDLE

    def handle_transcript(self, transcript: str) -> ActionResult:
        self.state = RuntimeState.PROCESSING
        request = self.router.route(transcript)
        if request is not None and request.action == "voice.stop":
            self.state = RuntimeState.STOPPED
            return ActionResult("stopped", "Hermes wurde sofort gestoppt.", request.action)
        if request is not None:
            result = self.broker.submit(request)
            self.state = RuntimeState.IDLE
            return result
        if self.hermes_fallback is None:
            self.state = RuntimeState.IDLE
            return ActionResult(
                "offline_unmatched",
                "Dieser Befehl ist im Offline-Modus nicht verfügbar.",
                "voice.unmatched",
            )
        result = self.hermes_fallback(transcript)
        self.state = RuntimeState.IDLE
        return result


def main(argv: Sequence[str] = ()) -> int:
    """Recovery/developer JSON-lines frontend; real audio is a plugin."""
    parser = argparse.ArgumentParser(description="VoiceOS transcript runtime")
    parser.add_argument("--stdin", action="store_true", help="read one transcript per line")
    parser.add_argument("--pipewire", action="store_true", help="start the local microphone frontend")
    args = parser.parse_args(list(argv) or None)
    if args.pipewire:
        from .assistant import main as assistant_main
        return assistant_main([])
    if not args.stdin:
        parser.error("choose --stdin or --pipewire")
    from .broker import SafeExecutor
    from .capabilities import CapabilityAuthority

    runtime = VoiceRuntime(
        OfflineRouter(),
        ActionBroker(CapabilityAuthority.generate(), SafeExecutor(dry_run=True)),
    )
    for line in sys.stdin:
        result = runtime.handle_transcript(line.rstrip("\n"))
        print(json.dumps(result.to_dict(), ensure_ascii=False), flush=True)
        if runtime.state is RuntimeState.STOPPED:
            break
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
