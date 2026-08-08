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

from clausis.installer import (
    InstallerPlan,
    calamares_prewrite_summary,
    discard_staged_recovery_key,
    discover_install_disks,
    generate_recovery_key,
    guard_calamares_erase_transaction,
    stage_recovery_key,
)
from clausis.trusted_audio import DirectInstallConfirmation


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
        "--guard-transaction",
        action="store_true",
        help="Calamares-Auswahl unmittelbar vor der Partitionierung erneut binden",
    )
    parser.add_argument("--device", default="")
    parser.add_argument("--install-mode", default="")
    parser.add_argument("--encrypted", default="")
    parser.add_argument("--filesystem", default="")
    parser.add_argument(
        "--fixture-no-device-check",
        action="store_true",
        help=argparse.SUPPRESS,
    )
    args = parser.parse_args(list(argv) or None)
    try:
        if args.inventory and args.guard_transaction:
            raise ValueError("choose exactly one bridge operation")
        if args.inventory:
            disks = discover_install_disks()
            print(json.dumps({"disks": [_public_disk(disk) for disk in disks]}, ensure_ascii=False))
            return 0
        if args.guard_transaction:
            # Remove a key left by a killed/aborted earlier guard before any
            # Calamares mode can continue into the LUKS module.
            discard_staged_recovery_key()
            if args.install_mode != "erase":
                # This process sits before Calamares' first partition job.
                # Returning success for an empty, unknown or non-erase value
                # would turn a failed GS hand-off into a confirmation bypass.
                # Manual/alongside installs need their own trusted transaction
                # binding before they can be enabled.
                raise ValueError(
                    "installation mode is missing or not protected by the Clausis guard"
                )
            disk = guard_calamares_erase_transaction(
                discover_install_disks(),
                device_node=args.device,
                encrypted=args.encrypted,
                filesystem=args.filesystem,
            )
            recovery_key = generate_recovery_key()
            stage_recovery_key(recovery_key)
            try:
                approved = DirectInstallConfirmation().authorize(
                    calamares_prewrite_summary(disk), recovery_key
                )
                if not approved:
                    raise ValueError("protected installation confirmation failed")
                print(
                    json.dumps(
                        {
                            "status": "target_bound",
                            "device": disk.path,
                            "stable_id": disk.stable_id,
                            "size_bytes": disk.size_bytes,
                            "serial_suffix": disk.serial_suffix,
                        },
                        ensure_ascii=False,
                    )
                )
            except Exception:
                discard_staged_recovery_key()
                raise
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
        RuntimeError,
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
