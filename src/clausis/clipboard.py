"""Bounded Wayland clipboard writer with no content in argv or output."""

from __future__ import annotations

import os
import selectors
import subprocess
import time
from typing import Callable


MAX_CLIPBOARD_CHARS = 100_000
MAX_CLIPBOARD_BYTES = MAX_CLIPBOARD_CHARS * 4


def write_text(
    value: str,
    *,
    run: Callable[..., subprocess.CompletedProcess[str]] = subprocess.run,
) -> None:
    if not isinstance(value, str) or not value or len(value) > MAX_CLIPBOARD_CHARS:
        raise ValueError("clipboard text must contain 1 to 100000 characters")
    if "\x00" in value:
        raise ValueError("clipboard text contains a NUL character")
    child_env = {"PATH": "/usr/local/bin:/usr/bin:/bin"}
    for name in ("LANG", "LC_ALL", "WAYLAND_DISPLAY", "XDG_RUNTIME_DIR"):
        if name in os.environ:
            child_env[name] = os.environ[name]
    completed = run(
        ["wl-copy", "--type", "text/plain;charset=utf-8"],
        input=value,
        text=True,
        capture_output=True,
        timeout=5.0,
        check=False,
        shell=False,
        env=child_env,
    )
    if completed.returncode != 0:
        raise RuntimeError("clipboard write failed")


def read_text(
    *,
    popen: Callable[..., subprocess.Popen[bytes]] = subprocess.Popen,
    timeout: float = 5.0,
) -> str:
    child_env = {"PATH": "/usr/local/bin:/usr/bin:/bin"}
    for name in ("LANG", "LC_ALL", "WAYLAND_DISPLAY", "XDG_RUNTIME_DIR"):
        if name in os.environ:
            child_env[name] = os.environ[name]
    process = popen(
        ["wl-paste", "--type", "text"],
        stdin=subprocess.DEVNULL,
        stdout=subprocess.PIPE,
        stderr=subprocess.DEVNULL,
        shell=False,
        close_fds=True,
        env=child_env,
    )
    if process.stdout is None:
        process.kill()
        process.wait()
        raise RuntimeError("clipboard read failed")
    chunks = bytearray()
    deadline = time.monotonic() + timeout
    selector = selectors.DefaultSelector()
    try:
        os.set_blocking(process.stdout.fileno(), False)
        selector.register(process.stdout, selectors.EVENT_READ)
        while True:
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                raise RuntimeError("clipboard read timed out")
            if not selector.select(remaining):
                raise RuntimeError("clipboard read timed out")
            chunk = os.read(
                process.stdout.fileno(),
                min(65_536, MAX_CLIPBOARD_BYTES + 1 - len(chunks)),
            )
            if not chunk:
                break
            chunks.extend(chunk)
            if len(chunks) > MAX_CLIPBOARD_BYTES:
                raise ValueError("clipboard text exceeds the byte limit")
        process.wait(timeout=max(0.01, deadline - time.monotonic()))
        if process.returncode != 0:
            raise RuntimeError("clipboard read failed")
    finally:
        selector.close()
        if process.poll() is None:
            process.kill()
            process.wait()
        process.stdout.close()
    try:
        value = bytes(chunks).decode("utf-8", errors="strict")
    except UnicodeDecodeError as exc:
        raise ValueError("clipboard text is not valid UTF-8") from exc
    if not value or len(value) > MAX_CLIPBOARD_CHARS or "\x00" in value:
        raise ValueError("clipboard text is empty, oversized or contains NUL")
    return value
