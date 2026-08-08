#!/usr/bin/env python3
"""Measure the software half of the wake-to-action latency budget.

This measures exactly what a build host can measure: the per-frame cost of the
energy gate, the cost of the keyword model when one is configured, and the time
from a recognised transcript to a broker decision.

It deliberately does **not** report an end-to-end wake-to-action latency. That
number is dominated by microphone buffering, PipeWire scheduling and speaker
output, none of which exist here, and publishing a figure measured without
audio hardware would be exactly the kind of unearned promise the release gate
exists to prevent.
"""

from __future__ import annotations

import argparse
import array
import json
import math
from pathlib import Path
import statistics
import sys
import time
from typing import List, Sequence

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from clausis.broker import ActionBroker, SafeExecutor  # noqa: E402
from clausis.capabilities import CapabilityAuthority  # noqa: E402
from clausis.executors import SessionExecutor  # noqa: E402
from clausis.router import OfflineRouter  # noqa: E402
from clausis.wake import (  # noqa: E402
    FRAME_MS,
    SAMPLE_RATE,
    EnergyGate,
    WakeWordGate,
    wake_model_is_configured,
)


def _frame(level: float) -> bytes:
    count = int(SAMPLE_RATE * FRAME_MS / 1000)
    data = array.array("h")
    amplitude = level * math.sqrt(2.0) * 32767
    for index in range(count):
        data.append(int(amplitude * math.sin(2.0 * math.pi * 440.0 * index / SAMPLE_RATE)))
    return data.tobytes()


def _percentiles(samples: Sequence[float]) -> dict:
    ordered = sorted(samples)
    return {
        "median_ms": round(statistics.median(ordered) * 1000, 4),
        "p95_ms": round(ordered[max(0, int(len(ordered) * 0.95) - 1)] * 1000, 4),
        "max_ms": round(ordered[-1] * 1000, 4),
    }


def measure_energy_gate(iterations: int) -> dict:
    gate = EnergyGate()
    silence = bytes(int(SAMPLE_RATE * FRAME_MS / 1000) * 2)
    speech = _frame(0.09)
    timings: List[float] = []
    for index in range(iterations):
        frame = speech if index % 4 == 0 else silence
        started = time.perf_counter()
        gate.accepts(frame)
        timings.append(time.perf_counter() - started)
    result = _percentiles(timings)
    # A frame lasts FRAME_MS; the gate must cost a small fraction of that or the
    # "permanent listener" is not cheap at all.
    result["frame_ms"] = FRAME_MS
    result["duty_cycle_percent"] = round(result["median_ms"] / FRAME_MS * 100, 3)
    return result


def measure_router_to_decision(iterations: int) -> dict:
    router = OfflineRouter()
    broker = ActionBroker(
        CapabilityAuthority.generate(), SessionExecutor(SafeExecutor(dry_run=True))
    )
    timings: List[float] = []
    for _ in range(iterations):
        started = time.perf_counter()
        request = router.route("Lautstärke 35 Prozent")
        broker.submit(request)
        timings.append(time.perf_counter() - started)
    return _percentiles(timings)


def measure_wake_model(iterations: int) -> dict:
    gate = WakeWordGate.from_model()
    if not gate.available():
        return {"configured": False}
    speech = _frame(0.09)
    timings: List[float] = []
    for _ in range(iterations):
        started = time.perf_counter()
        gate.push(speech)
        timings.append(time.perf_counter() - started)
    result = _percentiles(timings)
    result["configured"] = True
    return result


def main(argv: Sequence[str] = ()) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--iterations", type=int, default=2000)
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args(list(argv) or None)

    report = {
        "energy_gate": measure_energy_gate(args.iterations),
        "wake_model": measure_wake_model(max(50, args.iterations // 20)),
        "router_to_decision": measure_router_to_decision(args.iterations),
        "wake_model_configured": wake_model_is_configured(),
        "note": (
            "Software path only. End-to-end wake-to-action latency requires "
            "measurement on the target hardware with real audio."
        ),
    }
    if args.json:
        print(json.dumps(report, indent=2, sort_keys=True))
        return 0
    energy = report["energy_gate"]
    print(f"Energy gate: median {energy['median_ms']} ms per {energy['frame_ms']} ms frame")
    print(f"  duty cycle {energy['duty_cycle_percent']} % of one frame")
    if report["wake_model"].get("configured"):
        print(f"Wake model:  median {report['wake_model']['median_ms']} ms per frame")
    else:
        print("Wake model:  not configured; transcript gate remains in use")
    decision = report["router_to_decision"]
    print(f"Route+broker: median {decision['median_ms']} ms, p95 {decision['p95_ms']} ms")
    print(report["note"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
