#!/usr/bin/env python3
"""Read-only Clausis validation bridge for the Calamares hand-off.

The bridge never partitions.  It inventories disks or validates a secret-free
plan against the current hardware immediately before Calamares is opened.
"""

from __future__ import annotations

import argparse
from dataclasses import asdict
import json
import subprocess
import sys
from typing import Sequence

from clausis.installer import InstallerPlan, discover_install_disks


def _public_disk(disk) -> dict:
    data = asdict(disk)
    data["eligible"] = disk.eligible
    data["rejection_reasons"] = list(disk.rejection_reasons())
    return data


def main(argv: Sequence[str] = ()) -> int:
    parser = argparse.ArgumentParser(description="Clausis-Installationsplan sicher prüfen")
    parser.add_argument(
        "--inventory",
        action="store_true",
        help="nur die schreibgeschützte Datenträgererkennung als JSON ausgeben",
    )
    parser.add_argument(
        "--fixture-no-device-check",
        action="store_true",
        help=argparse.SUPPRESS,
    )
    args = parser.parse_args(list(argv) or None)
    try:
        if args.inventory:
            disks = discover_install_disks()
            print(json.dumps({"disks": [_public_disk(disk) for disk in disks]}, ensure_ascii=False))
            return 0
        payload = json.load(sys.stdin)
        if not isinstance(payload, dict):
            raise ValueError("installer plan must be a JSON object")
        plan = InstallerPlan(**payload)
        summary = plan.spoken_summary()
        if not args.fixture_no_device_check:
            disks = discover_install_disks()
            plan.bind_to(disks)
    except (
        OSError,
        TypeError,
        ValueError,
        json.JSONDecodeError,
        subprocess.SubprocessError,
    ) as exc:
        print(json.dumps({"status": "denied", "message": str(exc)}, ensure_ascii=False))
        return 2
    print(
        json.dumps(
            {"status": "confirmation_required", "summary": summary},
            ensure_ascii=False,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
