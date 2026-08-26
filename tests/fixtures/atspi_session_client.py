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
import threading
import time
import traceback
from typing import Any, Callable, List, Optional, Tuple

from clausis.gnome_adapter import GnomeAdapterError, PyAtSpiDesktop
from clausis.text_units import granular_chunk, sentence_bounds, word_bounds

WINDOW_TITLE = "ClausisSessionProbe"
INITIAL_TEXT = "hallo welt hier"
INSERTION = " jetzt"
POSITION_REPORT = re.compile(r"Position (\d+) von (\d+)")

#: Multi-line TextView content of the probe app (must match
#: ``atspi_session_probe_app.MULTILINE_TEXT``; the equality is asserted in
#: the session itself so a drift fails loudly instead of silently).
MULTILINE_TEXT = (
    "Erste Zeile des Dokuments.\n"
    "Zweite Zeile folgt.\n"
    "\n"
    "Neuer Absatz beginnt hier.\n"
    "Noch eine Zeile mit Inhalt.\n"
    "\n"
    "Letzter Absatz."
)
MULTILINE_NAME = "MehrzeiligesFeld"

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


class StubUtterance:
    """Waitable like ``SystemSpeaker``'s async handle.

    Completing pops the pending chunk into ``spoken``; a chunk cancelled
    while blocked never reaches ``spoken`` — exactly the distinction the
    bookmark is built on.
    """

    def __init__(self, speaker: "StubSpeaker") -> None:
        self._speaker = speaker

    def wait(self, timeout: Optional[float] = None) -> None:
        del timeout  # instant by design: the session has no audio pipeline
        if self._speaker.pending:
            self._speaker.spoken.append(self._speaker.pending.pop())


class StubSpeaker:
    """Stand-in for ``SystemSpeaker`` where the session has no audio stack.

    The say-all loop needs a cancelable, waitable speech handle; CI has no
    speech-dispatcher, so the stub completes each chunk instantly and records
    it.  ``block_after`` simulates playback the user interrupts: every chunk
    beyond that one-based count blocks on an internal gate until
    :meth:`cancel` (the ``spd-say -C`` of the session) opens it — a one-shot,
    because after the interruption the resumed run may play to the end.
    """

    def __init__(self, block_after: Optional[int] = None) -> None:
        self.spoken: List[str] = []
        self.pending: List[str] = []
        self.cancelled = 0
        self._lock = threading.Lock()
        self._block_after = block_after
        self._gate = threading.Event()
        self._gate.set()

    def speak_async(self, text: str, language: str = "de") -> StubUtterance:
        del language
        with self._lock:
            self.pending.append(text)
            in_flight = len(self.spoken) + len(self.pending)
            if self._block_after is not None and in_flight > self._block_after:
                self._gate.clear()
            else:
                self._gate.set()
        self._gate.wait()
        return StubUtterance(self)

    def cancel(self) -> None:
        self.cancelled += 1
        with self._lock:
            self._block_after = None  # one-shot interruption
            if self.pending:
                self.pending.pop()
        self._gate.set()


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


def find_node_by_name(name: str) -> Any:
    """Return the first node on the bus whose accessible name matches."""

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
            if node.name == name:
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


def wait_until(predicate: Callable[[], bool], timeout: float = 10.0) -> bool:
    deadline = time.time() + timeout
    while time.time() < deadline:
        if predicate():
            return True
        time.sleep(0.05)
    return False


def multiline_steps(desktop: PyAtSpiDesktop) -> None:
    """Counted navigation, line jumps and say-all against the Gtk.TextView.

    Say-all runs with a stub speech handle (CI has no speech-dispatcher):
    the stub completes chunks instantly but blocks the third one, so the
    session stops the run exactly where a user would interrupt playback,
    then resumes at the bookmark and verifies the field-end caret.
    """

    node = find_node_by_name(MULTILINE_NAME)
    if node is None:
        record("REFUSED", "multiline", "probe exposes no multi-line text view")
        return
    try:
        grabbed = bool(node.queryComponent().grabFocus())
    except Exception:
        grabbed = False
    focused = lambda: desktop.context().focused_name  # noqa: E731
    if not grabbed or not wait_until(lambda: focused() == MULTILINE_NAME, 5):
        record("REFUSED", "multiline-focus", f"grabbed={grabbed}, focused={focused()!r}")
        return
    record("OK", "multiline-focus", f"focused={focused()}")

    run(
        "multiline-content",
        desktop.read_text_field,
        lambda value: require(value == MULTILINE_TEXT, f"content={value!r}"),
    )
    total = len(MULTILINE_TEXT)

    # --- counted word navigation: one command, one position report --------
    run("multiline-caret-start", lambda: desktop.move_caret("start"))
    counted_ok, counted_spoken = run(
        "caret-word-counted",
        lambda: desktop.move_caret("word_next", 3),
    )
    counted_position = parse_position(counted_spoken)
    if counted_ok and counted_position:
        run(
            "caret-word-counted-check",
            lambda: None,
            lambda _: require(
                counted_position == (16, total),  # 4th word "Dokuments."
                f"position={counted_position}",
            ),
        )

    # --- line jumps: exact and clamped -------------------------------------
    line_ok, line_spoken = run("caret-line-5", lambda: desktop.move_caret_to_line(5))
    if line_ok:
        run(
            "caret-line-5-check",
            lambda: None,
            lambda _: require(
                "Zeile 5" in line_spoken
                and parse_position(line_spoken) == (75, total),
                f"spoken={line_spoken!r}",
            ),
        )
    clamp_ok, clamp_spoken = run("caret-line-99-clamps", lambda: desktop.move_caret_to_line(99))
    if clamp_ok:
        run(
            "caret-line-99-check",
            lambda: None,
            lambda _: require(
                "nur 7" in clamp_spoken
                and "Zeile 7" in clamp_spoken
                and parse_position(clamp_spoken) == (104, total),
                f"spoken={clamp_spoken!r}",
            ),
        )

    # --- counted line navigation back from the end --------------------------
    back_ok, back_spoken = run(
        "caret-lines-counted-back",
        lambda: desktop.move_caret("line_previous", 3),
    )
    back_position = parse_position(back_spoken)
    if back_ok and back_position:
        run(
            "caret-lines-counted-check",
            lambda: None,
            lambda _: require(
                # Empty lines are not units: 7 -> 5 -> 4 -> 2
                back_position == (27, total),
                f"position={back_position}",
            ),
        )

    # --- say-all: start, stop mid-chunk, resume, field-end caret ------------
    speaker = StubSpeaker(block_after=2)
    start_ok, start_spoken = run(
        "say-all-start", lambda: desktop.read_all_start(speaker)
    )
    if start_ok:
        run(
            "say-all-start-check",
            lambda: None,
            lambda _: require("Stopp" in start_spoken, f"spoken={start_spoken!r}"),
        )
        # Wait until chunks 1-2 completed and chunk 3 is blocked mid-playback.
        blocked = wait_until(
            lambda: len(speaker.spoken) == 2 and len(speaker.pending) == 1, 10
        )
        if not blocked:
            record("ERROR", "say-all-block", "reader never reached the third chunk")
            return
        stop_ok, stop_spoken = run(
            "say-all-stop", lambda: desktop.read_all_stop(speaker)
        )
        if stop_ok:
            run(
                "say-all-stop-check",
                lambda: None,
                lambda _: require(
                    "Zeile 2" in stop_spoken  # bookmark: end of sentence 2
                    and speaker.cancelled == 1,
                    f"spoken={stop_spoken!r}, cancelled={speaker.cancelled}",
                ),
            )
        resume_ok, resume_spoken = run(
            "say-all-resume", lambda: desktop.read_all_resume(speaker)
        )
        if resume_ok:
            run(
                "say-all-resume-check",
                lambda: None,
                lambda _: require(
                    "Zeile 2" in resume_spoken,  # bookmark offset sits at line 2's end
                    f"spoken={resume_spoken!r}",
                ),
            )
        # The resumed reader plays the remaining three sentences to the end.
        finished = wait_until(
            lambda: desktop._say_all_reader is None
            or desktop._say_all_reader.thread is None
            or not desktop._say_all_reader.thread.is_alive(),
            10,
        )
        if not finished:
            record("ERROR", "say-all-finish", "resumed reader never finished")
            return
        run(
            "say-all-all-five-sentences",
            lambda: None,
            lambda _: require(
                len(speaker.spoken) == 5,
                f"spoken={speaker.spoken!r}",
            ),
        )
        # Field completely read: the caret sits at the field end once, so
        # navigation continues from there (read-from-caret is empty).
        run(
            "say-all-caret-at-end",
            desktop.read_from_caret,
            lambda value: require(value == "", f"remaining={value!r}"),
        )
        nav_ok, nav_spoken = run(
            "say-all-then-word-back", lambda: desktop.move_caret("word_previous")
        )
        nav_position = parse_position(nav_spoken)
        if nav_ok and nav_position:
            run(
                "say-all-then-word-back-check",
                lambda: None,
                lambda _: require(
                    nav_position == (112, total),  # "Absatz." in the last line
                    f"position={nav_position}",
                ),
            )


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

    # --- correction slot: replace the dictation just inserted ----------------
    # "nein ich meinte …" must replace the remembered span, not append.  The
    # memory is verified against the live field content first (honesty check),
    # then the span is selected and replaced through the same text interface
    # the selection-replacement step above uses.
    if insert_ok:
        prefix = current[: len(current) - len(INSERTION)] if at_known_end else None

        def check_corrected(value: str) -> None:
            require(
                value == prefix + " sofort"
                if prefix is not None
                else " sofort" in value,
                f"content={value!r}",
            )

        correct_ok, corrected = run(
            "dictation-correct",
            lambda: desktop.replace_last_dictation(" sofort"),
            check_corrected,
        )
        if correct_ok:
            current = text_of(corrected, current)
        else:
            _, raw = run("read-after-refused-correction", desktop.read_text_field)
            current = text_of(raw, current) or current
    else:
        # Nothing was dictated, so the correction slot must refuse honestly
        # instead of touching the field — a refusal here is the correct
        # behaviour, an ERROR is not.
        try:
            desktop.replace_last_dictation("sofort")
            record(
                "ERROR",
                "dictation-correct-no-memory",
                "correction without a dictation was NOT refused",
            )
        except GnomeAdapterError as exc:
            record("OK", "dictation-correct-no-memory", str(exc))
        except Exception:
            record(
                "ERROR",
                "dictation-correct-no-memory",
                traceback.format_exc(limit=3).replace("\n", " | "),
            )

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

    # --- multi-line TextView: counted navigation, line jumps, say-all ------
    # The probe app ships a Gtk.TextView with three paragraphs; the entry
    # above is single-line and cannot provide these capabilities.  Focus is
    # moved through the same AT-SPI component interface the adapter itself
    # uses internally, so the steps below measure the adapter, not GTK.
    multiline_steps(desktop)

    # --- structure navigation: jump to the real GTK list box ----------------
    # The probe app ships a Gtk.ListBox — the one structure widget GTK fills
    # natively.  Its real AT-SPI role is "list box" (ATK_ROLE_LIST_BOX, per
    # the gtk-3-24 a11y sources), not "list": the check asserts the role the
    # live bus actually reports.  Headings, links and landmarks are
    # browser-provided roles GTK never exposes; those stay covered by the
    # fake-tree unit tests (test_structure_navigation).
    def check_list_jump(spoken: str) -> None:
        require(
            "StrukturListe" in str(spoken),
            f"jump announced {spoken!r} without the list name",
        )
        focused_role = desktop.context().focused_role.casefold()
        require(
            focused_role in ("list", "list box"),
            f"focused role after jump is {focused_role!r}, not a list role",
        )

    run(
        "structure-jump-list",
        lambda: desktop.jump_to_structure("list", backward=False),
        check_list_jump,
    )
    # No headings exist in a plain GTK window: the honest refusal (not an
    # ERROR) is the expected, documented behaviour.
    run(
        "structure-jump-heading-refused",
        lambda: desktop.jump_to_structure("heading", backward=False),
    )

    errors = sum(1 for line in lines if line.startswith("ERROR"))
    refusals = sum(1 for line in lines if line.startswith("REFUSED"))
    oks = sum(1 for line in lines if line.startswith("OK"))
    record("SUMMARY", "session", f"{oks} OK, {refusals} REFUSED, {errors} ERROR")
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())
