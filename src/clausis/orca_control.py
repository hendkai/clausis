"""Bounded session-level recovery controls for Orca."""

from __future__ import annotations

import subprocess
import sys
import time
from typing import Callable, Sequence


def restart_orca(
    *,
    popen: Callable[..., subprocess.Popen[bytes]] = subprocess.Popen,
    wait: Callable[[float], None] = time.sleep,
) -> None:
    process = popen(
        ["orca", "--replace", "--enable", "speech"],
        stdin=subprocess.DEVNULL,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        start_new_session=True,
        close_fds=True,
    )
    wait(1.0)
    returncode = process.poll()
    if returncode is not None:
        raise RuntimeError(f"Orca recovery exited during startup with status {returncode}")


def main(argv: Sequence[str] | None = None) -> int:
    arguments = list(sys.argv[1:] if argv is None else argv)
    if arguments != ["restart"]:
        return 2
    try:
        restart_orca()
    except (OSError, RuntimeError):
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
