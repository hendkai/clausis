"""Bounded semantic GNOME control through the AT-SPI accessibility tree.

No screen coordinates, screenshots or synthesized pointer events are used.
The adapter reads the current accessibility state again immediately before an
activation so a stale numbered target cannot silently select another window.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
import re
from typing import Any, Dict, Iterable, List, Optional, Protocol, Sequence, Tuple

from .models import ActionRequest, ActionResult
from .policy import ActionPolicy
from .text_units import (
    GRANULARITIES,
    granular_chunk,
    sentence_bounds,
    word_bounds,
)


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


class DialogKind(str, Enum):
    FILE_OPEN = "file_open"
    FILE_SAVE = "file_save"
    PERMISSION = "permission"
    MESSAGE = "message"


@dataclass(frozen=True)
class DialogContext:
    kind: DialogKind
    title: str
    affirmative: str
    negative: str
    buttons: Tuple[str, ...]

    def spoken(self) -> str:
        title = self.title or "unbenannter Dialog"
        if self.kind is DialogKind.PERMISSION:
            return (
                f"Achtung: {title} ist eine Berechtigungs- oder Anmeldeabfrage. "
                "Clausis bestätigt so etwas nicht per Sprache. "
                "Bitte entscheiden Sie über Tastatur oder Orca. "
                "Sie können Dialog abbrechen sagen."
            )
        if self.kind is DialogKind.FILE_SAVE:
            hint = "Diktieren Sie den Dateinamen und sagen Sie dann Dialog bestätigen."
        elif self.kind is DialogKind.FILE_OPEN:
            hint = "Sagen Sie Was kann ich hier tun, um die Auswahl zu hören."
        else:
            hint = "Sagen Sie Dialog bestätigen oder Dialog abbrechen."
        options = ", ".join(self.buttons) if self.buttons else "keine benannten Schaltflächen"
        return f"{title}. Verfügbar: {options}. {hint}"


class SemanticDesktop(Protocol):
    def context(self) -> DesktopContext:
        ...

    def activate(self, number: int) -> str:
        ...

    def cycle_window(self, direction: int) -> str:
        ...

    def navigate_back(self) -> str:
        ...

    def close_application(self, name: str) -> str:
        ...

    def read_text_field(self) -> str:
        ...

    def insert_text(self, text: str) -> str:
        ...

    def delete_word(self) -> str:
        ...

    def clear_text(self) -> str:
        ...

    def copy_selection(self) -> str:
        ...

    def paste(self) -> str:
        ...

    def move_caret(self, direction: str) -> str:
        ...

    def read_from_caret(self) -> str:
        ...

    def insert_newline(self) -> str:
        ...

    def insert_paragraph(self) -> str:
        ...

    def select_word(self) -> str:
        ...

    def select_sentence(self) -> str:
        ...

    def select_all(self) -> str:
        ...

    def replace_selection(self, replacement: str) -> str:
        ...

    def delete_selection(self) -> str:
        ...

    def edit_undo(self) -> str:
        ...

    def edit_redo(self) -> str:
        ...

    def read_granular(self, granularity: str) -> str:
        ...

    def list_files(self) -> str:
        ...

    def select_file(self, number: int) -> str:
        ...

    def open_folder(self, number: int) -> str:
        ...

    def describe_dialog(self) -> DialogContext:
        ...

    def accept_dialog(self) -> str:
        ...

    def cancel_dialog(self) -> str:
        ...


#: Shell surfaces that AT-SPI cannot reach, mapped to the extension's
#: parameterless D-Bus methods and the sentence Clausis speaks afterwards.
SHELL_ACTIONS: Dict[str, Tuple[str, str]] = {
    "desktop.overview": ("ShowOverview", "Die Übersicht ist geöffnet."),
    "desktop.applications": ("ShowApplications", "Die Anwendungsübersicht ist geöffnet."),
    "desktop.quick_settings": ("ShowQuickSettings", "Die Schnelleinstellungen sind geöffnet."),
    "desktop.notifications": ("ShowNotifications", "Die Benachrichtigungen sind geöffnet."),
    "desktop.window.minimize": ("MinimizeWindow", "Das Fenster wurde minimiert."),
    "desktop.window.maximize": ("MaximizeWindow", "Das Fenster wurde maximiert."),
    "desktop.window.unmaximize": ("UnmaximizeWindow", "Das Fenster wurde wiederhergestellt."),
    "desktop.workspace.next": ("NextWorkspace", "Sie sind auf der nächsten Arbeitsfläche."),
    "desktop.workspace.previous": ("PreviousWorkspace", "Sie sind auf der vorherigen Arbeitsfläche."),
    "desktop.window.to_next_workspace": (
        "MoveWindowToNextWorkspace",
        "Das Fenster ist auf der nächsten Arbeitsfläche.",
    ),
    "desktop.window.to_previous_workspace": (
        "MoveWindowToPreviousWorkspace",
        "Das Fenster ist auf der vorherigen Arbeitsfläche.",
    ),
}


#: The one shell method whose return value Clausis speaks instead of a canned
#: sentence, so it is not part of :data:`SHELL_ACTIONS`.
CLIPBOARD_READ_METHOD = "ReadClipboard"


class GnomeShell(Protocol):
    def invoke(self, method: str) -> str:
        ...


def _dbus_method_name(method: str) -> str:
    """Convert ``ShowQuickSettings`` to the ``call_show_quick_settings`` proxy."""

    if not re.fullmatch(r"[A-Z][A-Za-z0-9]{0,63}", method):
        raise GnomeAdapterError("Unbekannte Shell-Methode.")
    snake = re.sub(r"(?<!^)(?=[A-Z])", "_", method).lower()
    return f"call_{snake}"


class DbusGnomeShell:
    """Client for the Clausis GNOME Shell extension.

    GNOME Shell itself is not part of the AT-SPI tree, and Wayland offers no
    supported way to reach these surfaces from outside the compositor.  The
    extension in ``packaging/gnome-shell`` exports a private, parameterless
    session-bus interface; nothing else about the shell is exposed, and the
    caller can only name a method from :data:`SHELL_ACTIONS`.
    """

    BUS_NAME = "org.clausis.Shell1"
    PATH = "/org/clausis/Shell1"
    INTERFACE = "org.clausis.Shell1"

    def invoke(self, method: str) -> str:
        import asyncio

        return asyncio.run(self._call(_dbus_method_name(method)))

    async def _call(self, method: str) -> str:
        try:
            from dbus_next import BusType
            from dbus_next.aio import MessageBus
        except ImportError as exc:
            raise GnomeAdapterError("Die Sitzungs-D-Bus-Anbindung ist nicht installiert.") from exc
        try:
            bus = await MessageBus(bus_type=BusType.SESSION).connect()
        except Exception as exc:
            raise GnomeAdapterError("Die GNOME-Sitzung ist nicht erreichbar.") from exc
        try:
            node = await bus.introspect(self.BUS_NAME, self.PATH)
            interface = bus.get_proxy_object(self.BUS_NAME, self.PATH, node).get_interface(
                self.INTERFACE
            )
            reply = await getattr(interface, method)()
        except Exception as exc:
            raise GnomeAdapterError(
                "Die Clausis-Erweiterung für die GNOME-Shell ist nicht aktiv."
            ) from exc
        finally:
            bus.disconnect()
        return str(reply)[:240]


class PyAtSpiDesktop:
    """Real GNOME provider, imported lazily so non-GNOME tests still run."""

    MAX_NODES = 2500
    MAX_DEPTH = 24
    MAX_CONTROLS = 30
    MAX_ANCESTORS = 24
    MAX_FIELD_CHARS = 2000
    CLOSE_ACTIONS = frozenset({"close", "schließen", "beenden", "quit"})
    CLOSE_LABELS = frozenset({"close", "schließen", "beenden", "fenster schließen", "close window"})
    PROTECTED_ROLES = frozenset({"password text", "password"})
    TERMINAL_ROLES = frozenset({"terminal"})
    DIALOG_ROLES = frozenset({"dialog", "alert", "file chooser", "color chooser", "font chooser"})
    #: Top-level roles that count as a window.  A GTK file chooser reports the
    #: role "file chooser", so leaving the dialog roles out here made an active
    #: file dialog invisible to orientation, dictation and closing alike.
    WINDOW_ROLES = frozenset({"frame", "window"}) | DIALOG_ROLES
    AFFIRMATIVE_LABELS = frozenset(
        {
            "öffnen", "speichern", "ok", "ja", "anwenden", "weiter", "ersetzen",
            "open", "save", "yes", "apply", "continue", "replace",
        }
    )
    NEGATIVE_LABELS = frozenset(
        {
            "abbrechen", "nein", "schließen", "verwerfen", "zurück",
            "cancel", "no", "close", "discard",
        }
    )
    #: Words that mark a dialog as a permission or authentication prompt.  A
    #: false positive only costs a spoken refusal; a false negative would let a
    #: voice command approve something it must never approve.
    PERMISSION_WORDS = (
        "authentifiz", "berechtigung", "erlaub", "zugriff", "passwort", "anmeld",
        "kennwort", "administrator", "legitimier", "entsperr",
        "authentic", "permission", "password", "allow", "access", "credential",
        "privilege", "unlock", "sudo", "polkit", "keyring", "schlüsselbund",
    )
    COPY_ACTIONS = frozenset({"copy", "kopieren"})
    PASTE_ACTIONS = frozenset({"paste", "einfügen"})
    #: Named actions for whole-field selection.  The published English names
    #: cover GTK and Qt; a widget exposing none of them still gets an honest
    #: text-interface selection instead of a key event.
    SELECT_ALL_ACTIONS = frozenset({"select all", "select-all", "selectall"})
    #: Named actions for the widget's own undo/redo, so no synthetic
    #: keyboard shortcut is ever needed for editing history.
    UNDO_ACTIONS = frozenset({"undo", "rückgängig"})
    REDO_ACTIONS = frozenset({"redo", "wiederherstellen"})
    SAVE_WORDS = ("speichern", "save", "export", "sichern")
    OPEN_WORDS = ("öffnen", "open", "datei aus", "file chooser", "import", "auswähl", "select")

    def __init__(self) -> None:
        try:
            import pyatspi
        except ImportError as exc:
            raise GnomeAdapterError("GNOME-Zugriff ist nicht installiert.") from exc
        self._atspi = pyatspi

    def context(self) -> DesktopContext:
        application, window = self._active_window()
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
        node, actions = controls[number - 1]
        action = node.queryAction()
        preferred = ("click", "press", "activate", "toggle", "open")
        chosen = next(
            (index for name in preferred for index, value in enumerate(actions) if value.casefold() == name),
            0,
        )
        if not action.doAction(chosen):
            raise GnomeAdapterError("Das Bedienelement hat die Aktion abgelehnt.")
        return self._name(node) or self._role(node)

    def close_application(self, name: str) -> str:
        """Close a named window through its own accessible close action.

        No pointer event, key event or screen coordinate is used: Clausis only
        invokes an action the application itself publishes.  Applications
        without an accessible close action are reported honestly instead of
        being terminated by force.
        """

        needle = " ".join(name.split()).casefold()
        if not needle:
            raise GnomeAdapterError("Es wurde keine Anwendung genannt.")
        for application, window in self._visible_windows():
            haystack = f"{self._name(application)} {self._name(window)}".casefold()
            if needle not in haystack:
                continue
            label = self._name(window) or self._name(application) or needle
            if self._invoke_named_action(window, self.CLOSE_ACTIONS):
                return label
            for node in self._walk(window):
                if self._role(node) not in {"push button", "button"}:
                    continue
                if self._name(node).casefold() not in self.CLOSE_LABELS:
                    continue
                if self._invoke_named_action(node, self.CLOSE_ACTIONS | {"click", "press"}):
                    return label
            raise GnomeAdapterError(
                f"{label} bietet keine zugängliche Schließen-Aktion an."
            )
        raise GnomeAdapterError(f"Ich habe kein offenes Fenster für {name} gefunden.")

    def _focused_editable(self) -> Any:
        """Return the focused editable node, or refuse to dictate into it.

        Dictation is the one action that puts attacker-influenceable text into
        an application, so the refusals matter more than the feature: Clausis
        never writes into a password field and never into a terminal, where a
        line of text is a command.  Everything else is an ordinary, visible and
        correctable text edit and therefore stays low risk.
        """

        application, window = self._active_window()
        if self._is_terminal(window) or self._is_terminal(application):
            raise GnomeAdapterError(
                "In einem Terminal diktiert Clausis nicht. Dort wäre Text ein Befehl."
            )
        node = self._find_state(window, self._atspi.STATE_FOCUSED)
        if node is None:
            raise GnomeAdapterError("Es ist gerade kein Eingabefeld ausgewählt.")
        # AT-SPI2 has no "protected" state (that was ATK-only); a password
        # field is recognised purely by its "password text" role here.
        if self._role(node).casefold() in self.PROTECTED_ROLES:
            raise GnomeAdapterError(
                "Das ist ein Passwortfeld. Bitte tippen Sie es selbst über die Tastatur."
            )
        if self._is_terminal(node) or self._has_terminal_ancestor(node):
            raise GnomeAdapterError(
                "In einem Terminal diktiert Clausis nicht. Dort wäre Text ein Befehl."
            )
        if not self._has_state(node, self._atspi.STATE_EDITABLE):
            raise GnomeAdapterError(
                "Das ausgewählte Element nimmt keinen Text an. Sagen Sie Was kann ich hier tun."
            )
        return node

    def _is_terminal(self, node: Any) -> bool:
        return self._role(node).casefold() in self.TERMINAL_ROLES

    def _has_terminal_ancestor(self, node: Any) -> bool:
        current = node
        for _ in range(self.MAX_ANCESTORS):
            try:
                current = current.parent
            except Exception:
                return False
            if current is None:
                return False
            if self._is_terminal(current):
                return True
        return False

    @staticmethod
    def _field_text(node: Any) -> str:
        try:
            text = node.queryText()
            return str(text.getText(0, text.characterCount) or "")
        except Exception as exc:
            raise GnomeAdapterError("Der Feldinhalt ist nicht lesbar.") from exc

    def read_text_field(self) -> str:
        content = self._field_text(self._focused_editable())
        if not content.strip():
            return ""
        return content[: self.MAX_FIELD_CHARS]

    def insert_text(self, text: str) -> str:
        """Insert dictated text at the caret and report the resulting content.

        The result is read back from the accessibility tree instead of being
        assumed, so a field that silently rejected or transformed the input
        cannot be reported as a success.
        """

        node = self._focused_editable()
        try:
            editable = node.queryEditableText()
            caret = int(node.queryText().caretOffset)
        except Exception as exc:
            raise GnomeAdapterError("Das Feld erlaubt kein Einfügen.") from exc
        if caret < 0:
            caret = 0
        if not editable.insertText(caret, text, len(text)):
            raise GnomeAdapterError("Das Feld hat den Text abgelehnt.")
        content = self._field_text(node)
        if text not in content:
            raise GnomeAdapterError("Der Text steht nach dem Einfügen nicht im Feld.")
        return content[: self.MAX_FIELD_CHARS]

    def delete_word(self) -> str:
        node = self._focused_editable()
        content = self._field_text(node)
        stripped = content.rstrip()
        if not stripped:
            raise GnomeAdapterError("Das Feld ist bereits leer.")
        cut = stripped.rfind(" ") + 1
        try:
            node.queryEditableText().deleteText(cut, len(content))
        except Exception as exc:
            raise GnomeAdapterError("Das Feld erlaubt kein Löschen.") from exc
        return self._field_text(node)[: self.MAX_FIELD_CHARS]

    def clear_text(self) -> str:
        node = self._focused_editable()
        content = self._field_text(node)
        if not content:
            return ""
        try:
            node.queryEditableText().deleteText(0, len(content))
        except Exception as exc:
            raise GnomeAdapterError("Das Feld erlaubt kein Löschen.") from exc
        remaining = self._field_text(node)
        if remaining:
            raise GnomeAdapterError("Das Feld konnte nicht vollständig geleert werden.")
        return ""

    def copy_selection(self) -> str:
        """Copy through the widget's own accessible copy action.

        Password fields are refused: even where a toolkit exposes a copy action
        on one, putting a secret on the shared clipboard by voice is not a
        service Clausis should offer.
        """

        _, window = self._active_window()
        node = self._find_state(window, self._atspi.STATE_FOCUSED)
        if node is None:
            raise GnomeAdapterError("Es ist gerade kein Element ausgewählt.")
        # Password fields are recognised by role only — AT-SPI2 defines no
        # "protected" state, so the role check is the entire protection.
        if self._role(node).casefold() in self.PROTECTED_ROLES:
            raise GnomeAdapterError("Aus einem Passwortfeld kopiert Clausis nicht.")
        if not self._invoke_named_action(node, self.COPY_ACTIONS):
            raise GnomeAdapterError("Dieses Element bietet keine Kopieren-Aktion an.")
        return self._name(node) or self._role(node)

    def paste(self) -> str:
        """Paste into the focused field, with the dictation refusals applied.

        Clipboard content is attacker-influenceable — another process can place
        text there — so pasting reuses exactly the checks that guard dictation,
        which is what keeps a hijacked clipboard out of a terminal.
        """

        node = self._focused_editable()
        if not self._invoke_named_action(node, self.PASTE_ACTIONS):
            raise GnomeAdapterError("Dieses Feld bietet keine Einfügen-Aktion an.")
        return self._field_text(node)[: self.MAX_FIELD_CHARS]

    # ------------------------------------------------------------------
    # Cursor navigation inside the focused field (voice-only editing).
    # ------------------------------------------------------------------

    def move_caret(self, direction: str) -> str:
        """Move the caret in the focused field and report the new position.

        Uses only the AT-SPI component/text interfaces — no key events, no
        pointer, no screen coordinates.  A caret move that the field rejected
        or silently ignored is reported honestly instead of being assumed,
        which is why the offset is read back after the move.
        """

        node = self._focused_editable()
        try:
            text = node.queryText()
            count = int(text.characterCount)
            current = int(text.caretOffset)
        except Exception as exc:
            raise GnomeAdapterError("Die Cursorposition ist nicht lesbar.") from exc
        if direction == "start":
            target = 0
        elif direction == "end":
            target = count
        elif direction == "word_next":
            target = self._next_word_offset(self._field_text(node), current)
        elif direction == "word_previous":
            target = self._previous_word_offset(self._field_text(node), current)
        else:
            raise GnomeAdapterError(f"Unbekannte Cursorrichtung {direction}.")
        target = max(0, min(target, count))
        self._focus_node(node, "Das Feld lässt sich nicht fokussieren.")
        try:
            moved = node.queryText().setCaretOffset(target)
        except Exception as exc:
            raise GnomeAdapterError("Das Feld hat die Cursorbewegung abgelehnt.") from exc
        if moved is False:
            raise GnomeAdapterError("Das Feld hat die Cursorbewegung abgelehnt.")
        try:
            after = int(node.queryText().caretOffset)
        except Exception as exc:
            raise GnomeAdapterError("Die neue Cursorposition ist nicht lesbar.") from exc
        if after != target:
            raise GnomeAdapterError(
                "Der Cursor ist nicht an der gemeldeten Position gelandet."
            )
        return self._spoken_caret_position(after, count)

    def insert_newline(self) -> str:
        """Insert one line break at the caret and report the field content.

        "Neue Zeile" is its own typed action because a line break can never
        ride inside a dictated target: the request schema forbids control
        characters on every trust boundary.  The same read-back check as for
        dictation applies, so a field that swallowed the break is not reported
        as written.
        """

        content = self.insert_text("\n")
        return content

    def insert_paragraph(self) -> str:
        """Insert a paragraph break (one blank line) at the caret."""

        return self.insert_text("\n\n")

    # ------------------------------------------------------------------
    # Selection, replacement, undo/redo and granular reading.
    # ------------------------------------------------------------------

    def _selection(self, node: Any) -> Tuple[int, int]:
        """Current selection of a text interface, as ``(start, end)``.

        pyatspi returns a plain sequence ``(start, end)``; a missing or empty
        selection reads as the caret position itself.
        """

        try:
            selection = node.queryText().getSelection(0)
            start, end = int(selection[0]), int(selection[1])
        except Exception as exc:
            raise GnomeAdapterError("Die Auswahl ist nicht lesbar.") from exc
        if start > end:
            start, end = end, start
        return start, end

    def _apply_selection(self, node: Any, start: int, end: int) -> Tuple[int, int]:
        """Set the selection through the AT-SPI text interface and verify it."""

        try:
            text = node.queryText()
            count = int(text.characterCount)
            if not 0 <= start <= end <= count:
                raise GnomeAdapterError("Die Auswahl liegt außerhalb des Feldes.")
            if not text.addSelection(start, end):
                raise GnomeAdapterError("Das Feld hat die Auswahl abgelehnt.")
        except GnomeAdapterError:
            raise
        except Exception as exc:
            raise GnomeAdapterError("Das Feld hat die Auswahl abgelehnt.") from exc
        applied_start, applied_end = self._selection(node)
        if (applied_start, applied_end) != (start, end):
            raise GnomeAdapterError("Die Auswahl ist nicht an der gemeldeten Stelle.")
        return applied_start, applied_end

    def select_word(self) -> str:
        """Select the word at the caret and report it."""

        node = self._focused_editable()
        content = self._field_text(node)
        caret = self._caret_offset(node)
        start, end = word_bounds(content, caret)
        if start >= end:
            raise GnomeAdapterError("Hier gibt es kein Wort zum Auswählen.")
        self._apply_selection(node, start, end)
        return content[start:end]

    def select_sentence(self) -> str:
        """Select the sentence at the caret and report it."""

        node = self._focused_editable()
        content = self._field_text(node)
        caret = self._caret_offset(node)
        start, end = sentence_bounds(content, caret)
        if start >= end:
            raise GnomeAdapterError("Hier gibt es keinen Satz zum Auswählen.")
        self._apply_selection(node, start, end)
        return content[start:end]

    def select_all(self) -> str:
        """Select the whole field through the widget's own select-all action."""

        node = self._focused_editable()
        content = self._field_text(node)
        if not content:
            raise GnomeAdapterError("Das Feld ist leer.")
        if not self._invoke_named_action(node, self.SELECT_ALL_ACTIONS):
            # Widgets without a published select-all action still get the
            # selection through the text interface, which is equally honest
            # because the result is verified afterwards.
            self._apply_selection(node, 0, len(content))
        else:
            start, end = self._selection(node)
            if (start, end) != (0, len(content)):
                raise GnomeAdapterError("Die Auswahl ist nicht an der gemeldeten Stelle.")
        return content[: self.MAX_FIELD_CHARS]

    def replace_selection(self, replacement: str) -> str:
        """Replace the current selection with dictated text, verified.

        The replacement is visible in the field, spoken back and correctable,
        and the same password/terminal refusals as dictation apply because the
        focused editable is re-resolved — which keeps the risk low.
        """

        node = self._focused_editable()
        start, end = self._selection(node)
        if start >= end:
            # "Ersetzen" without a selection refuses instead of silently
            # degrading into an insertion: a voice-only user must be able to
            # trust that the command did what its name says, or hear why not.
            raise GnomeAdapterError("Es ist nichts ausgewählt.")
        try:
            editable = node.queryEditableText()
            removed = editable.deleteText(start, end)
            inserted = editable.insertText(start, replacement, len(replacement))
        except Exception as exc:
            raise GnomeAdapterError("Das Feld erlaubt das Ersetzen nicht.") from exc
        if not removed or not inserted:
            raise GnomeAdapterError("Das Feld hat die Ersetzung abgelehnt.")
        content = self._field_text(node)
        if replacement not in content:
            raise GnomeAdapterError("Die Ersetzung steht nicht im Feld.")
        return content[: self.MAX_FIELD_CHARS]

    def delete_selection(self) -> str:
        """Delete the current selection through the editable-text interface."""

        node = self._focused_editable()
        start, end = self._selection(node)
        if start >= end:
            raise GnomeAdapterError("Es ist nichts ausgewählt.")
        try:
            if not node.queryEditableText().deleteText(start, end):
                raise GnomeAdapterError("Das Feld hat das Löschen abgelehnt.")
        except GnomeAdapterError:
            raise
        except Exception as exc:
            raise GnomeAdapterError("Das Feld hat das Löschen abgelehnt.") from exc
        remaining = self._field_text(node)
        return remaining[: self.MAX_FIELD_CHARS]

    def edit_undo(self) -> str:
        """Undo the last field edit through the widget's own undo action."""

        return self._edit_history_action(self.UNDO_ACTIONS, "rückgängig")

    def edit_redo(self) -> str:
        """Redo the last undone field edit through the widget's redo action."""

        return self._edit_history_action(self.REDO_ACTIONS, "wiederhergestellt")

    def _edit_history_action(self, names: Any, participle: str) -> str:
        node = self._focused_editable()
        if not self._invoke_named_action(node, names):
            raise GnomeAdapterError(
                "Dieses Feld bietet keine eigene Rückgängig-Aktion an."
            )
        return participle

    def _caret_offset(self, node: Any) -> int:
        try:
            caret = int(node.queryText().caretOffset)
        except Exception as exc:
            raise GnomeAdapterError("Die Cursorposition ist nicht lesbar.") from exc
        return max(0, caret)

    def read_granular(self, granularity: str) -> str:
        """Speak the unit (character/word/line/sentence/paragraph) at the caret.

        Reading stops at the chunk limit so an overlong unit cannot turn into
        an endless monologue; the caller hears the truncation in the result.
        """

        if granularity not in GRANULARITIES:
            raise GnomeAdapterError(f"Unbekannte Granularität {granularity}.")
        node = self._focused_editable()
        content = self._field_text(node)
        caret = self._caret_offset(node)
        text, _next = granular_chunk(content, granularity, caret)
        return text[: self.MAX_FIELD_CHARS]

    @staticmethod
    def _next_word_offset(content: str, caret: int) -> int:
        if not content:
            return caret
        pos = min(caret, len(content))
        # If the caret sits inside a separator run, skip it first; otherwise
        # skip the rest of the current word, then the separator run.
        if pos < len(content) and content[pos].isspace():
            while pos < len(content) and content[pos].isspace():
                pos += 1
            return pos
        while pos < len(content) and not content[pos].isspace():
            pos += 1
        while pos < len(content) and content[pos].isspace():
            pos += 1
        return pos

    @staticmethod
    def _previous_word_offset(content: str, caret: int) -> int:
        if not content:
            return 0
        pos = min(caret, len(content))
        # Skip separators to the left, then walk back over the word.
        while pos > 0 and content[pos - 1].isspace():
            pos -= 1
        while pos > 0 and not content[pos - 1].isspace():
            pos -= 1
        return pos

    def read_from_caret(self) -> str:
        """Speak the field content from the caret to the end of the field."""

        node = self._focused_editable()
        try:
            text = node.queryText().getText(node.queryText().caretOffset, node.queryText().characterCount)
        except Exception as exc:
            raise GnomeAdapterError("Der Feldinhalt ist nicht lesbar.") from exc
        return str(text or "")[: self.MAX_FIELD_CHARS]

    @staticmethod
    def _spoken_caret_position(offset: int, total: int) -> str:
        return f"Der Cursor steht auf Position {offset} von {total}."

    def _dialog_window(self) -> Any:
        _, window = self._active_window()
        if self._role(window).casefold() not in self.DIALOG_ROLES:
            raise GnomeAdapterError("Es ist gerade kein Dialog offen.")
        return window

    def _dialog_buttons(self, window: Any) -> List[Tuple[str, Any]]:
        buttons: List[Tuple[str, Any]] = []
        for node in self._walk(window):
            if self._role(node).casefold() not in {"push button", "button"}:
                continue
            if not self._has_state(node, self._atspi.STATE_SHOWING):
                continue
            name = self._name(node).strip()
            if name:
                buttons.append((name, node))
            if len(buttons) >= self.MAX_CONTROLS:
                break
        return buttons

    def _classify_dialog(self, window: Any, labels: Sequence[str]) -> DialogKind:
        haystack = " ".join([self._name(window), self._role(window), *labels]).casefold()
        if any(word in haystack for word in self.PERMISSION_WORDS):
            return DialogKind.PERMISSION
        for node in self._walk(window):
            # Password widgets are recognised by their "password text" role;
            # AT-SPI2 has no separate "protected" state to consult.
            if self._role(node).casefold() in self.PROTECTED_ROLES:
                return DialogKind.PERMISSION
        if any(word in haystack for word in self.SAVE_WORDS):
            return DialogKind.FILE_SAVE
        if any(word in haystack for word in self.OPEN_WORDS):
            return DialogKind.FILE_OPEN
        return DialogKind.MESSAGE

    def describe_dialog(self) -> DialogContext:
        window = self._dialog_window()
        buttons = self._dialog_buttons(window)
        labels = [name for name, _ in buttons]
        kind = self._classify_dialog(window, labels)
        return DialogContext(
            kind=kind,
            title=self._name(window),
            affirmative=self._match_label(labels, self.AFFIRMATIVE_LABELS),
            negative=self._match_label(labels, self.NEGATIVE_LABELS),
            buttons=tuple(labels),
        )

    def accept_dialog(self) -> str:
        """Press the affirmative button, but never on a permission prompt.

        A permission or authentication dialog is exactly what an injected or
        overheard utterance would want approved, so Clausis refuses it the same
        way it refuses dictating into a password field: the keyboard and Orca
        paths stay available and are the intended way to decide.
        """

        window = self._dialog_window()
        buttons = self._dialog_buttons(window)
        labels = [name for name, _ in buttons]
        if self._classify_dialog(window, labels) is DialogKind.PERMISSION:
            raise GnomeAdapterError(
                "Berechtigungs- und Anmeldeabfragen bestätigt Clausis nicht per Sprache. "
                "Bitte entscheiden Sie über Tastatur oder Orca."
            )
        return self._press(buttons, self.AFFIRMATIVE_LABELS, "Zustimmen")

    def cancel_dialog(self) -> str:
        window = self._dialog_window()
        return self._press(self._dialog_buttons(window), self.NEGATIVE_LABELS, "Abbrechen")

    # ------------------------------------------------------------------
    # File chooser navigation (voice-only file selection).
    # ------------------------------------------------------------------

    #: Roles of individual, nameable rows in a file chooser: the sidebar's
    #: tree/list items and the file grid's cells.  Containers are not entries.
    FILE_ENTRY_ROLES = frozenset(
        {"tree item", "list item", "table cell", "table row", "grid item", "grid child"}
    )
    #: Containers of the file grid.  AT-SPI cannot prove that a row inside
    #: them is a folder rather than a file, so nothing under them is ever
    #: activated by :meth:`open_folder`; they are listed and focusable only.
    GRID_CONTAINER_ROLES = frozenset({"tree table", "table", "grid"})
    #: Roles that count as a provable folder when they are not a grid row:
    #: the sidebar's tree items (bookmarked places such as Home, Documents).
    #: A bare "list item" deliberately does not count: GTK file lists in list
    #: mode expose plain files as list items too, and refusing is safer than
    #: opening a file that merely looked like a folder.
    FOLDER_ROLES = frozenset({"tree item"})
    MAX_FILE_ENTRIES = 20

    def _file_dialog(self) -> Any:
        window = self._dialog_window()
        if self._role(window).casefold() != "file chooser":
            raise GnomeAdapterError("Es ist gerade kein Dateidialog offen.")
        return window

    def list_files(self) -> str:
        """Speak the visible file chooser entries, numbered.

        Read-only: this only walks the accessibility tree and names what is
        showing.  Nothing is activated, so no entry can be opened or run by
        asking what is in the dialog.
        """

        entries = self._file_entries(self._file_dialog())
        if not entries:
            raise GnomeAdapterError(
                "Der Dateidialog zeigt keine zugänglichen Einträge an."
            )
        spoken = ". ".join(
            f"Nummer {index}: {name}"
            for index, (name, _node, _role) in enumerate(entries, start=1)
        )
        return f"In diesem Dialog. {spoken}."

    def select_file(self, number: int) -> str:
        """Focus a numbered entry without opening it.

        Selection commits nothing: it only moves focus, which the application
        then shows.  Confirming stays a separate, medium-risk step
        (``dialog.accept``), exactly as with any other dialog, so a misheard
        number can select but never open or run anything.
        """

        node = self._numbered_file_entry(number)
        self._focus_node(node, "Der Eintrag lässt sich nicht fokussieren.")
        return self._name(node) or "Eintrag"

    def open_folder(self, number: int) -> str:
        """Open a provable folder from the file chooser's sidebar.

        Only sidebar tree items count as provable folders: activating a file
        grid row could open or run a file, and AT-SPI cannot prove that a grid
        row is a folder, so grid rows are never activated here — not even when
        the numbered entry happens to sit inside the grid.  Committing the
        dialog stays a separate medium-risk confirmation.
        """

        node = self._numbered_file_entry(number)
        if self._role(node).casefold() not in self.FOLDER_ROLES or self._has_grid_ancestor(node):
            raise GnomeAdapterError(
                f"Nummer {number} ist kein nachweisbarer Ordner. "
                "Bitte wählen Sie einen Ordner aus der Seitenleiste."
            )
        if not self._invoke_named_action(
            node, {"activate", "open", "click", "press", "expand or contract"}
        ):
            raise GnomeAdapterError("Der Ordner lässt sich nicht öffnen.")
        return self._name(node) or "Ordner"

    def _numbered_file_entry(self, number: int) -> Any:
        if number < 1 or number > self.MAX_FILE_ENTRIES:
            raise GnomeAdapterError("Die Zielnummer liegt außerhalb des erlaubten Bereichs.")
        entries = self._file_entries(self._file_dialog())
        if number > len(entries):
            raise GnomeAdapterError("Diese Zielnummer ist im aktuellen Dialog nicht vorhanden.")
        return entries[number - 1][1]

    def _has_grid_ancestor(self, node: Any) -> bool:
        current = node
        for _ in range(self.MAX_ANCESTORS):
            try:
                current = current.parent
            except Exception:
                return False
            if current is None:
                return False
            if self._role(current).casefold() in self.GRID_CONTAINER_ROLES:
                return True
        return False

    def _file_entries(self, window: Any) -> List[Tuple[str, Any, str]]:
        """Numberable entries in walk order: (name, node, role).

        A row inside the grid and its container are both showing, and nested
        rows can repeat a name, so an entry is only counted when it is the
        outermost node with that name at that point of the walk: names equal
        to the previous entry's name are skipped.  That keeps each visible
        row exactly once without guessing the toolkit's nesting.
        """

        entries: List[Tuple[str, Any, str]] = []
        for node in self._walk(window):
            if not self._has_state(node, self._atspi.STATE_SHOWING):
                continue
            role = self._role(node).casefold()
            if role not in self.FILE_ENTRY_ROLES:
                continue
            name = self._name(node).strip()
            if not name or (entries and name == entries[-1][0]):
                continue
            entries.append((name, node, role))
            if len(entries) >= self.MAX_FILE_ENTRIES:
                break
        return entries

    def _focus_node(self, node: Any, refusal: str) -> None:
        """Give a node the keyboard focus through AT-SPI, honestly."""

        try:
            focused = node.queryComponent().grabFocus()
        except Exception as exc:
            raise GnomeAdapterError(refusal) from exc
        if focused is False:
            raise GnomeAdapterError(refusal)


    @staticmethod
    def _match_label(labels: Sequence[str], wanted: Any) -> str:
        for label in labels:
            if label.casefold() in wanted:
                return label
        return ""

    def _press(self, buttons: Sequence[Tuple[str, Any]], wanted: Any, description: str) -> str:
        for name, node in buttons:
            if name.casefold() not in wanted:
                continue
            if self._invoke_named_action(node, {"click", "press", "activate"}):
                return name
            raise GnomeAdapterError(f"{name} hat die Aktion abgelehnt.")
        raise GnomeAdapterError(f"Dieser Dialog bietet keine {description}-Schaltfläche an.")

    def _invoke_named_action(self, node: Any, names: Any) -> bool:
        try:
            action = node.queryAction()
            available = tuple(action.getName(index) for index in range(action.nActions))
        except Exception:
            return False
        for index, available_name in enumerate(available):
            if available_name.casefold() in names:
                try:
                    if action.doAction(index):
                        return True
                except Exception:
                    return False
        return False

    def _visible_windows(self) -> List[Tuple[Any, Any]]:
        desktop = self._atspi.Registry.getDesktop(0)
        windows: List[Tuple[Any, Any]] = []
        for application in self._children(desktop):
            for child in self._children(application):
                if self._role(child).casefold() in self.WINDOW_ROLES and self._has_state(
                    child, self._atspi.STATE_SHOWING
                ):
                    windows.append((application, child))
        return windows

    def cycle_window(self, direction: int) -> str:
        windows = [window for _, window in self._visible_windows()]
        if not windows:
            raise GnomeAdapterError("Kein sichtbares GNOME-Fenster gefunden.")
        active_index = next(
            (index for index, item in enumerate(windows) if self._has_state(item, self._atspi.STATE_ACTIVE)),
            0,
        )
        target = windows[(active_index + (1 if direction >= 0 else -1)) % len(windows)]
        try:
            focused = bool(target.queryComponent().grabFocus())
        except Exception as exc:
            raise GnomeAdapterError("Das nächste Fenster konnte nicht fokussiert werden.") from exc
        if not focused:
            raise GnomeAdapterError("GNOME hat den Fensterfokus nicht geändert.")
        return self._name(target) or "unbenanntes Fenster"

    def navigate_back(self) -> str:
        _, window = self._active_window()
        for node in self._walk(window):
            try:
                action = node.queryAction()
                names = tuple(action.getName(index) for index in range(action.nActions))
            except Exception:
                continue
            for index, name in enumerate(names):
                if name.casefold() in {"back", "go back", "zurück"}:
                    if action.doAction(index):
                        return self._name(node) or "Zurück"
        raise GnomeAdapterError("Dieses Fenster bietet keine semantische Zurück-Aktion an.")

    def _active_window(self) -> Tuple[Any, Any]:
        desktop = self._atspi.Registry.getDesktop(0)
        fallback: Optional[Tuple[Any, Any]] = None
        for application in self._children(desktop):
            for child in self._children(application):
                if self._role(child).casefold() not in self.WINDOW_ROLES:
                    continue
                if self._has_state(child, self._atspi.STATE_ACTIVE):
                    return application, child
                if fallback is None and self._has_state(child, self._atspi.STATE_SHOWING):
                    fallback = (application, child)
        if fallback is not None:
            return fallback
        raise GnomeAdapterError("Kein zugängliches GNOME-Fenster gefunden.")

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
    set(SHELL_ACTIONS)
    | {
        "desktop.context.describe",
        "desktop.controls.list",
        "desktop.control.activate",
        "desktop.navigate.back",
        "desktop.window.next",
        "desktop.window.previous",
        "app.close",
        "text.read",
        "text.insert",
        "text.delete_word",
        "text.clear",
        "text.read_from_caret",
        "text.caret.start",
        "text.caret.end",
        "text.caret.word_next",
        "text.caret.word_previous",
        "text.newline",
        "text.paragraph",
        "text.select_word",
        "text.select_sentence",
        "text.select_all",
        "text.replace_selection",
        "text.delete_selection",
        "text.undo",
        "text.redo",
        "text.read_granular",
        "dialog.file.list",
        "dialog.file.select",
        "dialog.folder.open",
        "dialog.describe",
        "dialog.accept",
        "dialog.cancel",
        "clipboard.read",
        "clipboard.copy",
        "clipboard.paste",
    }
)
SEMANTIC_MUTATIONS = frozenset(
    set(SHELL_ACTIONS)
    | {
        "desktop.control.activate",
        "desktop.navigate.back",
        "desktop.window.next",
        "desktop.window.previous",
        "app.close",
        "text.insert",
        "text.delete_word",
        "text.clear",
        "text.caret.start",
        "text.caret.end",
        "text.caret.word_next",
        "text.caret.word_previous",
        "text.newline",
        "text.paragraph",
        "text.select_word",
        "text.select_sentence",
        "text.select_all",
        "text.replace_selection",
        "text.delete_selection",
        "text.undo",
        "text.redo",
        "dialog.file.select",
        "dialog.folder.open",
        "dialog.accept",
        "dialog.cancel",
        "clipboard.copy",
        "clipboard.paste",
    }
)


class GnomeSemanticExecutor:
    #: Caret actions mapped to their adapter direction.
    _CARET_ACTION_DIRECTIONS = {
        "text.caret.start": "start",
        "text.caret.end": "end",
        "text.caret.word_next": "word_next",
        "text.caret.word_previous": "word_previous",
    }

    def __init__(
        self,
        desktop: Optional[SemanticDesktop] = None,
        shell: Optional[GnomeShell] = None,
    ) -> None:
        self._desktop = desktop
        self._shell = shell

    def execute(self, request: ActionRequest, policy: ActionPolicy) -> ActionResult:
        del policy
        try:
            if request.action in SHELL_ACTIONS:
                method, spoken = SHELL_ACTIONS[request.action]
                (self._shell or DbusGnomeShell()).invoke(method)
                return ActionResult("completed", spoken, request.action)
            if request.action == "clipboard.read":
                content = (self._shell or DbusGnomeShell()).invoke(CLIPBOARD_READ_METHOD)
                spoken = (
                    f"In der Zwischenablage steht: {content}"
                    if content.strip()
                    else "Die Zwischenablage ist leer."
                )
                return ActionResult("completed", spoken, request.action)
            desktop = self._desktop or PyAtSpiDesktop()
            if request.action == "app.close":
                name = desktop.close_application(request.target)
                return ActionResult("completed", f"{name} wurde geschlossen.", request.action)
            if request.action == "text.read":
                content = desktop.read_text_field()
                spoken = f"Im Feld steht: {content}" if content else "Das Feld ist leer."
                return ActionResult("completed", spoken, request.action)
            if request.action == "text.insert":
                content = desktop.insert_text(request.target)
                return ActionResult(
                    "completed", f"Geschrieben. Im Feld steht jetzt: {content}", request.action
                )
            if request.action == "text.delete_word":
                content = desktop.delete_word()
                spoken = f"Im Feld steht jetzt: {content}" if content else "Das Feld ist jetzt leer."
                return ActionResult("completed", spoken, request.action)
            if request.action == "text.clear":
                desktop.clear_text()
                return ActionResult("completed", "Das Feld wurde geleert.", request.action)
            if request.action == "text.read_from_caret":
                content = desktop.read_from_caret()
                spoken = (
                    f"Ab dem Cursor steht: {content}" if content else "Ab dem Cursor ist das Feld leer."
                )
                return ActionResult("completed", spoken, request.action)
            if request.action in self._CARET_ACTION_DIRECTIONS:
                direction = self._CARET_ACTION_DIRECTIONS[request.action]
                spoken = desktop.move_caret(direction)
                return ActionResult("completed", spoken, request.action)
            if request.action == "text.newline":
                content = desktop.insert_newline()
                return ActionResult(
                    "completed", f"Neue Zeile. Im Feld steht jetzt: {content}", request.action
                )
            if request.action == "text.paragraph":
                content = desktop.insert_paragraph()
                return ActionResult(
                    "completed", f"Absatz. Im Feld steht jetzt: {content}", request.action
                )
            if request.action == "text.select_word":
                selected = desktop.select_word()
                return ActionResult("completed", f"Ausgewählt: {selected}", request.action)
            if request.action == "text.select_sentence":
                selected = desktop.select_sentence()
                return ActionResult("completed", f"Ausgewählt: {selected}", request.action)
            if request.action == "text.select_all":
                content = desktop.select_all()
                return ActionResult(
                    "completed", f"Alles ausgewählt. Im Feld steht: {content}", request.action
                )
            if request.action == "text.replace_selection":
                content = desktop.replace_selection(request.target)
                return ActionResult(
                    "completed", f"Ersetzt. Im Feld steht jetzt: {content}", request.action
                )
            if request.action == "text.delete_selection":
                content = desktop.delete_selection()
                spoken = f"Im Feld steht jetzt: {content}" if content else "Das Feld ist jetzt leer."
                return ActionResult("completed", spoken, request.action)
            if request.action == "text.undo":
                desktop.edit_undo()
                return ActionResult("completed", "Wurde rückgängig gemacht.", request.action)
            if request.action == "text.redo":
                desktop.edit_redo()
                return ActionResult("completed", "Wurde wiederhergestellt.", request.action)
            if request.action == "text.read_granular":
                unit = request.arguments["granularity"]
                content = desktop.read_granular(unit)
                spoken = f"{unit.capitalize()}: {content}" if content else "Hier ist nichts zu lesen."
                return ActionResult("completed", spoken, request.action)
            if request.action == "dialog.file.list":
                spoken = desktop.list_files()
                return ActionResult("completed", spoken, request.action)
            if request.action == "dialog.file.select":
                name = desktop.select_file(int(request.target))
                return ActionResult("completed", f"{name} ist ausgewählt.", request.action)
            if request.action == "dialog.folder.open":
                name = desktop.open_folder(int(request.target))
                return ActionResult("completed", f"Ordner {name} ist geöffnet.", request.action)
            if request.action == "clipboard.copy":
                name = desktop.copy_selection()
                return ActionResult("completed", f"{name} wurde kopiert.", request.action)
            if request.action == "clipboard.paste":
                content = desktop.paste()
                return ActionResult(
                    "completed", f"Eingefügt. Im Feld steht jetzt: {content}", request.action
                )
            if request.action == "dialog.describe":
                return ActionResult(
                    "completed", desktop.describe_dialog().spoken(), request.action
                )
            if request.action == "dialog.accept":
                name = desktop.accept_dialog()
                return ActionResult("completed", f"{name} wurde ausgelöst.", request.action)
            if request.action == "dialog.cancel":
                name = desktop.cancel_dialog()
                return ActionResult("completed", f"{name} wurde ausgelöst.", request.action)
            if request.action == "desktop.context.describe":
                context = desktop.context()
                return ActionResult("completed", context.spoken_location(), request.action)
            if request.action == "desktop.controls.list":
                context = desktop.context()
                return ActionResult("completed", context.spoken_controls(), request.action)
            if request.action == "desktop.control.activate":
                name = desktop.activate(int(request.target))
                return ActionResult("completed", f"{name} wurde ausgelöst.", request.action)
            if request.action == "desktop.navigate.back":
                name = desktop.navigate_back()
                return ActionResult("completed", f"{name} wurde ausgelöst.", request.action)
            if request.action in {"desktop.window.next", "desktop.window.previous"}:
                direction = 1 if request.action.endswith("next") else -1
                name = desktop.cycle_window(direction)
                return ActionResult("completed", f"Fenster {name} ist jetzt aktiv.", request.action)
        except (GnomeAdapterError, TypeError, ValueError) as exc:
            return ActionResult("failed", str(exc), request.action)
        return ActionResult("failed", "Keine semantische GNOME-Aktion verfügbar.", request.action)
