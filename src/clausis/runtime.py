"""Offline-first orchestration loop.

Production audio frontends feed final transcripts into this object.  Keeping
the orchestration independent of microphone libraries makes it usable by the
Calamares installer, speech-dispatcher, tests and recovery console.
"""

from __future__ import annotations

import argparse
import json
import math
import sys
import time
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
    CORRECTING = "correcting"
    STOPPED = "stopped"


class VoiceRuntime:
    def __init__(
        self,
        router: OfflineRouter,
        broker: ActionBroker,
        *,
        hermes_fallback: Optional[Callable[[str], ActionResult]] = None,
        correction_ttl_seconds: float = 30.0,
        clock: Callable[[], float] = time.monotonic,
    ) -> None:
        try:
            ttl = float(correction_ttl_seconds)
        except (TypeError, ValueError) as exc:
            raise ValueError("correction TTL must be numeric") from exc
        if not math.isfinite(ttl) or not 5.0 <= ttl <= 120.0:
            raise ValueError("correction TTL must be between 5 and 120 seconds")
        self.router = router
        self.broker = broker
        self.hermes_fallback = hermes_fallback
        self._correction_ttl_seconds = ttl
        self._clock = clock
        self.state = RuntimeState.IDLE
        self.last_result: Optional[ActionResult] = None
        self._correction_pending = False
        self._correction_deadline: Optional[float] = None

    @property
    def correction_pending(self) -> bool:
        """Whether exactly one replacement transcript is currently expected."""

        return self._correction_pending

    @property
    def correction_remaining_seconds(self) -> float:
        """Monotonic remaining time without extending or consuming the slot."""

        if not self._correction_pending or self._correction_deadline is None:
            return 0.0
        return max(0.0, self._correction_deadline - self._clock())

    def cancel_correction(self) -> None:
        """Clear a pending correction when the local wake gate is put to sleep."""

        self._clear_correction()
        if self.state is RuntimeState.CORRECTING:
            self.state = RuntimeState.IDLE

    def _clear_correction(self) -> None:
        self._correction_pending = False
        self._correction_deadline = None

    def handle_transcript(self, transcript: str) -> ActionResult:
        self.state = RuntimeState.PROCESSING
        request = self.router.route(transcript)
        if request is not None and request.action == "voice.stop":
            self._clear_correction()
            self.state = RuntimeState.STOPPED
            return ActionResult("stopped", "Hermes wurde sofort gestoppt.", request.action)
        if request is not None and request.action == "voice.cancel":
            self._clear_correction()
            self.state = RuntimeState.IDLE
            result = ActionResult("completed", "Der aktuelle Sprachdialog wurde abgebrochen.", request.action)
            self.last_result = result
            return result
        if request is not None and request.action == "voice.correct":
            self._correction_pending = True
            self._correction_deadline = self._clock() + self._correction_ttl_seconds
            self.state = RuntimeState.CORRECTING
            result = ActionResult(
                "correction_requested",
                f"Bitte sagen Sie jetzt innerhalb von {self._correction_ttl_seconds:g} Sekunden genau einen korrigierten Befehl. Die vorherige Aktion wird nicht automatisch rückgängig gemacht. Sagen Sie Abbrechen, um die Korrektur zu beenden.",
                request.action,
            )
            self.last_result = result
            return result
        if self._correction_pending and (
            self._correction_deadline is None or self._clock() >= self._correction_deadline
        ):
            self._clear_correction()
            self.state = RuntimeState.IDLE
            result = ActionResult(
                "correction_expired",
                "Die Korrekturzeit ist abgelaufen. Die verspätete Äußerung wurde nicht ausgeführt. Sagen Sie Korrigieren, um neu zu beginnen.",
                "voice.correct",
            )
            self.last_result = result
            return result
        if request is not None and request.action == "voice.repeat":
            self.state = (
                RuntimeState.CORRECTING if self._correction_pending else RuntimeState.IDLE
            )
            if self.last_result is None:
                return ActionResult("completed", "Es gibt noch nichts zu wiederholen.", request.action)
            return ActionResult("repeated", self.last_result.message, request.action)
        # A correction slot is deliberately one-shot and stores no transcript.
        # Its replacement follows the same router/broker/fallback path as a
        # normal utterance; unmatched input therefore cannot leave a stale slot.
        self._clear_correction()
        if request is not None:
            result = self.broker.submit(request)
            self.state = RuntimeState.IDLE
            self.last_result = result
            return result
        if self.hermes_fallback is None:
            self.state = RuntimeState.IDLE
            result = ActionResult(
                "offline_unmatched",
                "Dieser Befehl ist im Offline-Modus nicht verfügbar.",
                "voice.unmatched",
            )
            self.last_result = result
            return result
        result = self.hermes_fallback(transcript)
        self.state = RuntimeState.IDLE
        self.last_result = result
        return result


def main(argv: Sequence[str] = ()) -> int:
    """Recovery/developer JSON-lines frontend; real audio is a plugin."""
    parser = argparse.ArgumentParser(description="Clausis transcript runtime")
    parser.add_argument("--stdin", action="store_true", help="read one transcript per line")
    parser.add_argument("--pipewire", action="store_true", help="start the local microphone frontend")
    parser.add_argument(
        "--execute",
        action="store_true",
        help="execute validated low-risk actions in the user session",
    )
    args = parser.parse_args(list(argv) or None)
    if args.pipewire:
        from .assistant import main as assistant_main
        return assistant_main(["--execute"] if args.execute else [])
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
