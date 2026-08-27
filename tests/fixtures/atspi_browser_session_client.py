"""Drive Clausis structure navigation against a REAL browser AT-SPI tree.

firefox-esr loads ``browser_probe_page.html`` via ``file://``; this client
verifies ``jump_to_structure`` against the roles a real browser publishes:
headings (ROLE_HEADING), links (ROLE_LINK), lists (ROLE_LIST) and ARIA
landmarks (the ``xml-roles`` object attribute).

Unlike the GTK session client, refusals here are FAILURES: the entire point
of the browser session is proving the adapter against browser-provided
roles, so every step is a requirement.  The only expected refusals are the
honest out-of-range sentences at both ends of the document (asserted with
their exact wording).  On timeout the active window tree is dumped so the
CI log shows what the bus actually exposed.

Only reading and focus movement happen — a link landing NEVER activates the
link (V1 security invariant: browser activation stays with a separately
confirmed action, which does not exist yet).
"""

import sys
import time
import traceback
from typing import Any, Callable, List, Optional

from clausis.gnome_adapter import GnomeAdapterError, PyAtSpiDesktop

#: Window-title token of the probe page (Firefox titles the window after
#: the document); combined with the application name this cannot collide
#: with the GTK probe window of the GTK-only session.
PAGE_TITLE_TOKEN = "browser-strukturtest"
FIREFOX_APP_TOKEN = "firefox"

#: Headings in document order (h1 -> h2 -> h3).
EXPECTED_HEADINGS = ["Erste Überschrift", "Zweite Überschrift", "Dritte Überschrift"]
#: Links in document order.
EXPECTED_LINKS = ["Beispiel-Link Eins", "Beispiel-Link Zwei"]
#: Landmark xml-roles in document order; the session walk must verify all.
ALL_LANDMARKS = ["banner", "navigation", "main", "contentinfo"]

lines: List[str] = []


def flush_results() -> None:
    if len(sys.argv) > 1:
        with open(sys.argv[1], "w", encoding="utf-8") as handle:
            handle.write("\n".join(lines) + "\n")


def record(status: str, step: str, detail: str = "") -> None:
    line = f"{status} {step}" + (f" :: {detail}" if detail else "")
    lines.append(line)
    print(line, flush=True)
    flush_results()


def run(step: str, function: Callable[[], Any], checker: Optional[Callable[[Any], None]] = None):
    """Run one adapter call; a refusal is an ERROR (every step is required)."""

    try:
        value = function()
    except GnomeAdapterError as exc:
        record("ERROR", step, f"refused: {exc}")
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


def expect_refusal(step: str, function: Callable[[], str], needle: str) -> None:
    """Assert the adapter refuses with the honest out-of-range sentence."""

    try:
        value = function()
    except GnomeAdapterError as exc:
        if needle in str(exc):
            record("OK", step, str(exc))
        else:
            record("ERROR", step, f"refused, but without {needle!r}: {exc}")
        return
    except Exception:
        record("ERROR", step, traceback.format_exc(limit=3).replace("\n", " | "))
        return
    record("ERROR", step, f"expected refusal ({needle!r}) but the call returned {value!r}")


def wait_until(predicate: Callable[[], bool], timeout: float) -> bool:
    deadline = time.time() + timeout
    while time.time() < deadline:
        if predicate():
            return True
        time.sleep(0.25)
    return False


def dump_window_tree(desktop: PyAtSpiDesktop, max_nodes: int = 160) -> str:
    """Readable role/name dump of the active window for timeout diagnosis."""

    try:
        _, window = desktop._active_window()
    except Exception as exc:
        return f"(no active window: {exc})"
    out: List[str] = []
    try:
        for node in desktop._walk(window):
            if len(out) >= max_nodes:
                out.append("… (tree truncated)")
                break
            flags = "+FOCUSED" if desktop._has_state(node, desktop._atspi.STATE_FOCUSED) else ""
            out.append(f"{desktop._role(node)}={desktop._name(node)!r}{flags}")
    except Exception as exc:
        out.append(f"(walk failed: {exc})")
    return " | ".join(out)


def window_ready(desktop: PyAtSpiDesktop) -> bool:
    """The Firefox window showing the probe page is active."""

    try:
        application, window = desktop._active_window()
    except GnomeAdapterError:
        return False
    if FIREFOX_APP_TOKEN not in desktop._name(application).lower():
        return False
    return PAGE_TITLE_TOKEN in desktop._name(window).lower()


def tree_has_role(desktop: PyAtSpiDesktop, role: str) -> bool:
    """Read-only check that the window tree already exposes the role."""

    try:
        _, window = desktop._active_window()
    except GnomeAdapterError:
        return False
    return any(desktop._role(node).casefold() == role for node in desktop._walk(window))


def announced(name: str) -> Callable[[str], None]:
    def checker(spoken: Any) -> None:
        text = str(spoken)
        assert name.lower() in text.lower(), (
            f"announcement {text!r} does not contain {name!r}"
        )

    return checker


def jump(desktop: PyAtSpiDesktop, step: str, backward: bool, unit: str) -> Any:
    """One announcing jump.  The order assertions of the walk sequences —
    not the focus state, which browsers never set on non-focusable
    elements — verify that repeated jumps advance."""

    return run(step, lambda: desktop.jump_to_structure(unit, backward=backward))


def main() -> int:
    try:
        desktop = PyAtSpiDesktop()
    except GnomeAdapterError as exc:
        record("ERROR", "adapter-init", str(exc))
        return 2

    if not wait_until(lambda: window_ready(desktop), 30):
        record(
            "ERROR",
            "browser-window",
            f"Firefox window never appeared within 30 s; tree: {dump_window_tree(desktop)}",
        )
        return 2
    record("OK", "browser-window")
    # The content tree builds asynchronously and only when a client asks;
    # polling the bus IS the request, so wait for real heading roles.
    if not wait_until(lambda: tree_has_role(desktop, "heading"), 30):
        record(
            "ERROR",
            "browser-tree",
            f"accessibility tree never exposed a heading; tree: {dump_window_tree(desktop)}",
        )
        return 2
    record("OK", "browser-tree", "headings present on the bus")

    # --- headings: forward in document order, honest end, reversed -------
    # Initial focus sits on the document node (before every heading), so
    # the first forward jump must find h1, then h2, then h3.
    for index, name in enumerate(EXPECTED_HEADINGS, start=1):
        run(
            f"heading-next-{index}",
            lambda name=name: desktop.jump_to_structure("heading", backward=False),
            announced(name),
        )
    expect_refusal(
        "heading-next-past-end",
        lambda: desktop.jump_to_structure("heading", backward=False),
        "Keine weiteren Überschriften",
    )
    # Focus is still on h3: backward jumps reverse the order h2 -> h1.
    for name in reversed(EXPECTED_HEADINGS[:-1]):
        ok, spoken = jump(
            desktop, f"heading-previous-{EXPECTED_HEADINGS.index(name) + 1}", True, "heading"
        )
        if ok and name.lower() not in str(spoken).lower():
            record("ERROR", f"heading-previous-{name}", f"expected {name!r}, got {spoken!r}")
    # Repeatability: from h1 the forward jump moves to h2 again.
    ok, spoken = jump(desktop, "heading-next-again", False, "heading")
    if ok and EXPECTED_HEADINGS[1].lower() not in str(spoken).lower():
        record("ERROR", "heading-next-again", f"expected h2 again, got {spoken!r}")

    # --- links: document order, previous reverses, honest ends -----------
    # Focus is on h2 (inside <main>, before the first link).
    for index, name in enumerate(EXPECTED_LINKS, start=1):
        run(
            f"link-next-{index}",
            lambda name=name: desktop.jump_to_structure("link", backward=False),
            announced(name),
        )
    expect_refusal(
        "link-next-past-end",
        lambda: desktop.jump_to_structure("link", backward=False),
        "Keine weiteren Links",
    )
    run(
        "link-previous",
        lambda: desktop.jump_to_structure("link", backward=True),
        announced(EXPECTED_LINKS[0]),
    )
    expect_refusal(
        "link-previous-past-start",
        lambda: desktop.jump_to_structure("link", backward=True),
        "Keine Links mehr vor dieser Stelle",
    )

    # --- landmarks: walk back towards the document top with adapter moves -
    # Focus is on the first link (inside <main>, AFTER h2): one backward
    # heading jump lands on h2 (nearest first), from where the forward
    # landmark walk must find main, then navigation, then contentinfo —
    # document order, no wrap-around.  A further forward jump honestly
    # refuses; walking BACKWARD from there crosses main and navigation
    # and reaches banner, so all four landmarks are verified.
    run(
        "landmark-prep-previous-heading",
        lambda: desktop.jump_to_structure("heading", backward=True),
        announced(EXPECTED_HEADINGS[1]),
    )
    seen: List[str] = []
    # Forward from h2: <main> CONTAINS h2, so in the depth-first walk main
    # precedes h2 — the only landmark AFTER the position is the footer.
    ok, spoken = run(
        "landmark-next-contentinfo",
        lambda: desktop.jump_to_structure("landmark", backward=False),
    )
    if ok:
        text = str(spoken).strip()
        role = text.split()[0].strip(".").casefold() if text.split() else ""
        seen.append(role)
        if role != "contentinfo":
            record(
                "ERROR",
                "landmark-order-contentinfo",
                f"announced {text!r} (role {role!r}), expected 'contentinfo'",
            )
    expect_refusal(
        "landmark-next-past-end",
        lambda: desktop.jump_to_structure("landmark", backward=False),
        "Keine weiteren Landmarken",
    )
    # Backward from the footer position: each jump returns the NEAREST
    # earlier landmark — main, then navigation, then banner — verifying
    # the remaining three landmarks in reverse document order.
    for expected in ("main", "navigation", "banner"):
        ok, _ = run(
            f"landmark-previous-{expected}",
            lambda expected=expected: desktop.jump_to_structure("landmark", backward=True),
            announced(expected),
        )
        if ok:
            seen.append(expected)
    expect_refusal(
        "landmark-previous-past-start",
        lambda: desktop.jump_to_structure("landmark", backward=True),
        "Keine Landmarken mehr vor dieser Stelle",
    )
    for required in ALL_LANDMARKS:
        if required not in seen:
            record(
                "ERROR",
                f"landmark-missing-{required}",
                f"landmark walk verified only {seen!r}",
            )

    # --- list: a real <ul> with AT-SPI role "list" ------------------------
    def check_list(spoken: Any) -> None:
        # Firefox never carries STATE_FOCUSED on the list; the adapter's
        # virtual structure cursor IS the honest landing position, so the
        # check reads it back instead of a focus state the bus will not
        # reflect (see jump_to_structure).
        cursor = desktop._structure_cursor
        assert cursor is not None, "virtual structure cursor not set"
        cursor_role = desktop._role(cursor).casefold()
        assert cursor_role in ("list", "list box"), (
            f"cursor role after the list jump is {cursor_role!r}"
        )
        assert str(spoken).startswith("Liste"), f"announcement {spoken!r}"

    # Focus is on the banner (header), which precedes the <ul> in the walk.
    run(
        "list-next",
        lambda: desktop.jump_to_structure("list", backward=False),
        check_list,
    )

    errors = sum(1 for line in lines if line.startswith("ERROR"))
    oks = sum(1 for line in lines if line.startswith("OK"))
    record("SUMMARY", "browser-session", f"{oks} OK, {errors} ERROR")
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())
