"""Bounded semantic GNOME control through the AT-SPI accessibility tree.

No screen coordinates, screenshots or synthesized pointer events are used.
The adapter reads the current accessibility state again immediately before an
activation so a stale numbered target cannot silently select another window.
"""

from __future__ import annotations

from dataclasses import dataclass
import math
import time
from typing import Any, Callable, Iterable, List, Optional, Protocol, Sequence, Tuple

from .clipboard import read_text, write_text
from .models import ActionRequest, ActionResult
from .policy import ActionPolicy


class GnomeAdapterError(RuntimeError):
    """A recoverable missing-session or inaccessible-widget condition."""


@dataclass(frozen=True)
class SemanticControl:
    number: int
    name: str
    role: str
    actions: Tuple[str, ...]


@dataclass(frozen=True)
class DesktopContext:
    application: str
    window: str
    focused_name: str
    focused_role: str
    controls: Tuple[SemanticControl, ...]

    def spoken_location(self) -> str:
        app = self.application or "unbekannte Anwendung"
        window = self.window or "unbenanntes Fenster"
        focus = self.focused_name or self.focused_role or "kein benanntes Element"
        return f"Sie sind in {app}, Fenster {window}. Fokus auf {focus}."

    def spoken_controls(self) -> str:
        if not self.controls:
            return "In diesem Fenster wurden keine ausführbaren Bedienelemente gefunden."
        items = [
            f"Nummer {item.number}: {item.name or item.role}"
            for item in self.controls
        ]
        return "Verfügbare Ziele. " + ". ".join(items) + "."


class SemanticDesktop(Protocol):
    def context(self) -> DesktopContext:
        ...

    def activate(self, number: int) -> str:
        ...

    def activate_named(self, name: str) -> str:
        ...

    def cycle_focus(self, direction: int) -> str:
        ...

    def focus_named(self, name: str) -> str:
        ...

    def set_focused_text(self, value: str) -> str:
        ...

    def read_focused_text(self) -> Tuple[str, str]:
        ...

    def focused_text_for_clipboard(self) -> Tuple[str, str]:
        ...

    def selected_text_for_clipboard(self) -> Tuple[str, str]:
        ...

    def select_all_focused_text(self) -> str:
        ...

    def clear_focused_text_selection(self) -> str:
        ...

    def delete_focused_text_selection(self) -> str:
        ...

    def insert_focused_text_at_caret(self, value: str) -> str:
        ...

    def delete_focused_text_character(self, direction: str) -> str:
        ...

    def delete_focused_text_word(self, direction: str) -> str:
        ...

    def replace_focused_text_word(self, direction: str, value: str) -> str:
        ...

    def select_focused_text_character(self, direction: str) -> str:
        ...

    def select_focused_text_word(self, direction: str) -> str:
        ...

    def replace_focused_text_selection(self, value: str) -> str:
        ...

    def focused_text_character_at_caret(self, direction: str) -> Tuple[str, str]:
        ...

    def focused_text_word_at_caret(self, direction: str) -> Tuple[str, str]:
        ...

    def move_focused_text_caret(self, position: str) -> str:
        ...

    def move_focused_text_caret_word(self, direction: str) -> str:
        ...

    def focused_text_line_at_caret(self) -> Tuple[str, str]:
        ...

    def move_focused_text_caret_line(self, boundary: str) -> str:
        ...

    def select_focused_text_line(self) -> str:
        ...

    def delete_focused_text_line(self) -> str:
        ...

    def replace_focused_text_line(self, value: str) -> str:
        ...

    def insert_focused_text_line(self, direction: str, value: str) -> str:
        ...

    def duplicate_focused_text_line(self, direction: str) -> str:
        ...

    def move_focused_text_line(self, direction: str) -> str:
        ...

    def join_focused_text_line(self, direction: str) -> str:
        ...

    def split_focused_text_line(self) -> str:
        ...

    def indent_focused_text_line(self, direction: str) -> str:
        ...

    def focused_text_caret_position(self) -> Tuple[str, int, int]:
        ...

    def set_focused_clipboard_text(self, value: str) -> str:
        ...

    def select_named_item(self, name: str) -> str:
        ...

    def select_visible_file(self, name: str) -> str:
        ...

    def set_file_name(self, name: str) -> str:
        ...

    def set_file_location(self, path: str) -> str:
        ...

    def open_visible_folder(self, name: str) -> str:
        ...

    def decide_file_dialog(self, decision: str) -> str:
        ...

    def decide_standard_dialog(self, decision: str) -> str:
        ...

    def read_standard_dialog(self) -> Tuple[str, Tuple[str, ...]]:
        ...

    def dismiss_standard_dialog(self) -> str:
        ...

    def set_named_tree_item_expanded(self, name: str, expanded: bool) -> str:
        ...

    def select_table_row(self, name: str) -> str:
        ...

    def select_named_tab(self, name: str) -> str:
        ...

    def set_named_slider(self, name: str, percent: int) -> str:
        ...

    def read_named_progress(self, name: str) -> Tuple[str, int]:
        ...

    def set_named_checkbox(self, name: str, checked: bool) -> str:
        ...

    def set_named_switch(self, name: str, enabled: bool) -> str:
        ...

    def select_named_radio(self, name: str) -> str:
        ...

    def select_combo_item(self, combo_name: str, item_name: str) -> str:
        ...

    def set_named_spin_button(self, name: str, number: float) -> str:
        ...

    def activate_menu_item(self, name: str) -> str:
        ...

    def decide_permission(self, decision: str) -> str:
        ...

    def cycle_window(self, direction: int) -> str:
        ...

    def navigate_back(self) -> str:
        ...

    def window_action(self, operation: str) -> str:
        ...

    def shell_action(self, operation: str) -> str:
        ...

    def read_notifications(self) -> Tuple[str, ...]:
        ...

    def dismiss_notification(self, number: int) -> int:
        ...


class PyAtSpiDesktop:
    """Real GNOME provider, imported lazily so non-GNOME tests still run."""

    MAX_NODES = 2500
    MAX_DEPTH = 24
    MAX_CONTROLS = 30

    def __init__(self) -> None:
        try:
            import pyatspi
        except ImportError as exc:
            raise GnomeAdapterError("GNOME-Zugriff ist nicht installiert.") from exc
        self._atspi = pyatspi

    def context(self) -> DesktopContext:
        application, window = self._orientation_window()
        focused = self._find_state(window, self._atspi.STATE_FOCUSED)
        controls = self._controls(window)
        return DesktopContext(
            application=self._name(application),
            window=self._name(window),
            focused_name=self._name(focused),
            focused_role=self._role(focused),
            controls=tuple(
                SemanticControl(index, self._name(node), self._role(node), actions)
                for index, (node, actions) in enumerate(controls, start=1)
            ),
        )

    def activate(self, number: int) -> str:
        if number < 1 or number > self.MAX_CONTROLS:
            raise GnomeAdapterError("Die Zielnummer liegt außerhalb des erlaubten Bereichs.")
        _, window = self._active_window()
        controls = self._controls(window)
        if number > len(controls):
            raise GnomeAdapterError("Diese Zielnummer ist im aktuellen Fenster nicht vorhanden.")

        # A spoken number is meaningful only for the exact ordered snapshot
        # that was bound above. Re-read both the active window and the complete
        # operable-control order immediately before mutation; additions,
        # removals, reordering, or a dialog switch must invalidate the number.
        _, rebound_window = self._active_window()
        if rebound_window is not window:
            raise GnomeAdapterError(
                "Das aktive Fenster hat vor der nummerierten Aktivierung gewechselt; "
                "es wurde nichts ausgeführt."
            )
        rebound_controls = self._controls(rebound_window)
        if len(rebound_controls) != len(controls) or any(
            rebound_node is not original_node
            for (original_node, _original_actions), (rebound_node, _rebound_actions)
            in zip(controls, rebound_controls)
        ):
            raise GnomeAdapterError(
                "Die Nummerierung der Bedienelemente hat sich geändert; "
                "es wurde nichts ausgeführt."
            )
        return self._invoke_control(*rebound_controls[number - 1])

    def activate_named(self, name: str) -> str:
        """Activate one exact, uniquely named control in the current window."""

        normalized = " ".join(name.split()).casefold()
        if not normalized or len(normalized) > 120:
            raise GnomeAdapterError("Der Name des Bedienelements ist ung\u00fcltig.")
        _, window = self._active_window()
        matches = [
            (node, actions)
            for node, actions in self._controls(window)
            if self._name(node).casefold() == normalized
        ]
        if not matches:
            raise GnomeAdapterError("Kein Bedienelement mit diesem exakten Namen gefunden.")
        if len(matches) != 1:
            raise GnomeAdapterError("Der Name ist nicht eindeutig; bitte eine Nummer verwenden.")
        target, _discovered_actions = matches[0]

        # Discovery and invocation are separate AT-SPI calls. Rebind the active
        # window and the target immediately before mutation so a dialog switch,
        # disappearing control, or changed SHOWING/SENSITIVE state cannot turn
        # a previously safe name into an action on stale UI state.
        _, rebound_window = self._active_window()
        if rebound_window is not window:
            raise GnomeAdapterError(
                "Das aktive Fenster hat vor der Aktivierung gewechselt; es wurde nichts ausgeführt."
            )
        rebound = [
            (node, actions)
            for node, actions in self._controls(rebound_window)
            if node is target
        ]
        if len(rebound) != 1:
            raise GnomeAdapterError(
                "Das Bedienelement ist nicht mehr eindeutig an das aktive Fenster gebunden."
            )
        return self._invoke_control(*rebound[0])

    def cycle_focus(self, direction: int) -> str:
        """Move focus among controls and verify or restore the exact state."""

        _, window = self._active_window()
        controls = self._controls(window)
        if not controls:
            raise GnomeAdapterError("Dieses Fenster hat keine fokussierbaren Aktionen.")
        focused = [
            index
            for index, (node, _actions) in enumerate(controls)
            if self._has_state(node, self._atspi.STATE_FOCUSED)
        ]
        if len(focused) > 1:
            raise GnomeAdapterError(
                "Der aktuelle Fokus ist nicht eindeutig; er bleibt unverändert."
            )
        previous_index = focused[0] if focused else None
        step = 1 if direction >= 0 else -1
        target_index = (
            (previous_index + step) % len(controls)
            if previous_index is not None
            else (0 if step > 0 else len(controls) - 1)
        )
        node, _actions = controls[target_index]

        def exactly_focused(expected_index: Optional[int]) -> bool:
            return all(
                self._has_state(candidate, self._atspi.STATE_FOCUSED)
                == (index == expected_index)
                for index, (candidate, _candidate_actions) in enumerate(controls)
            )

        def restore_previous() -> bool:
            if previous_index is None:
                return exactly_focused(None)
            if exactly_focused(previous_index):
                return True
            previous = controls[previous_index][0]
            try:
                return bool(previous.queryComponent().grabFocus()) and exactly_focused(
                    previous_index
                )
            except Exception:
                return False

        try:
            accepted = bool(node.queryComponent().grabFocus())
        except Exception as exc:
            if not restore_previous():
                raise GnomeAdapterError(
                    "Die fehlgeschlagene Fokusänderung konnte nicht zurückgesetzt werden."
                ) from exc
            raise GnomeAdapterError("Das Bedienelement konnte nicht fokussiert werden.") from exc
        if not accepted or not exactly_focused(target_index):
            if not restore_previous():
                raise GnomeAdapterError(
                    "Der inkonsistente Fokus konnte nicht zurückgesetzt werden."
                )
            raise GnomeAdapterError("GNOME hat die Fokusänderung nicht bestätigt.")
        return self._name(node) or self._role(node)

    def focus_named(self, name: str) -> str:
        """Focus one exact visible focusable accessible and verify the result."""

        normalized = " ".join(name.split()).casefold()
        if not normalized or len(normalized) > 120:
            raise GnomeAdapterError("Der Name des Fokusziels ist ungültig.")
        _, window = self._active_window()
        matches = [
            node
            for node in self._walk(window)
            if self._name(node).casefold() == normalized
            and self._has_state(node, self._atspi.STATE_SHOWING)
            and self._has_state(node, self._atspi.STATE_FOCUSABLE)
        ]
        if not matches:
            raise GnomeAdapterError("Kein sichtbares fokussierbares Element mit diesem Namen gefunden.")
        if len(matches) != 1:
            raise GnomeAdapterError("Der Name des Fokusziels ist nicht eindeutig.")
        target = matches[0]
        nodes = list(self._walk(window))
        focused = [
            node for node in nodes if self._has_state(node, self._atspi.STATE_FOCUSED)
        ]
        if len(focused) != 1:
            raise GnomeAdapterError(
                "Der Ausgangsfokus ist nicht eindeutig; er bleibt unverändert."
            )
        previous = focused[0]
        if previous is target:
            return self._name(target) or self._role(target)

        def exactly_focused(expected: Any) -> bool:
            return all(
                self._has_state(node, self._atspi.STATE_FOCUSED) == (node is expected)
                for node in nodes
            )

        def restore_previous() -> bool:
            if exactly_focused(previous):
                return True
            try:
                return bool(previous.queryComponent().grabFocus()) and exactly_focused(
                    previous
                )
            except Exception:
                return False

        try:
            accepted = bool(target.queryComponent().grabFocus())
        except Exception as exc:
            if not restore_previous():
                raise GnomeAdapterError(
                    "Die fehlgeschlagene Fokusänderung konnte nicht zurückgesetzt werden."
                ) from exc
            raise GnomeAdapterError("Das benannte Element konnte nicht fokussiert werden.") from exc
        if not accepted or not exactly_focused(target):
            if not restore_previous():
                raise GnomeAdapterError(
                    "Die fehlgeschlagene Fokusänderung konnte nicht zurückgesetzt werden."
                )
            raise GnomeAdapterError("Die Fokusänderung konnte nicht bestätigt werden.")
        return self._name(target) or self._role(target)

    def read_focused_text(self) -> Tuple[str, str]:
        """Read a bounded, non-secret focused text field through AT-SPI."""

        _, window = self._active_window()
        focused = self._find_state(window, self._atspi.STATE_FOCUSED)
        if focused is None:
            raise GnomeAdapterError("Kein fokussiertes Textfeld gefunden.")
        role = self._role(focused).casefold()
        if role not in {"entry", "text", "document text"}:
            raise GnomeAdapterError("Das fokussierte Element ist kein lesbares Textfeld.")
        try:
            attributes = " ".join(str(value) for value in focused.getAttributes()).casefold()
        except Exception as exc:
            raise GnomeAdapterError("Die Schutzattribute des Textfelds sind nicht prüfbar.") from exc
        privacy = f"{role} {attributes}"
        if any(marker in privacy for marker in ("password", "passwort", "protected", "secret")):
            raise GnomeAdapterError("Geschützte Textfelder werden nicht vorgelesen.")
        try:
            text = focused.queryText()
            count = int(text.characterCount)
            if count < 0 or count > 10_000_000:
                raise ValueError("invalid character count")
            value = str(text.getText(0, min(count, 1000)))
        except Exception as exc:
            raise GnomeAdapterError("Der Inhalt des Textfelds ist nicht sicher lesbar.") from exc
        spoken = " ".join(value.split())
        if count > 1000:
            spoken += " …"
        return self._name(focused) or "Textfeld", spoken

    def focused_text_for_clipboard(self) -> Tuple[str, str]:
        """Return exact bounded text for a clipboard write, never a secret field."""

        _, window = self._active_window()
        focused = self._find_state(window, self._atspi.STATE_FOCUSED)
        if focused is None:
            raise GnomeAdapterError("Kein fokussiertes Textfeld gefunden.")
        role = self._role(focused).casefold()
        if role not in {"entry", "text", "document text"}:
            raise GnomeAdapterError("Das fokussierte Element ist kein kopierbares Textfeld.")
        try:
            attributes = " ".join(str(value) for value in focused.getAttributes()).casefold()
        except Exception as exc:
            raise GnomeAdapterError("Die Schutzattribute des Textfelds sind nicht prüfbar.") from exc
        privacy = f"{role} {attributes}"
        if any(marker in privacy for marker in ("password", "passwort", "protected", "secret")):
            raise GnomeAdapterError("Geschützte Textfelder werden nicht kopiert.")
        try:
            text = focused.queryText()
            count = int(text.characterCount)
            if count < 1 or count > 100_000:
                raise ValueError("invalid clipboard character count")
            value = str(text.getText(0, count))
        except Exception as exc:
            raise GnomeAdapterError("Der Inhalt des Textfelds ist nicht sicher kopierbar.") from exc
        if len(value) != count or "\x00" in value:
            raise GnomeAdapterError("Der Textinhalt konnte nicht vollständig gelesen werden.")
        return self._name(focused) or "Textfeld", value

    def selected_text_for_clipboard(self) -> Tuple[str, str]:
        """Return exactly one bounded AT-SPI text selection from a safe field."""

        _, window = self._active_window()
        focused = self._find_state(window, self._atspi.STATE_FOCUSED)
        if focused is None:
            raise GnomeAdapterError("Kein fokussiertes Textfeld gefunden.")
        role = self._role(focused).casefold()
        if role not in {"entry", "text", "document text"}:
            raise GnomeAdapterError("Das fokussierte Element ist kein auswählbares Textfeld.")
        try:
            attributes = " ".join(str(value) for value in focused.getAttributes()).casefold()
        except Exception as exc:
            raise GnomeAdapterError("Die Schutzattribute des Textfelds sind nicht prüfbar.") from exc
        privacy = f"{role} {attributes}"
        if any(marker in privacy for marker in ("password", "passwort", "protected", "secret")):
            raise GnomeAdapterError("Aus geschützten Textfeldern wird nicht kopiert.")
        try:
            text = focused.queryText()
            count = int(text.characterCount)
            selections = int(text.nSelections)
            if count < 1 or count > 10_000_000 or selections != 1:
                raise ValueError("invalid text selection metadata")
            start, end = text.getSelection(0)
            start, end = int(start), int(end)
            if start < 0 or end <= start or end > count or end - start > 100_000:
                raise ValueError("invalid text selection range")
            value = str(text.getText(start, end))
        except Exception as exc:
            raise GnomeAdapterError("Es ist keine eindeutige sichere Textauswahl verfügbar.") from exc
        if len(value) != end - start or "\x00" in value:
            raise GnomeAdapterError("Die Textauswahl konnte nicht vollständig gelesen werden.")
        return self._name(focused) or "Textfeld", value

    def select_all_focused_text(self) -> str:
        """Select all bounded safe text and verify or restore the prior selection."""

        _, window = self._active_window()
        focused = self._find_state(window, self._atspi.STATE_FOCUSED)
        if focused is None:
            raise GnomeAdapterError("Kein fokussiertes Textfeld gefunden.")
        role = self._role(focused).casefold()
        if role not in {"entry", "text", "document text"}:
            raise GnomeAdapterError("Das fokussierte Element ist kein auswählbares Textfeld.")
        try:
            attributes = " ".join(str(value) for value in focused.getAttributes()).casefold()
        except Exception as exc:
            raise GnomeAdapterError("Die Schutzattribute des Textfelds sind nicht prüfbar.") from exc
        privacy = f"{role} {attributes}"
        if any(marker in privacy for marker in ("password", "passwort", "protected", "secret")):
            raise GnomeAdapterError("Geschützte Textfelder werden nicht vollständig ausgewählt.")
        text = None
        previous: list[tuple[int, int]] = []
        mutation_started = False
        try:
            text = focused.queryText()
            count = int(text.characterCount)
            selection_count = int(text.nSelections)
            if count < 1 or count > 100_000 or selection_count < 0 or selection_count > 64:
                raise ValueError("invalid text selection metadata")
            previous = [tuple(map(int, text.getSelection(index))) for index in range(selection_count)]
            if any(start < 0 or end < start or end > count for start, end in previous):
                raise ValueError("invalid existing text selection")
            for index in range(selection_count - 1, -1, -1):
                mutation_started = True
                if not bool(text.removeSelection(index)):
                    raise RuntimeError("selection removal rejected")
            mutation_started = True
            accepted = bool(text.addSelection(0, count))
            observed = int(text.nSelections) == 1 and tuple(map(int, text.getSelection(0))) == (0, count)
        except Exception as exc:
            accepted = False
            observed = False
            failure = exc
        else:
            failure = None
        if not accepted or not observed:
            if not mutation_started or text is None:
                raise GnomeAdapterError("Die vollständige Textauswahl ist nicht sicher verfügbar.") from failure
            restored = False
            try:
                for index in range(int(text.nSelections) - 1, -1, -1):
                    if not bool(text.removeSelection(index)):
                        raise RuntimeError("selection rollback removal rejected")
                for start, end in previous:
                    if not bool(text.addSelection(start, end)):
                        raise RuntimeError("selection rollback rejected")
                restored = int(text.nSelections) == len(previous) and all(
                    tuple(map(int, text.getSelection(index))) == span
                    for index, span in enumerate(previous)
                )
            except Exception:
                restored = False
            if not restored:
                raise GnomeAdapterError(
                    "Die fehlgeschlagene Textauswahl konnte nicht zurückgesetzt werden."
                ) from failure
            raise GnomeAdapterError("Die vollständige Textauswahl konnte nicht bestätigt werden.") from failure
        return self._name(focused) or "Textfeld"

    def clear_focused_text_selection(self) -> str:
        """Remove bounded safe AT-SPI selections and verify or restore them."""

        _, window = self._active_window()
        focused = self._find_state(window, self._atspi.STATE_FOCUSED)
        if focused is None:
            raise GnomeAdapterError("Kein fokussiertes Textfeld gefunden.")
        role = self._role(focused).casefold()
        if role not in {"entry", "text", "document text"}:
            raise GnomeAdapterError("Das fokussierte Element ist kein auswählbares Textfeld.")
        try:
            attributes = " ".join(str(value) for value in focused.getAttributes()).casefold()
        except Exception as exc:
            raise GnomeAdapterError("Die Schutzattribute des Textfelds sind nicht prüfbar.") from exc
        privacy = f"{role} {attributes}"
        if any(marker in privacy for marker in ("password", "passwort", "protected", "secret")):
            raise GnomeAdapterError("Auswahlen in geschützten Textfeldern werden nicht verändert.")
        try:
            text = focused.queryText()
            count = int(text.characterCount)
            selection_count = int(text.nSelections)
            if count < 0 or count > 100_000 or selection_count < 0 or selection_count > 64:
                raise ValueError("invalid text selection metadata")
            previous = [tuple(map(int, text.getSelection(index))) for index in range(selection_count)]
            if any(start < 0 or end <= start or end > count for start, end in previous):
                raise ValueError("invalid existing text selection")
        except Exception as exc:
            raise GnomeAdapterError("Die Textauswahl ist nicht sicher prüfbar.") from exc
        if not previous:
            return self._name(focused) or "Textfeld"
        failure = None
        try:
            for index in range(selection_count - 1, -1, -1):
                if not bool(text.removeSelection(index)):
                    raise RuntimeError("selection removal rejected")
            observed = int(text.nSelections) == 0
        except Exception as exc:
            observed = False
            failure = exc
        if not observed:
            restored = False
            try:
                for index in range(int(text.nSelections) - 1, -1, -1):
                    if not bool(text.removeSelection(index)):
                        raise RuntimeError("selection rollback removal rejected")
                for start, end in previous:
                    if not bool(text.addSelection(start, end)):
                        raise RuntimeError("selection rollback rejected")
                restored = int(text.nSelections) == len(previous) and all(
                    tuple(map(int, text.getSelection(index))) == span
                    for index, span in enumerate(previous)
                )
            except Exception:
                restored = False
            if not restored:
                raise GnomeAdapterError(
                    "Das fehlgeschlagene Aufheben der Textauswahl konnte nicht zurückgesetzt werden."
                ) from failure
            raise GnomeAdapterError("Das Aufheben der Textauswahl konnte nicht bestätigt werden.") from failure
        return self._name(focused) or "Textfeld"

    def delete_focused_text_selection(self) -> str:
        """Delete one exact safe selection and restore the field on mismatch."""

        _, window = self._active_window()
        focused = self._find_state(window, self._atspi.STATE_FOCUSED)
        if focused is None:
            raise GnomeAdapterError("Kein fokussiertes Textfeld gefunden.")
        role = self._role(focused).casefold()
        if role not in {"entry", "text", "document text"}:
            raise GnomeAdapterError("Das fokussierte Element ist kein bearbeitbares Textfeld.")
        try:
            attributes = " ".join(str(value) for value in focused.getAttributes()).casefold()
        except Exception as exc:
            raise GnomeAdapterError("Die Schutzattribute des Textfelds sind nicht prüfbar.") from exc
        privacy = f"{role} {attributes}"
        if any(marker in privacy for marker in ("password", "passwort", "protected", "secret")):
            raise GnomeAdapterError("Aus geschützten Textfeldern wird nichts gelöscht.")
        try:
            text = focused.queryText()
            editable = focused.queryEditableText()
            count = int(text.characterCount)
            selection_count = int(text.nSelections)
            caret = int(text.caretOffset)
            if count < 1 or count > 100_000 or selection_count != 1 or caret < 0 or caret > count:
                raise ValueError("invalid editable selection metadata")
            start, end = map(int, text.getSelection(0))
            if start < 0 or end <= start or end > count:
                raise ValueError("invalid editable selection range")
            previous = str(text.getText(0, count))
            if len(previous) != count or "\x00" in previous:
                raise ValueError("incomplete editable text")
            expected = previous[:start] + previous[end:]
        except Exception as exc:
            raise GnomeAdapterError("Die Textauswahl ist nicht sicher löschbar.") from exc
        failure = None
        try:
            accepted = bool(editable.deleteText(start, end))
            observed_count = int(text.characterCount)
            observed = (
                accepted
                and observed_count == len(expected)
                and str(text.getText(0, observed_count)) == expected
                and int(text.nSelections) == 0
            )
        except Exception as exc:
            observed = False
            failure = exc
        if not observed:
            restored = False
            try:
                editable.setTextContents(previous)
                restored = (
                    int(text.characterCount) == count
                    and str(text.getText(0, count)) == previous
                    and bool(text.setCaretOffset(caret))
                    and int(text.caretOffset) == caret
                )
                if restored:
                    for index in range(int(text.nSelections) - 1, -1, -1):
                        if not bool(text.removeSelection(index)):
                            restored = False
                            break
                if restored:
                    restored = bool(text.addSelection(start, end)) and (
                        int(text.nSelections) == 1
                        and tuple(map(int, text.getSelection(0))) == (start, end)
                    )
            except Exception:
                restored = False
            if not restored:
                raise GnomeAdapterError(
                    "Das fehlgeschlagene Löschen konnte nicht zurückgesetzt werden."
                ) from failure
            raise GnomeAdapterError("Das Löschen der Textauswahl konnte nicht bestätigt werden.") from failure
        return self._name(focused) or "Textfeld"

    def move_focused_text_caret(self, position: str) -> str:
        """Move the caret to a fixed boundary and verify or restore its offset."""

        if position not in {"start", "end", "previous", "next"}:
            raise GnomeAdapterError("Unzulässige Textcursor-Position.")
        _, window = self._active_window()
        focused = self._find_state(window, self._atspi.STATE_FOCUSED)
        if focused is None:
            raise GnomeAdapterError("Kein fokussiertes Textfeld gefunden.")
        role = self._role(focused).casefold()
        if role not in {"entry", "text", "document text"}:
            raise GnomeAdapterError("Das fokussierte Element ist kein Textfeld.")
        try:
            attributes = " ".join(str(value) for value in focused.getAttributes()).casefold()
        except Exception as exc:
            raise GnomeAdapterError("Die Schutzattribute des Textfelds sind nicht prüfbar.") from exc
        privacy = f"{role} {attributes}"
        if any(marker in privacy for marker in ("password", "passwort", "protected", "secret")):
            raise GnomeAdapterError("Der Textcursor geschützter Textfelder wird nicht verändert.")
        try:
            text = focused.queryText()
            count = int(text.characterCount)
            previous = int(text.caretOffset)
            if count < 0 or count > 100_000 or previous < 0 or previous > count:
                raise ValueError("invalid caret metadata")
        except Exception as exc:
            raise GnomeAdapterError("Die Textcursor-Position ist nicht sicher prüfbar.") from exc
        targets = {
            "start": 0,
            "end": count,
            "previous": max(0, previous - 1),
            "next": min(count, previous + 1),
        }
        target = targets[position]
        if previous == target:
            return self._name(focused) or "Textfeld"
        failure = None
        try:
            accepted = bool(text.setCaretOffset(target))
            observed = int(text.caretOffset) == target
        except Exception as exc:
            accepted = False
            observed = False
            failure = exc
        if not accepted or not observed:
            restored = False
            try:
                restored = bool(text.setCaretOffset(previous)) and int(text.caretOffset) == previous
            except Exception:
                restored = False
            if not restored:
                raise GnomeAdapterError(
                    "Die fehlgeschlagene Textcursor-Bewegung konnte nicht zurückgesetzt werden."
                ) from failure
            raise GnomeAdapterError("Die Textcursor-Bewegung konnte nicht bestätigt werden.") from failure
        return self._name(focused) or "Textfeld"

    def move_focused_text_caret_word(self, direction: str) -> str:
        """Move to one bounded adjacent word start and verify or restore."""

        if direction not in {"previous", "next"}:
            raise GnomeAdapterError("Unzulässige Richtung für die Wortnavigation.")
        _, window = self._active_window()
        focused = self._find_state(window, self._atspi.STATE_FOCUSED)
        if focused is None:
            raise GnomeAdapterError("Kein fokussiertes Textfeld gefunden.")
        role = self._role(focused).casefold()
        if role not in {"entry", "text", "document text"}:
            raise GnomeAdapterError("Das fokussierte Element ist kein Textfeld.")
        try:
            attributes = " ".join(str(value) for value in focused.getAttributes()).casefold()
        except Exception as exc:
            raise GnomeAdapterError("Die Schutzattribute des Textfelds sind nicht prüfbar.") from exc
        privacy = f"{role} {attributes}"
        if any(marker in privacy for marker in ("password", "passwort", "protected", "secret")):
            raise GnomeAdapterError("Der Textcursor geschützter Textfelder wird nicht verändert.")
        try:
            text = focused.queryText()
            count = int(text.characterCount)
            previous = int(text.caretOffset)
            selections = int(text.nSelections)
            if (
                count < 0
                or count > 100_000
                or previous < 0
                or previous > count
                or selections != 0
            ):
                raise ValueError("invalid word navigation metadata")
            if (direction == "previous" and previous == 0) or (
                direction == "next" and previous == count
            ):
                return self._name(focused) or "Textfeld"
            inspected = 0

            def read_at(index: int) -> str:
                nonlocal inspected
                if inspected >= 256:
                    raise ValueError("word navigation limit exceeded")
                value = str(text.getText(index, index + 1))
                inspected += 1
                if len(value) != 1 or "\x00" in value:
                    raise ValueError("incomplete word navigation read")
                return value

            def is_word(character: str) -> bool:
                return character.isalnum() or character in "_'-"

            if direction == "previous":
                index = previous - 1
                character = read_at(index)
                while index >= 0 and not is_word(character):
                    index -= 1
                    if index >= 0:
                        character = read_at(index)
                while index >= 0 and is_word(character):
                    index -= 1
                    if index >= 0:
                        character = read_at(index)
                target = index + 1
            else:
                index = previous
                character = read_at(index)
                while index < count and is_word(character):
                    index += 1
                    if index < count:
                        character = read_at(index)
                while index < count and not is_word(character):
                    index += 1
                    if index < count:
                        character = read_at(index)
                target = index
        except GnomeAdapterError:
            raise
        except Exception as exc:
            raise GnomeAdapterError(
                "Das benachbarte Wort ist innerhalb der sicheren Suchgrenze nicht bestimmbar."
            ) from exc
        if previous == target:
            return self._name(focused) or "Textfeld"
        failure = None
        try:
            accepted = bool(text.setCaretOffset(target))
            observed = int(text.caretOffset) == target and int(text.nSelections) == 0
        except Exception as exc:
            accepted = False
            observed = False
            failure = exc
        if not accepted or not observed:
            restored = False
            try:
                restored = (
                    bool(text.setCaretOffset(previous))
                    and int(text.caretOffset) == previous
                    and int(text.nSelections) == 0
                )
            except Exception:
                restored = False
            if not restored:
                raise GnomeAdapterError(
                    "Die fehlgeschlagene Wortnavigation konnte nicht zurückgesetzt werden."
                ) from failure
            raise GnomeAdapterError("Die Wortnavigation konnte nicht bestätigt werden.") from failure
        return self._name(focused) or "Textfeld"

    def focused_text_caret_position(self) -> Tuple[str, int, int]:
        """Return only bounded caret metadata from a safe focused text object."""

        _, window = self._active_window()
        focused = self._find_state(window, self._atspi.STATE_FOCUSED)
        if focused is None:
            raise GnomeAdapterError("Kein fokussiertes Textfeld gefunden.")
        role = self._role(focused).casefold()
        if role not in {"entry", "text", "document text"}:
            raise GnomeAdapterError("Das fokussierte Element ist kein Textfeld.")
        try:
            attributes = " ".join(str(value) for value in focused.getAttributes()).casefold()
        except Exception as exc:
            raise GnomeAdapterError("Die Schutzattribute des Textfelds sind nicht prüfbar.") from exc
        privacy = f"{role} {attributes}"
        if any(marker in privacy for marker in ("password", "passwort", "protected", "secret")):
            raise GnomeAdapterError("Die Textcursor-Position geschützter Textfelder wird nicht ausgegeben.")
        try:
            text = focused.queryText()
            count = int(text.characterCount)
            offset = int(text.caretOffset)
            if count < 0 or count > 100_000 or offset < 0 or offset > count:
                raise ValueError("invalid caret metadata")
        except Exception as exc:
            raise GnomeAdapterError("Die Textcursor-Position ist nicht sicher lesbar.") from exc
        return self._name(focused) or "Textfeld", offset, count

    def insert_focused_text_at_caret(self, value: str) -> str:
        """Insert bounded dictated text at the exact caret and verify or restore."""

        if not value or len(value) > 500 or any(not character.isprintable() for character in value):
            raise GnomeAdapterError("Der einzufügende Text muss 1 bis 500 druckbare Zeichen enthalten.")
        _, window = self._active_window()
        focused = self._find_state(window, self._atspi.STATE_FOCUSED)
        if focused is None:
            raise GnomeAdapterError("Kein fokussiertes Textfeld gefunden.")
        role = self._role(focused).casefold()
        if role not in {"entry", "text", "document text"}:
            raise GnomeAdapterError("Das fokussierte Element ist kein bearbeitbares Textfeld.")
        try:
            attributes = " ".join(str(item) for item in focused.getAttributes()).casefold()
        except Exception as exc:
            raise GnomeAdapterError("Die Schutzattribute des Textfelds sind nicht prüfbar.") from exc
        privacy = f"{role} {attributes}"
        if any(marker in privacy for marker in ("password", "passwort", "protected", "secret")):
            raise GnomeAdapterError("In geschützte Textfelder wird kein Text eingefügt.")
        try:
            text = focused.queryText()
            editable = focused.queryEditableText()
            count = int(text.characterCount)
            caret = int(text.caretOffset)
            selections = int(text.nSelections)
            if count < 0 or count > 100_000 - len(value) or caret < 0 or caret > count or selections != 0:
                raise ValueError("invalid insertion metadata")
            previous = str(text.getText(0, count))
            if len(previous) != count or "\x00" in previous:
                raise ValueError("incomplete insertion snapshot")
            expected = previous[:caret] + value + previous[caret:]
            expected_caret = caret + len(value)
        except Exception as exc:
            raise GnomeAdapterError("Der Textcursor ist nicht sicher zum Einfügen verfügbar.") from exc

        def restore_previous() -> bool:
            try:
                return (
                    bool(editable.setTextContents(previous))
                    and int(text.characterCount) == count
                    and str(text.getText(0, count)) == previous
                    and bool(text.setCaretOffset(caret))
                    and int(text.caretOffset) == caret
                    and int(text.nSelections) == 0
                )
            except Exception:
                return False

        failure = None
        try:
            accepted = bool(editable.insertText(caret, value, len(value)))
            caret_accepted = accepted and bool(text.setCaretOffset(expected_caret))
            observed_count = int(text.characterCount)
            observed = (
                accepted
                and caret_accepted
                and observed_count == len(expected)
                and str(text.getText(0, observed_count)) == expected
                and int(text.caretOffset) == expected_caret
                and int(text.nSelections) == 0
            )
        except Exception as exc:
            observed = False
            failure = exc
        if not observed:
            if not restore_previous():
                raise GnomeAdapterError(
                    "Das fehlgeschlagene Einfügen konnte nicht zurückgesetzt werden."
                ) from failure
            raise GnomeAdapterError("Das Einfügen am Textcursor konnte nicht bestätigt werden.") from failure
        return self._name(focused) or "Textfeld"

    def delete_focused_text_character(self, direction: str) -> str:
        """Delete exactly one character beside the caret and verify or restore."""

        if direction not in {"previous", "next"}:
            raise GnomeAdapterError("Unzulässige Richtung für das Löschen am Textcursor.")
        _, window = self._active_window()
        focused = self._find_state(window, self._atspi.STATE_FOCUSED)
        if focused is None:
            raise GnomeAdapterError("Kein fokussiertes Textfeld gefunden.")
        role = self._role(focused).casefold()
        if role not in {"entry", "text", "document text"}:
            raise GnomeAdapterError("Das fokussierte Element ist kein bearbeitbares Textfeld.")
        try:
            attributes = " ".join(str(item) for item in focused.getAttributes()).casefold()
        except Exception as exc:
            raise GnomeAdapterError("Die Schutzattribute des Textfelds sind nicht prüfbar.") from exc
        privacy = f"{role} {attributes}"
        if any(marker in privacy for marker in ("password", "passwort", "protected", "secret")):
            raise GnomeAdapterError("Aus geschützten Textfeldern werden keine Zeichen gelöscht.")
        try:
            text = focused.queryText()
            editable = focused.queryEditableText()
            count = int(text.characterCount)
            caret = int(text.caretOffset)
            selections = int(text.nSelections)
            if count < 0 or count > 100_000 or caret < 0 or caret > count or selections != 0:
                raise ValueError("invalid character deletion metadata")
            previous = str(text.getText(0, count))
            if len(previous) != count or "\x00" in previous:
                raise ValueError("incomplete character deletion snapshot")
        except Exception as exc:
            raise GnomeAdapterError("Der Textcursor ist nicht sicher zum Löschen verfügbar.") from exc
        if (direction == "previous" and caret == 0) or (direction == "next" and caret == count):
            return self._name(focused) or "Textfeld"
        start = caret - 1 if direction == "previous" else caret
        end = start + 1
        expected = previous[:start] + previous[end:]
        expected_caret = start if direction == "previous" else caret

        def restore_previous() -> bool:
            try:
                return (
                    bool(editable.setTextContents(previous))
                    and int(text.characterCount) == count
                    and str(text.getText(0, count)) == previous
                    and bool(text.setCaretOffset(caret))
                    and int(text.caretOffset) == caret
                    and int(text.nSelections) == 0
                )
            except Exception:
                return False

        failure = None
        try:
            accepted = bool(editable.deleteText(start, end))
            caret_accepted = accepted and bool(text.setCaretOffset(expected_caret))
            observed_count = int(text.characterCount)
            observed = (
                accepted
                and caret_accepted
                and observed_count == len(expected)
                and str(text.getText(0, observed_count)) == expected
                and int(text.caretOffset) == expected_caret
                and int(text.nSelections) == 0
            )
        except Exception as exc:
            observed = False
            failure = exc
        if not observed:
            if not restore_previous():
                raise GnomeAdapterError(
                    "Das fehlgeschlagene Löschen des Zeichens konnte nicht zurückgesetzt werden."
                ) from failure
            raise GnomeAdapterError("Das Löschen des Zeichens konnte nicht bestätigt werden.") from failure
        return self._name(focused) or "Textfeld"

    def delete_focused_text_word(self, direction: str) -> str:
        """Delete one bounded adjacent Unicode word and verify or restore."""

        if direction not in {"previous", "next"}:
            raise GnomeAdapterError("Unzulässige Richtung für die Wortlöschung.")
        _, window = self._active_window()
        focused = self._find_state(window, self._atspi.STATE_FOCUSED)
        if focused is None:
            raise GnomeAdapterError("Kein fokussiertes Textfeld gefunden.")
        role = self._role(focused).casefold()
        if role not in {"entry", "text", "document text"}:
            raise GnomeAdapterError("Das fokussierte Element ist kein bearbeitbares Textfeld.")
        try:
            attributes = " ".join(str(item) for item in focused.getAttributes()).casefold()
        except Exception as exc:
            raise GnomeAdapterError("Die Schutzattribute des Textfelds sind nicht prüfbar.") from exc
        privacy = f"{role} {attributes}"
        if any(marker in privacy for marker in ("password", "passwort", "protected", "secret")):
            raise GnomeAdapterError("Aus geschützten Textfeldern werden keine Wörter gelöscht.")
        try:
            text = focused.queryText()
            editable = focused.queryEditableText()
            count = int(text.characterCount)
            caret = int(text.caretOffset)
            selections = int(text.nSelections)
            if count < 0 or count > 100_000 or caret < 0 or caret > count or selections != 0:
                raise ValueError("invalid word deletion metadata")
            if (direction == "previous" and caret == 0) or (
                direction == "next" and caret == count
            ):
                return self._name(focused) or "Textfeld"
            inspected = 0

            def read_at(index: int) -> str:
                nonlocal inspected
                if inspected >= 256:
                    raise ValueError("word deletion limit exceeded")
                value = str(text.getText(index, index + 1))
                inspected += 1
                if len(value) != 1 or "\x00" in value:
                    raise ValueError("incomplete word deletion read")
                return value

            def is_word(character: str) -> bool:
                return character.isalnum() or character in "_'-"

            if direction == "previous":
                index = caret - 1
                character = read_at(index)
                while index >= 0 and not is_word(character):
                    index -= 1
                    if index >= 0:
                        character = read_at(index)
                if index < 0:
                    return self._name(focused) or "Textfeld"
                end = index + 1
                while index >= 0 and is_word(character):
                    index -= 1
                    if index >= 0:
                        character = read_at(index)
                start = index + 1
                expected_caret = caret - (end - start)
            else:
                index = caret
                character = read_at(index)
                while index < count and not is_word(character):
                    index += 1
                    if index < count:
                        character = read_at(index)
                if index >= count:
                    return self._name(focused) or "Textfeld"
                start = index
                while index < count and is_word(character):
                    index += 1
                    if index < count:
                        character = read_at(index)
                end = index
                expected_caret = caret
            previous = str(text.getText(0, count))
            if len(previous) != count or "\x00" in previous:
                raise ValueError("incomplete word deletion snapshot")
            expected = previous[:start] + previous[end:]
        except GnomeAdapterError:
            raise
        except Exception as exc:
            raise GnomeAdapterError(
                "Das benachbarte Wort ist innerhalb der sicheren Suchgrenze nicht löschbar."
            ) from exc

        def restore_previous() -> bool:
            try:
                return (
                    bool(editable.setTextContents(previous))
                    and int(text.characterCount) == count
                    and str(text.getText(0, count)) == previous
                    and bool(text.setCaretOffset(caret))
                    and int(text.caretOffset) == caret
                    and int(text.nSelections) == 0
                )
            except Exception:
                return False

        failure = None
        try:
            accepted = bool(editable.deleteText(start, end))
            caret_accepted = accepted and bool(text.setCaretOffset(expected_caret))
            observed_count = int(text.characterCount)
            observed = (
                accepted
                and caret_accepted
                and observed_count == len(expected)
                and str(text.getText(0, observed_count)) == expected
                and int(text.caretOffset) == expected_caret
                and int(text.nSelections) == 0
            )
        except Exception as exc:
            observed = False
            failure = exc
        if not observed:
            if not restore_previous():
                raise GnomeAdapterError(
                    "Die fehlgeschlagene Wortlöschung konnte nicht zurückgesetzt werden."
                ) from failure
            raise GnomeAdapterError("Die Wortlöschung konnte nicht bestätigt werden.") from failure
        return self._name(focused) or "Textfeld"

    def replace_focused_text_word(self, direction: str, value: str) -> str:
        """Replace one bounded adjacent Unicode word and verify or restore."""

        if direction not in {"previous", "next"}:
            raise GnomeAdapterError("Unzulässige Richtung für den Wortersatz.")
        if not value or len(value) > 500 or any(not character.isprintable() for character in value):
            raise GnomeAdapterError("Der Wortersatz muss 1 bis 500 druckbare Zeichen enthalten.")
        _, window = self._active_window()
        focused = self._find_state(window, self._atspi.STATE_FOCUSED)
        if focused is None:
            raise GnomeAdapterError("Kein fokussiertes Textfeld gefunden.")
        role = self._role(focused).casefold()
        if role not in {"entry", "text", "document text"}:
            raise GnomeAdapterError("Das fokussierte Element ist kein bearbeitbares Textfeld.")
        try:
            attributes = " ".join(str(item) for item in focused.getAttributes()).casefold()
        except Exception as exc:
            raise GnomeAdapterError("Die Schutzattribute des Textfelds sind nicht prüfbar.") from exc
        privacy = f"{role} {attributes}"
        if any(marker in privacy for marker in ("password", "passwort", "protected", "secret")):
            raise GnomeAdapterError("Wörter in geschützten Textfeldern werden nicht ersetzt.")
        try:
            text = focused.queryText()
            editable = focused.queryEditableText()
            count = int(text.characterCount)
            caret = int(text.caretOffset)
            selections = int(text.nSelections)
            if count < 0 or count > 100_000 or caret < 0 or caret > count or selections != 0:
                raise ValueError("invalid word replacement metadata")
            if (direction == "previous" and caret == 0) or (
                direction == "next" and caret == count
            ):
                return self._name(focused) or "Textfeld"
            inspected = 0

            def read_at(index: int) -> str:
                nonlocal inspected
                if inspected >= 256:
                    raise ValueError("word replacement limit exceeded")
                character = str(text.getText(index, index + 1))
                inspected += 1
                if len(character) != 1 or "\x00" in character:
                    raise ValueError("incomplete word replacement read")
                return character

            def is_word(character: str) -> bool:
                return character.isalnum() or character in "_'-"

            if direction == "previous":
                index = caret - 1
                character = read_at(index)
                while index >= 0 and not is_word(character):
                    index -= 1
                    if index >= 0:
                        character = read_at(index)
                if index < 0:
                    return self._name(focused) or "Textfeld"
                end = index + 1
                while index >= 0 and is_word(character):
                    index -= 1
                    if index >= 0:
                        character = read_at(index)
                start = index + 1
            else:
                index = caret
                character = read_at(index)
                while index < count and not is_word(character):
                    index += 1
                    if index < count:
                        character = read_at(index)
                if index >= count:
                    return self._name(focused) or "Textfeld"
                start = index
                while index < count and is_word(character):
                    index += 1
                    if index < count:
                        character = read_at(index)
                end = index
            previous = str(text.getText(0, count))
            if len(previous) != count or "\x00" in previous:
                raise ValueError("incomplete word replacement snapshot")
            expected = previous[:start] + value + previous[end:]
            if len(expected) > 100_000:
                raise ValueError("word replacement result too large")
            expected_caret = start + len(value)
        except GnomeAdapterError:
            raise
        except Exception as exc:
            raise GnomeAdapterError(
                "Das benachbarte Wort ist innerhalb der sicheren Suchgrenze nicht ersetzbar."
            ) from exc

        def restore_previous() -> bool:
            try:
                return (
                    bool(editable.setTextContents(previous))
                    and int(text.characterCount) == count
                    and str(text.getText(0, count)) == previous
                    and bool(text.setCaretOffset(caret))
                    and int(text.caretOffset) == caret
                    and int(text.nSelections) == 0
                )
            except Exception:
                return False

        failure = None
        try:
            accepted = bool(editable.setTextContents(expected))
            caret_accepted = accepted and bool(text.setCaretOffset(expected_caret))
            observed_count = int(text.characterCount)
            observed = (
                accepted
                and caret_accepted
                and observed_count == len(expected)
                and str(text.getText(0, observed_count)) == expected
                and int(text.caretOffset) == expected_caret
                and int(text.nSelections) == 0
            )
        except Exception as exc:
            observed = False
            failure = exc
        if not observed:
            if not restore_previous():
                raise GnomeAdapterError(
                    "Der fehlgeschlagene Wortersatz konnte nicht zurückgesetzt werden."
                ) from failure
            raise GnomeAdapterError("Der Wortersatz konnte nicht bestätigt werden.") from failure
        return self._name(focused) or "Textfeld"

    def select_focused_text_character(self, direction: str) -> str:
        """Select exactly one character beside the caret and verify or restore."""

        if direction not in {"previous", "next"}:
            raise GnomeAdapterError("Unzulässige Richtung für die Zeichenauswahl.")
        _, window = self._active_window()
        focused = self._find_state(window, self._atspi.STATE_FOCUSED)
        if focused is None:
            raise GnomeAdapterError("Kein fokussiertes Textfeld gefunden.")
        role = self._role(focused).casefold()
        if role not in {"entry", "text", "document text"}:
            raise GnomeAdapterError("Das fokussierte Element ist kein auswählbares Textfeld.")
        try:
            attributes = " ".join(str(item) for item in focused.getAttributes()).casefold()
        except Exception as exc:
            raise GnomeAdapterError("Die Schutzattribute des Textfelds sind nicht prüfbar.") from exc
        privacy = f"{role} {attributes}"
        if any(marker in privacy for marker in ("password", "passwort", "protected", "secret")):
            raise GnomeAdapterError("In geschützten Textfeldern werden keine Zeichen ausgewählt.")
        try:
            text = focused.queryText()
            count = int(text.characterCount)
            caret = int(text.caretOffset)
            selections = int(text.nSelections)
            if count < 0 or count > 100_000 or caret < 0 or caret > count or selections != 0:
                raise ValueError("invalid character selection metadata")
        except Exception as exc:
            raise GnomeAdapterError("Der Textcursor ist nicht sicher zur Auswahl verfügbar.") from exc
        if (direction == "previous" and caret == 0) or (direction == "next" and caret == count):
            return self._name(focused) or "Textfeld"
        start = caret - 1 if direction == "previous" else caret
        end = start + 1
        target_caret = start if direction == "previous" else end
        failure = None
        try:
            accepted = bool(text.addSelection(start, end))
            caret_accepted = accepted and bool(text.setCaretOffset(target_caret))
            observed = (
                accepted
                and caret_accepted
                and int(text.nSelections) == 1
                and tuple(map(int, text.getSelection(0))) == (start, end)
                and int(text.caretOffset) == target_caret
            )
        except Exception as exc:
            observed = False
            failure = exc
        if not observed:
            restored = False
            try:
                for index in range(int(text.nSelections) - 1, -1, -1):
                    if not bool(text.removeSelection(index)):
                        raise RuntimeError("character selection rollback removal rejected")
                restored = (
                    int(text.nSelections) == 0
                    and bool(text.setCaretOffset(caret))
                    and int(text.caretOffset) == caret
                )
            except Exception:
                restored = False
            if not restored:
                raise GnomeAdapterError(
                    "Die fehlgeschlagene Zeichenauswahl konnte nicht zurückgesetzt werden."
                ) from failure
            raise GnomeAdapterError("Die Zeichenauswahl konnte nicht bestätigt werden.") from failure
        return self._name(focused) or "Textfeld"

    def select_focused_text_word(self, direction: str) -> str:
        """Select one bounded adjacent Unicode word and verify or restore."""

        if direction not in {"previous", "next"}:
            raise GnomeAdapterError("Unzulässige Richtung für die Wortauswahl.")
        _, window = self._active_window()
        focused = self._find_state(window, self._atspi.STATE_FOCUSED)
        if focused is None:
            raise GnomeAdapterError("Kein fokussiertes Textfeld gefunden.")
        role = self._role(focused).casefold()
        if role not in {"entry", "text", "document text"}:
            raise GnomeAdapterError("Das fokussierte Element ist kein Textfeld.")
        try:
            attributes = " ".join(str(item) for item in focused.getAttributes()).casefold()
        except Exception as exc:
            raise GnomeAdapterError("Die Schutzattribute des Textfelds sind nicht prüfbar.") from exc
        privacy = f"{role} {attributes}"
        if any(marker in privacy for marker in ("password", "passwort", "protected", "secret")):
            raise GnomeAdapterError("In geschützten Textfeldern werden keine Wörter ausgewählt.")
        try:
            text = focused.queryText()
            count = int(text.characterCount)
            caret = int(text.caretOffset)
            selections = int(text.nSelections)
            if count < 0 or count > 100_000 or caret < 0 or caret > count or selections != 0:
                raise ValueError("invalid word selection metadata")
            if (direction == "previous" and caret == 0) or (
                direction == "next" and caret == count
            ):
                return self._name(focused) or "Textfeld"
            inspected = 0

            def read_at(index: int) -> str:
                nonlocal inspected
                if inspected >= 256:
                    raise ValueError("word selection limit exceeded")
                value = str(text.getText(index, index + 1))
                inspected += 1
                if len(value) != 1 or "\x00" in value:
                    raise ValueError("incomplete word selection read")
                return value

            def is_word(character: str) -> bool:
                return character.isalnum() or character in "_'-"

            if direction == "previous":
                index = caret - 1
                character = read_at(index)
                while index >= 0 and not is_word(character):
                    index -= 1
                    if index >= 0:
                        character = read_at(index)
                if index < 0:
                    return self._name(focused) or "Textfeld"
                end = index + 1
                while index >= 0 and is_word(character):
                    index -= 1
                    if index >= 0:
                        character = read_at(index)
                start = index + 1
                target_caret = start
            else:
                index = caret
                character = read_at(index)
                while index < count and not is_word(character):
                    index += 1
                    if index < count:
                        character = read_at(index)
                if index >= count:
                    return self._name(focused) or "Textfeld"
                start = index
                while index < count and is_word(character):
                    index += 1
                    if index < count:
                        character = read_at(index)
                end = index
                target_caret = end
        except GnomeAdapterError:
            raise
        except Exception as exc:
            raise GnomeAdapterError(
                "Das benachbarte Wort ist innerhalb der sicheren Suchgrenze nicht auswählbar."
            ) from exc
        failure = None
        try:
            accepted = bool(text.addSelection(start, end))
            caret_accepted = accepted and bool(text.setCaretOffset(target_caret))
            observed = (
                accepted
                and caret_accepted
                and int(text.nSelections) == 1
                and tuple(map(int, text.getSelection(0))) == (start, end)
                and int(text.caretOffset) == target_caret
            )
        except Exception as exc:
            observed = False
            failure = exc
        if not observed:
            restored = False
            try:
                for index in range(int(text.nSelections) - 1, -1, -1):
                    if not bool(text.removeSelection(index)):
                        raise RuntimeError("word selection rollback removal rejected")
                restored = (
                    int(text.nSelections) == 0
                    and bool(text.setCaretOffset(caret))
                    and int(text.caretOffset) == caret
                )
            except Exception:
                restored = False
            if not restored:
                raise GnomeAdapterError(
                    "Die fehlgeschlagene Wortauswahl konnte nicht zurückgesetzt werden."
                ) from failure
            raise GnomeAdapterError("Die Wortauswahl konnte nicht bestätigt werden.") from failure
        return self._name(focused) or "Textfeld"

    def replace_focused_text_selection(self, value: str) -> str:
        """Replace exactly one safe selection and verify or restore all state."""

        if not value or len(value) > 500 or any(not character.isprintable() for character in value):
            raise GnomeAdapterError("Der Ersatztext muss 1 bis 500 druckbare Zeichen enthalten.")
        _, window = self._active_window()
        focused = self._find_state(window, self._atspi.STATE_FOCUSED)
        if focused is None:
            raise GnomeAdapterError("Kein fokussiertes Textfeld gefunden.")
        role = self._role(focused).casefold()
        if role not in {"entry", "text", "document text"}:
            raise GnomeAdapterError("Das fokussierte Element ist kein bearbeitbares Textfeld.")
        try:
            attributes = " ".join(str(item) for item in focused.getAttributes()).casefold()
        except Exception as exc:
            raise GnomeAdapterError("Die Schutzattribute des Textfelds sind nicht prüfbar.") from exc
        privacy = f"{role} {attributes}"
        if any(marker in privacy for marker in ("password", "passwort", "protected", "secret")):
            raise GnomeAdapterError("Auswahlen in geschützten Textfeldern werden nicht ersetzt.")
        try:
            text = focused.queryText()
            editable = focused.queryEditableText()
            count = int(text.characterCount)
            caret = int(text.caretOffset)
            selections = int(text.nSelections)
            if count < 1 or count > 100_000 or caret < 0 or caret > count or selections != 1:
                raise ValueError("invalid selection replacement metadata")
            start, end = map(int, text.getSelection(0))
            if start < 0 or end <= start or end > count:
                raise ValueError("invalid selection replacement range")
            previous = str(text.getText(0, count))
            if len(previous) != count or "\x00" in previous:
                raise ValueError("incomplete selection replacement snapshot")
            expected = previous[:start] + value + previous[end:]
            if len(expected) > 100_000:
                raise ValueError("replacement result too large")
            expected_caret = start + len(value)
        except Exception as exc:
            raise GnomeAdapterError("Die Textauswahl ist nicht sicher ersetzbar.") from exc

        def restore_previous() -> bool:
            try:
                if not bool(editable.setTextContents(previous)):
                    return False
                for index in range(int(text.nSelections) - 1, -1, -1):
                    if not bool(text.removeSelection(index)):
                        return False
                return (
                    int(text.characterCount) == count
                    and str(text.getText(0, count)) == previous
                    and bool(text.setCaretOffset(caret))
                    and int(text.caretOffset) == caret
                    and bool(text.addSelection(start, end))
                    and int(text.nSelections) == 1
                    and tuple(map(int, text.getSelection(0))) == (start, end)
                )
            except Exception:
                return False

        failure = None
        try:
            accepted = bool(editable.setTextContents(expected))
            caret_accepted = accepted and bool(text.setCaretOffset(expected_caret))
            observed_count = int(text.characterCount)
            observed = (
                accepted
                and caret_accepted
                and observed_count == len(expected)
                and str(text.getText(0, observed_count)) == expected
                and int(text.caretOffset) == expected_caret
                and int(text.nSelections) == 0
            )
        except Exception as exc:
            observed = False
            failure = exc
        if not observed:
            if not restore_previous():
                raise GnomeAdapterError(
                    "Das fehlgeschlagene Ersetzen konnte nicht zurückgesetzt werden."
                ) from failure
            raise GnomeAdapterError("Das Ersetzen der Textauswahl konnte nicht bestätigt werden.") from failure
        return self._name(focused) or "Textfeld"

    def focused_text_character_at_caret(self, direction: str) -> Tuple[str, str]:
        """Read at most one safe AT-SPI character beside the caret."""

        if direction not in {"previous", "next"}:
            raise GnomeAdapterError("Unzulässige Richtung für die Zeichenausgabe.")
        _, window = self._active_window()
        focused = self._find_state(window, self._atspi.STATE_FOCUSED)
        if focused is None:
            raise GnomeAdapterError("Kein fokussiertes Textfeld gefunden.")
        role = self._role(focused).casefold()
        if role not in {"entry", "text", "document text"}:
            raise GnomeAdapterError("Das fokussierte Element ist kein lesbares Textfeld.")
        try:
            attributes = " ".join(str(item) for item in focused.getAttributes()).casefold()
        except Exception as exc:
            raise GnomeAdapterError("Die Schutzattribute des Textfelds sind nicht prüfbar.") from exc
        privacy = f"{role} {attributes}"
        if any(marker in privacy for marker in ("password", "passwort", "protected", "secret")):
            raise GnomeAdapterError("Aus geschützten Textfeldern werden keine Zeichen vorgelesen.")
        try:
            text = focused.queryText()
            count = int(text.characterCount)
            caret = int(text.caretOffset)
            if count < 0 or count > 100_000 or caret < 0 or caret > count:
                raise ValueError("invalid character read metadata")
            if (direction == "previous" and caret == 0) or (direction == "next" and caret == count):
                return self._name(focused) or "Textfeld", ""
            start = caret - 1 if direction == "previous" else caret
            value = str(text.getText(start, start + 1))
            if len(value) != 1 or "\x00" in value:
                raise ValueError("incomplete character read")
        except Exception as exc:
            raise GnomeAdapterError("Das Zeichen ist nicht sicher lesbar.") from exc
        return self._name(focused) or "Textfeld", value

    def focused_text_word_at_caret(self, direction: str) -> Tuple[str, str]:
        """Read one nearby word through bounded one-character AT-SPI reads."""

        if direction not in {"previous", "next"}:
            raise GnomeAdapterError("Unzulässige Richtung für die Wortausgabe.")
        _, window = self._active_window()
        focused = self._find_state(window, self._atspi.STATE_FOCUSED)
        if focused is None:
            raise GnomeAdapterError("Kein fokussiertes Textfeld gefunden.")
        role = self._role(focused).casefold()
        if role not in {"entry", "text", "document text"}:
            raise GnomeAdapterError("Das fokussierte Element ist kein lesbares Textfeld.")
        try:
            attributes = " ".join(str(item) for item in focused.getAttributes()).casefold()
        except Exception as exc:
            raise GnomeAdapterError("Die Schutzattribute des Textfelds sind nicht prüfbar.") from exc
        privacy = f"{role} {attributes}"
        if any(marker in privacy for marker in ("password", "passwort", "protected", "secret")):
            raise GnomeAdapterError("Aus geschützten Textfeldern werden keine Wörter vorgelesen.")
        try:
            text = focused.queryText()
            count = int(text.characterCount)
            caret = int(text.caretOffset)
            if count < 0 or count > 100_000 or caret < 0 or caret > count:
                raise ValueError("invalid word read metadata")
            inspected = 0

            def read_at(index: int) -> str:
                nonlocal inspected
                if inspected >= 256:
                    raise ValueError("word search limit exceeded")
                value = str(text.getText(index, index + 1))
                inspected += 1
                if len(value) != 1 or "\x00" in value:
                    raise ValueError("incomplete word read")
                return value

            def is_word(character: str) -> bool:
                return character.isalnum() or character in "_'-"

            characters = []
            if direction == "previous":
                index = caret - 1
                while index >= 0:
                    character = read_at(index)
                    if is_word(character):
                        break
                    index -= 1
                while index >= 0 and is_word(character):
                    characters.append(character)
                    if len(characters) > 128:
                        raise ValueError("word is too long")
                    index -= 1
                    if index >= 0:
                        character = read_at(index)
                characters.reverse()
            else:
                index = caret
                while index < count:
                    character = read_at(index)
                    if is_word(character):
                        break
                    index += 1
                while index < count and is_word(character):
                    characters.append(character)
                    if len(characters) > 128:
                        raise ValueError("word is too long")
                    index += 1
                    if index < count:
                        character = read_at(index)
        except Exception as exc:
            raise GnomeAdapterError("Das Wort ist innerhalb der sicheren Suchgrenze nicht lesbar.") from exc
        return self._name(focused) or "Textfeld", "".join(characters)

    def _focused_text_line_context(
        self, require_no_selection: bool = False
    ) -> Tuple[Any, Any, str, str, int, int, int, int]:
        """Bind and derive one line around the caret through one-character reads."""

        _, window = self._active_window()
        focused = self._find_state(window, self._atspi.STATE_FOCUSED)
        if focused is None:
            raise GnomeAdapterError("Kein fokussiertes Textfeld gefunden.")
        role = self._role(focused).casefold()
        if role not in {"entry", "text", "document text"}:
            raise GnomeAdapterError("Das fokussierte Element ist kein lesbares Textfeld.")
        try:
            attributes = " ".join(str(value) for value in focused.getAttributes()).casefold()
        except Exception as exc:
            raise GnomeAdapterError("Die Schutzattribute des Textfelds sind nicht prüfbar.") from exc
        privacy = f"{role} {attributes}"
        if any(marker in privacy for marker in ("password", "passwort", "protected", "secret")):
            raise GnomeAdapterError("Zeilen geschützter Textfelder werden nicht verarbeitet.")
        try:
            text = focused.queryText()
            count = int(text.characterCount)
            caret = int(text.caretOffset)
            selections = int(text.nSelections)
            if (
                count < 0
                or count > 100_000
                or caret < 0
                or caret > count
                or selections < 0
                or selections > 64
                or (require_no_selection and selections != 0)
            ):
                raise ValueError("invalid line metadata")

            def read_at(index: int) -> str:
                character = str(text.getText(index, index + 1))
                if len(character) != 1 or "\x00" in character:
                    raise ValueError("incomplete line read")
                return character

            left = []
            index = caret - 1
            while index >= 0:
                character = read_at(index)
                if character == "\n":
                    break
                left.append(character)
                if len(left) > 1_000:
                    raise ValueError("line is too long")
                index -= 1
            start = index + 1
            left.reverse()
            right = []
            index = caret
            while index < count:
                character = read_at(index)
                if character == "\n":
                    break
                right.append(character)
                if len(left) + len(right) > 1_000:
                    raise ValueError("line is too long")
                index += 1
            end = index
            value = "".join(left + right)
        except Exception as exc:
            raise GnomeAdapterError("Die aktuelle Zeile ist nicht sicher bestimmbar.") from exc
        return focused, text, self._name(focused) or "Textfeld", value, start, end, caret, selections

    def focused_text_line_at_caret(self) -> Tuple[str, str]:
        """Return one bounded current line for confirmed speech."""

        _focused, _text, name, value, _start, _end, _caret, _selections = (
            self._focused_text_line_context()
        )
        return name, value

    def move_focused_text_caret_line(self, boundary: str) -> str:
        """Move to the current line start or end and verify or restore."""

        if boundary not in {"start", "end"}:
            raise GnomeAdapterError("Unzulässige Zeilengrenze für den Textcursor.")
        focused, text, name, _value, start, end, previous, _selections = (
            self._focused_text_line_context(require_no_selection=True)
        )
        target = start if boundary == "start" else end
        if target == previous:
            return name
        failure = None
        try:
            accepted = bool(text.setCaretOffset(target))
            observed = int(text.caretOffset) == target and int(text.nSelections) == 0
        except Exception as exc:
            accepted = False
            observed = False
            failure = exc
        if not accepted or not observed:
            restored = False
            try:
                restored = (
                    bool(text.setCaretOffset(previous))
                    and int(text.caretOffset) == previous
                    and int(text.nSelections) == 0
                )
            except Exception:
                restored = False
            if not restored:
                raise GnomeAdapterError(
                    "Die fehlgeschlagene Zeilennavigation konnte nicht zurückgesetzt werden."
                ) from failure
            raise GnomeAdapterError("Die Zeilennavigation konnte nicht bestätigt werden.") from failure
        return self._name(focused) or name

    def select_focused_text_line(self) -> str:
        """Select the bounded current line and verify or restore cursor state."""

        focused, text, name, value, start, end, previous, _selections = (
            self._focused_text_line_context(require_no_selection=True)
        )
        if not value or end <= start:
            raise GnomeAdapterError("Die aktuelle Zeile ist leer und kann nicht ausgewählt werden.")
        failure = None
        try:
            accepted = bool(text.addSelection(start, end))
            caret_accepted = accepted and bool(text.setCaretOffset(end))
            observed = (
                accepted
                and caret_accepted
                and int(text.nSelections) == 1
                and tuple(map(int, text.getSelection(0))) == (start, end)
                and int(text.caretOffset) == end
            )
        except Exception as exc:
            observed = False
            failure = exc
        if not observed:
            restored = False
            try:
                for index in range(int(text.nSelections) - 1, -1, -1):
                    if not bool(text.removeSelection(index)):
                        raise RuntimeError("line selection rollback removal rejected")
                restored = (
                    int(text.nSelections) == 0
                    and bool(text.setCaretOffset(previous))
                    and int(text.caretOffset) == previous
                )
            except Exception:
                restored = False
            if not restored:
                raise GnomeAdapterError(
                    "Die fehlgeschlagene Zeilenauswahl konnte nicht zurückgesetzt werden."
                ) from failure
            raise GnomeAdapterError("Die Zeilenauswahl konnte nicht bestätigt werden.") from failure
        return self._name(focused) or name

    def delete_focused_text_line(self) -> str:
        """Delete exactly the current line and one delimiter, with rollback."""

        focused, text, name, value, start, end, previous_caret, _selections = (
            self._focused_text_line_context(require_no_selection=True)
        )
        if not value or end <= start:
            raise GnomeAdapterError("Die aktuelle Zeile ist leer und wird nicht gelöscht.")
        try:
            editable = focused.queryEditableText()
            count = int(text.characterCount)
            previous = str(text.getText(0, count))
            if len(previous) != count or "\x00" in previous:
                raise ValueError("incomplete line deletion snapshot")
            if end < count:
                delete_start, delete_end = start, end + 1
            elif start > 0:
                delete_start, delete_end = start - 1, end
            else:
                delete_start, delete_end = start, end
            expected = previous[:delete_start] + previous[delete_end:]
            expected_caret = delete_start
        except Exception as exc:
            raise GnomeAdapterError("Die aktuelle Zeile ist nicht sicher löschbar.") from exc

        def restore_previous() -> bool:
            try:
                if not bool(editable.setTextContents(previous)):
                    return False
                for index in range(int(text.nSelections) - 1, -1, -1):
                    if not bool(text.removeSelection(index)):
                        return False
                return (
                    int(text.characterCount) == count
                    and str(text.getText(0, count)) == previous
                    and bool(text.setCaretOffset(previous_caret))
                    and int(text.caretOffset) == previous_caret
                    and int(text.nSelections) == 0
                )
            except Exception:
                return False

        failure = None
        try:
            accepted = bool(editable.deleteText(delete_start, delete_end))
            observed_count = int(text.characterCount)
            observed = (
                accepted
                and observed_count == len(expected)
                and str(text.getText(0, observed_count)) == expected
                and int(text.caretOffset) == expected_caret
                and int(text.nSelections) == 0
            )
        except Exception as exc:
            observed = False
            failure = exc
        if not observed:
            if not restore_previous():
                raise GnomeAdapterError(
                    "Das fehlgeschlagene Löschen der Zeile konnte nicht zurückgesetzt werden."
                ) from failure
            raise GnomeAdapterError("Das Löschen der Zeile konnte nicht bestätigt werden.") from failure
        return self._name(focused) or name

    def replace_focused_text_line(self, value: str) -> str:
        """Replace the bounded current line and verify or restore full state."""

        if not value or len(value) > 500 or any(not character.isprintable() for character in value):
            raise GnomeAdapterError("Der Ersatztext muss 1 bis 500 druckbare Zeichen enthalten.")
        focused, text, name, current, start, end, previous_caret, _selections = (
            self._focused_text_line_context(require_no_selection=True)
        )
        if not current or end <= start:
            raise GnomeAdapterError("Die aktuelle Zeile ist leer und wird nicht ersetzt.")
        try:
            editable = focused.queryEditableText()
            count = int(text.characterCount)
            previous = str(text.getText(0, count))
            if len(previous) != count or "\x00" in previous:
                raise ValueError("incomplete line replacement snapshot")
            expected = previous[:start] + value + previous[end:]
            if len(expected) > 100_000:
                raise ValueError("line replacement result too large")
            expected_caret = start + len(value)
        except Exception as exc:
            raise GnomeAdapterError("Die aktuelle Zeile ist nicht sicher ersetzbar.") from exc

        def restore_previous() -> bool:
            try:
                if not bool(editable.setTextContents(previous)):
                    return False
                for index in range(int(text.nSelections) - 1, -1, -1):
                    if not bool(text.removeSelection(index)):
                        return False
                return (
                    int(text.characterCount) == count
                    and str(text.getText(0, count)) == previous
                    and bool(text.setCaretOffset(previous_caret))
                    and int(text.caretOffset) == previous_caret
                    and int(text.nSelections) == 0
                )
            except Exception:
                return False

        failure = None
        try:
            accepted = bool(editable.setTextContents(expected))
            caret_accepted = accepted and bool(text.setCaretOffset(expected_caret))
            observed_count = int(text.characterCount)
            observed = (
                accepted
                and caret_accepted
                and observed_count == len(expected)
                and str(text.getText(0, observed_count)) == expected
                and int(text.caretOffset) == expected_caret
                and int(text.nSelections) == 0
            )
        except Exception as exc:
            observed = False
            failure = exc
        if not observed:
            if not restore_previous():
                raise GnomeAdapterError(
                    "Das fehlgeschlagene Ersetzen der Zeile konnte nicht zurückgesetzt werden."
                ) from failure
            raise GnomeAdapterError("Das Ersetzen der Zeile konnte nicht bestätigt werden.") from failure
        return self._name(focused) or name

    def insert_focused_text_line(self, direction: str, value: str) -> str:
        """Insert one bounded line above or below the caret line with rollback."""

        if direction not in {"above", "below"}:
            raise GnomeAdapterError("Unzulässige Richtung für die neue Zeile.")
        if not value or len(value) > 500 or any(not character.isprintable() for character in value):
            raise GnomeAdapterError("Die neue Zeile muss 1 bis 500 druckbare Zeichen enthalten.")
        focused, text, name, _current, start, end, previous_caret, _selections = (
            self._focused_text_line_context(require_no_selection=True)
        )
        try:
            editable = focused.queryEditableText()
            count = int(text.characterCount)
            previous = str(text.getText(0, count))
            if len(previous) != count or "\x00" in previous:
                raise ValueError("incomplete line insertion snapshot")
            if count == 0:
                expected = value
                expected_caret = len(value)
            elif direction == "above":
                expected = previous[:start] + value + "\n" + previous[start:]
                expected_caret = start + len(value)
            else:
                expected = previous[:end] + "\n" + value + previous[end:]
                expected_caret = end + 1 + len(value)
            if len(expected) > 100_000:
                raise ValueError("line insertion result too large")
        except Exception as exc:
            raise GnomeAdapterError("Die neue Zeile ist nicht sicher einfügbar.") from exc

        def restore_previous() -> bool:
            try:
                if not bool(editable.setTextContents(previous)):
                    return False
                for index in range(int(text.nSelections) - 1, -1, -1):
                    if not bool(text.removeSelection(index)):
                        return False
                return (
                    int(text.characterCount) == count
                    and str(text.getText(0, count)) == previous
                    and bool(text.setCaretOffset(previous_caret))
                    and int(text.caretOffset) == previous_caret
                    and int(text.nSelections) == 0
                )
            except Exception:
                return False

        failure = None
        try:
            accepted = bool(editable.setTextContents(expected))
            caret_accepted = accepted and bool(text.setCaretOffset(expected_caret))
            observed_count = int(text.characterCount)
            observed = (
                accepted
                and caret_accepted
                and observed_count == len(expected)
                and str(text.getText(0, observed_count)) == expected
                and int(text.caretOffset) == expected_caret
                and int(text.nSelections) == 0
            )
        except Exception as exc:
            observed = False
            failure = exc
        if not observed:
            if not restore_previous():
                raise GnomeAdapterError(
                    "Das fehlgeschlagene Einfügen der Zeile konnte nicht zurückgesetzt werden."
                ) from failure
            raise GnomeAdapterError("Das Einfügen der Zeile konnte nicht bestätigt werden.") from failure
        return self._name(focused) or name

    def duplicate_focused_text_line(self, direction: str) -> str:
        """Duplicate the bounded current line above or below with rollback."""

        if direction not in {"above", "below"}:
            raise GnomeAdapterError("Unzulässige Richtung für die Zeilenduplizierung.")
        focused, text, name, current, start, end, previous_caret, _selections = (
            self._focused_text_line_context(require_no_selection=True)
        )
        if not current or end <= start:
            raise GnomeAdapterError("Die aktuelle Zeile ist leer und wird nicht dupliziert.")
        try:
            editable = focused.queryEditableText()
            count = int(text.characterCount)
            previous = str(text.getText(0, count))
            if len(previous) != count or "\x00" in previous:
                raise ValueError("incomplete line duplication snapshot")
            if direction == "above":
                expected = previous[:start] + current + "\n" + previous[start:]
                expected_caret = start + len(current)
            else:
                expected = previous[:end] + "\n" + current + previous[end:]
                expected_caret = end + 1 + len(current)
            if len(expected) > 100_000:
                raise ValueError("line duplication result too large")
        except Exception as exc:
            raise GnomeAdapterError("Die aktuelle Zeile ist nicht sicher duplizierbar.") from exc

        def restore_previous() -> bool:
            try:
                if not bool(editable.setTextContents(previous)):
                    return False
                for index in range(int(text.nSelections) - 1, -1, -1):
                    if not bool(text.removeSelection(index)):
                        return False
                return (
                    int(text.characterCount) == count
                    and str(text.getText(0, count)) == previous
                    and bool(text.setCaretOffset(previous_caret))
                    and int(text.caretOffset) == previous_caret
                    and int(text.nSelections) == 0
                )
            except Exception:
                return False

        failure = None
        try:
            accepted = bool(editable.setTextContents(expected))
            caret_accepted = accepted and bool(text.setCaretOffset(expected_caret))
            observed_count = int(text.characterCount)
            observed = (
                accepted
                and caret_accepted
                and observed_count == len(expected)
                and str(text.getText(0, observed_count)) == expected
                and int(text.caretOffset) == expected_caret
                and int(text.nSelections) == 0
            )
        except Exception as exc:
            observed = False
            failure = exc
        if not observed:
            if not restore_previous():
                raise GnomeAdapterError(
                    "Die fehlgeschlagene Zeilenduplizierung konnte nicht zurückgesetzt werden."
                ) from failure
            raise GnomeAdapterError("Die Zeilenduplizierung konnte nicht bestätigt werden.") from failure
        return self._name(focused) or name

    def move_focused_text_line(self, direction: str) -> str:
        """Swap the bounded current line with one adjacent line and roll back."""

        if direction not in {"up", "down"}:
            raise GnomeAdapterError("Unzulässige Richtung für das Verschieben der Zeile.")
        focused, text, name, current, start, end, previous_caret, _selections = (
            self._focused_text_line_context(require_no_selection=True)
        )
        try:
            editable = focused.queryEditableText()
            count = int(text.characterCount)
            previous = str(text.getText(0, count))
            if len(previous) != count or "\x00" in previous:
                raise ValueError("incomplete line move snapshot")
            relative_caret = previous_caret - start
            if direction == "up":
                if start == 0:
                    raise GnomeAdapterError("Oberhalb der aktuellen Zeile gibt es keine Zeile.")
                previous_end = start - 1
                previous_start = previous.rfind("\n", 0, previous_end) + 1
                adjacent = previous[previous_start:previous_end]
                if len(adjacent) > 1_000:
                    raise ValueError("adjacent line is too long")
                expected = (
                    previous[:previous_start]
                    + current
                    + "\n"
                    + adjacent
                    + previous[end:]
                )
                expected_caret = previous_start + relative_caret
            else:
                if end >= count:
                    raise GnomeAdapterError("Unterhalb der aktuellen Zeile gibt es keine Zeile.")
                next_start = end + 1
                delimiter = previous.find("\n", next_start)
                next_end = count if delimiter < 0 else delimiter
                adjacent = previous[next_start:next_end]
                if len(adjacent) > 1_000:
                    raise ValueError("adjacent line is too long")
                expected = previous[:start] + adjacent + "\n" + current + previous[next_end:]
                expected_caret = start + len(adjacent) + 1 + relative_caret
        except GnomeAdapterError:
            raise
        except Exception as exc:
            raise GnomeAdapterError("Die aktuelle Zeile ist nicht sicher verschiebbar.") from exc

        def restore_previous() -> bool:
            try:
                if not bool(editable.setTextContents(previous)):
                    return False
                for index in range(int(text.nSelections) - 1, -1, -1):
                    if not bool(text.removeSelection(index)):
                        return False
                return (
                    int(text.characterCount) == count
                    and str(text.getText(0, count)) == previous
                    and bool(text.setCaretOffset(previous_caret))
                    and int(text.caretOffset) == previous_caret
                    and int(text.nSelections) == 0
                )
            except Exception:
                return False

        failure = None
        try:
            accepted = bool(editable.setTextContents(expected))
            caret_accepted = accepted and bool(text.setCaretOffset(expected_caret))
            observed_count = int(text.characterCount)
            observed = (
                accepted
                and caret_accepted
                and observed_count == len(expected)
                and str(text.getText(0, observed_count)) == expected
                and int(text.caretOffset) == expected_caret
                and int(text.nSelections) == 0
            )
        except Exception as exc:
            observed = False
            failure = exc
        if not observed:
            if not restore_previous():
                raise GnomeAdapterError(
                    "Das fehlgeschlagene Verschieben der Zeile konnte nicht zurückgesetzt werden."
                ) from failure
            raise GnomeAdapterError("Das Verschieben der Zeile konnte nicht bestätigt werden.") from failure
        return self._name(focused) or name

    def join_focused_text_line(self, direction: str) -> str:
        """Join the current line with one bounded neighbor by deleting one newline."""

        if direction not in {"previous", "next"}:
            raise GnomeAdapterError("Unzulässige Richtung für das Verbinden der Zeilen.")
        focused, text, name, current, start, end, previous_caret, _selections = (
            self._focused_text_line_context(require_no_selection=True)
        )
        try:
            editable = focused.queryEditableText()
            count = int(text.characterCount)
            previous = str(text.getText(0, count))
            if len(previous) != count or "\x00" in previous:
                raise ValueError("incomplete line join snapshot")
            if direction == "previous":
                if start == 0:
                    raise GnomeAdapterError("Vor der aktuellen Zeile gibt es keinen Zeilenumbruch.")
                adjacent_end = start - 1
                adjacent_start = previous.rfind("\n", 0, adjacent_end) + 1
                adjacent = previous[adjacent_start:adjacent_end]
                delimiter = start - 1
                expected_caret = previous_caret - 1
            else:
                if end >= count:
                    raise GnomeAdapterError("Nach der aktuellen Zeile gibt es keinen Zeilenumbruch.")
                adjacent_start = end + 1
                found = previous.find("\n", adjacent_start)
                adjacent_end = count if found < 0 else found
                adjacent = previous[adjacent_start:adjacent_end]
                delimiter = end
                expected_caret = previous_caret
            if len(adjacent) > 1_000 or len(current) + len(adjacent) > 2_000:
                raise ValueError("joined line is too long")
            expected = previous[:delimiter] + previous[delimiter + 1 :]
        except GnomeAdapterError:
            raise
        except Exception as exc:
            raise GnomeAdapterError("Die Zeilen sind nicht sicher verbindbar.") from exc

        def restore_previous() -> bool:
            try:
                if not bool(editable.setTextContents(previous)):
                    return False
                for index in range(int(text.nSelections) - 1, -1, -1):
                    if not bool(text.removeSelection(index)):
                        return False
                return (
                    int(text.characterCount) == count
                    and str(text.getText(0, count)) == previous
                    and bool(text.setCaretOffset(previous_caret))
                    and int(text.caretOffset) == previous_caret
                    and int(text.nSelections) == 0
                )
            except Exception:
                return False

        failure = None
        try:
            accepted = bool(editable.deleteText(delimiter, delimiter + 1))
            caret_accepted = accepted and bool(text.setCaretOffset(expected_caret))
            observed_count = int(text.characterCount)
            observed = (
                accepted
                and caret_accepted
                and observed_count == len(expected)
                and str(text.getText(0, observed_count)) == expected
                and int(text.caretOffset) == expected_caret
                and int(text.nSelections) == 0
            )
        except Exception as exc:
            observed = False
            failure = exc
        if not observed:
            if not restore_previous():
                raise GnomeAdapterError(
                    "Das fehlgeschlagene Verbinden der Zeilen konnte nicht zurückgesetzt werden."
                ) from failure
            raise GnomeAdapterError("Das Verbinden der Zeilen konnte nicht bestätigt werden.") from failure
        return self._name(focused) or name

    def split_focused_text_line(self) -> str:
        """Split the bounded current line at the caret by inserting one newline."""

        focused, text, name, _current, _start, _end, previous_caret, _selections = (
            self._focused_text_line_context(require_no_selection=True)
        )
        try:
            editable = focused.queryEditableText()
            count = int(text.characterCount)
            previous = str(text.getText(0, count))
            if len(previous) != count or "\x00" in previous or count >= 100_000:
                raise ValueError("incomplete or oversized line split snapshot")
            expected = previous[:previous_caret] + "\n" + previous[previous_caret:]
            expected_caret = previous_caret + 1
        except Exception as exc:
            raise GnomeAdapterError("Die aktuelle Zeile ist nicht sicher teilbar.") from exc

        def restore_previous() -> bool:
            try:
                if not bool(editable.setTextContents(previous)):
                    return False
                for index in range(int(text.nSelections) - 1, -1, -1):
                    if not bool(text.removeSelection(index)):
                        return False
                return (
                    int(text.characterCount) == count
                    and str(text.getText(0, count)) == previous
                    and bool(text.setCaretOffset(previous_caret))
                    and int(text.caretOffset) == previous_caret
                    and int(text.nSelections) == 0
                )
            except Exception:
                return False

        failure = None
        try:
            accepted = bool(editable.insertText(previous_caret, "\n", 1))
            caret_accepted = accepted and bool(text.setCaretOffset(expected_caret))
            observed_count = int(text.characterCount)
            observed = (
                accepted
                and caret_accepted
                and observed_count == len(expected)
                and str(text.getText(0, observed_count)) == expected
                and int(text.caretOffset) == expected_caret
                and int(text.nSelections) == 0
            )
        except Exception as exc:
            observed = False
            failure = exc
        if not observed:
            if not restore_previous():
                raise GnomeAdapterError(
                    "Das fehlgeschlagene Teilen der Zeile konnte nicht zur\u00fcckgesetzt werden."
                ) from failure
            raise GnomeAdapterError("Das Teilen der Zeile konnte nicht best\u00e4tigt werden.") from failure
        return self._name(focused) or name

    def indent_focused_text_line(self, direction: str) -> str:
        """Indent or outdent the bounded current line and verify exact state."""

        if direction not in {"indent", "outdent"}:
            raise GnomeAdapterError("Unzulässige Richtung für die Zeileneinrückung.")
        focused, text, name, current, start, _end, previous_caret, _selections = (
            self._focused_text_line_context(require_no_selection=True)
        )
        try:
            editable = focused.queryEditableText()
            count = int(text.characterCount)
            previous = str(text.getText(0, count))
            if len(previous) != count or "\x00" in previous:
                raise ValueError("incomplete line indentation snapshot")
            if direction == "indent":
                if len(current) > 996 or count > 99_996:
                    raise ValueError("indented line or field would be too long")
                expected = previous[:start] + "    " + previous[start:]
                expected_caret = previous_caret + 4
                mutation = ("insert", start, start + 4)
            else:
                if current.startswith("\t"):
                    width = 1
                else:
                    width = min(4, len(current) - len(current.lstrip(" ")))
                if width == 0:
                    raise GnomeAdapterError("Die aktuelle Zeile ist nicht eingerückt.")
                expected = previous[:start] + previous[start + width :]
                expected_caret = max(start, previous_caret - width)
                mutation = ("delete", start, start + width)
        except GnomeAdapterError:
            raise
        except Exception as exc:
            raise GnomeAdapterError("Die aktuelle Zeile ist nicht sicher einrückbar.") from exc

        def restore_previous() -> bool:
            try:
                if not bool(editable.setTextContents(previous)):
                    return False
                for index in range(int(text.nSelections) - 1, -1, -1):
                    if not bool(text.removeSelection(index)):
                        return False
                return (
                    int(text.characterCount) == count
                    and str(text.getText(0, count)) == previous
                    and bool(text.setCaretOffset(previous_caret))
                    and int(text.caretOffset) == previous_caret
                    and int(text.nSelections) == 0
                )
            except Exception:
                return False

        failure = None
        try:
            if mutation[0] == "insert":
                accepted = bool(editable.insertText(mutation[1], "    ", 4))
            else:
                accepted = bool(editable.deleteText(mutation[1], mutation[2]))
            caret_accepted = accepted and bool(text.setCaretOffset(expected_caret))
            observed_count = int(text.characterCount)
            observed = (
                accepted
                and caret_accepted
                and observed_count == len(expected)
                and str(text.getText(0, observed_count)) == expected
                and int(text.caretOffset) == expected_caret
                and int(text.nSelections) == 0
            )
        except Exception as exc:
            observed = False
            failure = exc
        if not observed:
            if not restore_previous():
                raise GnomeAdapterError(
                    "Die fehlgeschlagene Zeileneinrückung konnte nicht zurückgesetzt werden."
                ) from failure
            raise GnomeAdapterError("Die Zeileneinrückung konnte nicht bestätigt werden.") from failure
        return self._name(focused) or name

    def set_focused_text(self, value: str) -> str:
        """Replace focused editable text and verify it without speaking it back."""

        if len(value) > 500 or any(ord(character) < 32 for character in value):
            raise GnomeAdapterError("Der Text ist nicht als sichere Einzeleingabe erlaubt.")
        _, window = self._active_window()
        node = self._find_state(window, self._atspi.STATE_FOCUSED)
        if node is None:
            raise GnomeAdapterError("Kein fokussiertes Textfeld gefunden.")
        return self._set_text_node(node, value)

    def set_focused_clipboard_text(self, value: str) -> str:
        """Replace focused text exactly, allowing only tab/newline controls."""

        if (
            not isinstance(value, str)
            or not value
            or len(value) > 100_000
            or any(ord(character) < 32 and character not in "\t\n" for character in value)
            or "\x7f" in value
        ):
            raise GnomeAdapterError("Der Zwischenablageinhalt ist nicht als sicherer Text erlaubt.")
        _, window = self._active_window()
        node = self._find_state(window, self._atspi.STATE_FOCUSED)
        if node is None:
            raise GnomeAdapterError("Kein fokussiertes Textfeld gefunden.")
        return self._set_text_node(node, value)

    def _set_text_node(self, node: Any, value: str) -> str:
        """Mutate the already-bound node so dialog checks cannot race a window switch."""

        role = self._role(node).casefold()
        if not role:
            raise GnomeAdapterError("Die Art des fokussierten Feldes ist nicht pr\u00fcfbar.")
        try:
            attributes = " ".join(node.getAttributes()).casefold()
        except Exception as exc:
            raise GnomeAdapterError(
                "Die Sicherheitseigenschaften des Textfeldes sind nicht pr\u00fcfbar."
            ) from exc
        sensitive_markers = ("password", "passwort", "protected", "secret")
        if any(marker in role or marker in attributes for marker in sensitive_markers):
            raise GnomeAdapterError(
                "Passwort- und gesch\u00fctzte Felder d\u00fcrfen nicht per Sprache bef\u00fcllt werden."
            )
        try:
            editable = node.queryEditableText()
            text = node.queryText()
            previous = text.getText(0, -1)
        except Exception as exc:
            raise GnomeAdapterError(
                "Das fokussierte Element ist nicht sicher editierbar."
            ) from exc

        def restore_previous() -> bool:
            try:
                return bool(editable.setTextContents(previous)) and text.getText(0, -1) == previous
            except Exception:
                return False

        try:
            accepted = bool(editable.setTextContents(value))
            observed = text.getText(0, -1)
        except Exception as exc:
            if not restore_previous():
                raise GnomeAdapterError(
                    "Die fehlgeschlagene Texteingabe konnte nicht zur\u00fcckgesetzt werden."
                ) from exc
            raise GnomeAdapterError("Die Texteingabe ist fehlgeschlagen.") from exc
        if not accepted:
            if not restore_previous():
                raise GnomeAdapterError(
                    "Die abgelehnte Texteingabe konnte nicht zur\u00fcckgesetzt werden."
                )
            raise GnomeAdapterError("Das Textfeld hat die Eingabe abgelehnt.")
        if observed != value:
            if not restore_previous():
                raise GnomeAdapterError(
                    "Die Texteingabe war inkonsistent und konnte nicht zur\u00fcckgesetzt werden."
                )
            raise GnomeAdapterError("Die Texteingabe konnte nicht best\u00e4tigt werden.")
        return self._name(node) or "Textfeld"

    def select_named_item(self, name: str) -> str:
        """Select one exact item in the focused AT-SPI Selection container."""

        normalized = " ".join(name.split()).casefold()
        if not normalized or len(normalized) > 120:
            raise GnomeAdapterError("Der Name des Listeneintrags ist ung\u00fcltig.")
        _, window = self._active_window()
        focused = self._find_state(window, self._atspi.STATE_FOCUSED)
        if focused is None:
            raise GnomeAdapterError("Kein fokussierter Auswahlbereich gefunden.")
        container = focused
        selection = None
        for _depth in range(12):
            try:
                selection = container.querySelection()
                break
            except Exception:
                pass
            if container is window:
                break
            try:
                container = container.parent
            except Exception:
                container = None
            if container is None:
                break
        if selection is None:
            raise GnomeAdapterError("Der Fokus liegt nicht in einer semantischen Auswahlliste.")
        return self._select_container_item(container, selection, normalized)

    def select_visible_file(self, name: str) -> str:
        """Select one visible item in an exact, recognized active file chooser."""

        normalized = " ".join(name.split()).casefold()
        if (
            not normalized
            or len(normalized) > 255
            or "/" in normalized
            or normalized in {".", ".."}
        ):
            raise GnomeAdapterError("Der Datei- oder Ordnername ist ung\u00fcltig.")
        _, window = self._active_window()
        role = self._role(window).casefold()
        title = self._name(window).casefold()
        title_markers = (
            "open",
            "open file",
            "save",
            "save file",
            "select file",
            "select folder",
            "choose file",
            "choose folder",
            "\u00f6ffnen",
            "datei \u00f6ffnen",
            "speichern",
            "datei speichern",
            "datei ausw\u00e4hlen",
            "ordner ausw\u00e4hlen",
        )
        recognized = "file chooser" in role or title in title_markers
        if not recognized:
            raise GnomeAdapterError("Das aktive Fenster ist kein erkannter Dateiauswahldialog.")
        control_names = {self._name(node).casefold() for node, _actions in self._controls(window)}
        accept_names = {
            "open",
            "save",
            "select",
            "choose",
            "\u00f6ffnen",
            "speichern",
            "ausw\u00e4hlen",
        }
        cancel_names = {"cancel", "abbrechen"}
        if not control_names.intersection(accept_names) or not control_names.intersection(
            cancel_names
        ):
            raise GnomeAdapterError(
                "Der Dateidialog bietet keine eindeutigen Best\u00e4tigen-/Abbrechen-Aktionen."
            )
        candidates = []
        for node in self._walk(window):
            try:
                selection = node.querySelection()
            except Exception:
                continue
            children = list(self._children(node))
            if any(self._name(child).casefold() == normalized for child in children):
                candidates.append((node, selection))
        if not candidates:
            raise GnomeAdapterError("Die sichtbare Datei oder der Ordner wurde nicht gefunden.")
        if len(candidates) != 1:
            raise GnomeAdapterError("Das sichtbare Datei- oder Ordnerziel ist nicht eindeutig.")
        return self._select_container_item(*candidates[0], normalized)

    def set_file_name(self, name: str) -> str:
        """Set, but never commit, one file name in a recognized save dialog."""

        normalized = " ".join(name.split())
        if (
            not normalized
            or len(normalized) > 255
            or "/" in normalized
            or normalized in {".", ".."}
        ):
            raise GnomeAdapterError("Der Dateiname ist ung\u00fcltig.")
        _, window = self._active_window()
        role = self._role(window).casefold()
        title = self._name(window).casefold()
        save_titles = {"save", "save file", "speichern", "datei speichern"}
        if "file chooser" not in role and title not in save_titles:
            raise GnomeAdapterError("Das aktive Fenster ist kein erkannter Speichern-Dialog.")
        controls = self._controls(window)
        control_names = {self._name(node).casefold() for node, _actions in controls}
        if not control_names.intersection({"save", "speichern"}) or not control_names.intersection(
            {"cancel", "abbrechen"}
        ):
            raise GnomeAdapterError(
                "Der Speichern-Dialog bietet keine getrennten Speichern-/Abbrechen-Aktionen."
            )
        focused = self._find_state(window, self._atspi.STATE_FOCUSED)
        if focused is None:
            raise GnomeAdapterError("Kein fokussiertes Dateinamensfeld gefunden.")
        field_name = self._name(focused).casefold().rstrip(":")
        allowed_fields = {"name", "file name", "filename", "dateiname"}
        if field_name not in allowed_fields:
            raise GnomeAdapterError("Der Fokus liegt nicht im erkannten Dateinamensfeld.")
        result = self._set_text_node(focused, normalized)
        return result

    def set_file_location(self, path: str) -> str:
        """Set, but never submit, an absolute location in a recognized file chooser."""

        if (
            not path
            or len(path) > 4096
            or not path.startswith("/")
            or path.startswith("//")
            or "//" in path
            or any(ord(character) < 32 for character in path)
            or any(part in {".", ".."} for part in path.split("/"))
        ):
            raise GnomeAdapterError("Der Pfad muss absolut und kanonisch sein.")
        _, window = self._active_window()
        role = self._role(window).casefold()
        title = self._name(window).casefold()
        title_markers = {
            "open",
            "open file",
            "save",
            "save file",
            "select file",
            "select folder",
            "choose file",
            "choose folder",
            "öffnen",
            "datei öffnen",
            "speichern",
            "datei speichern",
            "datei auswählen",
            "ordner auswählen",
        }
        if "file chooser" not in role and title not in title_markers:
            raise GnomeAdapterError("Das aktive Fenster ist kein erkannter Dateiauswahldialog.")
        controls = self._controls(window)
        control_names = {self._name(node).casefold() for node, _actions in controls}
        accept_names = {
            "open",
            "save",
            "select",
            "choose",
            "öffnen",
            "speichern",
            "auswählen",
        }
        if not control_names.intersection(accept_names) or not control_names.intersection(
            {"cancel", "abbrechen"}
        ):
            raise GnomeAdapterError(
                "Der Dateidialog bietet keine getrennten Bestätigen-/Abbrechen-Aktionen."
            )
        focused = self._find_state(window, self._atspi.STATE_FOCUSED)
        if focused is None:
            raise GnomeAdapterError("Kein fokussiertes Pfadfeld gefunden.")
        field_name = self._name(focused).casefold().rstrip(":")
        if field_name not in {"location", "path", "ort", "pfad"}:
            raise GnomeAdapterError("Der Fokus liegt nicht im erkannten Pfadfeld.")
        return self._set_text_node(focused, path)

    def open_visible_folder(self, name: str) -> str:
        """Navigate into one semantically proven visible folder without accepting the dialog."""

        normalized = " ".join(name.split()).casefold()
        if (
            not normalized
            or len(normalized) > 255
            or "/" in normalized
            or normalized in {".", ".."}
        ):
            raise GnomeAdapterError("Der sichtbare Ordnername ist ungültig.")
        _, window = self._active_window()
        role = self._role(window).casefold()
        title = self._name(window).casefold()
        title_markers = {
            "open", "open file", "save", "save file", "select file", "select folder",
            "choose file", "choose folder", "öffnen", "datei öffnen", "speichern",
            "datei speichern", "datei auswählen", "ordner auswählen",
        }
        if "file chooser" not in role and title not in title_markers:
            raise GnomeAdapterError("Das aktive Fenster ist kein erkannter Dateiauswahldialog.")
        controls = self._controls(window)
        control_names = {self._name(node).casefold() for node, _actions in controls}
        accept_names = {
            "open", "save", "select", "choose", "öffnen", "speichern", "auswählen",
        }
        if not control_names.intersection(accept_names) or not control_names.intersection(
            {"cancel", "abbrechen"}
        ):
            raise GnomeAdapterError(
                "Der Dateidialog bietet keine getrennten Bestätigen-/Abbrechen-Aktionen."
            )
        candidates = []
        for container in self._walk(window):
            try:
                container.querySelection()
            except Exception:
                continue
            candidates.extend(
                child
                for child in self._children(container)
                if self._name(child).casefold() == normalized
            )
        if not candidates:
            raise GnomeAdapterError("Der sichtbare Ordner wurde nicht gefunden.")
        if len(candidates) != 1:
            raise GnomeAdapterError("Der sichtbare Ordnername ist nicht eindeutig.")
        folder = candidates[0]
        if not self._is_semantic_folder(folder):
            raise GnomeAdapterError("Das sichtbare Ziel ist nicht sicher als Ordner erkennbar.")
        try:
            action = folder.queryAction()
            actions = tuple(action.getName(index) for index in range(action.nActions))
        except Exception as exc:
            raise GnomeAdapterError("Der Ordner bietet keine semantische Navigationsaktion.") from exc
        chosen = next(
            (
                index
                for wanted in ("open", "activate")
                for index, action_name in enumerate(actions)
                if action_name.casefold() == wanted
            ),
            None,
        )
        if chosen is None:
            raise GnomeAdapterError("Der Ordner bietet keine exakte Open-/Activate-Aktion.")
        if not action.doAction(chosen):
            raise GnomeAdapterError("Der Ordner hat die Navigation abgelehnt.")
        return self._name(folder) or "Ordner"

    def decide_file_dialog(self, decision: str) -> str:
        """Accept or cancel one exact recognized file chooser action pair."""

        normalized = decision.casefold()
        if normalized not in {"accept", "cancel"}:
            raise GnomeAdapterError("Unbekannte Dateidialogentscheidung.")
        application, window = self._active_window()
        title_markers = {
            "open", "open file", "save", "save file", "select file", "select folder",
            "choose file", "choose folder", "öffnen", "datei öffnen", "speichern",
            "datei speichern", "datei auswählen", "ordner auswählen",
        }

        def recognized_file_dialog(candidate: Any) -> bool:
            role = self._role(candidate).casefold()
            title = self._name(candidate).casefold()
            return "file chooser" in role or (
                role in {"dialog", "alert", "alert dialog"} and title in title_markers
            )

        def top_level_windows(candidate: Any) -> Tuple[Any, ...]:
            try:
                children = tuple(
                    candidate.getChildAtIndex(index)
                    for index in range(int(candidate.childCount))
                )
            except Exception as exc:
                raise GnomeAdapterError(
                    "Die Fensterliste der gebundenen Anwendung ist nicht lesbar."
                ) from exc
            return tuple(
                child
                for child in children
                if child is not None
                and self._role(child).casefold()
                in {"frame", "dialog", "alert", "alert dialog", "window", "file chooser"}
            )

        if not recognized_file_dialog(window):
            raise GnomeAdapterError("Das aktive Fenster ist kein erkannter Dateiauswahldialog.")

        accept_names = {
            "open", "save", "select", "choose", "öffnen", "speichern", "auswählen",
        }
        cancel_names = {"cancel", "abbrechen"}

        def bind_pair(
            controls: Sequence[Tuple[Any, Sequence[str]]],
        ) -> dict[str, Tuple[Any, Sequence[str]]]:
            accepted = [
                item for item in controls
                if self._name(item[0]).casefold() in accept_names
            ]
            cancelled = [
                item for item in controls
                if self._name(item[0]).casefold() in cancel_names
            ]
            if len(accepted) != 1 or len(cancelled) != 1:
                raise GnomeAdapterError(
                    "Der Dateidialog bietet kein eindeutiges Bestätigen-/Abbrechen-Paar."
                )
            for _node, actions in (accepted[0], cancelled[0]):
                allowed = [
                    name for name in actions
                    if str(name).casefold() in {"click", "press", "activate"}
                ]
                if len(allowed) != 1:
                    raise GnomeAdapterError(
                        "Der Dateidialog bietet keine eindeutigen semantischen Abschlussaktionen."
                    )
            return {"accept": accepted[0], "cancel": cancelled[0]}

        bound = bind_pair(self._controls(window))
        windows = top_level_windows(application)
        if sum(candidate is window for candidate in windows) != 1:
            raise GnomeAdapterError(
                "Der Dateidialog ist nicht eindeutig an seine Anwendung gebunden."
            )
        rebound_application, rebound_window = self._active_window()
        if rebound_application is not application or rebound_window is not window:
            raise GnomeAdapterError(
                "Der Dateidialog hat vor der Entscheidung gewechselt; es wurde nichts ausgeführt."
            )
        if not recognized_file_dialog(rebound_window):
            raise GnomeAdapterError("Das aktive Fenster ist nicht mehr als Dateidialog gebunden.")
        rebound_windows = top_level_windows(rebound_application)
        if len(rebound_windows) != len(windows) or any(
            current is not previous for current, previous in zip(rebound_windows, windows)
        ):
            raise GnomeAdapterError(
                "Die Fensterliste der Anwendung hat sich vor der Dateidialogentscheidung "
                "geändert; es wurde nichts ausgeführt."
            )
        rebound = bind_pair(self._controls(rebound_window))
        if any(rebound[key][0] is not bound[key][0] for key in ("accept", "cancel")):
            raise GnomeAdapterError(
                "Das Bestätigen-/Abbrechen-Paar hat sich vor der Entscheidung geändert; "
                "es wurde nichts ausgeführt."
            )
        control = self._invoke_control(*rebound[normalized])
        expected = tuple(candidate for candidate in windows if candidate is not window)
        deadline = time.monotonic() + 2.0
        while True:
            try:
                observed = top_level_windows(application)
            except GnomeAdapterError:
                observed = None
            if observed is not None and len(observed) == len(expected) and all(
                current is previous for current, previous in zip(observed, expected)
            ):
                return control
            if time.monotonic() >= deadline:
                break
            time.sleep(0.05)
        raise GnomeAdapterError(
            "Die Dateidialogentscheidung wurde ausgelöst, aber der exakte "
            "Nachzustand konnte nicht bestätigt werden."
        )

    def decide_standard_dialog(self, decision: str) -> str:
        """Accept or cancel one exact conventional pair in a regular dialog."""

        normalized = decision.casefold()
        if normalized not in {"accept", "cancel", "retry", "apply"}:
            raise GnomeAdapterError("Unbekannte Dialogentscheidung.")
        application, window = self._active_window()
        file_titles = {
            "open", "open file", "save", "save file", "select file", "select folder",
            "choose file", "choose folder", "öffnen", "datei öffnen", "speichern",
            "datei speichern", "datei auswählen", "ordner auswählen",
        }

        def recognized_regular_dialog(candidate: Any) -> bool:
            role = self._role(candidate).casefold()
            title = self._name(candidate).casefold()
            return (
                role in {"dialog", "alert", "alert dialog"}
                and "file chooser" not in role
                and title not in file_titles
            )

        def top_level_windows(candidate: Any) -> Tuple[Any, ...]:
            try:
                children = tuple(
                    candidate.getChildAtIndex(index)
                    for index in range(int(candidate.childCount))
                )
            except Exception as exc:
                raise GnomeAdapterError(
                    "Die Fensterliste der gebundenen Anwendung ist nicht lesbar."
                ) from exc
            return tuple(
                child
                for child in children
                if child is not None
                and self._role(child).casefold()
                in {"frame", "dialog", "alert", "alert dialog", "window"}
            )

        if not recognized_regular_dialog(window):
            raise GnomeAdapterError("Das aktive Fenster ist kein erkannter Standarddialog.")

        decision_pairs = (
            ("accept", {"ok"}, {"cancel", "abbrechen"}),
            ("accept", {"yes", "ja"}, {"no", "nein"}),
            ("accept", {"confirm", "bestätigen"}, {"cancel", "abbrechen"}),
            ("retry", {"retry", "wiederholen"}, {"cancel", "abbrechen"}),
            ("apply", {"apply", "anwenden"}, {"cancel", "abbrechen"}),
        )

        def bind_pair(
            controls: Sequence[Tuple[Any, Sequence[str]]],
        ) -> dict[str, Tuple[Any, Sequence[str]]]:
            matches = None
            matched_decision = None
            for positive_decision, positive_names, cancel_names in decision_pairs:
                positive = [
                    item for item in controls
                    if self._name(item[0]).casefold() in positive_names
                ]
                cancelled = [
                    item for item in controls
                    if self._name(item[0]).casefold() in cancel_names
                ]
                if positive:
                    if len(positive) != 1 or len(cancelled) != 1:
                        raise GnomeAdapterError(
                            "Der Standarddialog bietet kein eindeutiges Entscheidungspaar."
                        )
                    if matches is not None:
                        raise GnomeAdapterError(
                            "Der Standarddialog enthält mehrere Entscheidungsgruppen."
                        )
                    matched_decision = positive_decision
                    matches = {"positive": positive[0], "cancel": cancelled[0]}
            if matches is None:
                raise GnomeAdapterError(
                    "Das aktive Fenster bietet kein erkanntes Standarddialogpaar."
                )
            if normalized != "cancel" and normalized != matched_decision:
                raise GnomeAdapterError(
                    "Der Standarddialog bietet nicht die angeforderte Entscheidung an."
                )
            for _node, actions in matches.values():
                allowed = [
                    name for name in actions
                    if str(name).casefold() in {"click", "press", "activate"}
                ]
                if len(allowed) != 1:
                    raise GnomeAdapterError(
                        "Der Standarddialog bietet keine eindeutigen semantischen Aktionen."
                    )
            return matches

        bound = bind_pair(self._controls(window))
        windows = top_level_windows(application)
        if sum(candidate is window for candidate in windows) != 1:
            raise GnomeAdapterError(
                "Der Standarddialog ist nicht eindeutig an seine Anwendung gebunden."
            )
        rebound_application, rebound_window = self._active_window()
        if rebound_application is not application or rebound_window is not window:
            raise GnomeAdapterError(
                "Der Standarddialog hat vor der Entscheidung gewechselt; es wurde nichts ausgeführt."
            )
        if not recognized_regular_dialog(rebound_window):
            raise GnomeAdapterError("Das aktive Fenster ist nicht mehr als Standarddialog gebunden.")
        rebound_windows = top_level_windows(rebound_application)
        if len(rebound_windows) != len(windows) or any(
            current is not previous for current, previous in zip(rebound_windows, windows)
        ):
            raise GnomeAdapterError(
                "Die Fensterliste der Anwendung hat sich vor der Standarddialogentscheidung "
                "geändert; es wurde nichts ausgeführt."
            )
        rebound = bind_pair(self._controls(rebound_window))
        if any(rebound[key][0] is not bound[key][0] for key in ("positive", "cancel")):
            raise GnomeAdapterError(
                "Das Standarddialogpaar hat sich vor der Entscheidung geändert; "
                "es wurde nichts ausgeführt."
            )
        selected = "cancel" if normalized == "cancel" else "positive"
        control = self._invoke_control(*rebound[selected])
        expected = tuple(candidate for candidate in windows if candidate is not window)
        deadline = time.monotonic() + 2.0
        while True:
            try:
                observed = top_level_windows(application)
            except GnomeAdapterError:
                observed = None
            if observed is not None and len(observed) == len(expected) and all(
                current is previous for current, previous in zip(observed, expected)
            ):
                return control
            if time.monotonic() >= deadline:
                break
            time.sleep(0.05)
        raise GnomeAdapterError(
            "Die Standarddialogentscheidung wurde ausgelöst, aber der exakte "
            "Nachzustand konnte nicht bestätigt werden."
        )

    def read_standard_dialog(self) -> Tuple[str, Tuple[str, ...]]:
        """Read only bounded static text from one active regular dialog."""

        _, window = self._active_window()
        role = self._role(window).casefold()
        title = self._name(window)
        file_titles = {
            "open", "open file", "save", "save file", "select file", "select folder",
            "choose file", "choose folder", "öffnen", "datei öffnen", "speichern",
            "datei speichern", "datei auswählen", "ordner auswählen",
        }
        if (
            role not in {"dialog", "alert", "alert dialog"}
            or "file chooser" in role
            or title.casefold() in file_titles
        ):
            raise GnomeAdapterError("Das aktive Fenster ist kein lesbarer Standarddialog.")

        static_roles = {"label", "paragraph", "static", "static text", "description"}
        privacy_markers = ("password", "passwort", "protected", "secret")
        messages: list[str] = []
        seen: set[str] = set()
        total = 0
        for node in self._walk(window):
            if node is window or self._role(node).casefold() not in static_roles:
                continue
            try:
                attributes = " ".join(str(value) for value in node.getAttributes()).casefold()
            except Exception as exc:
                raise GnomeAdapterError(
                    "Die Schutzattribute des Dialogtexts sind nicht prüfbar."
                ) from exc
            if any(marker in attributes for marker in privacy_markers):
                continue
            value = self._name(node)
            key = value.casefold()
            if not value or key == title.casefold() or key in seen:
                continue
            if len(messages) >= 20 or total + len(value) > 1_000:
                raise GnomeAdapterError("Der Standarddialogtext überschreitet die sichere Grenze.")
            seen.add(key)
            messages.append(value)
            total += len(value)
        if not messages:
            raise GnomeAdapterError("Der Standarddialog enthält keinen sicheren statischen Text.")
        return title or "Unbenannter Dialog", tuple(messages)

    def dismiss_standard_dialog(self) -> str:
        """Dismiss a regular dialog exposing one sole exact close control."""

        application, window = self._active_window()
        file_titles = {
            "open", "open file", "save", "save file", "select file", "select folder",
            "choose file", "choose folder", "öffnen", "datei öffnen", "speichern",
            "datei speichern", "datei auswählen", "ordner auswählen",
        }

        def recognized_regular_dialog(candidate: Any) -> bool:
            role = self._role(candidate).casefold()
            title = self._name(candidate).casefold()
            return (
                role in {"dialog", "alert", "alert dialog"}
                and "file chooser" not in role
                and title not in file_titles
            )

        def bind_close(candidate: Any) -> Tuple[Any, Sequence[str]]:
            controls = self._controls(candidate)
            if len(controls) != 1:
                raise GnomeAdapterError(
                    "Der Standarddialog ist kein eindeutiger reiner Schließen-Dialog."
                )
            node, actions = controls[0]
            if self._name(node).casefold() not in {"close", "schliessen", "dismiss"}:
                raise GnomeAdapterError(
                    "Der Standarddialog bietet keine exakte Schließen-Aktion."
                )
            allowed = [
                name for name in actions
                if str(name).casefold() in {"click", "press", "activate"}
            ]
            if len(allowed) != 1:
                raise GnomeAdapterError(
                    "Der Standarddialog bietet keine eindeutige semantische Schließen-Aktion."
                )
            return node, actions

        def top_level_windows(candidate: Any) -> Tuple[Any, ...]:
            try:
                children = tuple(
                    candidate.getChildAtIndex(index)
                    for index in range(int(candidate.childCount))
                )
            except Exception as exc:
                raise GnomeAdapterError(
                    "Die Fensterliste der gebundenen Anwendung ist nicht lesbar."
                ) from exc
            return tuple(
                child
                for child in children
                if child is not None
                and self._role(child).casefold()
                in {"frame", "dialog", "alert", "alert dialog", "window"}
            )

        if not recognized_regular_dialog(window):
            raise GnomeAdapterError("Das aktive Fenster ist kein erkannter Standarddialog.")
        bound = bind_close(window)
        windows = top_level_windows(application)
        if sum(candidate is window for candidate in windows) != 1:
            raise GnomeAdapterError(
                "Der Standarddialog ist nicht eindeutig an seine Anwendung gebunden."
            )
        rebound_application, rebound_window = self._active_window()
        if rebound_application is not application or rebound_window is not window:
            raise GnomeAdapterError(
                "Der Standarddialog hat vor dem Schließen gewechselt; es wurde nichts ausgeführt."
            )
        if not recognized_regular_dialog(rebound_window):
            raise GnomeAdapterError("Das aktive Fenster ist nicht mehr als Standarddialog gebunden.")
        rebound_windows = top_level_windows(rebound_application)
        if len(rebound_windows) != len(windows) or any(
            current is not previous for current, previous in zip(rebound_windows, windows)
        ):
            raise GnomeAdapterError(
                "Die Fensterliste der Anwendung hat sich vor dem Schließen geändert; "
                "es wurde nichts ausgeführt."
            )
        rebound = bind_close(rebound_window)
        if rebound[0] is not bound[0]:
            raise GnomeAdapterError(
                "Das Schließen-Bedienelement hat sich vor der Aktivierung geändert; "
                "es wurde nichts ausgeführt."
            )
        control = self._invoke_control(*rebound)
        expected = tuple(candidate for candidate in windows if candidate is not window)
        deadline = time.monotonic() + 2.0
        while True:
            try:
                observed = top_level_windows(application)
            except GnomeAdapterError:
                observed = None
            if observed is not None and len(observed) == len(expected) and all(
                current is previous for current, previous in zip(observed, expected)
            ):
                return control
            if time.monotonic() >= deadline:
                break
            time.sleep(0.05)
        raise GnomeAdapterError(
            "Der Standarddialog wurde ausgelöst, aber der exakte Nachzustand "
            "konnte nicht bestätigt werden."
        )

    def _is_semantic_folder(self, node: Any) -> bool:
        if self._role(node).casefold() in {"folder", "directory"}:
            return True
        try:
            attributes = {
                " ".join(str(attribute).split()).casefold()
                for attribute in node.getAttributes()
            }
        except Exception:
            attributes = set()
        if attributes.intersection(
            {"is-folder:true", "is-directory:true", "file-type:folder", "type:folder"}
        ):
            return True
        for descendant in self._walk(node):
            if descendant is node:
                continue
            if self._role(descendant).casefold() in {"icon", "image"} and self._name(
                descendant
            ).casefold() in {"folder", "directory", "ordner"}:
                return True
        return False

    def set_named_tree_item_expanded(self, name: str, expanded: bool) -> str:
        """Expand or collapse one exact item in the focused semantic tree."""

        normalized = " ".join(name.split()).casefold()
        if not normalized or len(normalized) > 120:
            raise GnomeAdapterError("Der Name des Baumelements ist ungültig.")
        _, window = self._active_window()
        focused = self._find_state(window, self._atspi.STATE_FOCUSED)
        if focused is None:
            raise GnomeAdapterError("Kein fokussierter Baumbereich gefunden.")
        container = focused
        for _depth in range(12):
            if self._role(container).casefold() in {"tree", "tree table"}:
                break
            if container is window:
                container = None
                break
            try:
                container = container.parent
            except Exception:
                container = None
            if container is None:
                break
        if container is None or self._role(container).casefold() not in {
            "tree",
            "tree table",
        }:
            raise GnomeAdapterError("Der Fokus liegt nicht in einem semantischen Baum.")
        matches = [
            node
            for node in self._walk(container)
            if self._role(node).casefold() in {"tree item", "row", "table row"}
            and self._name(node).casefold() == normalized
        ]
        if not matches:
            raise GnomeAdapterError("Kein exaktes Baumelement mit diesem Namen gefunden.")
        if len(matches) != 1:
            raise GnomeAdapterError("Der Baumelementname ist nicht eindeutig.")
        item = matches[0]
        before = self._has_state(item, self._atspi.STATE_EXPANDED)
        if expanded and not self._has_state(item, self._atspi.STATE_EXPANDABLE):
            raise GnomeAdapterError("Das Baumelement ist nicht semantisch aufklappbar.")
        if before == expanded:
            state = "aufgeklappt" if expanded else "zugeklappt"
            raise GnomeAdapterError(f"Das Baumelement ist bereits {state}.")
        wanted = "expand" if expanded else "collapse"
        try:
            action = item.queryAction()
            actions = tuple(action.getName(index) for index in range(action.nActions))
        except Exception as exc:
            raise GnomeAdapterError("Das Baumelement bietet keine semantische Aktion.") from exc
        matches_action = [
            index for index, action_name in enumerate(actions) if action_name.casefold() == wanted
        ]
        if len(matches_action) != 1:
            raise GnomeAdapterError(f"Das Baumelement bietet keine eindeutige {wanted}-Aktion.")

        def restore_before() -> bool:
            if self._has_state(item, self._atspi.STATE_EXPANDED) == before:
                return True
            restore_name = "expand" if before else "collapse"
            restore_matches = [
                index
                for index, action_name in enumerate(actions)
                if action_name.casefold() == restore_name
            ]
            if len(restore_matches) != 1:
                return False
            try:
                accepted_restore = bool(action.doAction(restore_matches[0]))
            except Exception:
                return False
            return accepted_restore and (
                self._has_state(item, self._atspi.STATE_EXPANDED) == before
            )

        try:
            accepted = bool(action.doAction(matches_action[0]))
        except Exception as exc:
            if not restore_before():
                raise GnomeAdapterError(
                    "Die fehlgeschlagene Baumzustandsänderung konnte nicht zurückgesetzt werden."
                ) from exc
            raise GnomeAdapterError("Das Baumelement hat die Zustandsänderung abgelehnt.") from exc
        after = self._has_state(item, self._atspi.STATE_EXPANDED)
        if not accepted or after != expanded:
            if not restore_before():
                raise GnomeAdapterError(
                    "Der inkonsistente Baumzustand konnte nicht zurückgesetzt werden."
                )
            raise GnomeAdapterError("Die Zustandsänderung des Baumelements ist nicht bestätigt.")
        return self._name(item) or "Baumelement"

    def select_table_row(self, name: str) -> str:
        """Select one exact row in the nearest focused semantic table."""

        normalized = " ".join(name.split()).casefold()
        if not normalized or len(normalized) > 120:
            raise GnomeAdapterError("Der Name der Tabellenzeile ist ungültig.")
        _, window = self._active_window()
        focused = self._find_state(window, self._atspi.STATE_FOCUSED)
        if focused is None:
            raise GnomeAdapterError("Kein fokussierter Tabellenbereich gefunden.")
        table = focused
        for _depth in range(12):
            if self._role(table).casefold() in {"table", "tree table"}:
                break
            if table is window:
                table = None
                break
            try:
                table = table.parent
            except Exception:
                table = None
            if table is None:
                break
        if table is None or self._role(table).casefold() not in {"table", "tree table"}:
            raise GnomeAdapterError("Der Fokus liegt nicht in einer semantischen Tabelle.")
        try:
            selection = table.querySelection()
        except Exception as exc:
            raise GnomeAdapterError("Die Tabelle bietet keine prüfbare Zeilenauswahl.") from exc
        children = list(self._children(table))
        matches = []
        for index, row in enumerate(children):
            if self._role(row).casefold() not in {"row", "table row"}:
                continue
            names = {
                self._name(node).casefold()
                for node in self._walk(row)
                if self._role(node).casefold() in {"row", "table row", "cell", "table cell"}
            }
            if normalized in names:
                matches.append(index)
        if not matches:
            raise GnomeAdapterError("Keine Tabellenzeile mit diesem exakten Namen gefunden.")
        if len(matches) != 1:
            raise GnomeAdapterError("Der Tabellenzeilenname ist nicht eindeutig.")
        self._select_container_index(table, selection, matches[0])
        return self._name(children[matches[0]]) or name

    def select_named_tab(self, name: str) -> str:
        """Select one exact direct tab in the nearest focused semantic tab list."""

        normalized = " ".join(name.split()).casefold()
        if not normalized or len(normalized) > 120:
            raise GnomeAdapterError("Der Name der Registerkarte ist ungültig.")
        _, window = self._active_window()
        focused = self._find_state(window, self._atspi.STATE_FOCUSED)
        if focused is None:
            raise GnomeAdapterError("Kein fokussierter Registerkartenbereich gefunden.")
        tab_list = focused
        for _depth in range(12):
            if self._role(tab_list).casefold() == "page tab list":
                break
            if tab_list is window:
                tab_list = None
                break
            try:
                tab_list = tab_list.parent
            except Exception:
                tab_list = None
            if tab_list is None:
                break
        if tab_list is None or self._role(tab_list).casefold() != "page tab list":
            raise GnomeAdapterError("Der Fokus liegt nicht in einer semantischen Registerleiste.")
        try:
            selection = tab_list.querySelection()
        except Exception as exc:
            raise GnomeAdapterError("Die Registerleiste bietet keine prüfbare Auswahl.") from exc
        children = list(self._children(tab_list))
        matches = [
            index
            for index, tab in enumerate(children)
            if self._role(tab).casefold() == "page tab"
            and self._name(tab).casefold() == normalized
        ]
        if not matches:
            raise GnomeAdapterError("Keine Registerkarte mit diesem exakten Namen gefunden.")
        if len(matches) != 1:
            raise GnomeAdapterError("Der Registerkartenname ist nicht eindeutig.")
        self._select_container_index(tab_list, selection, matches[0])
        return self._name(children[matches[0]]) or name

    def set_named_slider(self, name: str, percent: int) -> str:
        """Set one uniquely named slider in the once-bound active window."""

        normalized = " ".join(name.split()).casefold()
        if not normalized or len(normalized) > 120:
            raise GnomeAdapterError("Der Name des Schiebereglers ist ungültig.")
        if isinstance(percent, bool) or not isinstance(percent, int) or not 0 <= percent <= 100:
            raise GnomeAdapterError("Der Schiebereglerwert muss zwischen 0 und 100 Prozent liegen.")
        _, window = self._active_window()
        matches = [
            node
            for node in self._walk(window)
            if self._role(node).casefold() == "slider"
            and self._name(node).casefold() == normalized
        ]
        if not matches:
            raise GnomeAdapterError("Kein Schieberegler mit diesem exakten Namen gefunden.")
        if len(matches) != 1:
            raise GnomeAdapterError("Der Name des Schiebereglers ist nicht eindeutig.")
        slider = matches[0]
        try:
            value = slider.queryValue()
            before = float(value.currentValue)
            minimum = float(value.minimumValue)
            maximum = float(value.maximumValue)
        except Exception as exc:
            raise GnomeAdapterError("Der Schieberegler bietet keinen prüfbaren Wert.") from exc
        if not all(math.isfinite(item) for item in (before, minimum, maximum)) or minimum >= maximum:
            raise GnomeAdapterError("Der Wertebereich des Schiebereglers ist ungültig.")
        target = minimum + (maximum - minimum) * percent / 100
        try:
            increment = float(value.minimumIncrement)
        except Exception:
            increment = 0.0
        if math.isfinite(increment) and 0 < increment <= maximum - minimum:
            steps = math.floor((target - minimum) / increment + 0.5)
            target = min(maximum, minimum + steps * increment)
        tolerance = max((maximum - minimum) * 1e-6, 1e-6)
        if abs(before - target) <= tolerance:
            return self._name(slider) or name
        try:
            accepted = value.setCurrentValue(target)
        except Exception as exc:
            if not self._restore_numeric_value(value, before, tolerance):
                raise GnomeAdapterError(
                    "Die fehlgeschlagene Schieberegleränderung konnte nicht zurückgesetzt werden."
                ) from exc
            raise GnomeAdapterError("Der Schieberegler hat die Änderung abgelehnt.") from exc
        try:
            after = float(value.currentValue)
        except Exception:
            after = float("nan")
        if accepted is False or not math.isfinite(after) or abs(after - target) > tolerance:
            if not self._restore_numeric_value(value, before, tolerance):
                raise GnomeAdapterError(
                    "Der inkonsistente Schiebereglerwert konnte nicht zurückgesetzt werden."
                )
            raise GnomeAdapterError("Der neue Schiebereglerwert konnte nicht bestätigt werden.")
        return self._name(slider) or name

    @staticmethod
    def _restore_numeric_value(value: Any, before: float, tolerance: float) -> bool:
        """Restore one AT-SPI Value and verify its numeric post-state."""

        try:
            current = float(value.currentValue)
            if math.isfinite(current) and abs(current - before) <= tolerance:
                return True
            value.setCurrentValue(before)
            restored = float(value.currentValue)
            return math.isfinite(restored) and abs(restored - before) <= tolerance
        except Exception:
            return False

    def read_named_progress(self, name: str) -> Tuple[str, int]:
        """Read one exact progress bar as a bounded percentage."""

        progress = self._unique_named_role(name, "progress bar", "Fortschrittsanzeige")
        try:
            value = progress.queryValue()
            current = float(value.currentValue)
            minimum = float(value.minimumValue)
            maximum = float(value.maximumValue)
        except Exception as exc:
            raise GnomeAdapterError("Die Fortschrittsanzeige bietet keinen prüfbaren Wert.") from exc
        if (
            not all(math.isfinite(item) for item in (current, minimum, maximum))
            or minimum >= maximum
            or current < minimum
            or current > maximum
        ):
            raise GnomeAdapterError("Der Wertebereich der Fortschrittsanzeige ist ungültig.")
        percent = int(math.floor(((current - minimum) / (maximum - minimum)) * 100 + 0.5))
        return self._name(progress) or name, percent

    def set_named_spin_button(self, name: str, number: float) -> str:
        """Set one exact numeric spin button through AT-SPI Value."""

        spin = self._unique_named_role(name, "spin button", "Zahlenfeld")
        if isinstance(number, bool) or not isinstance(number, (int, float)):
            raise GnomeAdapterError("Der Zahlenfeldwert ist ungültig.")
        target = float(number)
        if not math.isfinite(target):
            raise GnomeAdapterError("Der Zahlenfeldwert ist ungültig.")
        try:
            value = spin.queryValue()
            before = float(value.currentValue)
            minimum = float(value.minimumValue)
            maximum = float(value.maximumValue)
        except Exception as exc:
            raise GnomeAdapterError("Das Zahlenfeld bietet keinen prüfbaren Wert.") from exc
        if not all(math.isfinite(item) for item in (before, minimum, maximum)) or minimum > maximum:
            raise GnomeAdapterError("Der Wertebereich des Zahlenfelds ist ungültig.")
        if target < minimum or target > maximum:
            raise GnomeAdapterError("Der Zahlenfeldwert liegt außerhalb des erlaubten Bereichs.")
        tolerance = max((maximum - minimum) * 1e-6, 1e-6)
        try:
            increment = float(value.minimumIncrement)
        except Exception:
            increment = 0.0
        if math.isfinite(increment) and 0 < increment <= max(maximum - minimum, tolerance):
            steps = math.floor((target - minimum) / increment + 0.5)
            snapped = min(maximum, minimum + steps * increment)
            if abs(snapped - target) > tolerance:
                raise GnomeAdapterError("Der Zahlenfeldwert passt nicht zur erlaubten Schrittweite.")
            target = snapped
        if abs(before - target) <= tolerance:
            return self._name(spin) or name
        try:
            accepted = value.setCurrentValue(target)
        except Exception as exc:
            if not self._restore_numeric_value(value, before, tolerance):
                raise GnomeAdapterError(
                    "Die fehlgeschlagene Zahlenfeldänderung konnte nicht zurückgesetzt werden."
                ) from exc
            raise GnomeAdapterError("Das Zahlenfeld hat die Änderung abgelehnt.") from exc
        try:
            after = float(value.currentValue)
        except Exception:
            after = float("nan")
        if accepted is False or not math.isfinite(after) or abs(after - target) > tolerance:
            if not self._restore_numeric_value(value, before, tolerance):
                raise GnomeAdapterError(
                    "Der inkonsistente Zahlenfeldwert konnte nicht zurückgesetzt werden."
                )
            raise GnomeAdapterError("Der neue Zahlenfeldwert konnte nicht bestätigt werden.")
        return self._name(spin) or name

    def set_named_checkbox(self, name: str, checked: bool) -> str:
        """Set one exact checkbox and verify its checked state."""

        return self._set_named_checked_role(
            name, checked, role="check box", label="Kontrollkästchen"
        )

    def set_named_switch(self, name: str, enabled: bool) -> str:
        """Set one exact switch and verify its checked state."""

        return self._set_named_checked_role(name, enabled, role="switch", label="Schalter")

    def _set_named_checked_role(
        self, name: str, checked: bool, *, role: str, label: str
    ) -> str:
        control = self._unique_named_role(name, role, label)
        if not isinstance(checked, bool):
            raise GnomeAdapterError(f"Der {label}zustand ist ungültig.")
        before = self._has_state(control, self._atspi.STATE_CHECKED)
        if before == checked:
            return self._name(control) or name
        action, index = self._exact_named_action(control, {"toggle"}, label)

        def restore_before() -> bool:
            if self._has_state(control, self._atspi.STATE_CHECKED) == before:
                return True
            try:
                accepted_restore = bool(action.doAction(index))
            except Exception:
                return False
            return accepted_restore and (
                self._has_state(control, self._atspi.STATE_CHECKED) == before
            )

        try:
            accepted = bool(action.doAction(index))
        except Exception as exc:
            if not restore_before():
                raise GnomeAdapterError(
                    f"Die fehlgeschlagene {label}änderung konnte nicht zurückgesetzt werden."
                ) from exc
            raise GnomeAdapterError(f"Das Bedienelement {label} hat die Änderung abgelehnt.") from exc
        after = self._has_state(control, self._atspi.STATE_CHECKED)
        if not accepted or after != checked:
            if not restore_before():
                raise GnomeAdapterError(
                    f"Der inkonsistente {label}zustand konnte nicht zurückgesetzt werden."
                )
            raise GnomeAdapterError(f"Der {label}zustand konnte nicht bestätigt werden.")
        return self._name(control) or name

    def select_named_radio(self, name: str) -> str:
        """Select one exact radio and verify or restore the whole group."""

        normalized = " ".join(name.split()).casefold()
        if not normalized or len(normalized) > 120:
            raise GnomeAdapterError("Der Name des Optionsfelds ist ungültig.")
        _, window = self._active_window()
        radios = [node for node in self._walk(window) if self._role(node).casefold() == "radio button"]
        matches = [node for node in radios if self._name(node).casefold() == normalized]
        if not matches:
            raise GnomeAdapterError("Kein Optionsfeld mit diesem exakten Namen gefunden.")
        if len(matches) != 1:
            raise GnomeAdapterError("Der Name des Optionsfelds ist nicht eindeutig.")
        radio = matches[0]
        before = tuple(
            self._has_state(node, self._atspi.STATE_CHECKED) for node in radios
        )
        if sum(before) > 1:
            raise GnomeAdapterError(
                "Die Optionsfeldgruppe hat keinen eindeutigen Ausgangszustand."
            )
        target_index = radios.index(radio)
        if before[target_index]:
            return self._name(radio) or name
        action, index = self._exact_named_action(radio, {"select", "click"}, "Optionsfeld")

        def bitmap() -> Tuple[bool, ...]:
            return tuple(
                self._has_state(node, self._atspi.STATE_CHECKED) for node in radios
            )

        expected = tuple(position == target_index for position in range(len(radios)))

        def restore_before() -> bool:
            if bitmap() == before:
                return True
            if not any(before):
                return False
            previous_index = before.index(True)
            previous = radios[previous_index]
            try:
                old_action, old_index = self._exact_named_action(
                    previous, {"select", "click"}, "vorheriges Optionsfeld"
                )
                accepted_restore = bool(old_action.doAction(old_index))
            except Exception:
                return False
            return accepted_restore and bitmap() == before

        try:
            accepted = bool(action.doAction(index))
        except Exception as exc:
            if not restore_before():
                raise GnomeAdapterError(
                    "Die fehlgeschlagene Optionsfeldauswahl konnte nicht zurückgesetzt werden."
                ) from exc
            raise GnomeAdapterError("Das Optionsfeld hat die Auswahl abgelehnt.") from exc
        if not accepted or bitmap() != expected:
            if not restore_before():
                raise GnomeAdapterError(
                    "Die inkonsistente Optionsfeldgruppe konnte nicht zurückgesetzt werden."
                )
            raise GnomeAdapterError("Die Optionsfeldauswahl konnte nicht bestätigt werden.")
        return self._name(radio) or name

    def select_combo_item(self, combo_name: str, item_name: str) -> str:
        """Select one exact direct item of one exact combo box."""

        combo = self._unique_named_role(combo_name, "combo box", "Kombinationsfeld")
        normalized_item = " ".join(item_name.split()).casefold()
        if not normalized_item or len(normalized_item) > 120:
            raise GnomeAdapterError("Der Name des Auswahllisteneintrags ist ungültig.")
        try:
            selection = combo.querySelection()
        except Exception as exc:
            raise GnomeAdapterError("Das Kombinationsfeld bietet keine prüfbare Auswahl.") from exc
        children = list(self._children(combo))
        matches = [
            index
            for index, child in enumerate(children)
            if self._role(child).casefold() in {"menu item", "list item", "option"}
            and self._name(child).casefold() == normalized_item
        ]
        if not matches:
            raise GnomeAdapterError("Kein direkter Auswahllisteneintrag mit diesem exakten Namen gefunden.")
        if len(matches) != 1:
            raise GnomeAdapterError("Der Auswahllisteneintrag ist nicht eindeutig.")
        self._select_container_index(combo, selection, matches[0])
        return self._name(children[matches[0]]) or item_name

    def activate_menu_item(self, name: str) -> str:
        """Activate one exact direct item in the nearest focused menu."""

        normalized = " ".join(name.split()).casefold()
        if not normalized or len(normalized) > 120:
            raise GnomeAdapterError("Der Name des Menüeintrags ist ungültig.")
        _, window = self._active_window()

        def bind_menu_item(bound_window: Any) -> Tuple[Any, Any]:
            focused = self._find_state(bound_window, self._atspi.STATE_FOCUSED)
            if focused is None:
                raise GnomeAdapterError("Kein fokussierter Menübereich gefunden.")
            menu = focused
            for _depth in range(12):
                if self._role(menu).casefold() in {"menu", "menu bar"}:
                    break
                if menu is bound_window:
                    menu = None
                    break
                try:
                    menu = menu.parent
                except Exception:
                    menu = None
                if menu is None:
                    break
            if menu is None or self._role(menu).casefold() not in {"menu", "menu bar"}:
                raise GnomeAdapterError("Der Fokus liegt nicht in einem semantischen Menü.")
            matches = [
                child
                for child in self._children(menu)
                if self._role(child).casefold()
                in {"menu item", "check menu item", "radio menu item"}
                and self._name(child).casefold() == normalized
            ]
            if not matches:
                raise GnomeAdapterError(
                    "Kein direkter Menüeintrag mit diesem exakten Namen gefunden."
                )
            if len(matches) != 1:
                raise GnomeAdapterError("Der Menüeintragsname ist nicht eindeutig.")
            return menu, matches[0]

        menu, item = bind_menu_item(window)
        _, rebound_window = self._active_window()
        if rebound_window is not window:
            raise GnomeAdapterError(
                "Das aktive Fenster hat vor der Menüaktivierung gewechselt; "
                "es wurde nichts ausgeführt."
            )
        rebound_menu, rebound_item = bind_menu_item(rebound_window)
        if rebound_menu is not menu or rebound_item is not item:
            raise GnomeAdapterError(
                "Menü oder Menüeintrag haben sich vor der Aktivierung geändert; "
                "es wurde nichts ausgeführt."
            )
        item = rebound_item
        action, index = self._exact_named_action(
            item, {"activate", "click", "press"}, "Menüeintrag"
        )
        try:
            accepted = bool(action.doAction(index))
        except Exception as exc:
            raise GnomeAdapterError("Der Menüeintrag ist nicht mehr ausführbar.") from exc
        if not accepted:
            raise GnomeAdapterError("Der Menüeintrag hat die Aktion abgelehnt.")
        return self._name(item) or name

    def _unique_named_role(self, name: str, role: str, label: str) -> Any:
        normalized = " ".join(name.split()).casefold()
        if not normalized or len(normalized) > 120:
            raise GnomeAdapterError(f"Der Name des {label}s ist ungültig.")
        _, window = self._active_window()
        matches = [
            node for node in self._walk(window)
            if self._role(node).casefold() == role and self._name(node).casefold() == normalized
        ]
        if not matches:
            raise GnomeAdapterError(f"Kein {label} mit diesem exakten Namen gefunden.")
        if len(matches) != 1:
            raise GnomeAdapterError(f"Der Name des {label}s ist nicht eindeutig.")
        return matches[0]

    @staticmethod
    def _exact_named_action(node: Any, allowed: set[str], label: str) -> Tuple[Any, int]:
        try:
            action = node.queryAction()
            matches = [
                index
                for index in range(action.nActions)
                if action.getName(index).casefold() in allowed
            ]
        except Exception as exc:
            raise GnomeAdapterError(f"Das {label} bietet keine semantische Aktion.") from exc
        if len(matches) != 1:
            raise GnomeAdapterError(f"Das {label} bietet keine eindeutige semantische Aktion.")
        return action, matches[0]

    def decide_permission(self, decision: str) -> str:
        """Invoke one side of an exact permission pair in the bound active dialog."""

        normalized = decision.casefold()
        if normalized not in {"allow", "deny"}:
            raise GnomeAdapterError("Unbekannte Berechtigungsentscheidung.")
        application, window = self._active_window()
        role = self._role(window).casefold()
        if role not in {"dialog", "alert", "alert dialog"}:
            raise GnomeAdapterError("Das aktive Fenster ist kein erkannter Berechtigungsdialog.")

        permission_pairs = (
            (
                {"allow", "erlauben", "zulassen"},
                {"deny", "don't allow", "do not allow", "ablehnen", "nicht erlauben", "nicht zulassen"},
            ),
            (
                {"grant access", "zugriff erlauben", "zugriff gewähren"},
                {"deny access", "zugriff ablehnen", "zugriff verweigern"},
            ),
            (
                {"share", "freigeben", "teilen"},
                {"don't share", "do not share", "nicht freigeben", "nicht teilen"},
            ),
        )
        def top_level_windows(candidate: Any) -> Tuple[Any, ...]:
            try:
                children = tuple(
                    candidate.getChildAtIndex(index)
                    for index in range(int(candidate.childCount))
                )
            except Exception as exc:
                raise GnomeAdapterError(
                    "Die Fensterliste der gebundenen Anwendung ist nicht lesbar."
                ) from exc
            return tuple(
                child
                for child in children
                if child is not None
                and self._role(child).casefold()
                in {"frame", "dialog", "alert", "alert dialog", "window"}
            )

        def bind_pair(controls: Sequence[Tuple[Any, Sequence[str]]]) -> dict[str, Tuple[Any, Sequence[str]]]:
            matches = None
            for allow_names, deny_names in permission_pairs:
                allow = [item for item in controls if self._name(item[0]).casefold() in allow_names]
                deny = [item for item in controls if self._name(item[0]).casefold() in deny_names]
                if allow or deny:
                    if len(allow) != 1 or len(deny) != 1:
                        raise GnomeAdapterError(
                            "Der Berechtigungsdialog bietet kein eindeutiges Erlauben-/Ablehnen-Paar."
                        )
                    if matches is not None:
                        raise GnomeAdapterError(
                            "Der Berechtigungsdialog enthält mehrere Entscheidungsgruppen."
                        )
                    matches = {"allow": allow[0], "deny": deny[0]}
            if matches is None:
                raise GnomeAdapterError(
                    "Das aktive Fenster bietet kein erkanntes Berechtigungsentscheidungspaar."
                )
            return matches

        matches = bind_pair(self._controls(window))
        windows = top_level_windows(application)
        if sum(candidate is window for candidate in windows) != 1:
            raise GnomeAdapterError(
                "Der Berechtigungsdialog ist nicht eindeutig an seine Anwendung gebunden."
            )
        rebound_application, rebound_window = self._active_window()
        if rebound_application is not application or rebound_window is not window:
            raise GnomeAdapterError(
                "Der Berechtigungsdialog hat vor der Entscheidung gewechselt; "
                "es wurde nichts ausgeführt."
            )
        if self._role(rebound_window).casefold() not in {"dialog", "alert", "alert dialog"}:
            raise GnomeAdapterError(
                "Das aktive Fenster ist nicht mehr als Berechtigungsdialog gebunden."
            )
        rebound_windows = top_level_windows(rebound_application)
        if len(rebound_windows) != len(windows) or any(
            current is not previous for current, previous in zip(rebound_windows, windows)
        ):
            raise GnomeAdapterError(
                "Die Fensterliste der Anwendung hat sich vor der Berechtigungsentscheidung "
                "geändert; es wurde nichts ausgeführt."
            )
        rebound = bind_pair(self._controls(rebound_window))
        if any(rebound[key][0] is not matches[key][0] for key in ("allow", "deny")):
            raise GnomeAdapterError(
                "Das Erlauben-/Ablehnen-Paar hat sich vor der Entscheidung geändert; "
                "es wurde nichts ausgeführt."
            )
        control = self._invoke_control(*rebound[normalized])
        expected = tuple(candidate for candidate in windows if candidate is not window)
        deadline = time.monotonic() + 2.0
        while True:
            try:
                observed = top_level_windows(application)
            except GnomeAdapterError:
                observed = None
            if observed is not None and len(observed) == len(expected) and all(
                current is previous for current, previous in zip(observed, expected)
            ):
                return control
            if time.monotonic() >= deadline:
                break
            time.sleep(0.05)
        raise GnomeAdapterError(
            "Die Berechtigungsentscheidung wurde ausgelöst, aber der exakte "
            "Nachzustand konnte nicht bestätigt werden."
        )

    def _select_container_item(self, container: Any, selection: Any, normalized: str) -> str:
        children = list(self._children(container))
        matches = [
            index
            for index, child in enumerate(children)
            if self._name(child).casefold() == normalized
        ]
        if not matches:
            raise GnomeAdapterError("Kein Listeneintrag mit diesem exakten Namen gefunden.")
        if len(matches) != 1:
            raise GnomeAdapterError("Der Listeneintragsname ist nicht eindeutig.")
        return self._select_container_index(container, selection, matches[0])

    def _select_container_index(self, container: Any, selection: Any, index: int) -> str:
        children = list(self._children(container))
        if index < 0 or index >= len(children):
            raise GnomeAdapterError("Der Auswahlindex liegt außerhalb des Containers.")
        try:
            previous = tuple(
                child_index
                for child_index in range(len(children))
                if bool(selection.isChildSelected(child_index))
            )
        except Exception as exc:
            raise GnomeAdapterError("Die aktuelle Auswahl ist nicht sicher lesbar.") from exc

        def restore_previous() -> bool:
            try:
                if not bool(selection.clearSelection()):
                    return False
                for child_index in previous:
                    if not bool(selection.selectChild(child_index)):
                        return False
                return all(
                    bool(selection.isChildSelected(child_index)) == (child_index in previous)
                    for child_index in range(len(children))
                )
            except Exception:
                return False

        try:
            cleared = bool(selection.clearSelection())
            accepted = cleared and bool(selection.selectChild(index))
            observed = accepted and all(
                bool(selection.isChildSelected(child_index)) == (child_index == index)
                for child_index in range(len(children))
            )
        except Exception as exc:
            if not restore_previous():
                raise GnomeAdapterError(
                    "Die fehlgeschlagene Auswahl konnte nicht zur\u00fcckgesetzt werden."
                ) from exc
            raise GnomeAdapterError("Die Listenauswahl ist fehlgeschlagen.") from exc
        if not accepted or not observed:
            if not restore_previous():
                raise GnomeAdapterError(
                    "Die inkonsistente Auswahl konnte nicht zur\u00fcckgesetzt werden."
                )
            raise GnomeAdapterError("Die Listenauswahl konnte nicht best\u00e4tigt werden.")
        return self._name(children[index]) or "Listeneintrag"

    def _invoke_control(self, node: Any, _actions: Sequence[str]) -> str:
        """Invoke only a freshly rebound, explicitly activation-like action."""

        try:
            action = node.queryAction()
            fresh_actions = tuple(
                str(action.getName(index)) for index in range(int(action.nActions))
            )
            preferred = ("click", "press", "activate", "toggle", "open")
            chosen = next(
                (
                    index
                    for name in preferred
                    for index, value in enumerate(fresh_actions)
                    if value.casefold() == name
                ),
                None,
            )
        except Exception as exc:
            raise GnomeAdapterError(
                "Die semantischen Aktionen des Bedienelements sind nicht mehr pr\u00fcfbar."
            ) from exc
        if chosen is None:
            raise GnomeAdapterError(
                "Das Bedienelement bietet keine erlaubte Aktivierungsaktion."
            )
        try:
            accepted = bool(action.doAction(chosen))
        except Exception as exc:
            raise GnomeAdapterError(
                "Das Bedienelement ist nicht mehr semantisch ausf\u00fchrbar."
            ) from exc
        if not accepted:
            raise GnomeAdapterError("Das Bedienelement hat die Aktion abgelehnt.")
        return self._name(node) or self._role(node)

    def cycle_window(self, direction: int) -> str:
        """Focus one adjacent visible window and verify the exact active state."""

        desktop = self._atspi.Registry.getDesktop(0)
        windows: List[Any] = []
        for application in self._children(desktop):
            for child in self._children(application):
                if self._role(child) in {"frame", "dialog", "window"} and self._has_state(
                    child, self._atspi.STATE_SHOWING
                ):
                    windows.append(child)
        if not windows:
            raise GnomeAdapterError("Kein sichtbares GNOME-Fenster gefunden.")
        active = [
            index
            for index, item in enumerate(windows)
            if self._has_state(item, self._atspi.STATE_ACTIVE)
        ]
        if len(active) != 1:
            raise GnomeAdapterError(
                "Das aktive GNOME-Fenster ist nicht eindeutig; der Fokus bleibt unverändert."
            )
        if len(windows) == 1:
            raise GnomeAdapterError("Kein weiteres sichtbares GNOME-Fenster gefunden.")
        active_index = active[0]
        previous = windows[active_index]
        target = windows[(active_index + (1 if direction >= 0 else -1)) % len(windows)]

        def exactly_active(expected: Any) -> bool:
            return all(
                self._has_state(item, self._atspi.STATE_ACTIVE) == (item is expected)
                for item in windows
            )

        def restore_previous() -> bool:
            if exactly_active(previous):
                return True
            try:
                return bool(previous.queryComponent().grabFocus()) and exactly_active(previous)
            except Exception:
                return False

        try:
            focused = bool(target.queryComponent().grabFocus())
        except Exception as exc:
            if not restore_previous():
                raise GnomeAdapterError(
                    "Der fehlgeschlagene Fensterwechsel konnte nicht zurückgesetzt werden."
                ) from exc
            raise GnomeAdapterError("Das nächste Fenster konnte nicht fokussiert werden.") from exc
        if not focused or not exactly_active(target):
            if not restore_previous():
                raise GnomeAdapterError(
                    "Der inkonsistente Fensterfokus konnte nicht zurückgesetzt werden."
                )
            raise GnomeAdapterError("GNOME hat den Fensterfokus nicht bestätigt.")
        return self._name(target) or "unbenanntes Fenster"

    def navigate_back(self) -> str:
        """Invoke one globally unique, freshly rebound Back action."""

        _, window = self._active_window()
        aliases = {"back", "go back", "zurück"}
        candidates = []
        for node in self._walk(window):
            try:
                action = node.queryAction()
                names = tuple(action.getName(index) for index in range(action.nActions))
            except Exception:
                continue
            matches = [index for index, name in enumerate(names) if name.casefold() in aliases]
            candidates.extend((node, names) for _index in matches)
        if not candidates:
            raise GnomeAdapterError("Dieses Fenster bietet keine semantische Zurück-Aktion an.")
        if len(candidates) != 1:
            raise GnomeAdapterError("Die semantische Zurück-Aktion ist nicht eindeutig.")
        node, _discovered_names = candidates[0]
        try:
            action = node.queryAction()
            fresh_names = tuple(
                str(action.getName(index)) for index in range(int(action.nActions))
            )
            matches = [
                index for index, name in enumerate(fresh_names) if name.casefold() in aliases
            ]
        except Exception as exc:
            raise GnomeAdapterError("Die Zurück-Aktion ist nicht mehr prüfbar.") from exc
        if len(matches) != 1:
            raise GnomeAdapterError("Die Zurück-Aktion ist nicht mehr eindeutig gebunden.")
        try:
            accepted = bool(action.doAction(matches[0]))
        except Exception as exc:
            raise GnomeAdapterError("Die Zurück-Aktion ist nicht mehr ausführbar.") from exc
        if not accepted:
            raise GnomeAdapterError("Das Fenster hat die Zurück-Aktion abgelehnt.")
        return self._name(node) or "Zurück"

    def window_action(self, operation: str) -> str:
        """Invoke a window-manager action exposed by the active AT-SPI frame."""

        aliases = {
            "minimize": {"minimize", "minimieren"},
            "maximize": {"maximize", "maximieren"},
            "restore": {"restore", "unmaximize", "wiederherstellen"},
            "close": {"close", "schließen", "schliessen"},
            "workspace_previous": {
                "move to workspace left",
                "move to previous workspace",
                "auf arbeitsfläche links verschieben",
                "auf vorherige arbeitsfläche verschieben",
            },
            "workspace_next": {
                "move to workspace right",
                "move to next workspace",
                "auf arbeitsfläche rechts verschieben",
                "auf nächste arbeitsfläche verschieben",
            },
        }
        wanted = aliases.get(operation)
        if wanted is None:
            raise GnomeAdapterError("Unbekannte semantische Fensteraktion.")
        _, window = self._active_window()
        try:
            action = window.queryAction()
            names = tuple(action.getName(index) for index in range(action.nActions))
        except Exception as exc:
            raise GnomeAdapterError(
                "Das aktive Fenster bietet keine semantischen Fensteraktionen an."
            ) from exc
        matches = [index for index, name in enumerate(names) if name.casefold() in wanted]
        if not matches:
            raise GnomeAdapterError(
                f"Das aktive Fenster unterstützt {operation} nicht über AT-SPI."
            )
        if len(matches) != 1:
            raise GnomeAdapterError(f"Die Fensteraktion {operation} ist nicht eindeutig.")
        try:
            accepted = bool(action.doAction(matches[0]))
        except Exception as exc:
            raise GnomeAdapterError("Die Fensteraktion ist nicht mehr ausführbar.") from exc
        if not accepted:
            raise GnomeAdapterError("GNOME hat die Fensteraktion abgelehnt.")
        return self._name(window) or "unbenanntes Fenster"

    def shell_action(self, operation: str) -> str:
        """Invoke a tightly named GNOME Shell control exposed over AT-SPI."""

        targets = {
            "overview": {"activities", "aktivitäten", "overview", "übersicht"},
            "applications": {
                "show applications",
                "anwendungen anzeigen",
                "applications",
                "anwendungen",
            },
        }
        targets["quick_settings"] = {
            "quick settings",
            "schnelleinstellungen",
            "system",
        }
        targets["notifications"] = {
            "notifications",
            "benachrichtigungen",
            "notification center",
            "benachrichtigungszentrale",
            "calendar",
            "kalender",
        }
        wanted = targets.get(operation)
        if wanted is None:
            raise GnomeAdapterError("Unbekannte semantische Shell-Aktion.")
        desktop = self._atspi.Registry.getDesktop(0)
        candidates = []
        for application in self._children(desktop):
            if self._name(application).casefold() not in {"gnome shell", "gnome-shell"}:
                continue
            for node in self._walk(application):
                if self._name(node).casefold() not in wanted:
                    continue
                try:
                    action = node.queryAction()
                    names = tuple(action.getName(index) for index in range(action.nActions))
                except Exception:
                    continue
                chosen = next(
                    (
                        index
                        for index, name in enumerate(names)
                        if name.casefold() in {"click", "press", "activate", "toggle"}
                    ),
                    None,
                )
                if chosen is None:
                    continue
                candidates.append((node, names))
        if not candidates:
            raise GnomeAdapterError(
                f"GNOME Shell bietet {operation} nicht semantisch über AT-SPI an."
            )
        if len(candidates) != 1:
            raise GnomeAdapterError(
                f"Das GNOME-Shell-Ziel für {operation} ist nicht eindeutig."
            )
        return self._invoke_control(*candidates[0])

    def _visible_notifications(self) -> Tuple[Any, Tuple[Any, ...]]:
        """Bind the unique GNOME Shell and its ordered Showing notifications."""
        desktop = self._atspi.Registry.getDesktop(0)
        shells = [
            application for application in self._children(desktop)
            if self._name(application).casefold() in {"gnome shell", "gnome-shell"}
        ]
        if len(shells) != 1:
            raise GnomeAdapterError("Die GNOME-Shell-Anwendung ist nicht eindeutig verfügbar.")
        notifications = [
            node for node in self._walk(shells[0])
            if self._role(node).casefold() == "notification"
            and self._has_state(node, self._atspi.STATE_SHOWING)
        ]
        if len(notifications) > 20:
            raise GnomeAdapterError("Es sind zu viele sichtbare Benachrichtigungen vorhanden.")
        return shells[0], tuple(notifications)

    def read_notifications(self) -> Tuple[str, ...]:
        """Read bounded visible notification-role content from GNOME Shell."""

        _shell, notifications = self._visible_notifications()

        static_roles = {"notification", "label", "paragraph", "static", "static text", "description"}
        privacy_markers = ("password", "passwort", "protected", "secret")
        messages: list[str] = []
        total = 0
        item_count = 0
        for notification in notifications:
            parts: list[str] = []
            seen: set[str] = set()
            for node in self._walk(notification):
                if self._role(node).casefold() not in static_roles:
                    continue
                try:
                    attributes = " ".join(
                        str(value) for value in node.getAttributes()
                    ).casefold()
                except Exception as exc:
                    raise GnomeAdapterError(
                        "Die Schutzattribute einer Benachrichtigung sind nicht prüfbar."
                    ) from exc
                if any(marker in attributes for marker in privacy_markers):
                    continue
                value = self._name(node)
                key = value.casefold()
                if not value or key in seen:
                    continue
                if item_count >= 40 or total + len(value) > 2_000:
                    raise GnomeAdapterError(
                        "Der Benachrichtigungstext überschreitet die sichere Grenze."
                    )
                seen.add(key)
                parts.append(value)
                total += len(value)
                item_count += 1
            messages.append(" — ".join(parts) if parts else "Kein sicher lesbarer Text")
        return tuple(messages)

    def dismiss_notification(self, number: int) -> int:
        """Dismiss one numbered visible notification after full snapshot rebinding."""

        if number < 1 or number > 20:
            raise GnomeAdapterError("Die Benachrichtigungsnummer ist außerhalb des Bereichs.")
        shell, notifications = self._visible_notifications()
        if number > len(notifications):
            raise GnomeAdapterError("Diese Benachrichtigungsnummer ist nicht sichtbar.")
        original = notifications[number - 1]

        rebound_shell, rebound = self._visible_notifications()
        if rebound_shell is not shell or len(rebound) != len(notifications) or any(
            fresh is not bound for fresh, bound in zip(rebound, notifications)
        ):
            raise GnomeAdapterError(
                "Die sichtbare Benachrichtigungsreihenfolge hat sich geändert; "
                "es wurde nichts ausgeführt."
            )
        target = rebound[number - 1]
        if target is not original:
            raise GnomeAdapterError("Die gewählte Benachrichtigung wurde ersetzt.")
        try:
            action = target.queryAction()
            names = tuple(action.getName(index) for index in range(action.nActions))
        except Exception as exc:
            raise GnomeAdapterError(
                "Die Benachrichtigung bietet keine semantische Verwerfen-Aktion."
            ) from exc
        matches = [
            index for index, name in enumerate(names)
            if str(name).casefold() in {"dismiss", "close"}
        ]
        if len(matches) != 1:
            raise GnomeAdapterError(
                "Die Benachrichtigung bietet keine eindeutige Dismiss-/Close-Aktion."
            )
        try:
            accepted = bool(action.doAction(matches[0]))
        except Exception as exc:
            raise GnomeAdapterError("Die Benachrichtigung ist nicht mehr verwerfbar.") from exc
        if not accepted:
            raise GnomeAdapterError("GNOME Shell hat das Verwerfen der Benachrichtigung abgelehnt.")
        expected = notifications[: number - 1] + notifications[number:]
        deadline = time.monotonic() + 2.0
        while True:
            try:
                observed_shell, observed = self._visible_notifications()
            except GnomeAdapterError:
                observed_shell, observed = None, ()
            if observed_shell is shell and len(observed) == len(expected) and all(
                current is previous for current, previous in zip(observed, expected)
            ):
                return number
            if time.monotonic() >= deadline:
                break
            time.sleep(0.05)
        raise GnomeAdapterError(
            "Die Benachrichtigung wurde ausgelöst, aber der exakte Nachzustand "
            "konnte nicht bestätigt werden."
        )

    def _active_window(self) -> Tuple[Any, Any]:
        """Return exactly one active window; never bind work to mere visibility."""

        desktop = self._atspi.Registry.getDesktop(0)
        active: List[Tuple[Any, Any]] = []
        for application in self._children(desktop):
            for child in self._children(application):
                if self._role(child) not in {"frame", "dialog", "window"}:
                    continue
                if self._has_state(child, self._atspi.STATE_ACTIVE):
                    active.append((application, child))
        if len(active) != 1:
            raise GnomeAdapterError("Das aktive GNOME-Fenster ist nicht eindeutig.")
        return active[0]

    def _orientation_window(self) -> Tuple[Any, Any]:
        """Permit one unique showing window only for non-mutating orientation."""

        desktop = self._atspi.Registry.getDesktop(0)
        active: List[Tuple[Any, Any]] = []
        showing: List[Tuple[Any, Any]] = []
        for application in self._children(desktop):
            for child in self._children(application):
                if self._role(child) not in {"frame", "dialog", "window"}:
                    continue
                if self._has_state(child, self._atspi.STATE_ACTIVE):
                    active.append((application, child))
                if self._has_state(child, self._atspi.STATE_SHOWING):
                    showing.append((application, child))
        if len(active) == 1:
            return active[0]
        if len(active) > 1 or len(showing) != 1:
            raise GnomeAdapterError("Das Fenster für die Orientierung ist nicht eindeutig.")
        return showing[0]

    def _controls(self, root: Any) -> List[Tuple[Any, Tuple[str, ...]]]:
        controls: List[Tuple[Any, Tuple[str, ...]]] = []
        for node in self._walk(root):
            if not self._has_state(node, self._atspi.STATE_SHOWING):
                continue
            try:
                action = node.queryAction()
                names = tuple(action.getName(index) for index in range(action.nActions))
            except Exception:
                continue
            if names:
                controls.append((node, names))
                if len(controls) >= self.MAX_CONTROLS:
                    break
        return controls

    def _find_state(self, root: Any, state: Any) -> Any:
        return next((node for node in self._walk(root) if self._has_state(node, state)), None)

    def _walk(self, root: Any) -> Iterable[Any]:
        pending = [(root, 0)]
        visited = 0
        while pending and visited < self.MAX_NODES:
            node, depth = pending.pop()
            visited += 1
            yield node
            if depth < self.MAX_DEPTH:
                children = list(self._children(node))
                pending.extend((child, depth + 1) for child in reversed(children))

    @staticmethod
    def _children(node: Any) -> Iterable[Any]:
        try:
            for index in range(int(node.childCount)):
                child = node.getChildAtIndex(index)
                if child is not None:
                    yield child
        except Exception:
            return

    @staticmethod
    def _name(node: Any) -> str:
        if node is None:
            return ""
        try:
            return " ".join(str(node.name or "").split())[:240]
        except Exception:
            return ""

    @staticmethod
    def _role(node: Any) -> str:
        if node is None:
            return ""
        try:
            return str(node.getRoleName() or "")[:80]
        except Exception:
            return ""

    @staticmethod
    def _has_state(node: Any, state: Any) -> bool:
        try:
            return bool(node.getState().contains(state))
        except Exception:
            return False


SEMANTIC_ACTIONS = frozenset(
    {
        "desktop.context.describe",
        "desktop.controls.list",
        "desktop.overview",
        "desktop.applications",
        "desktop.control.activate",
        "desktop.control.activate_named",
        "desktop.focus.next",
        "desktop.focus.previous",
        "desktop.focus.named",
        "desktop.text.read_focused",
        "desktop.text.set",
        "desktop.text.clear",
        "desktop.text.copy_focused",
        "desktop.text.copy_selection",
        "desktop.text.read_selection",
        "desktop.text.select_all",
        "desktop.text.clear_selection",
        "desktop.text.delete_selection",
        "desktop.text.insert_at_caret",
        "desktop.text.delete_previous_character",
        "desktop.text.delete_next_character",
        "desktop.text.delete_previous_word",
        "desktop.text.delete_next_word",
        "desktop.text.replace_previous_word",
        "desktop.text.replace_next_word",
        "desktop.text.select_previous_character",
        "desktop.text.select_next_character",
        "desktop.text.select_previous_word",
        "desktop.text.select_next_word",
        "desktop.text.select_current_line",
        "desktop.text.delete_current_line",
        "desktop.text.replace_current_line",
        "desktop.text.insert_line_above",
        "desktop.text.insert_line_below",
        "desktop.text.duplicate_line_above",
        "desktop.text.duplicate_line_below",
        "desktop.text.move_line_up",
        "desktop.text.move_line_down",
        "desktop.text.join_previous_line",
        "desktop.text.join_next_line",
        "desktop.text.split_line_at_caret",
        "desktop.text.indent_current_line",
        "desktop.text.outdent_current_line",
        "desktop.text.replace_selection",
        "desktop.text.read_previous_character",
        "desktop.text.read_next_character",
        "desktop.text.read_previous_word",
        "desktop.text.read_next_word",
        "desktop.text.read_current_line",
        "desktop.text.caret_start",
        "desktop.text.caret_end",
        "desktop.text.caret_previous",
        "desktop.text.caret_next",
        "desktop.text.caret_previous_word",
        "desktop.text.caret_next_word",
        "desktop.text.caret_line_start",
        "desktop.text.caret_line_end",
        "desktop.text.caret_describe",
        "desktop.text.paste_focused",
        "desktop.clipboard.read_text",
        "desktop.clipboard.write_text",
        "desktop.selection.select_named",
        "desktop.file_dialog.select_visible",
        "desktop.file_dialog.set_name",
        "desktop.file_dialog.set_location",
        "desktop.file_dialog.open_visible_folder",
        "desktop.file_dialog.decide",
        "desktop.standard_dialog.decide",
        "desktop.standard_dialog.read",
        "desktop.standard_dialog.dismiss",
        "desktop.tree.expand_named",
        "desktop.tree.collapse_named",
        "desktop.table.select_row",
        "desktop.tabs.select_named",
        "desktop.slider.set_percent",
        "desktop.progress.read_named",
        "desktop.standard_dialog.read",
        "desktop.checkbox.set_checked",
        "desktop.switch.set_enabled",
        "desktop.radio.select_named",
        "desktop.combo.select_item",
        "desktop.spin_button.set_value",
        "desktop.menu.activate_item",
        "desktop.permission_dialog.decide",
        "desktop.navigate.back",
        "desktop.window.next",
        "desktop.window.previous",
        "desktop.window.minimize",
        "desktop.window.maximize",
        "desktop.window.restore",
        "desktop.window.close",
        "desktop.window.workspace_previous",
        "desktop.window.workspace_next",
        "desktop.quick_settings",
        "desktop.notifications",
        "desktop.notifications.read",
        "desktop.notifications.dismiss",
    }
)
SEMANTIC_READ_ONLY = frozenset(
    {
        "desktop.context.describe",
        "desktop.controls.list",
        "desktop.text.read_focused",
        "desktop.text.read_selection",
        "desktop.text.read_previous_character",
        "desktop.text.read_next_character",
        "desktop.text.read_previous_word",
        "desktop.text.read_next_word",
        "desktop.text.read_current_line",
        "desktop.text.caret_describe",
        "desktop.clipboard.read_text",
        "desktop.progress.read_named",
        "desktop.notifications.read",
        "desktop.standard_dialog.read",
    }
)
# Default every semantic action to mutating. Only the small explicit set above
# may execute while the developer command adapter is in dry-run mode. Keeping
# this derived prevents new text/caret/selection actions from silently bypassing
# dry-run when their action name is added to SEMANTIC_ACTIONS.
SEMANTIC_MUTATIONS = SEMANTIC_ACTIONS - SEMANTIC_READ_ONLY


class GnomeSemanticExecutor:
    def __init__(
        self,
        desktop: Optional[SemanticDesktop] = None,
        clipboard_write: Callable[[str], None] = write_text,
        clipboard_read: Callable[[], str] = read_text,
    ) -> None:
        self._desktop = desktop
        self._clipboard_write = clipboard_write
        self._clipboard_read = clipboard_read

    def execute(self, request: ActionRequest, policy: ActionPolicy) -> ActionResult:
        del policy
        try:
            desktop = self._desktop or PyAtSpiDesktop()
            if request.action == "desktop.context.describe":
                context = desktop.context()
                return ActionResult("completed", context.spoken_location(), request.action)
            if request.action == "desktop.controls.list":
                context = desktop.context()
                return ActionResult("completed", context.spoken_controls(), request.action)
            if request.action == "desktop.control.activate":
                name = desktop.activate(int(request.target))
                return ActionResult("completed", f"{name} wurde ausgelöst.", request.action)
            if request.action == "desktop.control.activate_named":
                name = desktop.activate_named(request.target)
                return ActionResult("completed", f"{name} was activated.", request.action)
            if request.action in {"desktop.focus.next", "desktop.focus.previous"}:
                direction = 1 if request.action.endswith("next") else -1
                name = desktop.cycle_focus(direction)
                return ActionResult("completed", f"Fokus auf {name}.", request.action)
            if request.action == "desktop.focus.named":
                name = desktop.focus_named(request.target)
                return ActionResult("completed", f"Fokus auf {name}.", request.action)
            if request.action == "desktop.text.read_focused":
                name, value = desktop.read_focused_text()
                message = f"Text in {name}: {value}" if value else "Das fokussierte Textfeld ist leer."
                return ActionResult("completed", message, request.action)
            if request.action == "desktop.text.caret_describe":
                name, offset, count = desktop.focused_text_caret_position()
                return ActionResult(
                    "completed",
                    f"Textcursor in {name}: Offset {offset} von {count} Zeichen.",
                    request.action,
                )
            if request.action in {"desktop.text.set", "desktop.text.clear"}:
                value = request.target if request.action.endswith("set") else ""
                name = desktop.set_focused_text(value)
                return ActionResult("completed", f"Text in {name} wurde aktualisiert.", request.action)
            if request.action == "desktop.selection.select_named":
                name = desktop.select_named_item(request.target)
                return ActionResult("completed", f"{name} wurde ausgew\u00e4hlt.", request.action)
            if request.action == "desktop.file_dialog.select_visible":
                name = desktop.select_visible_file(request.target)
                return ActionResult(
                    "completed",
                    f"{name} wurde markiert; der Dialog wurde nicht best\u00e4tigt.",
                    request.action,
                )
            if request.action == "desktop.text.copy_focused":
                name, value = desktop.focused_text_for_clipboard()
                self._clipboard_write(value)
                return ActionResult(
                    "completed",
                    f"Der Inhalt von {name} wurde in die Zwischenablage kopiert.",
                    request.action,
                )
            if request.action == "desktop.text.copy_selection":
                name, value = desktop.selected_text_for_clipboard()
                self._clipboard_write(value)
                return ActionResult(
                    "completed",
                    f"Die Textauswahl aus {name} wurde in die Zwischenablage kopiert.",
                    request.action,
                )
            if request.action == "desktop.text.read_selection":
                name, value = desktop.selected_text_for_clipboard()
                spoken = " ".join(value.split())
                if len(spoken) > 1000:
                    spoken = spoken[:1000].rstrip() + " … Der restliche Inhalt wurde gekürzt."
                return ActionResult(
                    "completed",
                    f"Textauswahl in {name}: {spoken}",
                    request.action,
                )
            if request.action == "desktop.text.select_all":
                name = desktop.select_all_focused_text()
                return ActionResult(
                    "completed",
                    f"Der gesamte Text in {name} wurde ausgewählt.",
                    request.action,
                )
            if request.action == "desktop.text.clear_selection":
                name = desktop.clear_focused_text_selection()
                return ActionResult(
                    "completed",
                    f"Die Textauswahl in {name} wurde aufgehoben.",
                    request.action,
                )
            if request.action == "desktop.text.delete_selection":
                name = desktop.delete_focused_text_selection()
                return ActionResult(
                    "completed",
                    f"Die Textauswahl in {name} wurde gelöscht; der Inhalt wird nicht wiederholt.",
                    request.action,
                )
            if request.action == "desktop.text.insert_at_caret":
                name = desktop.insert_focused_text_at_caret(request.target)
                return ActionResult(
                    "completed",
                    f"Text wurde am Textcursor in {name} eingefügt; der Inhalt wird nicht wiederholt.",
                    request.action,
                )
            if request.action in {
                "desktop.text.delete_previous_character",
                "desktop.text.delete_next_character",
            }:
                direction = "previous" if request.action.endswith("previous_character") else "next"
                name = desktop.delete_focused_text_character(direction)
                location = "vor" if direction == "previous" else "nach"
                return ActionResult(
                    "completed",
                    f"Das Zeichen {location} dem Textcursor in {name} wurde gelöscht, sofern eines vorhanden war.",
                    request.action,
                )
            if request.action in {
                "desktop.text.delete_previous_word",
                "desktop.text.delete_next_word",
            }:
                direction = "previous" if request.action.endswith("previous_word") else "next"
                name = desktop.delete_focused_text_word(direction)
                location = "vor" if direction == "previous" else "nach"
                return ActionResult(
                    "completed",
                    f"Das Wort {location} dem Textcursor in {name} wurde gelöscht, sofern eines vorhanden war.",
                    request.action,
                )
            if request.action in {
                "desktop.text.replace_previous_word",
                "desktop.text.replace_next_word",
            }:
                direction = "previous" if request.action.endswith("previous_word") else "next"
                name = desktop.replace_focused_text_word(direction, request.target)
                location = "vor" if direction == "previous" else "nach"
                return ActionResult(
                    "completed",
                    f"Das Wort {location} dem Textcursor in {name} wurde ersetzt; der Inhalt wird nicht wiederholt.",
                    request.action,
                )
            if request.action == "desktop.text.replace_selection":
                name = desktop.replace_focused_text_selection(request.target)
                return ActionResult(
                    "completed",
                    f"Die Textauswahl in {name} wurde ersetzt; der Inhalt wird nicht wiederholt.",
                    request.action,
                )
            if request.action in {
                "desktop.text.read_previous_character",
                "desktop.text.read_next_character",
            }:
                direction = "previous" if request.action.endswith("previous_character") else "next"
                name, value = desktop.focused_text_character_at_caret(direction)
                location = "vor" if direction == "previous" else "nach"
                if not value:
                    message = f"In {name} gibt es kein Zeichen {location} dem Textcursor."
                else:
                    spoken = {" ": "Leerzeichen", "\t": "Tabulator", "\n": "Zeilenumbruch"}.get(
                        value, value
                    )
                    message = f"Zeichen {location} dem Textcursor in {name}: {spoken}"
                return ActionResult("completed", message, request.action)
            if request.action in {
                "desktop.text.read_previous_word",
                "desktop.text.read_next_word",
            }:
                direction = "previous" if request.action.endswith("previous_word") else "next"
                name, value = desktop.focused_text_word_at_caret(direction)
                location = "vor" if direction == "previous" else "nach"
                if value:
                    message = f"Wort {location} dem Textcursor in {name}: {value}"
                else:
                    message = f"In {name} gibt es kein Wort {location} dem Textcursor."
                return ActionResult("completed", message, request.action)
            if request.action == "desktop.text.read_current_line":
                name, value = desktop.focused_text_line_at_caret()
                message = (
                    f"Aktuelle Zeile in {name}: {value}"
                    if value
                    else f"Die aktuelle Zeile in {name} ist leer."
                )
                return ActionResult("completed", message, request.action)
            if request.action == "desktop.text.select_current_line":
                name = desktop.select_focused_text_line()
                return ActionResult(
                    "completed",
                    f"Die aktuelle Zeile in {name} wurde ausgewählt.",
                    request.action,
                )
            if request.action == "desktop.text.delete_current_line":
                name = desktop.delete_focused_text_line()
                return ActionResult(
                    "completed",
                    f"Die aktuelle Zeile in {name} wurde gelöscht.",
                    request.action,
                )
            if request.action == "desktop.text.replace_current_line":
                name = desktop.replace_focused_text_line(request.target)
                return ActionResult(
                    "completed",
                    f"Die aktuelle Zeile in {name} wurde ersetzt.",
                    request.action,
                )
            if request.action in {
                "desktop.text.insert_line_above",
                "desktop.text.insert_line_below",
            }:
                direction = "above" if request.action.endswith("above") else "below"
                name = desktop.insert_focused_text_line(direction, request.target)
                location = "oberhalb" if direction == "above" else "unterhalb"
                return ActionResult(
                    "completed",
                    f"In {name} wurde eine neue Zeile {location} eingefügt.",
                    request.action,
                )
            if request.action in {
                "desktop.text.duplicate_line_above",
                "desktop.text.duplicate_line_below",
            }:
                direction = "above" if request.action.endswith("above") else "below"
                name = desktop.duplicate_focused_text_line(direction)
                location = "oberhalb" if direction == "above" else "unterhalb"
                return ActionResult(
                    "completed",
                    f"Die aktuelle Zeile in {name} wurde {location} dupliziert.",
                    request.action,
                )
            if request.action in {
                "desktop.text.move_line_up",
                "desktop.text.move_line_down",
            }:
                direction = "up" if request.action.endswith("up") else "down"
                name = desktop.move_focused_text_line(direction)
                location = "nach oben" if direction == "up" else "nach unten"
                return ActionResult(
                    "completed",
                    f"Die aktuelle Zeile in {name} wurde {location} verschoben.",
                    request.action,
                )
            if request.action in {
                "desktop.text.join_previous_line",
                "desktop.text.join_next_line",
            }:
                direction = "previous" if request.action.endswith("previous_line") else "next"
                name = desktop.join_focused_text_line(direction)
                location = "vorherigen" if direction == "previous" else "nächsten"
                return ActionResult(
                    "completed",
                    f"Die aktuelle Zeile in {name} wurde mit der {location} Zeile verbunden.",
                    request.action,
                )
            if request.action == "desktop.text.split_line_at_caret":
                name = desktop.split_focused_text_line()
                return ActionResult(
                    "completed",
                    f"Die aktuelle Zeile in {name} wurde am Textcursor geteilt.",
                    request.action,
                )
            if request.action in {
                "desktop.text.indent_current_line",
                "desktop.text.outdent_current_line",
            }:
                direction = "outdent" if request.action.endswith("outdent_current_line") else "indent"
                name = desktop.indent_focused_text_line(direction)
                operation = "ausgerückt" if direction == "outdent" else "eingerückt"
                return ActionResult(
                    "completed",
                    f"Die aktuelle Zeile in {name} wurde {operation}.",
                    request.action,
                )
            if request.action in {
                "desktop.text.select_previous_word",
                "desktop.text.select_next_word",
            }:
                direction = "previous" if request.action.endswith("previous_word") else "next"
                name = desktop.select_focused_text_word(direction)
                location = "vor" if direction == "previous" else "nach"
                return ActionResult(
                    "completed",
                    f"Das Wort {location} dem Textcursor in {name} wurde ausgewählt, sofern eines vorhanden war.",
                    request.action,
                )
            if request.action in {
                "desktop.text.select_previous_character",
                "desktop.text.select_next_character",
            }:
                direction = "previous" if request.action.endswith("previous_character") else "next"
                name = desktop.select_focused_text_character(direction)
                location = "vor" if direction == "previous" else "nach"
                return ActionResult(
                    "completed",
                    f"Das Zeichen {location} dem Textcursor in {name} wurde ausgewählt, sofern eines vorhanden war.",
                    request.action,
                )
            if request.action in {
                "desktop.text.caret_previous_word",
                "desktop.text.caret_next_word",
            }:
                direction = "previous" if request.action.endswith("previous_word") else "next"
                name = desktop.move_focused_text_caret_word(direction)
                description = "am vorherigen Wortanfang" if direction == "previous" else "am nächsten Wortanfang"
                return ActionResult(
                    "completed",
                    f"Textcursor in {name} steht {description}.",
                    request.action,
                )
            if request.action in {
                "desktop.text.caret_line_start",
                "desktop.text.caret_line_end",
            }:
                boundary = "start" if request.action.endswith("line_start") else "end"
                name = desktop.move_focused_text_caret_line(boundary)
                description = "am Anfang" if boundary == "start" else "am Ende"
                return ActionResult(
                    "completed",
                    f"Textcursor in {name} steht {description} der aktuellen Zeile.",
                    request.action,
                )
            if request.action in {
                "desktop.text.caret_start",
                "desktop.text.caret_end",
                "desktop.text.caret_previous",
                "desktop.text.caret_next",
            }:
                position = request.action.removeprefix("desktop.text.caret_")
                name = desktop.move_focused_text_caret(position)
                descriptions = {
                    "start": "am Anfang",
                    "end": "am Ende",
                    "previous": "ein Zeichen weiter links",
                    "next": "ein Zeichen weiter rechts",
                }
                return ActionResult(
                    "completed",
                    f"Textcursor in {name} steht {descriptions[position]}.",
                    request.action,
                )
            if request.action == "desktop.text.paste_focused":
                value = self._clipboard_read()
                name = desktop.set_focused_clipboard_text(value)
                return ActionResult(
                    "completed",
                    f"Der Zwischenablageinhalt wurde in {name} eingefügt; der Inhalt wird nicht wiederholt.",
                    request.action,
                )
            if request.action == "desktop.clipboard.read_text":
                value = self._clipboard_read()
                spoken = " ".join(value.split())
                if len(spoken) > 1000:
                    spoken = spoken[:1000].rstrip() + " … Der restliche Inhalt wurde gekürzt."
                return ActionResult(
                    "completed",
                    f"Zwischenablage: {spoken}",
                    request.action,
                )
            if request.action == "desktop.clipboard.write_text":
                self._clipboard_write(request.target)
                return ActionResult(
                    "completed",
                    "Der diktierte Text wurde in die Zwischenablage geschrieben; der Inhalt wird nicht wiederholt.",
                    request.action,
                )
            if request.action == "desktop.file_dialog.set_name":
                field = desktop.set_file_name(request.target)
                return ActionResult(
                    "completed",
                    f"Dateiname in {field} wurde gesetzt; der Dialog wurde nicht gespeichert.",
                    request.action,
                )
            if request.action == "desktop.file_dialog.set_location":
                field = desktop.set_file_location(request.target)
                return ActionResult(
                    "completed",
                    f"Pfad in {field} wurde gesetzt; der Pfad wurde nicht geöffnet.",
                    request.action,
                )
            if request.action == "desktop.file_dialog.open_visible_folder":
                folder = desktop.open_visible_folder(request.target)
                return ActionResult(
                    "completed",
                    f"Ordner {folder} wurde geöffnet; der Dateidialog wurde nicht bestätigt.",
                    request.action,
                )
            if request.action == "desktop.file_dialog.decide":
                control = desktop.decide_file_dialog(request.target)
                state = "bestätigt" if request.target == "accept" else "abgebrochen"
                return ActionResult(
                    "completed",
                    f"Dateidialog wurde mit {control} {state}.",
                    request.action,
                )
            if request.action == "desktop.standard_dialog.decide":
                control = desktop.decide_standard_dialog(request.target)
                state = {
                    "accept": "bestätigt",
                    "cancel": "abgebrochen",
                    "retry": "wiederholt",
                    "apply": "angewendet",
                }[request.target]
                return ActionResult(
                    "completed",
                    f"Standarddialog wurde mit {control} {state}.",
                    request.action,
                )
            if request.action == "desktop.standard_dialog.read":
                title, messages = desktop.read_standard_dialog()
                return ActionResult(
                    "completed",
                    f"Dialog {title}. " + ". ".join(messages) + ".",
                    request.action,
                )
            if request.action == "desktop.standard_dialog.dismiss":
                control = desktop.dismiss_standard_dialog()
                return ActionResult(
                    "completed",
                    f"Standarddialog wurde mit {control} geschlossen.",
                    request.action,
                )
            if request.action in {"desktop.tree.expand_named", "desktop.tree.collapse_named"}:
                expanded = request.action.endswith("expand_named")
                item = desktop.set_named_tree_item_expanded(request.target, expanded)
                state = "aufgeklappt" if expanded else "zugeklappt"
                return ActionResult(
                    "completed",
                    f"Baumelement {item} wurde {state}.",
                    request.action,
                )
            if request.action == "desktop.table.select_row":
                row = desktop.select_table_row(request.target)
                return ActionResult(
                    "completed",
                    f"Tabellenzeile {row} wurde ausgewählt.",
                    request.action,
                )
            if request.action == "desktop.tabs.select_named":
                tab = desktop.select_named_tab(request.target)
                return ActionResult(
                    "completed",
                    f"Registerkarte {tab} wurde ausgewählt.",
                    request.action,
                )
            if request.action == "desktop.slider.set_percent":
                percent = request.arguments["percent"]
                slider = desktop.set_named_slider(request.target, percent)
                return ActionResult(
                    "completed",
                    f"Schieberegler {slider} wurde auf {percent} Prozent gesetzt.",
                    request.action,
                )
            if request.action == "desktop.progress.read_named":
                progress, percent = desktop.read_named_progress(request.target)
                return ActionResult(
                    "completed",
                    f"Fortschritt {progress}: {percent} Prozent.",
                    request.action,
                )
            if request.action == "desktop.checkbox.set_checked":
                checked = request.arguments["checked"]
                checkbox = desktop.set_named_checkbox(request.target, checked)
                state = "aktiviert" if checked else "deaktiviert"
                return ActionResult(
                    "completed",
                    f"Kontrollkästchen {checkbox} wurde {state}.",
                    request.action,
                )
            if request.action == "desktop.switch.set_enabled":
                enabled = request.arguments["checked"]
                switch = desktop.set_named_switch(request.target, enabled)
                state = "eingeschaltet" if enabled else "ausgeschaltet"
                return ActionResult(
                    "completed",
                    f"Schalter {switch} wurde {state}.",
                    request.action,
                )
            if request.action == "desktop.radio.select_named":
                radio = desktop.select_named_radio(request.target)
                return ActionResult(
                    "completed",
                    f"Optionsfeld {radio} wurde ausgewählt.",
                    request.action,
                )
            if request.action == "desktop.combo.select_item":
                item = desktop.select_combo_item(request.target, request.arguments["item"])
                return ActionResult(
                    "completed",
                    f"Auswahllisteneintrag {item} wurde ausgewählt.",
                    request.action,
                )
            if request.action == "desktop.spin_button.set_value":
                number = request.arguments["value"]
                spin = desktop.set_named_spin_button(request.target, number)
                return ActionResult(
                    "completed",
                    f"Zahlenfeld {spin} wurde auf {number:g} gesetzt.",
                    request.action,
                )
            if request.action == "desktop.menu.activate_item":
                item = desktop.activate_menu_item(request.target)
                return ActionResult(
                    "completed",
                    f"Menüeintrag {item} wurde ausgelöst.",
                    request.action,
                )
            if request.action == "desktop.permission_dialog.decide":
                control = desktop.decide_permission(request.target)
                return ActionResult(
                    "completed",
                    f"Berechtigungsentscheidung {control} wurde ausgelöst.",
                    request.action,
                )
            if request.action == "desktop.navigate.back":
                name = desktop.navigate_back()
                return ActionResult("completed", f"{name} wurde ausgelöst.", request.action)
            if request.action in {"desktop.window.next", "desktop.window.previous"}:
                direction = 1 if request.action.endswith("next") else -1
                name = desktop.cycle_window(direction)
                return ActionResult("completed", f"Fenster {name} ist jetzt aktiv.", request.action)
            if request.action.startswith("desktop.window."):
                operation = request.action.rsplit(".", 1)[-1]
                name = desktop.window_action(operation)
                return ActionResult(
                    "completed", f"Fenster {name}: {operation} wurde ausgelöst.", request.action
                )
            if request.action in {
                "desktop.overview",
                "desktop.applications",
                "desktop.quick_settings",
                "desktop.notifications",
            }:
                operation = request.action.rsplit(".", 1)[-1]
                name = desktop.shell_action(operation)
                return ActionResult(
                    "completed", f"GNOME Shell: {name} wurde ausgelöst.", request.action
                )
            if request.action == "desktop.notifications.read":
                messages = desktop.read_notifications()
                message = (
                    "Sichtbare Benachrichtigungen. "
                    + ". ".join(
                        f"Nummer {index}: {value}"
                        for index, value in enumerate(messages, start=1)
                    )
                    + "."
                    if messages
                    else "Es sind keine sichtbaren Benachrichtigungen vorhanden."
                )
                return ActionResult("completed", message, request.action)
            if request.action == "desktop.notifications.dismiss":
                number = desktop.dismiss_notification(int(request.target))
                return ActionResult(
                    "completed",
                    f"Benachrichtigung Nummer {number} wurde verworfen.",
                    request.action,
                )
        except (GnomeAdapterError, RuntimeError, TypeError, ValueError) as exc:
            return ActionResult("failed", str(exc), request.action)
        return ActionResult("failed", "Keine semantische GNOME-Aktion verfügbar.", request.action)


class SessionExecutor:
    """Route semantic session actions locally and fixed commands elsewhere."""

    def __init__(self, command_executor: Any, semantic_executor: Optional[Any] = None) -> None:
        self.command_executor = command_executor
        self.semantic_executor = semantic_executor or GnomeSemanticExecutor()

    def execute(self, request: ActionRequest, policy: ActionPolicy) -> ActionResult:
        if request.action in SEMANTIC_ACTIONS:
            if request.action in SEMANTIC_MUTATIONS and bool(
                getattr(self.command_executor, "dry_run", False)
            ):
                return ActionResult(
                    "dry_run",
                    "validated semantic action; execution disabled",
                    request.action,
                )
            return self.semantic_executor.execute(request, policy)
        return self.command_executor.execute(request, policy)
