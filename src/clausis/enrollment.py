"""Secret-safe enrollment and installation of the trusted voice PIN."""

from __future__ import annotations

import json
import os
from pathlib import Path
import secrets
import stat
from typing import Mapping

from .confirmation import PinVerifier


STAGED_PIN = Path(".config/clausis-installer/system/voice-pin.json")
MAX_PIN_FILE_BYTES = 4096


def _validated_payload(data: Mapping[str, object]) -> dict:
    PinVerifier.from_export(data)
    allowed = {"algorithm", "iterations", "salt", "digest"}
    return {name: str(data[name]) for name in sorted(allowed)}


def _atomic_private_json(path: Path, payload: Mapping[str, object]) -> None:
    path.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
    path.parent.chmod(0o700)
    temporary = path.parent / f".{path.name}.clausis-{secrets.token_hex(8)}"
    descriptor = None
    try:
        descriptor = os.open(
            temporary,
            os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW,
            0o600,
        )
        encoded = (json.dumps(dict(payload), sort_keys=True) + "\n").encode("utf-8")
        if len(encoded) > MAX_PIN_FILE_BYTES:
            raise ValueError("voice PIN verifier is too large")
        view = memoryview(encoded)
        while view:
            view = view[os.write(descriptor, view):]
        os.fchmod(descriptor, 0o600)
        os.fsync(descriptor)
        os.close(descriptor)
        descriptor = None
        os.replace(temporary, path)
    finally:
        if descriptor is not None:
            os.close(descriptor)
        temporary.unlink(missing_ok=True)


def stage_voice_pin(live_home: Path, pin: str) -> Path:
    verifier = PinVerifier.enroll(pin)
    destination = live_home / STAGED_PIN
    _atomic_private_json(destination, verifier.export())
    return destination


def install_staged_voice_pin(root: Path, source: Path) -> bool:
    root = root.resolve()
    if root == Path("/") or not (root / "etc/passwd").is_file():
        raise ValueError("invalid Calamares target root")
    try:
        source_stat = source.lstat()
    except FileNotFoundError:
        return False
    if not stat.S_ISREG(source_stat.st_mode) or source_stat.st_size > MAX_PIN_FILE_BYTES:
        raise ValueError("staged voice PIN verifier is unsafe")
    descriptor = os.open(source, os.O_RDONLY | os.O_NOFOLLOW)
    try:
        opened_stat = os.fstat(descriptor)
        if not stat.S_ISREG(opened_stat.st_mode):
            raise ValueError("staged voice PIN verifier is unsafe")
        chunks = []
        remaining = MAX_PIN_FILE_BYTES + 1
        while remaining:
            chunk = os.read(descriptor, min(remaining, 1024))
            if not chunk:
                break
            chunks.append(chunk)
            remaining -= len(chunk)
        raw = b"".join(chunks)
    finally:
        os.close(descriptor)
    if len(raw) > MAX_PIN_FILE_BYTES:
        raise ValueError("staged voice PIN verifier is too large")
    try:
        payload = _validated_payload(json.loads(raw.decode("utf-8")))
    except (UnicodeDecodeError, json.JSONDecodeError, TypeError) as exc:
        raise ValueError("staged voice PIN verifier is malformed") from exc
    destination = root / "etc/clausis/voice-pin.json"
    _atomic_private_json(destination, payload)
    os.chown(destination, 0, 0)
    return True
