#!/usr/bin/env python3
"""Fail closed when required release evidence is absent or still placeholder."""

from __future__ import annotations

import json
from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[1]
REQUIRED = (
    "LICENSE",
    "THIRD_PARTY_NOTICES.md",
    "SECURITY.md",
    "NOTICE",
    "sbom.cdx.json",
    "docs/security/THREAT_MODEL.md",
    "docs/compliance/AI_CONTRIBUTION.md",
    "docs/compliance/CRA_SCOPE.md",
    "docs/compliance/DPIA_DRAFT.md",
    "docs/release/RELEASE_GATE.md",
    ".well-known/security.txt",
    "packaging/trust/hermes-maintainers.asc",
)


def main() -> int:
    errors = []
    for relative in REQUIRED:
        path = ROOT / relative
        if not path.is_file() or path.stat().st_size == 0:
            errors.append(f"missing release evidence: {relative}")

    try:
        sbom = json.loads((ROOT / "sbom.cdx.json").read_text(encoding="utf-8"))
        if sbom.get("bomFormat") != "CycloneDX" or not sbom.get("components"):
            errors.append("SBOM is not a non-empty CycloneDX document")
    except (OSError, json.JSONDecodeError):
        errors.append("SBOM cannot be parsed")

    security = (ROOT / ".well-known/security.txt").read_text(encoding="utf-8")
    if "example.invalid" in security or "PLACEHOLDER" in security:
        errors.append("security.txt still contains release-blocking placeholders")

    sys.path.insert(0, str(ROOT / "src"))
    try:
        from clausis.signing import trust_store_is_configured

        if not trust_store_is_configured(ROOT / "packaging/trust/hermes-maintainers.asc"):
            errors.append(
                "no Hermes maintainer trust anchor is configured; online releases "
                "cannot be verified"
            )
    except ImportError:
        errors.append("the signing module is missing")

    gate = (ROOT / "docs/release/RELEASE_GATE.md").read_text(encoding="utf-8")
    if "blocked for end-user release" in gate:
        errors.append("release gate explicitly blocks end-user release")

    if errors:
        for error in errors:
            print(f"BLOCKED: {error}")
        return 1
    print("release evidence gate passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

