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
        if self._role(node).casefold() in self.PROTECTED_ROLES:
            raise GnomeAdapterError(
                "Das ist ein Passwortfeld. Bitte tippen Sie es selbst über die Tastatur."
            )
        if self._has_state(node, self._atspi.STATE_PROTECTED):
            raise GnomeAdapterError(
                "Das Feld ist als geschützt markiert. Bitte tippen Sie es selbst."
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
        if self._role(node).casefold() in self.PROTECTED_ROLES or self._has_state(
            node, self._atspi.STATE_PROTECTED
        ):
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
            if self._role(node).casefold() in self.PROTECTED_ROLES or self._has_state(
                node, self._atspi.STATE_PROTECTED
            ):
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
        "dialog.accept",
        "dialog.cancel",
        "clipboard.copy",
        "clipboard.paste",
    }
)


class GnomeSemanticExecutor:
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
