#!/usr/bin/env python3
"""Calamares process-module validation bridge.

Calamares supplies a JSON plan on stdin.  The bridge validates it and emits a
secret-free canonical summary. It intentionally does not partition disks in
the prototype; Calamares owns that operation after trusted confirmation.
"""

from __future__ import annotations

import json
import sys

from clausis.installer import InstallerPlan


def main() -> int:
    try:
        payload = json.load(sys.stdin)
        plan = InstallerPlan(**payload)
        summary = plan.spoken_summary()
    except (TypeError, ValueError, json.JSONDecodeError) as exc:
        print(json.dumps({"status": "denied", "message": str(exc)}))
        return 2
    print(json.dumps({"status": "confirmation_required", "summary": summary}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

