"""Signature verification for the online Hermes release.

Until now the updater trusted whatever the official GitHub repository served
under an accepted stable tag: a compromised account or repository could publish
a malicious release and Clausis would install it.  This module adds the missing
trust anchor — a pinned set of maintainer public keys shipped with Clausis —
and verifies the fetched tag or commit against it.

Everything here fails closed.  An unconfigured trust store, a missing
signature, an unsigned lightweight tag or a signature from an unknown key all
end the update, which leaves the reviewed version bundled in the image active.
The keys themselves are not something Clausis can invent: they must be obtained
and checked out of band, and the release gate stays blocked until they are.
"""

from __future__ import annotations

from dataclasses import dataclass
import os
from pathlib import Path
import re
import subprocess
import tempfile
from typing import Callable, List, Optional, Sequence


TRUST_STORE = Path("/usr/share/clausis/trust/hermes-maintainers.asc")
PUBLIC_KEY_HEADER = "-----BEGIN PGP PUBLIC KEY BLOCK-----"
PLACEHOLDER_MARKER = "CLAUSIS-PLACEHOLDER-NO-TRUST-ANCHOR"
FINGERPRINT_RE = re.compile(r"\b([0-9A-F]{40})\b")

CommandRunner = Callable[[Sequence[str], Optional[dict]], "subprocess.CompletedProcess[str]"]


class SignatureError(RuntimeError):
    """The release could not be proven to come from a trusted maintainer."""


@dataclass(frozen=True)
class Verification:
    reference: str
    kind: str
    fingerprint: str


def _run(command: Sequence[str], env: Optional[dict] = None) -> "subprocess.CompletedProcess[str]":
    child = {"PATH": "/usr/local/bin:/usr/bin:/bin", "LC_ALL": "C"}
    child.update(env or {})
    return subprocess.run(
        list(command),
        shell=False,
        check=False,
        capture_output=True,
        text=True,
        timeout=120.0,
        env=child,
    )


def trust_store_is_configured(path: Path = TRUST_STORE) -> bool:
    """Return whether a real trust anchor, not the placeholder, is installed."""

    try:
        content = path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return False
    if PLACEHOLDER_MARKER in content:
        return False
    return PUBLIC_KEY_HEADER in content


def _import_keys(home: Path, trust_store: Path, runner: CommandRunner) -> List[str]:
    completed = runner(
        ["gpg", "--batch", "--no-tty", "--import", str(trust_store)],
        {"GNUPGHOME": str(home)},
    )
    if completed.returncode != 0:
        raise SignatureError("the maintainer keys could not be imported")
    listed = runner(
        ["gpg", "--batch", "--no-tty", "--with-colons", "--fingerprint"],
        {"GNUPGHOME": str(home)},
    )
    fingerprints = [
        line.split(":")[9]
        for line in (listed.stdout or "").splitlines()
        if line.startswith("fpr:") and len(line.split(":")) > 9
    ]
    if not fingerprints:
        raise SignatureError("the trust store contains no usable key")
    return fingerprints


def _verify(
    repository: Path,
    reference: str,
    kind: str,
    home: Path,
    runner: CommandRunner,
) -> Optional[str]:
    subcommand = "verify-tag" if kind == "tag" else "verify-commit"
    completed = runner(
        [
            "git", "-C", str(repository),
            "-c", "gpg.program=gpg",
            subcommand, "--raw", reference,
        ],
        {"GNUPGHOME": str(home)},
    )
    if completed.returncode != 0:
        return None
    output = f"{completed.stdout or ''}\n{completed.stderr or ''}"
    if "GOODSIG" not in output and "VALIDSIG" not in output:
        return None
    match = FINGERPRINT_RE.search(output)
    return match.group(1) if match else None


def verify_release(
    repository: Path,
    tag: str,
    *,
    trust_store: Path = TRUST_STORE,
    runner: CommandRunner = _run,
) -> Verification:
    """Verify the tag, or the commit it points at, against the pinned keys.

    An annotated signed tag is preferred.  Projects that publish lightweight
    tags over signed commits are still verifiable, but an object with no
    signature at all is rejected — there is no "unsigned is fine" path.
    """

    if not trust_store_is_configured(trust_store):
        raise SignatureError(
            "no Hermes maintainer trust anchor is configured; the bundled "
            "release stays active"
        )
    with tempfile.TemporaryDirectory(prefix="clausis-trust-") as directory:
        home = Path(directory)
        os.chmod(home, 0o700)
        trusted = set(_import_keys(home, trust_store, runner))
        for kind, reference in (("tag", tag), ("commit", f"{tag}^{{commit}}")):
            fingerprint = _verify(repository, reference, kind, home, runner)
            if fingerprint is None:
                continue
            if fingerprint not in trusted:
                raise SignatureError(
                    "the release is signed by a key that Clausis does not trust"
                )
            return Verification(reference=reference, kind=kind, fingerprint=fingerprint)
    raise SignatureError("the release carries no verifiable maintainer signature")
