"""The Btrfs subvolume layout that makes the rollback safe.

Btrfs was already selected as the root filesystem, but no subvolume layout was
declared, which means the installed system would be one flat volume.  That has
a consequence the rollback guard cannot fix on its own: ``snapper undochange``
would revert *everything*, including the tamper-evident audit log and the record
of which Hermes release is installed.

Undoing a bad update must never erase the evidence of what that update did.  So
the layout below is not a convenience — the paths marked ``snapshot=False`` are
deliberately outside the snapshot boundary, and each one carries the reason it
has to survive a rollback.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import PurePosixPath
from typing import Dict, Iterable, List, Sequence, Tuple


@dataclass(frozen=True)
class Subvolume:
    name: str
    mount_point: str
    #: Whether this subvolume is inside the snapshot and rollback boundary.
    snapshot: bool
    reason: str


SUBVOLUMES: Tuple[Subvolume, ...] = (
    Subvolume("@", "/", True, "The system state a rollback is meant to restore."),
    Subvolume(
        "@home", "/home", False,
        "A failed system update must never take the user's documents with it.",
    ),
    Subvolume(
        "@snapshots", "/.snapshots", False,
        "Snapper's own store; inside the snapshot it would nest recursively.",
    ),
    Subvolume(
        "@var-log", "/var/log", False,
        "Logs are the record of what happened, including the tamper-evident "
        "Clausis audit chain in /var/log/clausis. Rolling them back would erase "
        "the evidence of the very update being undone.",
    ),
    Subvolume(
        "@var-lib-clausis", "/var/lib/clausis", False,
        "Records which Hermes release is installed and how it was verified; a "
        "rollback must not silently disagree with what is on disk.",
    ),
    Subvolume(
        "@var-cache", "/var/cache", False,
        "Package caches are large, worthless in a snapshot and churn constantly.",
    ),
    Subvolume(
        "@var-tmp", "/var/tmp", False,
        "Temporary files by definition need no history.",
    ),
    Subvolume(
        "@swap", "/swap", False,
        "A swapfile inside a snapshotted subvolume corrupts on rollback and "
        "cannot use copy-on-write.",
    ),
)

#: Paths whose contents must be readable and unchanged after a rollback.
MUST_SURVIVE_ROLLBACK = ("/var/log/clausis", "/var/lib/clausis", "/home")


def snapshotted() -> Tuple[str, ...]:
    return tuple(item.mount_point for item in SUBVOLUMES if item.snapshot)


def excluded() -> Tuple[str, ...]:
    return tuple(item.mount_point for item in SUBVOLUMES if not item.snapshot)


def calamares_subvolumes() -> List[Dict[str, str]]:
    """Return the layout in the shape Calamares' partition module expects."""

    return [
        {"subvolume": f"/{item.name}", "mountPoint": item.mount_point}
        for item in SUBVOLUMES
    ]


def _covered_by(path: str, boundary: str) -> bool:
    """Return whether ``path`` lies inside ``boundary``."""

    candidate = PurePosixPath(path)
    parent = PurePosixPath(boundary)
    return candidate == parent or parent in candidate.parents


def rollback_safety_report(layout: Sequence[Subvolume] = SUBVOLUMES) -> Dict[str, object]:
    """Check that nothing which must survive a rollback sits in the snapshot."""

    excluded_points = [item.mount_point for item in layout if not item.snapshot]
    unprotected: List[str] = []
    for path in MUST_SURVIVE_ROLLBACK:
        if not any(_covered_by(path, point) for point in excluded_points):
            unprotected.append(path)
    return {
        "safe": not unprotected,
        "unprotected": unprotected,
        "excluded": excluded_points,
    }


def mounted_subvolumes(mounts: str) -> List[str]:
    """Extract the mount points of Btrfs subvolumes from /proc/self/mounts."""

    points: List[str] = []
    for line in mounts.splitlines():
        fields = line.split()
        if len(fields) < 4 or fields[2] != "btrfs":
            continue
        if "subvol=" not in fields[3]:
            continue
        points.append(fields[1].replace("\\040", " "))
    return points


def validate_present(mount_points: Iterable[str]) -> Dict[str, object]:
    """Compare an installed system's mounts against the intended layout.

    ``mount_points`` is whatever the running system actually has mounted, so
    this reports drift on a machine that was installed by an older image or
    partitioned by hand.
    """

    present = set(mount_points)
    missing = [item.mount_point for item in SUBVOLUMES if item.mount_point not in present]
    exposed = [
        path
        for path in MUST_SURVIVE_ROLLBACK
        if not any(_covered_by(path, point) for point in present if point in excluded())
    ]
    return {
        "complete": not missing,
        "missing": missing,
        "rollback_safe": not exposed,
        "exposed": exposed,
    }
