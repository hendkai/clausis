"""Secret-safe installation plans and conservative block-device discovery.

Nothing in this module writes to a block device.  The inventory is deliberately
stricter than Calamares: a device is only offered when it is a writable,
non-removable disk, is large enough and neither it nor a child is mounted.
"""

from __future__ import annotations

from dataclasses import dataclass, field
import json
import os
from pathlib import Path
import re
import secrets
import stat
import subprocess
import time
from typing import Callable, Iterable, Mapping, Optional, Sequence


LOCALES = {"de_DE.UTF-8", "en_GB.UTF-8", "en_US.UTF-8"}
TIMEZONE_RE = re.compile(r"^[A-Za-z_+-]+(?:/[A-Za-z0-9_+.-]+)+$")
USERNAME_RE = re.compile(r"^[a-z_][a-z0-9_-]{0,31}$")
DEVICE_RE = re.compile(r"^/dev/(?:disk/by-id/)?[A-Za-z0-9._:+-]+$")
DEVICE_NODE_RE = re.compile(r"^/dev/[A-Za-z0-9._+-]+$")
RECOVERY_KEY_RE = re.compile(r"^[0-9]{4}(?:-[0-9]{4}){11}$")
PROVIDERS = {"none", "nous", "openai-compatible", "local"}
FILESYSTEMS = {"btrfs", "ext4"}
BOOT_MODES = {"uefi", "bios"}
MINIMUM_DISK_BYTES = 32 * 1024**3
LIVE_MOUNT_PREFIXES = (
    "/run/live/medium",
    "/lib/live/mount/medium",
    "/usr/lib/live/mount/medium",
)
RECOVERY_STAGING_DIRECTORY = Path("/run/clausis-installer")
RECOVERY_STAGING_FILE = RECOVERY_STAGING_DIRECTORY / "recovery.key"


def _clean(value: object) -> str:
    return " ".join(str(value or "").split())


def _mountpoints(value: object) -> tuple[str, ...]:
    if isinstance(value, str):
        values: Iterable[object] = (value,)
    elif isinstance(value, list):
        values = value
    else:
        values = ()
    return tuple(text for item in values if (text := _clean(item)))


def _as_bool(value: object) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, int):
        return value != 0
    if isinstance(value, str):
        normalized = value.casefold().strip()
        if normalized in {"0", "false", "no"}:
            return False
        if normalized in {"1", "true", "yes"}:
            return True
    raise ValueError("lsblk returned an invalid boolean field")


@dataclass(frozen=True)
class InstallDisk:
    path: str
    stable_id: str
    size_bytes: int
    model: str = "Unbekannter Datenträger"
    serial: str = ""
    transport: str = ""
    removable: bool = False
    readonly: bool = False
    mountpoints: tuple[str, ...] = ()
    child_mountpoints: tuple[str, ...] = ()
    device_type: str = "disk"

    @property
    def serial_suffix(self) -> str:
        return self.serial[-6:] if self.serial else "nicht verfügbar"

    @property
    def size_gib(self) -> float:
        return self.size_bytes / 1024**3

    def rejection_reasons(self, *, minimum_bytes: int = MINIMUM_DISK_BYTES) -> tuple[str, ...]:
        reasons: list[str] = []
        if self.device_type != "disk":
            reasons.append("kein physischer Gesamtdatenträger")
        if self.readonly:
            reasons.append("schreibgeschützt")
        if self.removable:
            reasons.append("Wechseldatenträger")
        if self.size_bytes < minimum_bytes:
            reasons.append("kleiner als 32 GiB")
        mounts = self.mountpoints + self.child_mountpoints
        if mounts:
            if any(any(mount.startswith(prefix) for prefix in LIVE_MOUNT_PREFIXES) for mount in mounts):
                reasons.append("enthält das gestartete Live-System")
            else:
                reasons.append("Datenträger oder Partition ist eingehängt")
        if not self.stable_id.startswith("/dev/disk/by-id/"):
            reasons.append("keine stabile Gerätekennung")
        return tuple(reasons)

    @property
    def eligible(self) -> bool:
        return not self.rejection_reasons()

    def spoken_identity(self) -> str:
        return (
            f"{self.model}, {self.size_gib:.1f} GiB, "
            f"Seriennummer endet auf {self.serial_suffix}"
        )


def _stable_ids(by_id_directory: Path = Path("/dev/disk/by-id")) -> dict[str, str]:
    """Map canonical device paths to stable IDs, ignoring partition aliases."""
    result: dict[str, str] = {}
    try:
        entries = sorted(by_id_directory.iterdir(), key=lambda item: item.name)
    except OSError:
        return result
    for entry in entries:
        if "-part" in entry.name:
            continue
        try:
            resolved = str(entry.resolve(strict=True))
        except OSError:
            continue
        result.setdefault(resolved, str(entry))
    return result


def parse_lsblk_inventory(
    payload: Mapping[str, object],
    *,
    stable_ids: Optional[Mapping[str, str]] = None,
) -> tuple[InstallDisk, ...]:
    """Convert an ``lsblk --json`` response into immutable disk identities."""
    devices = payload.get("blockdevices")
    if not isinstance(devices, list):
        raise ValueError("lsblk response has no blockdevices list")
    stable_ids = stable_ids or {}
    disks: list[InstallDisk] = []
    for item in devices:
        if not isinstance(item, Mapping):
            continue
        path = _clean(item.get("path") or item.get("name"))
        children = item.get("children")
        child_mounts: list[str] = []

        def collect_mounts(nodes: object) -> None:
            if not isinstance(nodes, list):
                return
            for node in nodes:
                if not isinstance(node, Mapping):
                    continue
                child_mounts.extend(_mountpoints(node.get("mountpoints") or node.get("mountpoint")))
                collect_mounts(node.get("children"))

        collect_mounts(children)
        try:
            size_bytes = int(item.get("size") or 0)
        except (TypeError, ValueError):
            size_bytes = 0
        disks.append(
            InstallDisk(
                path=path,
                stable_id=stable_ids.get(path, path),
                size_bytes=size_bytes,
                model=_clean(item.get("model")) or "Unbekannter Datenträger",
                serial=_clean(item.get("serial")),
                transport=_clean(item.get("tran")),
                removable=_as_bool(item.get("rm", False)),
                readonly=_as_bool(item.get("ro", False)),
                mountpoints=_mountpoints(item.get("mountpoints") or item.get("mountpoint")),
                child_mountpoints=tuple(child_mounts),
                device_type=_clean(item.get("type")),
            )
        )
    return tuple(disks)


def discover_install_disks(
    *,
    by_id_directory: Path = Path("/dev/disk/by-id"),
    runner: Callable[..., subprocess.CompletedProcess[str]] = subprocess.run,
) -> tuple[InstallDisk, ...]:
    """Run one fixed, read-only ``lsblk`` query and return all discovered disks."""
    command = (
        "lsblk",
        "--json",
        "--bytes",
        "--paths",
        "--output",
        "NAME,PATH,TYPE,SIZE,MODEL,SERIAL,WWN,TRAN,RM,RO,MOUNTPOINTS",
    )
    result = runner(command, check=True, capture_output=True, text=True, timeout=10)
    payload = json.loads(result.stdout)
    if not isinstance(payload, Mapping):
        raise ValueError("lsblk returned an invalid JSON object")
    return parse_lsblk_inventory(payload, stable_ids=_stable_ids(by_id_directory))


def eligible_install_disks(disks: Sequence[InstallDisk]) -> tuple[InstallDisk, ...]:
    return tuple(disk for disk in disks if disk.eligible)


def guard_calamares_erase_transaction(
    disks: Sequence[InstallDisk],
    *,
    device_node: str,
    encrypted: str,
    filesystem: str,
) -> InstallDisk:
    """Bind Calamares' in-memory erase choice to a freshly discovered disk.

    The patched partition view exports these three non-secret values when the
    user leaves that page.  This guard runs in the execution queue immediately
    before Calamares' partition module and must complete before its first write.
    """
    if not DEVICE_NODE_RE.fullmatch(device_node):
        raise ValueError("invalid Calamares target device")
    if encrypted != "true":
        raise ValueError("voice whole-disk installation requires encryption")
    if filesystem != "btrfs":
        raise ValueError("voice whole-disk installation requires btrfs")
    matches = [disk for disk in disks if disk.path == device_node]
    if len(matches) != 1:
        raise ValueError("Calamares target is missing or no longer unique")
    disk = matches[0]
    if not disk.eligible:
        reasons = ", ".join(disk.rejection_reasons())
        raise ValueError(f"Calamares target is not eligible: {reasons}")
    return disk


def calamares_prewrite_summary(disk: InstallDisk) -> str:
    """Canonical warning spoken by the isolated pre-write guard."""
    if not disk.eligible:
        raise ValueError("cannot summarize an ineligible installation target")
    return (
        f"Achtung. Clausis wird jetzt auf {disk.spoken_identity()} installiert. "
        "Der gesamte Datenträger und alle darauf gespeicherten Daten werden "
        "dauerhaft gelöscht. Die Installation verwendet LUKS 2 Verschlüsselung "
        "und das Btrfs Dateisystem."
    )


def generate_recovery_key(
    randbelow: Callable[[int], int] = secrets.randbelow,
) -> str:
    """Return a speech-friendly recovery key with about 159 bits of entropy."""
    groups = [f"{randbelow(10_000):04d}" for _ in range(12)]
    key = "-".join(groups)
    if not RECOVERY_KEY_RE.fullmatch(key):
        raise RuntimeError("recovery-key generator returned an invalid value")
    return key


def discard_staged_recovery_key(path: Path = RECOVERY_STAGING_FILE) -> None:
    """Best-effort overwrite and unlink of the tmpfs staging file."""
    try:
        file_size = path.lstat().st_size
        flags = os.O_WRONLY | getattr(os, "O_NOFOLLOW", 0)
        descriptor = os.open(path, flags)
        try:
            os.write(descriptor, b"0" * file_size)
            os.fsync(descriptor)
        finally:
            os.close(descriptor)
        path.unlink(missing_ok=True)
    except FileNotFoundError:
        return


def stage_recovery_key(
    key: str,
    *,
    directory: Path = RECOVERY_STAGING_DIRECTORY,
    path: Path = RECOVERY_STAGING_FILE,
) -> None:
    """Stage one recovery key in root-only tmpfs for Calamares' LUKS job."""
    if not RECOVERY_KEY_RE.fullmatch(key):
        raise ValueError("invalid recovery-key format")
    directory.mkdir(mode=0o700, parents=True, exist_ok=True)
    directory_metadata = directory.lstat()
    if (
        not stat.S_ISDIR(directory_metadata.st_mode)
        or directory_metadata.st_uid != os.geteuid()
        or stat.S_IMODE(directory_metadata.st_mode) != 0o700
    ):
        raise ValueError("recovery staging directory has unsafe metadata")
    # A previous aborted run may leave a root-only tmpfs key. Only this trusted
    # pre-write process replaces it, immediately before a new confirmation.
    discard_staged_recovery_key(path)
    flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL | getattr(os, "O_NOFOLLOW", 0)
    descriptor = os.open(path, flags, 0o600)
    try:
        encoded = (key + "\n").encode("ascii")
        written = os.write(descriptor, encoded)
        if written != len(encoded):
            raise OSError("short recovery-key write")
        os.fsync(descriptor)
    except Exception:
        os.close(descriptor)
        discard_staged_recovery_key(path)
        raise
    else:
        os.close(descriptor)
        metadata = path.lstat()
        if metadata.st_uid != os.geteuid() or stat.S_IMODE(metadata.st_mode) != 0o600:
            discard_staged_recovery_key(path)
            raise ValueError("recovery staging file has unsafe metadata")


@dataclass(frozen=True)
class InstallerPlan:
    locale: str
    timezone: str
    username: str
    disk_id: str
    erase_disk: bool
    encryption: bool = True
    tpm_enroll: bool = True
    hermes_provider: str = "none"
    cloud_consent: bool = False
    recovery_key_exported: bool = False
    disk_bytes: int = 0
    disk_model: str = ""
    disk_serial_suffix: str = ""
    filesystem: str = "btrfs"
    boot_mode: str = "uefi"
    metadata: Mapping[str, str] = field(default_factory=dict)

    def validate(self) -> None:
        if self.locale not in LOCALES:
            raise ValueError("unsupported locale")
        if not TIMEZONE_RE.fullmatch(self.timezone):
            raise ValueError("invalid timezone")
        if not USERNAME_RE.fullmatch(self.username):
            raise ValueError("invalid username")
        if not DEVICE_RE.fullmatch(self.disk_id):
            raise ValueError("invalid disk identifier")
        if not self.erase_disk:
            raise ValueError("voice-native mode currently supports whole-disk installation only")
        if self.filesystem not in FILESYSTEMS:
            raise ValueError("unsupported filesystem")
        if self.boot_mode not in BOOT_MODES:
            raise ValueError("unsupported boot mode")
        if self.disk_bytes < 0:
            raise ValueError("invalid disk size")
        if self.hermes_provider not in PROVIDERS:
            raise ValueError("unsupported Hermes provider")
        if self.hermes_provider in {"nous", "openai-compatible"} and not self.cloud_consent:
            raise ValueError("cloud provider requires explicit consent")
        if self.encryption and not self.recovery_key_exported:
            raise ValueError("encrypted installation requires an exported recovery key")
        forbidden = {"password", "passphrase", "pin", "api_key", "token", "voiceprint"}
        if any(key.casefold() in forbidden for key in self.metadata):
            raise ValueError("installer plan must not contain secrets or biometric templates")

    def bind_to(self, disks: Sequence[InstallDisk]) -> InstallDisk:
        """Fail closed if a recorded device identity changed before execution."""
        self.validate()
        matches = [disk for disk in disks if disk.stable_id == self.disk_id]
        if len(matches) != 1:
            raise ValueError("selected disk is missing or no longer unique")
        disk = matches[0]
        if not disk.eligible:
            raise ValueError("selected disk is no longer eligible")
        if self.disk_bytes and self.disk_bytes != disk.size_bytes:
            raise ValueError("selected disk size changed")
        if self.disk_serial_suffix and self.disk_serial_suffix != disk.serial_suffix:
            raise ValueError("selected disk serial identity changed")
        return disk

    def spoken_summary(self) -> str:
        self.validate()
        disk = self.disk_model or self.disk_id
        size = f", {self.disk_bytes / 1024**3:.1f} GiB" if self.disk_bytes else ""
        serial = (
            f", Seriennummer endet auf {self.disk_serial_suffix}"
            if self.disk_serial_suffix
            else ""
        )
        cloud = "mit freigegebenem Cloud-Zugang" if self.cloud_consent else "ohne Cloud-Zugang"
        encryption = "mit LUKS 2 verschlüsselt" if self.encryption else "nicht verschlüsselt"
        return (
            f"Achtung. Installation auf {disk}{size}{serial}. "
            "Der gesamte Datenträger und alle darauf gespeicherten Daten werden dauerhaft gelöscht. "
            f"Das System wird {encryption}, mit {self.filesystem} und im Modus {self.boot_mode} eingerichtet. "
            f"Benutzer {self.username}. Sprache {self.locale}. Zeitzone {self.timezone}. Hermes {cloud}."
        )


CONFIRMATION_WORDS = (
    "anker",
    "birke",
    "feder",
    "hafen",
    "insel",
    "laterne",
    "mond",
    "quelle",
    "segel",
    "wolke",
)


class InstallConfirmationChallenge:
    """Single-use, expiring exact-phrase confirmation held only in memory."""

    def __init__(self, *, ttl_seconds: float = 120.0, clock: Callable[[], float] = time.monotonic) -> None:
        if ttl_seconds <= 0:
            raise ValueError("confirmation timeout must be positive")
        self._ttl_seconds = ttl_seconds
        self._clock = clock
        self._phrase: Optional[str] = None
        self._expires_at = 0.0

    def issue(self) -> str:
        first, second = secrets.SystemRandom().sample(CONFIRMATION_WORDS, 2)
        self._phrase = f"{first} {second} {secrets.randbelow(900) + 100}"
        self._expires_at = self._clock() + self._ttl_seconds
        return self._phrase

    def confirm(self, response: str) -> bool:
        expected, self._phrase = self._phrase, None
        expires_at, self._expires_at = self._expires_at, 0.0
        if expected is None or self._clock() > expires_at:
            return False
        normalized = " ".join(re.findall(r"[\wäöüß]+", response.casefold()))
        canonical = " ".join(re.findall(r"[\wäöüß]+", expected.casefold()))
        return secrets.compare_digest(normalized, canonical)
