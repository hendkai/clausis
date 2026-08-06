"""Boot health checks used by snapshot rollback integration."""

from __future__ import annotations

import argparse
import json
import shutil
from typing import Dict, Sequence


REQUIRED = ("wpctl", "systemctl", "loginctl", "gio")
OPTIONAL = ("nmcli", "gtk-launch", "gnome-control-center", "orca")


def collect() -> Dict[str, object]:
    required = {name: bool(shutil.which(name)) for name in REQUIRED}
    optional = {name: bool(shutil.which(name)) for name in OPTIONAL}
    return {
        "healthy": all(required.values()),
        "required": required,
        "optional": optional,
        "rollback_recommended": not all(required.values()),
    }


def main(argv: Sequence[str] = ()) -> int:
    parser = argparse.ArgumentParser(description="Check VoiceOS boot health")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args(list(argv) or None)
    result = collect()
    if args.json:
        print(json.dumps(result, sort_keys=True))
    else:
        print("healthy" if result["healthy"] else "degraded")
    return 0 if result["healthy"] else 2


if __name__ == "__main__":
    raise SystemExit(main())

