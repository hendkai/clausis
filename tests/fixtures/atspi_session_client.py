"""Drive the real Clausis text-editing adapter against the live GTK probe app.

Every mutation goes through :class:`clausis.gnome_adapter.PyAtSpiDesktop`,
exactly as the runtime would use it.  Each step is recorded as

- ``OK``      the adapter succeeded and the checked postcondition held,
- ``REFUSED`` the adapter honestly refused (``GnomeAdapterError``), which is
              an acceptable outcome when GTK does not expose the capability,
- ``ERROR``   an unexpected exception or a violated postcondition — a bug.

The result file is rewritten after every step so a crash still leaves
evidence.  Caret expectations are derived from the adapter's own spoken
position reports (``Position X von Y``), so a refused earlier step never
invalidates the expectation of a later one.
"""

import re
import sys
import time
import traceback
from typing import Any, Callable, Optional, Tuple

from clausis.gnome_adapter import GnomeAdapterError, PyAtSpiDesktop
from clausis.text_units import granular_chunk, word_bounds

WINDOW_TITLE = "ClausisSessionProbe"
INITIAL_TEXT = "hallo welt hier"
INSERTION = " jetzt"
POSITION_REPORT = re.compile(r"Position (\d+) von (\d+)")

lines = []


def flush_results() -> None:
    if len(sys.argv) > 1:
        with open(sys.argv[1], "w", encoding="utf-8") as handle:
            handle.write("\n".join(lines) + "\n")


def record(status: str, step: str, detail: str = "") -> None:
    line = f"{status} {step}" + (f" :: {detail}" if detail else "")
    lines.append(line)
    print(line, flush=True)
    flush_results()


def require(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def run(step: str, function: Callable[[], Any], checker: Optional[Callable[[Any], None]] = None):
    """Run one adapter call; returns ``(ok, value)``."""

    try:
        value = function()
    except GnomeAdapterError as exc:
        record("REFUSED", step, str(exc))
        return False, None
    except Exception:
        record("ERROR", step, traceback.format_exc(limit=3).replace("\n", " | "))
        return False, None
    if checker is not None:
        try:
            checker(value)
        except AssertionError as exc:
            record("ERROR", step, f"postcondition failed: {exc}")
            return False, value
    record("OK", step, "" if value is None else str(value))
    return True, value


def parse_position(value: Any) -> Optional[Tuple[int, int]]:
    """Return ``(offset, total)`` from an adapter caret report, else ``None``."""

    if not isinstance(value, str):
        return None
    match = POSITION_REPORT.search(value)
    return (int(match.group(1)), int(match.group(2))) if match else None


def previous_word_offset(content: str, caret: int) -> int:
    """Same arithmetic as the adapter's ``_previous_word_offset``."""

    pos = min(caret, len(content))
    while pos > 0 and content[pos - 1].isspace():
        pos -= 1
    while pos > 0 and not content[pos - 1].isspace():
        pos -= 1
    return pos


def text_of(value: Any, fallback: str) -> str:
    return value if isinstance(value, str) else fallback


def find_password_node() -> Any:
    """Return the first ``password text`` node on the bus, or ``None``.

    A GTK entry publishes an ``activate`` action (the Enter signal), not a
    focus grab, so the client moves focus itself through the same AT-SPI
    component interface the adapter uses internally — the refusal under test
    is then purely the adapter's own password check.
    """

    try:
        import pyatspi
    except ImportError:
        return None
    try:
        root = pyatspi.Registry.getDesktop(0)
    except Exception:
        return None
    stack = [root]
    while stack:
        node = stack.pop(0)
        try:
            if node.getRoleName().casefold() == "password text":
                return node
            count = node.childCount
        except Exception:
            continue
        for index in range(count):
            try:
                stack.append(node.getChildAtIndex(index))
            except Exception:
                continue
    return None


def main() -> int:
    try:
        desktop = PyAtSpiDesktop()
    except GnomeAdapterError as exc:
        record("ERROR", "adapter-init", str(exc))
        return 2

    # The GTK probe app may still be mapping its window; retry orientation
    # instead of failing the whole session on a slow start.
    def check_context(ctx: Any) -> None:
        require(ctx.window == WINDOW_TITLE, f"window={ctx.window!r}")

    context_ok = False
    for _ in range(20):
        context_ok, _ = run("context", desktop.context, check_context)
        if context_ok:
            break
        time.sleep(1)
    if not context_ok:
        record("ERROR", "session", "probe window never appeared on the bus")
        return 2

    field_ok, field_value = run(
        "read_field",
        desktop.read_text_field,
        lambda value: require(value == INITIAL_TEXT, f"field={value!r}"),
    )
    current = text_of(field_value, "")
    if not field_ok or not current:
        _, raw = run("read_field-raw", desktop.read_text_field)
        current = text_of(raw, INITIAL_TEXT) or INITIAL_TEXT

    caret = 0
    total = len(current)

    # --- caret navigation --------------------------------------------------
    end_ok, end_spoken = run("caret-end", lambda: desktop.move_caret("end"))
    end_position = parse_position(end_spoken)
    if end_ok and end_position:
        run(
            "caret-end-check",
            lambda: None,
            lambda _: require(end_position == (total, total), f"position={end_position}"),
        )
        caret = end_position[0]

    word_back_target = previous_word_offset(current, caret)
    word_ok, word_spoken = run("caret-word-back", lambda: desktop.move_caret("word_previous"))
    word_position = parse_position(word_spoken)
    if word_ok and word_position:
        run(
            "caret-word-back-check",
            lambda: None,
            lambda _: require(
                word_position == (word_back_target, total), f"position={word_position}"
            ),
        )
        caret = word_position[0]

    start_ok, start_spoken = run("caret-start", lambda: desktop.move_caret("start"))
    start_position = parse_position(start_spoken)
    if start_ok and start_position:
        run(
            "caret-start-check",
            lambda: None,
            lambda _: require(start_position == (0, total), f"position={start_position}"),
        )
        caret = start_position[0]

    # --- selection and replacement ------------------------------------------
    start, end = word_bounds(current, caret)
    expected_word = current[start:end]
    select_ok, _ = run(
        "select-word",
        desktop.select_word,
        lambda word: require(
            bool(word) and word == expected_word,
            f"selected={word!r}, expected {expected_word!r}",
        ),
    )

    replace_ok, replaced = run(
        "replace-selection",
        lambda: desktop.replace_selection("guten"),
        lambda value: require("guten" in value, f"content={value!r}"),
    )
    if replace_ok:
        current = text_of(replaced, current)
    else:
        _, raw = run("read-after-refused-replace", desktop.read_text_field)
        current = text_of(raw, current) or current

    # --- undo / redo ----------------------------------------------------------
    undo_ok, _ = run("edit-undo", desktop.edit_undo)
    _, after_undo = run("read-after-undo", desktop.read_text_field)
    after_undo = text_of(after_undo, "")
    if after_undo:
        if undo_ok and replace_ok:
            run(
                "undo-check",
                lambda: None,
                lambda _: require(
                    after_undo == INITIAL_TEXT, f"after undo={after_undo!r}"
                ),
            )
        current = after_undo

    redo_ok, _ = run("edit-redo", desktop.edit_redo)
    _, after_redo = run("read-after-redo", desktop.read_text_field)
    after_redo = text_of(after_redo, "")
    if after_redo:
        if redo_ok and undo_ok and replace_ok:
            run(
                "redo-check",
                lambda: None,
                lambda _: require("guten" in after_redo, f"after redo={after_redo!r}"),
            )
        current = after_redo

    # --- insertion and granular reading ----------------------------------------
    insert_end_ok, insert_end_spoken = run(
        "caret-end-for-insert", lambda: desktop.move_caret("end")
    )
    insert_position = parse_position(insert_end_spoken)
    at_known_end = insert_end_ok and insert_position is not None
    if at_known_end and insert_position is not None:
        caret = insert_position[0]

    insert_ok, inserted = run(
        "insert",
        lambda: desktop.insert_text(INSERTION),
        lambda value: require(
            value == current + INSERTION if at_known_end else bool(value),
            f"content={value!r}",
        ),
    )
    if insert_ok:
        current = text_of(inserted, current)

    expected_line, _next = granular_chunk(current, "line", 0)
    run(
        "read-granular-line",
        lambda: desktop.read_granular("line"),
        lambda value: require(value == expected_line, f"line={value!r}"),
    )

    # --- password-field protection on the real bus ---------------------------
    # A smoke test that only drives the happy path would be dishonest: the
    # refusals are the security property.  The probe app shows a second entry
    # with visibility off, which GTK exposes with the "password text" role.
    try:
        password_node = find_password_node()
        if password_node is None:
            record(
                "REFUSED",
                "password-field",
                "probe exposes no password field on the bus",
            )
        else:
            try:
                grabbed = password_node.queryComponent().grabFocus()
            except Exception:
                grabbed = False
            focused_role = desktop.context().focused_role.casefold()
            if not grabbed or focused_role != "password text":
                record(
                    "REFUSED",
                    "password-field",
                    f"could not focus the password field (grabbed={grabbed}, "
                    f"focused_role={focused_role!r})",
                )
            else:
                try:
                    desktop.insert_text("geheim123")
                    record(
                        "ERROR",
                        "password-field",
                        "dictation into a password field was NOT refused",
                    )
                except GnomeAdapterError as exc:
                    if "Passwortfeld" in str(exc):
                        record("OK", "password-field", str(exc))
                    else:
                        record(
                            "ERROR",
                            "password-field",
                            f"refused for the wrong reason: {exc}",
                        )
    except Exception:
        record(
            "ERROR",
            "password-field",
            traceback.format_exc(limit=3).replace("\n", " | "),
        )

    errors = sum(1 for line in lines if line.startswith("ERROR"))
    refusals = sum(1 for line in lines if line.startswith("REFUSED"))
    oks = sum(1 for line in lines if line.startswith("OK"))
    record("SUMMARY", "session", f"{oks} OK, {refusals} REFUSED, {errors} ERROR")
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())
