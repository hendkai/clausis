"""Bounded semantic GNOME control through the AT-SPI accessibility tree.

No screen coordinates, screenshots or synthesized pointer events are used.
The adapter reads the current accessibility state again immediately before an
activation so a stale numbered target cannot silently select another window.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Iterable, List, Optional, Protocol, Sequence, Tuple

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

    def cycle_window(self, direction: int) -> str:
        ...

    def navigate_back(self) -> str:
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

    def cycle_window(self, direction: int) -> str:
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
                if self._role(child) not in {"frame", "dialog", "window"}:
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
    {
        "desktop.context.describe",
        "desktop.controls.list",
        "desktop.control.activate",
        "desktop.navigate.back",
        "desktop.window.next",
        "desktop.window.previous",
    }
)
SEMANTIC_MUTATIONS = frozenset(
    {
        "desktop.control.activate",
        "desktop.navigate.back",
        "desktop.window.next",
        "desktop.window.previous",
    }
)


class GnomeSemanticExecutor:
    def __init__(self, desktop: Optional[SemanticDesktop] = None) -> None:
        self._desktop = desktop

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
