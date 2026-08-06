"""Developer CLI. Execution is dry-run unless explicitly enabled."""

from __future__ import annotations

import argparse
import json
import os
import sys
from typing import Sequence

from .broker import ActionBroker, SafeExecutor
from .capabilities import CapabilityAuthority
from .models import ActionRequest
from .router import OfflineRouter


def main(argv: Sequence[str] = ()) -> int:
    parser = argparse.ArgumentParser(prog="clausisctl")
    subparsers = parser.add_subparsers(dest="command", required=True)
    route = subparsers.add_parser("route", help="route an offline voice command")
    route.add_argument("transcript")
    validate = subparsers.add_parser("validate", help="validate an action request")
    validate.add_argument("request_json")
    args = parser.parse_args(list(argv) or None)

    if args.command == "route":
        request = OfflineRouter().route(args.transcript)
        if request is None:
            print(json.dumps({"status": "unmatched"}))
            return 1
    else:
        try:
            request = ActionRequest.from_dict(json.loads(args.request_json))
        except (ValueError, json.JSONDecodeError) as exc:
            print(json.dumps({"status": "invalid", "message": str(exc)}))
            return 2

    authority = CapabilityAuthority(os.urandom(32))
    result = ActionBroker(authority, SafeExecutor(dry_run=True)).submit(request)
    print(json.dumps({"request": request.to_dict(), "result": result.to_dict()}, ensure_ascii=False))
    return 0 if result.status in {"dry_run", "confirmation_required"} else 2


if __name__ == "__main__":
    raise SystemExit(main())

