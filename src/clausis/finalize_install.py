"""Copy staged Hermes settings into a Calamares target without logging secrets."""

from __future__ import annotations

import argparse
import os
from pathlib import Path
import re
import secrets
import stat
from typing import Sequence

from .enrollment import STAGED_PIN, install_staged_voice_pin
from .hermes_update import HermesUpdateError, install_latest_stable, record_fallback


USERNAME_RE = re.compile(r"^[a-z_][a-z0-9_-]{0,31}$")
DEFAULT_SOURCE = Path("/home/clausis/.config/clausis-installer/target-home/.hermes")
MAX_CONFIGURATION_BYTES = 1024 * 1024


def target_account(root: Path, username: str) -> tuple[Path, int, int]:
    if not root.is_absolute() or root == Path("/") or not (root / "etc/passwd").is_file():
        raise ValueError("invalid Calamares target root")
    if not USERNAME_RE.fullmatch(username):
        raise ValueError("invalid target username")
    for line in (root / "etc/passwd").read_text(encoding="utf-8").splitlines():
        fields = line.split(":")
        if len(fields) >= 7 and fields[0] == username:
            uid, gid = int(fields[2]), int(fields[3])
            relative_home = Path(fields[5].lstrip("/"))
            home = (root / relative_home).resolve()
            if root.resolve() not in home.parents:
                raise ValueError("target home escapes target root")
            return home, uid, gid
    raise ValueError("target user was not created")


def copy_configuration(root: Path, username: str, source: Path = DEFAULT_SOURCE) -> bool:
    try:
        config_stat = (source / "config.yaml").lstat()
    except FileNotFoundError:
        return False
    if not stat.S_ISREG(config_stat.st_mode):
        raise ValueError("staged Hermes configuration is not a regular file")
    home, uid, gid = target_account(root.resolve(), username)
    destination = home / ".hermes"
    try:
        destination.mkdir(mode=0o700)
    except FileExistsError:
        pass
    directory_flags = os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW
    try:
        directory_fd = os.open(destination, directory_flags)
    except OSError as exc:
        raise ValueError("target Hermes directory is unsafe") from exc
    try:
        os.fchmod(directory_fd, 0o700)
        os.fchown(directory_fd, uid, gid)
        for name in ("config.yaml", ".env", ".gpt-live.env"):
            source_file = source / name
            try:
                source_stat = source_file.lstat()
            except FileNotFoundError:
                if name == "config.yaml":
                    raise ValueError("staged Hermes configuration disappeared")
                continue
            if not stat.S_ISREG(source_stat.st_mode):
                raise ValueError("staged Hermes configuration contains a non-regular file")
            _atomic_copy_private(source_file, directory_fd, name, uid, gid)
    finally:
        os.close(directory_fd)
    return True


def _atomic_copy_private(
    source: Path, directory_fd: int, name: str, uid: int, gid: int
) -> None:
    """Copy one bounded regular file without following source or target links."""
    try:
        source_fd = os.open(source, os.O_RDONLY | os.O_NOFOLLOW)
    except OSError as exc:
        raise ValueError("staged Hermes configuration is unsafe") from exc
    temporary = f".{name}.clausis-{secrets.token_hex(8)}"
    target_fd: int | None = None
    try:
        source_stat = os.fstat(source_fd)
        if not stat.S_ISREG(source_stat.st_mode):
            raise ValueError("staged Hermes configuration is not a regular file")
        if source_stat.st_size > MAX_CONFIGURATION_BYTES:
            raise ValueError("staged Hermes configuration is too large")
        target_fd = os.open(
            temporary,
            os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW,
            0o600,
            dir_fd=directory_fd,
        )
        remaining = MAX_CONFIGURATION_BYTES + 1
        while remaining:
            chunk = os.read(source_fd, min(65536, remaining))
            if not chunk:
                break
            remaining -= len(chunk)
            if remaining == 0:
                raise ValueError("staged Hermes configuration is too large")
            view = memoryview(chunk)
            while view:
                written = os.write(target_fd, view)
                view = view[written:]
        os.fchmod(target_fd, 0o600)
        os.fchown(target_fd, uid, gid)
        os.fsync(target_fd)
        os.close(target_fd)
        target_fd = None
        os.replace(
            temporary,
            name,
            src_dir_fd=directory_fd,
            dst_dir_fd=directory_fd,
        )
    finally:
        os.close(source_fd)
        if target_fd is not None:
            os.close(target_fd)
        try:
            os.unlink(temporary, dir_fd=directory_fd)
        except FileNotFoundError:
            pass


def main(argv: Sequence[str] = ()) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument("--user", required=True)
    args = parser.parse_args(list(argv) or None)
    copied = copy_configuration(args.root, args.user)
    print("Hermes configuration installed." if copied else "No staged Hermes configuration.")
    pin_source = DEFAULT_SOURCE.parents[3] / STAGED_PIN
    pin_installed = install_staged_voice_pin(args.root, pin_source)
    print(
        "Trusted voice PIN installed."
        if pin_installed
        else "No trusted voice PIN was staged."
    )
    try:
        result = install_latest_stable(args.root)
    except HermesUpdateError:
        record_fallback(args.root.resolve(), "online-update-unavailable")
        print("Latest Hermes release unavailable; bundled reviewed version retained.")
    else:
        print(f"Hermes {result.release.tag} installed from official stable release.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
