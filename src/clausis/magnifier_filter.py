"""Set all GNOME magnifier brightness or contrast channels safely."""

from __future__ import annotations

from decimal import Decimal, InvalidOperation
import re
import subprocess
import sys
from typing import Callable, Sequence


SCHEMA = "org.gnome.desktop.a11y.magnifier"
KINDS = {"brightness", "contrast"}
CANONICAL_VALUE = re.compile(r"^-?0\.\d{2}$")


def _validate(kind: str, value_text: str) -> Decimal:
    if kind not in KINDS:
        raise ValueError("unsupported magnifier filter")
    if not CANONICAL_VALUE.fullmatch(value_text):
        raise ValueError("filter value must be a canonical two-decimal fraction")
    try:
        value = Decimal(value_text)
    except InvalidOperation as exc:
        raise ValueError("invalid filter value") from exc
    if not Decimal("-0.75") <= value <= Decimal("0.75"):
        raise ValueError("filter value must be between -0.75 and 0.75")
    return value


def set_filter(
    kind: str,
    value_text: str,
    *,
    runner: Callable[..., subprocess.CompletedProcess[str]] = subprocess.run,
) -> None:
    _validate(kind, value_text)
    keys = [f"{kind}-{channel}" for channel in ("red", "green", "blue")]
    previous = []
    for key in keys:
        result = runner(
            ["gsettings", "get", SCHEMA, key],
            check=True,
            capture_output=True,
            text=True,
        )
        previous.append(result.stdout.strip())

    changed = 0
    try:
        for key in keys:
            runner(
                ["gsettings", "set", SCHEMA, key, value_text],
                check=True,
                capture_output=True,
                text=True,
            )
            changed += 1
    except subprocess.CalledProcessError:
        for key, old_value in zip(keys[:changed], previous[:changed]):
            runner(
                ["gsettings", "set", SCHEMA, key, old_value],
                check=False,
                capture_output=True,
                text=True,
            )
        raise


def main(argv: Sequence[str] | None = None) -> int:
    arguments = list(sys.argv[1:] if argv is None else argv)
    if len(arguments) != 2:
        return 2
    try:
        set_filter(arguments[0], arguments[1])
    except (ValueError, subprocess.CalledProcessError):
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
