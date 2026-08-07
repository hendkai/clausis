"""Install the latest stable Hermes release into a Calamares target.

The live image always contains a reviewed, pinned fallback.  This updater only
switches the launcher after an exact official release tag has been fetched and
its frozen dependency environment has been created successfully.
"""

from __future__ import annotations

from dataclasses import dataclass
import json
import os
from pathlib import Path
import re
import secrets
import shutil
import subprocess
from typing import Callable, Optional
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


LATEST_RELEASE_API = "https://api.github.com/repos/NousResearch/hermes-agent/releases/latest"
UPSTREAM_GIT = "https://github.com/NousResearch/hermes-agent.git"
RELEASE_TAG_RE = re.compile(
    r"^v(?:[0-9]{4}\.[0-9]{1,2}\.[0-9]{1,2}(?:\.[0-9]+)?|[0-9]+\.[0-9]+\.[0-9]+)$"
)
MAX_RELEASE_RESPONSE = 1024 * 1024
UPDATER_UV = "/opt/clausis-hermes-updater/bin/uv"
RECORD_PATH = Path("var/lib/clausis/hermes-install.json")


class HermesUpdateError(RuntimeError):
    """A safe online update could not be completed."""


@dataclass(frozen=True)
class StableRelease:
    tag: str
    published_at: str


@dataclass(frozen=True)
class UpdateResult:
    release: StableRelease
    commit: str
    changed: bool


def latest_stable_release(
    opener: Optional[Callable[..., object]] = None,
) -> StableRelease:
    opener = opener or urlopen
    request = Request(
        LATEST_RELEASE_API,
        headers={
            "Accept": "application/vnd.github+json",
            "User-Agent": "Clausis-Hermes-Installer/0.2",
            "X-GitHub-Api-Version": "2022-11-28",
        },
    )
    try:
        with opener(request, timeout=15) as response:
            raw = response.read(MAX_RELEASE_RESPONSE + 1)
    except (HTTPError, URLError, OSError, TimeoutError) as exc:
        raise HermesUpdateError("release lookup unavailable") from exc
    if len(raw) > MAX_RELEASE_RESPONSE:
        raise HermesUpdateError("release response is too large")
    try:
        payload = json.loads(raw.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise HermesUpdateError("release response is invalid") from exc
    if not isinstance(payload, dict):
        raise HermesUpdateError("release response is not an object")
    tag = payload.get("tag_name")
    published_at = payload.get("published_at")
    if payload.get("draft") is not False or payload.get("prerelease") is not False:
        raise HermesUpdateError("latest release is not stable")
    if not isinstance(tag, str) or not RELEASE_TAG_RE.fullmatch(tag):
        raise HermesUpdateError("latest release tag is not accepted")
    if not isinstance(published_at, str) or len(published_at) > 64:
        raise HermesUpdateError("latest release date is invalid")
    return StableRelease(tag=tag, published_at=published_at)


def _checked_root(root: Path) -> Path:
    resolved = root.resolve()
    if not resolved.is_absolute() or not (resolved / "etc/os-release").is_file():
        raise HermesUpdateError("target root is invalid")
    opt = (resolved / "opt").resolve()
    if opt != resolved / "opt" or resolved not in opt.parents:
        raise HermesUpdateError("target opt directory is unsafe")
    return resolved


def _run(command: list[str], *, timeout: int = 120) -> str:
    try:
        completed = subprocess.run(
            command,
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            timeout=timeout,
        )
    except (OSError, subprocess.SubprocessError) as exc:
        raise HermesUpdateError("release installation command failed") from exc
    return completed.stdout.strip()


def _atomic_launcher(root: Path, executable: str) -> None:
    launcher_dir = root / "usr/local/bin"
    launcher_dir.mkdir(mode=0o755, parents=True, exist_ok=True)
    temporary = launcher_dir / f".hermes.clausis-{secrets.token_hex(8)}"
    temporary.symlink_to(executable)
    try:
        os.replace(temporary, launcher_dir / "hermes")
    finally:
        temporary.unlink(missing_ok=True)


def write_install_record(root: Path, payload: dict) -> None:
    path = root / RECORD_PATH
    path.parent.mkdir(mode=0o755, parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.{secrets.token_hex(8)}")
    temporary.write_text(json.dumps(payload, sort_keys=True, indent=2) + "\n", encoding="utf-8")
    temporary.chmod(0o644)
    os.replace(temporary, path)


def record_fallback(root: Path, reason: str) -> None:
    write_install_record(
        root,
        {
            "status": "bundled-fallback",
            "reason": reason,
            "source": "Clausis installation image",
        },
    )


def install_latest_stable(root: Path) -> UpdateResult:
    root = _checked_root(root)
    release = latest_stable_release()
    relative_release = f"/opt/hermes-agent-releases/{release.tag}"
    destination = root / relative_release.lstrip("/")
    executable = f"{relative_release}/venv/bin/hermes"

    if (destination / "venv/bin/hermes").is_file() and (destination / ".git").is_dir():
        commit = _run(["git", "-C", str(destination), "rev-parse", "HEAD^{commit}"])
        if not re.fullmatch(r"[0-9a-f]{40}", commit):
            raise HermesUpdateError("installed release commit is invalid")
        _atomic_launcher(root, executable)
        result = UpdateResult(release, commit, False)
        _record_success(root, result)
        return result

    releases = root / "opt/hermes-agent-releases"
    releases.mkdir(mode=0o755, parents=True, exist_ok=True)
    staging = releases / f".{release.tag}.{secrets.token_hex(8)}"
    staging.mkdir(mode=0o755)
    installed_destination = False
    try:
        _run(["git", "-C", str(staging), "init"])
        _run(["git", "-C", str(staging), "remote", "add", "origin", UPSTREAM_GIT])
        _run(
            [
                "git",
                "-C",
                str(staging),
                "fetch",
                "--depth",
                "1",
                "origin",
                f"refs/tags/{release.tag}",
            ],
            timeout=300,
        )
        _run(["git", "-C", str(staging), "checkout", "--detach", "FETCH_HEAD"])
        commit = _run(["git", "-C", str(staging), "rev-parse", "HEAD^{commit}"])
        if not re.fullmatch(r"[0-9a-f]{40}", commit):
            raise HermesUpdateError("fetched release commit is invalid")
        if not (staging / "uv.lock").is_file() or not (staging / "LICENSE").is_file():
            raise HermesUpdateError("release lacks lockfile or license")
        os.replace(staging, destination)
        installed_destination = True
        _run(
            [
                "chroot",
                str(root),
                "/usr/bin/env",
                "-i",
                "PATH=/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin",
                "HOME=/root",
                "UV_NO_CONFIG=1",
                f"UV_PROJECT_ENVIRONMENT={relative_release}/venv",
                UPDATER_UV,
                "sync",
                "--frozen",
                "--no-dev",
                "--extra",
                "cli",
                "--extra",
                "voice",
                "--extra",
                "anthropic",
                "--python",
                "/usr/bin/python3",
                "--project",
                relative_release,
            ],
            timeout=1500,
        )
        target_executable = root / executable.lstrip("/")
        if not target_executable.is_file() or not os.access(target_executable, os.X_OK):
            raise HermesUpdateError("updated Hermes executable is missing")
        _atomic_launcher(root, executable)
        result = UpdateResult(release, commit, True)
        _record_success(root, result)
        return result
    except Exception as exc:
        if installed_destination:
            shutil.rmtree(destination, ignore_errors=True)
        if isinstance(exc, HermesUpdateError):
            raise
        raise HermesUpdateError("release installation failed safely") from exc
    finally:
        shutil.rmtree(staging, ignore_errors=True)


def _record_success(root: Path, result: UpdateResult) -> None:
    write_install_record(
        root,
        {
            "status": "updated" if result.changed else "already-current",
            "release": result.release.tag,
            "commit": result.commit,
            "published_at": result.release.published_at,
            "source": UPSTREAM_GIT,
        },
    )
