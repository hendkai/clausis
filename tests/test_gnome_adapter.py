import ast
import inspect
import tempfile
import unittest
from unittest.mock import patch
from dataclasses import replace
from pathlib import Path

from clausis.audit import AuditLog
from clausis.broker import ActionBroker, SafeExecutor
from clausis.capabilities import CapabilityAuthority
from clausis.gnome_adapter import (
    DesktopContext,
    GnomeSemanticExecutor,
    GnomeAdapterError,
    PyAtSpiDesktop,
    SEMANTIC_ACTIONS,
    SEMANTIC_MUTATIONS,
    SEMANTIC_READ_ONLY,
    SemanticDesktop,
    SemanticControl,
    SessionExecutor,
)
from clausis.models import ActionRequest, Risk


class FakeDesktop:
    def __init__(self):
        self.activated = []
        self.cycled = []
        self.window_actions = []
        self.shell_actions = []
        self.notification_reads = 0
        self.notification_dismissals = []
        self.named_activations = []
        self.focus_cycles = []
        self.named_focuses = []
        self.text_values = []
        self.text_reads = 0
        self.clipboard_reads = 0
        self.selection_reads = 0
        self.select_all_calls = 0
        self.clear_selection_calls = 0
        self.delete_selection_calls = 0
        self.inserted_texts = []
        self.character_deletions = []
        self.word_deletions = []
        self.word_replacements = []
        self.character_selections = []
        self.word_selections = []
        self.character_reads = []
        self.word_reads = []
        self.selection_replacements = []
        self.caret_moves = []
        self.word_caret_moves = []
        self.line_reads = 0
        self.line_caret_moves = []
        self.line_selections = 0
        self.line_deletions = 0
        self.line_replacements = []
        self.line_insertions = []
        self.line_duplications = []
        self.line_moves = []
        self.line_joins = []
        self.line_splits = 0
        self.line_indents = []
        self.caret_reads = 0
        self.clipboard_values = []
        self.selected_items = []
        self.selected_files = []
        self.file_names = []
        self.file_locations = []
        self.opened_folders = []
        self.file_dialog_decisions = []
        self.standard_dialog_decisions = []
        self.standard_dialog_reads = 0
        self.standard_dialog_dismissals = 0
        self.tree_changes = []
        self.table_rows = []
        self.tabs = []
        self.sliders = []
        self.progress_reads = []
        self.checkboxes = []
        self.switches = []
        self.radios = []
        self.combo_items = []
        self.spin_values = []
        self.menu_items = []
        self.permission_decisions = []

    def context(self):
        return DesktopContext(
            "Dateien",
            "Persönlicher Ordner",
            "Dokumente",
            "folder",
            (
                SemanticControl(1, "Öffnen", "push button", ("click",)),
                SemanticControl(2, "Abbrechen", "push button", ("click",)),
            ),
        )

    def activate(self, number):
        self.activated.append(number)
        return "Öffnen"

    def activate_named(self, name):
        self.named_activations.append(name)
        return name

    def cycle_focus(self, direction):
        self.focus_cycles.append(direction)
        return "Cancel"

    def focus_named(self, name):
        self.named_focuses.append(name)
        return name

    def set_focused_text(self, value):
        self.text_values.append(value)
        return "Search"

    def read_focused_text(self):
        self.text_reads += 1
        return "Notes", "Quarterly report"

    def focused_text_for_clipboard(self):
        self.clipboard_reads += 1
        return "Notes", "Quarterly\nreport"

    def selected_text_for_clipboard(self):
        self.selection_reads += 1
        return "Notes", "selected words"

    def select_all_focused_text(self):
        self.select_all_calls += 1
        return "Notes"

    def clear_focused_text_selection(self):
        self.clear_selection_calls += 1
        return "Notes"

    def delete_focused_text_selection(self):
        self.delete_selection_calls += 1
        return "Notes"

    def insert_focused_text_at_caret(self, value):
        self.inserted_texts.append(value)
        return "Notes"

    def delete_focused_text_character(self, direction):
        self.character_deletions.append(direction)
        return "Notes"

    def delete_focused_text_word(self, direction):
        self.word_deletions.append(direction)
        return "Notes"

    def replace_focused_text_word(self, direction, value):
        self.word_replacements.append((direction, value))
        return "Notes"

    def select_focused_text_character(self, direction):
        self.character_selections.append(direction)
        return "Notes"

    def select_focused_text_word(self, direction):
        self.word_selections.append(direction)
        return "Notes"

    def focused_text_character_at_caret(self, direction):
        self.character_reads.append(direction)
        return "Notes", "🙂"

    def focused_text_word_at_caret(self, direction):
        self.word_reads.append(direction)
        return "Notes", "Grüße"

    def replace_focused_text_selection(self, value):
        self.selection_replacements.append(value)
        return "Notes"

    def move_focused_text_caret(self, position):
        self.caret_moves.append(position)
        return "Notes"

    def move_focused_text_caret_word(self, direction):
        self.word_caret_moves.append(direction)
        return "Notes"

    def focused_text_line_at_caret(self):
        self.line_reads += 1
        return "Notes", "βeta line"

    def move_focused_text_caret_line(self, boundary):
        self.line_caret_moves.append(boundary)
        return "Notes"

    def select_focused_text_line(self):
        self.line_selections += 1
        return "Notes"

    def delete_focused_text_line(self):
        self.line_deletions += 1
        return "Notes"

    def replace_focused_text_line(self, value):
        self.line_replacements.append(value)
        return "Notes"

    def insert_focused_text_line(self, direction, value):
        self.line_insertions.append((direction, value))
        return "Notes"

    def duplicate_focused_text_line(self, direction):
        self.line_duplications.append(direction)
        return "Notes"

    def move_focused_text_line(self, direction):
        self.line_moves.append(direction)
        return "Notes"

    def join_focused_text_line(self, direction):
        self.line_joins.append(direction)
        return "Notes"

    def split_focused_text_line(self):
        self.line_splits += 1
        return "Notes"

    def indent_focused_text_line(self, direction):
        self.line_indents.append(direction)
        return "Notes"

    def focused_text_caret_position(self):
        self.caret_reads += 1
        return "Notes", 4, 12

    def set_focused_clipboard_text(self, value):
        self.clipboard_values.append(value)
        return "Notes"

    def select_named_item(self, name):
        self.selected_items.append(name)
        return name

    def select_visible_file(self, name):
        self.selected_files.append(name)
        return name

    def set_file_name(self, name):
        self.file_names.append(name)
        return "File Name"

    def set_file_location(self, path):
        self.file_locations.append(path)
        return "Location"

    def open_visible_folder(self, name):
        self.opened_folders.append(name)
        return name

    def decide_file_dialog(self, decision):
        self.file_dialog_decisions.append(decision)
        return "Open" if decision == "accept" else "Cancel"

    def decide_standard_dialog(self, decision):
        self.standard_dialog_decisions.append(decision)
        return {
            "accept": "OK",
            "cancel": "Cancel",
            "retry": "Retry",
            "apply": "Apply",
        }[decision]

    def read_standard_dialog(self):
        self.standard_dialog_reads += 1
        return "Warning", ("The operation failed", "Check the connection")

    def dismiss_standard_dialog(self):
        self.standard_dialog_dismissals += 1
        return "Close"

    def set_named_tree_item_expanded(self, name, expanded):
        self.tree_changes.append((name, expanded))
        return name

    def select_table_row(self, name):
        self.table_rows.append(name)
        return name

    def select_named_tab(self, name):
        self.tabs.append(name)
        return name

    def set_named_slider(self, name, percent):
        self.sliders.append((name, percent))
        return name

    def read_named_progress(self, name):
        self.progress_reads.append(name)
        return name, 42

    def set_named_checkbox(self, name, checked):
        self.checkboxes.append((name, checked))
        return name

    def set_named_switch(self, name, enabled):
        self.switches.append((name, enabled))
        return name

    def select_named_radio(self, name):
        self.radios.append(name)
        return name

    def select_combo_item(self, combo_name, item_name):
        self.combo_items.append((combo_name, item_name))
        return item_name

    def set_named_spin_button(self, name, number):
        self.spin_values.append((name, number))
        return name

    def activate_menu_item(self, name):
        self.menu_items.append(name)
        return name

    def decide_permission(self, decision):
        self.permission_decisions.append(decision)
        return "Allow" if decision == "allow" else "Don't Allow"

    def cycle_window(self, direction):
        self.cycled.append(direction)
        return "Einstellungen"

    def navigate_back(self):
        return "Zurück"

    def window_action(self, operation):
        self.window_actions.append(operation)
        return "Persönlicher Ordner"

    def shell_action(self, operation):
        self.shell_actions.append(operation)
        return {
            "overview": "Activities",
            "applications": "Show Applications",
            "quick_settings": "Quick Settings",
            "notifications": "Notifications",
        }[operation]

    def read_notifications(self):
        self.notification_reads += 1
        return ("Backup complete", "Files are safe")

    def dismiss_notification(self, number):
        self.notification_dismissals.append(number)
        return number


class FakeWindowAction:
    def __init__(self, names, *, accepted=True):
        self.names = tuple(names)
        self.nActions = len(self.names)
        self.accepted = accepted
        self.called = []

    def getName(self, index):
        return self.names[index]

    def doAction(self, index):
        self.called.append(index)
        return self.accepted


class FakeWindow:
    name = "Dokumente"

    def __init__(self, action):
        self.action = action

    def queryAction(self):
        return self.action


class FakeNode:
    def __init__(self, name, *, children=(), action=None, role="", attributes=()):
        self.name = name
        self.children = tuple(children)
        self.childCount = len(self.children)
        self.action = action
        self.role = role
        self.attributes = tuple(attributes)

    def getChildAtIndex(self, index):
        return self.children[index]

    def queryAction(self):
        if self.action is None:
            raise RuntimeError("no action")
        return self.action

    def getRoleName(self):
        return self.role

    def getAttributes(self):
        return self.attributes


class FakeCyclingWindow(FakeNode):
    def __init__(
        self, name, *, active=False, accepted=True, mismatch=False, partial=False
    ):
        super().__init__(name, role="frame")
        self.active = active
        self.accepted = accepted
        self.mismatch = mismatch
        self.partial = partial
        self.group = (self,)
        self.focus_calls = 0

    def getState(self):
        node = self
        return type(
            "State",
            (),
            {
                "contains": lambda _self, state: {
                    "showing": True,
                    "active": node.active,
                }.get(state, False)
            },
        )()

    def queryComponent(self):
        return self

    def grabFocus(self):
        self.focus_calls += 1
        if not self.accepted:
            return False
        if self.partial:
            self.active = True
        elif not self.mismatch:
            for window in self.group:
                window.active = window is self
        return True


class FakeFocusNode(FakeNode):
    def __init__(
        self, name, *, focused=False, accepted=True, mismatch=False, partial=False,
        role=""
    ):
        super().__init__(name, action=FakeWindowAction(("click",)), role=role)
        self.focused = focused
        self.accepted = accepted
        self.mismatch = mismatch
        self.partial = partial
        self.group = (self,)
        self.focus_calls = 0

    def getState(self):
        focused = self.focused
        return type("State", (), {"contains": lambda _self, _state: focused})()

    def queryComponent(self):
        return self

    def grabFocus(self):
        self.focus_calls += 1
        if not self.accepted:
            return False
        if self.partial:
            self.focused = True
        elif not self.mismatch:
            for node in self.group:
                node.focused = node is self
        return True


class FakeReadableText(FakeNode):
    def __init__(
        self,
        value,
        *,
        name="Notes",
        role="entry",
        attributes=(),
        selections=(),
        accept_selection=True,
        selection_mismatch=False,
        reject_remove_once_at=None,
        caret_offset=0,
        accept_caret=True,
        caret_mismatch_once=False,
        accept_delete=True,
        delete_mismatch=False,
        accept_insert=True,
        insert_mismatch=False,
        set_contents_mismatch=False,
    ):
        super().__init__(name, role=role, attributes=attributes)
        self.value = value
        self.characterCount = len(value)
        self.read_ranges = []
        self.selections = tuple(selections)
        self.nSelections = len(self.selections)
        self.accept_selection = accept_selection
        self.selection_mismatch = selection_mismatch
        self.reject_remove_once_at = reject_remove_once_at
        self.caretOffset = caret_offset
        self.accept_caret = accept_caret
        self.caret_mismatch_once = caret_mismatch_once
        self.accept_delete = accept_delete
        self.delete_mismatch = delete_mismatch
        self.accept_insert = accept_insert
        self.insert_mismatch = insert_mismatch
        self.set_contents_mismatch = set_contents_mismatch

    def queryText(self):
        return self

    def queryEditableText(self):
        return self

    def getText(self, start, end):
        self.read_ranges.append((start, end))
        return self.value[start:end]

    def getSelection(self, index):
        return self.selections[index]

    def removeSelection(self, index):
        if self.reject_remove_once_at == index:
            self.reject_remove_once_at = None
            return False
        selections = list(self.selections)
        if index < 0 or index >= len(selections):
            return False
        selections.pop(index)
        self.selections = tuple(selections)
        self.nSelections = len(self.selections)
        return True

    def addSelection(self, start, end):
        if not self.accept_selection:
            return False
        span = (start, end - 1) if self.selection_mismatch else (start, end)
        self.selection_mismatch = False
        self.selections = (*self.selections, span)
        self.nSelections = len(self.selections)
        return True

    def setCaretOffset(self, offset):
        if not self.accept_caret:
            return False
        self.caretOffset = offset - 1 if self.caret_mismatch_once else offset
        self.caret_mismatch_once = False
        return True

    def deleteText(self, start, end):
        if not self.accept_delete:
            return False
        actual_end = end - 1 if self.delete_mismatch else end
        self.delete_mismatch = False
        self.value = self.value[:start] + self.value[actual_end:]
        self.characterCount = len(self.value)
        self.selections = ()
        self.nSelections = 0
        self.caretOffset = start
        return True

    def setTextContents(self, value):
        self.value = value[:-1] if self.set_contents_mismatch else value
        self.set_contents_mismatch = False
        self.characterCount = len(self.value)
        self.selections = ()
        self.nSelections = 0
        return True

    def insertText(self, position, value, length):
        if not self.accept_insert or length != len(value):
            return False
        inserted = value[:-1] if self.insert_mismatch else value
        self.insert_mismatch = False
        self.value = self.value[:position] + inserted + self.value[position:]
        self.characterCount = len(self.value)
        return True


class FakeNamedFocusNode(FakeNode):
    def __init__(
        self,
        name,
        *,
        focused=False,
        showing=True,
        focusable=True,
        accepted=True,
        mismatch=False,
        raise_after_mutation=False,
        fail_rollback=False,
        role="label",
    ):
        super().__init__(name, role=role)
        self.focused = focused
        self.showing = showing
        self.focusable = focusable
        self.accepted = accepted
        self.mismatch = mismatch
        self.raise_after_mutation = raise_after_mutation
        self.fail_rollback = fail_rollback
        self.group = (self,)
        self.focus_calls = 0

    def getState(self):
        node = self
        return type(
            "State",
            (),
            {
                "contains": lambda _self, state: {
                    "focused": node.focused,
                    "showing": node.showing,
                    "focusable": node.focusable,
                }.get(state, False)
            },
        )()

    def queryComponent(self):
        return self

    def grabFocus(self):
        self.focus_calls += 1
        if not self.accepted or (self.fail_rollback and self.focus_calls > 1):
            return False
        for node in self.group:
            node.focused = False
        if not self.mismatch:
            self.focused = True
        if self.raise_after_mutation:
            self.raise_after_mutation = False
            raise RuntimeError("partial named-focus mutation")
        return True


class FakeTreeAction(FakeWindowAction):
    def __init__(
        self, item, names, *, accepted=True, mutate=True,
        raise_after_mutation=False, fail_rollback=False
    ):
        super().__init__(names, accepted=accepted)
        self.item = item
        self.mutate = mutate
        self.raise_after_mutation = raise_after_mutation
        self.fail_rollback = fail_rollback

    def doAction(self, index):
        if self.fail_rollback and self.called:
            self.called.append(index)
            return False
        accepted = super().doAction(index)
        if accepted and self.mutate:
            name = self.names[index].casefold()
            if name == "expand":
                self.item.expanded = True
            elif name == "collapse":
                self.item.expanded = False
            if self.raise_after_mutation:
                self.raise_after_mutation = False
                raise RuntimeError("partial tree-state mutation")
        return accepted


class FakeTreeItem(FakeNode):
    def __init__(
        self,
        name,
        *,
        focused=False,
        expanded=False,
        expandable=True,
        actions=("expand", "collapse"),
        mutate=True,
        raise_after_mutation=False,
        fail_rollback=False,
    ):
        super().__init__(name, role="tree item")
        self.focused = focused
        self.expanded = expanded
        self.expandable = expandable
        self.action = FakeTreeAction(
            self, actions, mutate=mutate,
            raise_after_mutation=raise_after_mutation,
            fail_rollback=fail_rollback,
        )

    def getState(self):
        item = self

        class State:
            def contains(self, state):
                return {
                    "focused": item.focused,
                    "expanded": item.expanded,
                    "expandable": item.expandable,
                }.get(state, False)

        return State()


class FakeTree(FakeNode):
    def __init__(self, children):
        super().__init__("Navigation", children=children, role="tree")
        for child in children:
            child.parent = self


class FakeEditableNode(FakeNode):
    def __init__(self, name="Search", *, attributes=(), accepted=True, mismatch=False):
        super().__init__(name)
        self.attributes = tuple(attributes)
        self.accepted = accepted
        self.mismatch = mismatch
        self.value = ""

    def getAttributes(self):
        return self.attributes

    def getRoleName(self):
        return "entry"

    def queryEditableText(self):
        return self

    def setTextContents(self, value):
        self.value = value
        return self.accepted

    def queryText(self):
        return self

    def getText(self, _start, _end):
        return self.value + ("changed" if self.mismatch and self.value else "")


class FakeSelection:
    def __init__(self, selected=(), *, ignored_index=None):
        self.selected = set(selected)
        self.ignored_index = ignored_index

    def isChildSelected(self, index):
        return index in self.selected

    def clearSelection(self):
        self.selected.clear()
        return True

    def selectChild(self, index):
        if index != self.ignored_index:
            self.selected.add(index)
        return True


class FakeSelectionContainer(FakeNode):
    def __init__(self, children, selection):
        super().__init__("Choices", children=children)
        self.selection = selection
        for child in children:
            child.parent = self

    def querySelection(self):
        return self.selection


class FakeTableRow(FakeNode):
    def __init__(self, name, cells):
        super().__init__(name, children=cells, role="table row")
        for cell in cells:
            cell.parent = self


class FakeTable(FakeSelectionContainer):
    def __init__(self, rows, selection):
        super().__init__(rows, selection)
        self.name = "Records"
        self.role = "table"


class FakeTabList(FakeSelectionContainer):
    def __init__(self, tabs, selection):
        super().__init__(tabs, selection)
        self.name = "Sections"
        self.role = "page tab list"


class FakeComboBox(FakeSelectionContainer):
    def __init__(self, name, items, selection):
        super().__init__(items, selection)
        self.name = name
        self.role = "combo box"


class FakeMenu(FakeNode):
    def __init__(self, items, *, role="menu"):
        super().__init__("Menu", children=items, role=role)
        for item in items:
            item.parent = self


class FakeSlider(FakeNode):
    def __init__(
        self,
        name,
        *,
        current=0.0,
        minimum=0.0,
        maximum=100.0,
        increment=0.0,
        accepted=True,
        mismatch=False,
        restore_rejected=False,
        raise_after_mutation=False,
        role="slider",
    ):
        super().__init__(name, role=role)
        self.currentValue = current
        self.minimumValue = minimum
        self.maximumValue = maximum
        self.minimumIncrement = increment
        self.initial = current
        self.accepted = accepted
        self.mismatch = mismatch
        self.restore_rejected = restore_rejected
        self.raise_after_mutation = raise_after_mutation
        self.set_calls = []

    def queryValue(self):
        return self

    def setCurrentValue(self, value):
        self.set_calls.append(value)
        if self.restore_rejected and value == self.initial and self.currentValue != self.initial:
            return False
        if not self.accepted:
            return False
        if self.mismatch and value != self.initial:
            self.currentValue = value + 1
        else:
            self.currentValue = value
        if self.raise_after_mutation and value != self.initial:
            raise RuntimeError("partial value mutation")
        return True


class FakeCheckedAction(FakeWindowAction):
    def __init__(
        self, control, names, *, mutate=True, mismatch=False,
        raise_after_mutation=False, fail_rollback=False
    ):
        super().__init__(names)
        self.control = control
        self.mutate = mutate
        self.mismatch = mismatch
        self.raise_after_mutation = raise_after_mutation
        self.fail_rollback = fail_rollback

    def doAction(self, index):
        if self.fail_rollback and self.called:
            self.called.append(index)
            return False
        accepted = super().doAction(index)
        if not accepted or not self.mutate:
            return accepted
        if self.control.role == "radio button":
            for item in self.control.group:
                item.checked = False
            if not self.mismatch:
                self.control.checked = True
        else:
            self.control.checked = not self.control.checked
        if self.raise_after_mutation:
            self.raise_after_mutation = False
            raise RuntimeError("partial checked-state mutation")
        return accepted


class FakeCheckedControl(FakeNode):
    def __init__(
        self,
        name,
        *,
        role="check box",
        checked=False,
        actions=("toggle",),
        mutate=True,
        mismatch=False,
        raise_after_mutation=False,
        fail_rollback=False,
    ):
        super().__init__(name, role=role)
        self.checked = checked
        self.group = (self,)
        self.action = FakeCheckedAction(
            self, actions, mutate=mutate, mismatch=mismatch,
            raise_after_mutation=raise_after_mutation, fail_rollback=fail_rollback,
        )

    def getState(self):
        control = self
        return type(
            "State",
            (),
            {"contains": lambda _self, state: control.checked if state == "checked" else False},
        )()


class FakeDialog(FakeNode):
    def __init__(self, name, children):
        super().__init__(name, children=children)

    def getRoleName(self):
        return "dialog"


class FakeRegistry:
    def __init__(self, desktop):
        self.desktop = desktop

    def getDesktop(self, _index):
        return self.desktop


class GnomeAdapterTests(unittest.TestCase):
    def test_semantic_desktop_protocol_contains_signatures_only(self):
        tree = ast.parse(inspect.getsource(SemanticDesktop))
        protocol = tree.body[0]
        methods = [node for node in protocol.body if isinstance(node, ast.FunctionDef)]
        self.assertGreater(len(methods), 40)
        for method in methods:
            self.assertEqual(len(method.body), 1, method.name)
            statement = method.body[0]
            self.assertIsInstance(statement, ast.Expr, method.name)
            self.assertIsInstance(statement.value, ast.Constant, method.name)
            self.assertEqual(statement.value.value, Ellipsis, method.name)

    def setUp(self):
        self.desktop = FakeDesktop()
        self.authority = CapabilityAuthority(b"g" * 32)
        executor = SessionExecutor(
            SafeExecutor(dry_run=False), GnomeSemanticExecutor(self.desktop)
        )
        self.broker = ActionBroker(self.authority, executor)

    def test_describes_real_semantic_context(self):
        result = self.broker.submit(ActionRequest("desktop.context.describe"))
        self.assertEqual(result.status, "completed")
        self.assertIn("Dateien", result.message)
        self.assertIn("Dokumente", result.message)

    def test_lists_numbered_controls(self):
        result = self.broker.submit(ActionRequest("desktop.controls.list"))
        self.assertIn("Nummer 1: Öffnen", result.message)
        self.assertIn("Nummer 2: Abbrechen", result.message)

    def test_arbitrary_control_activation_requires_confirmation(self):
        request = ActionRequest(
            "desktop.control.activate", target="1", risk=Risk.MEDIUM
        )
        self.assertEqual(self.broker.submit(request).status, "confirmation_required")
        approved = replace(request, capability_token=self.authority.issue(request))
        self.assertEqual(self.broker.submit(approved).status, "completed")
        self.assertEqual(self.desktop.activated, [1])

    def test_invalid_control_number_fails_before_adapter(self):
        request = ActionRequest(
            "desktop.control.activate", target="31", risk=Risk.MEDIUM
        )
        self.assertEqual(self.broker.submit(request).status, "denied")
        self.assertEqual(self.desktop.activated, [])

    def test_named_activation_requires_confirmation(self):
        request = ActionRequest(
            "desktop.control.activate_named", target="Cancel", risk=Risk.MEDIUM
        )
        self.assertEqual(self.broker.submit(request).status, "confirmation_required")
        approved = replace(request, capability_token=self.authority.issue(request))
        self.assertEqual(self.broker.submit(approved).status, "completed")
        self.assertEqual(self.desktop.named_activations, ["Cancel"])

    def test_named_focus_is_low_risk_and_immediate(self):
        result = self.broker.submit(ActionRequest("desktop.focus.named", target="Details"))
        self.assertEqual(result.status, "completed")
        self.assertEqual(self.desktop.named_focuses, ["Details"])

    def test_focused_text_read_is_low_risk_and_immediate(self):
        result = self.broker.submit(ActionRequest("desktop.text.read_focused"))
        self.assertEqual(result.status, "completed")
        self.assertIn("Quarterly report", result.message)
        self.assertEqual(self.desktop.text_reads, 1)

    def test_focused_text_copy_is_confirmed_exact_and_never_echoed(self):
        copied = []
        executor = SessionExecutor(
            SafeExecutor(dry_run=False),
            GnomeSemanticExecutor(self.desktop, clipboard_write=copied.append),
        )
        broker = ActionBroker(self.authority, executor)
        request = ActionRequest(
            "desktop.text.copy_focused", risk=Risk.MEDIUM, reversible=False
        )
        self.assertEqual(broker.submit(request).status, "confirmation_required")
        approved = replace(request, capability_token=self.authority.issue(request))
        result = broker.submit(approved)
        self.assertEqual(result.status, "completed")
        self.assertEqual(copied, ["Quarterly\nreport"])
        self.assertNotIn("Quarterly", result.message)
        self.assertEqual(self.desktop.clipboard_reads, 1)

    def test_focused_text_copy_content_never_reaches_audit(self):
        copied = []
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "audit.jsonl"
            executor = SessionExecutor(
                SafeExecutor(dry_run=False),
                GnomeSemanticExecutor(self.desktop, clipboard_write=copied.append),
            )
            broker = ActionBroker(
                self.authority, executor, audit_log=AuditLog(path, b"a" * 32)
            )
            request = ActionRequest(
                "desktop.text.copy_focused", risk=Risk.MEDIUM, reversible=False
            )
            broker.submit(request)
            approved = replace(request, capability_token=self.authority.issue(request))
            self.assertEqual(broker.submit(approved).status, "completed")
            audit = path.read_text(encoding="utf-8")
        self.assertEqual(copied, ["Quarterly\nreport"])
        self.assertNotIn("Quarterly", audit)
        self.assertNotIn("report", audit)

    def test_text_selection_copy_is_confirmed_exact_and_never_echoed(self):
        copied = []
        executor = SessionExecutor(
            SafeExecutor(dry_run=False),
            GnomeSemanticExecutor(self.desktop, clipboard_write=copied.append),
        )
        broker = ActionBroker(self.authority, executor)
        request = ActionRequest(
            "desktop.text.copy_selection", risk=Risk.MEDIUM, reversible=False
        )
        self.assertEqual(broker.submit(request).status, "confirmation_required")
        approved = replace(request, capability_token=self.authority.issue(request))
        result = broker.submit(approved)
        self.assertEqual(result.status, "completed")
        self.assertEqual(copied, ["selected words"])
        self.assertNotIn("selected words", result.message)
        self.assertEqual(self.desktop.selection_reads, 1)

    def test_text_selection_read_is_confirmed_bounded_and_audit_redacted(self):
        secret = "private\n" + "x" * 1200
        self.desktop.selected_text_for_clipboard = lambda: ("Notes", secret)
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "audit.jsonl"
            broker = ActionBroker(
                self.authority,
                SessionExecutor(
                    SafeExecutor(dry_run=False), GnomeSemanticExecutor(self.desktop)
                ),
                audit_log=AuditLog(path, b"q" * 32),
            )
            request = ActionRequest("desktop.text.read_selection", risk=Risk.MEDIUM)
            self.assertEqual(broker.submit(request).status, "confirmation_required")
            approved = replace(request, capability_token=self.authority.issue(request))
            result = broker.submit(approved)
            audit = path.read_text(encoding="utf-8")
        self.assertEqual(result.status, "completed")
        self.assertIn("private", result.message)
        self.assertIn("restliche Inhalt wurde gekürzt", result.message)
        self.assertNotIn("private", audit)
        self.assertNotIn("x" * 20, audit)
        self.assertIn("[REDACTED: selected text]", audit)

    def test_select_all_text_uses_semantic_adapter_without_confirmation(self):
        result = self.broker.submit(ActionRequest("desktop.text.select_all"))
        self.assertEqual(result.status, "completed")
        self.assertEqual(self.desktop.select_all_calls, 1)
        self.assertIn("Notes", result.message)

    def test_clear_text_selection_uses_semantic_adapter_without_confirmation(self):
        result = self.broker.submit(ActionRequest("desktop.text.clear_selection"))
        self.assertEqual(result.status, "completed")
        self.assertEqual(self.desktop.clear_selection_calls, 1)
        self.assertIn("Notes", result.message)

    def test_delete_text_selection_requires_confirmation_and_never_echoes_content(self):
        request = ActionRequest("desktop.text.delete_selection", risk=Risk.MEDIUM)
        self.assertEqual(self.broker.submit(request).status, "confirmation_required")
        self.assertEqual(self.desktop.delete_selection_calls, 0)
        approved = replace(request, capability_token=self.authority.issue(request))
        result = self.broker.submit(approved)
        self.assertEqual(result.status, "completed")
        self.assertEqual(self.desktop.delete_selection_calls, 1)
        self.assertNotIn("selected words", result.message)

    def test_caret_boundary_moves_use_semantic_adapter_without_confirmation(self):
        for action, expected in (
            ("desktop.text.caret_start", "start"),
            ("desktop.text.caret_end", "end"),
            ("desktop.text.caret_previous", "previous"),
            ("desktop.text.caret_next", "next"),
        ):
            result = self.broker.submit(ActionRequest(action))
            self.assertEqual(result.status, "completed")
            self.assertIn("Notes", result.message)
            self.assertEqual(self.desktop.caret_moves[-1], expected)

    def test_word_caret_moves_use_semantic_adapter_without_confirmation(self):
        for action, direction in (
            ("desktop.text.caret_previous_word", "previous"),
            ("desktop.text.caret_next_word", "next"),
        ):
            result = self.broker.submit(ActionRequest(action))
            self.assertEqual(result.status, "completed")
            self.assertEqual(self.desktop.word_caret_moves[-1], direction)
            self.assertIn("Wortanfang", result.message)

    def test_caret_position_is_read_without_confirmation_or_text_content(self):
        result = self.broker.submit(ActionRequest("desktop.text.caret_describe"))
        self.assertEqual(result.status, "completed")
        self.assertEqual(self.desktop.caret_reads, 1)
        self.assertIn("Offset 4 von 12 Zeichen", result.message)
        self.assertNotIn("Quarterly", result.message)

    def test_insert_at_caret_requires_confirmation_and_never_echoes_text(self):
        request = ActionRequest(
            "desktop.text.insert_at_caret", "private words", risk=Risk.MEDIUM
        )
        self.assertEqual(self.broker.submit(request).status, "confirmation_required")
        self.assertEqual(self.desktop.inserted_texts, [])
        approved = replace(request, capability_token=self.authority.issue(request))
        result = self.broker.submit(approved)
        self.assertEqual(result.status, "completed")
        self.assertEqual(self.desktop.inserted_texts, ["private words"])
        self.assertNotIn("private words", result.message)

    def test_character_deletions_require_confirmation_and_use_exact_direction(self):
        for action, direction in (
            ("desktop.text.delete_previous_character", "previous"),
            ("desktop.text.delete_next_character", "next"),
        ):
            request = ActionRequest(action, risk=Risk.MEDIUM)
            self.assertEqual(self.broker.submit(request).status, "confirmation_required")
            approved = replace(request, capability_token=self.authority.issue(request))
            result = self.broker.submit(approved)
            self.assertEqual(result.status, "completed")
            self.assertEqual(self.desktop.character_deletions[-1], direction)

    def test_word_deletions_require_confirmation_and_use_exact_direction(self):
        for action, direction in (
            ("desktop.text.delete_previous_word", "previous"),
            ("desktop.text.delete_next_word", "next"),
        ):
            calls_before = list(self.desktop.word_deletions)
            request = ActionRequest(action, risk=Risk.MEDIUM)
            self.assertEqual(self.broker.submit(request).status, "confirmation_required")
            self.assertEqual(self.desktop.word_deletions, calls_before)
            approved = replace(request, capability_token=self.authority.issue(request))
            result = self.broker.submit(approved)
            self.assertEqual(result.status, "completed")
            self.assertEqual(self.desktop.word_deletions[-1], direction)
            self.assertNotIn("private", result.message)

    def test_word_replacements_require_confirmation_and_never_echo_target(self):
        for action, direction in (
            ("desktop.text.replace_previous_word", "previous"),
            ("desktop.text.replace_next_word", "next"),
        ):
            request = ActionRequest(action, "private replacement", risk=Risk.MEDIUM)
            calls_before = list(self.desktop.word_replacements)
            self.assertEqual(self.broker.submit(request).status, "confirmation_required")
            self.assertEqual(self.desktop.word_replacements, calls_before)
            approved = replace(request, capability_token=self.authority.issue(request))
            result = self.broker.submit(approved)
            self.assertEqual(result.status, "completed")
            self.assertEqual(
                self.desktop.word_replacements[-1], (direction, "private replacement")
            )
            self.assertNotIn("private replacement", result.message)

    def test_character_selections_are_immediate_and_use_exact_direction(self):
        for action, direction in (
            ("desktop.text.select_previous_character", "previous"),
            ("desktop.text.select_next_character", "next"),
        ):
            result = self.broker.submit(ActionRequest(action))
            self.assertEqual(result.status, "completed")
            self.assertEqual(self.desktop.character_selections[-1], direction)

    def test_word_selections_are_immediate_and_use_exact_direction(self):
        for action, direction in (
            ("desktop.text.select_previous_word", "previous"),
            ("desktop.text.select_next_word", "next"),
        ):
            result = self.broker.submit(ActionRequest(action))
            self.assertEqual(result.status, "completed")
            self.assertEqual(self.desktop.word_selections[-1], direction)
            self.assertIn("Wort", result.message)

    def test_current_line_selection_is_immediate_and_semantic(self):
        result = self.broker.submit(ActionRequest("desktop.text.select_current_line"))
        self.assertEqual(result.status, "completed")
        self.assertEqual(self.desktop.line_selections, 1)
        self.assertIn("aktuelle Zeile", result.message)

    def test_current_line_deletion_requires_confirmation_and_is_semantic(self):
        request = ActionRequest("desktop.text.delete_current_line", risk=Risk.MEDIUM)
        self.assertEqual(self.broker.submit(request).status, "confirmation_required")
        self.assertEqual(self.desktop.line_deletions, 0)
        approved = replace(request, capability_token=self.authority.issue(request))
        result = self.broker.submit(approved)
        self.assertEqual(result.status, "completed")
        self.assertEqual(self.desktop.line_deletions, 1)

    def test_current_line_replacement_requires_confirmation_without_echo(self):
        request = ActionRequest(
            "desktop.text.replace_current_line", "private replacement", risk=Risk.MEDIUM
        )
        self.assertEqual(self.broker.submit(request).status, "confirmation_required")
        self.assertEqual(self.desktop.line_replacements, [])
        approved = replace(request, capability_token=self.authority.issue(request))
        result = self.broker.submit(approved)
        self.assertEqual(result.status, "completed")
        self.assertEqual(self.desktop.line_replacements, ["private replacement"])
        self.assertNotIn("private replacement", result.message)

    def test_line_insertions_require_confirmation_without_echo(self):
        for action, direction in (
            ("desktop.text.insert_line_above", "above"),
            ("desktop.text.insert_line_below", "below"),
        ):
            request = ActionRequest(action, "private line", risk=Risk.MEDIUM)
            before = list(self.desktop.line_insertions)
            self.assertEqual(self.broker.submit(request).status, "confirmation_required")
            self.assertEqual(self.desktop.line_insertions, before)
            approved = replace(request, capability_token=self.authority.issue(request))
            result = self.broker.submit(approved)
            self.assertEqual(result.status, "completed")
            self.assertEqual(self.desktop.line_insertions[-1], (direction, "private line"))
            self.assertNotIn("private line", result.message)

    def test_line_duplications_require_confirmation_and_exact_direction(self):
        for action, direction in (
            ("desktop.text.duplicate_line_above", "above"),
            ("desktop.text.duplicate_line_below", "below"),
        ):
            request = ActionRequest(action, risk=Risk.MEDIUM)
            before = list(self.desktop.line_duplications)
            self.assertEqual(self.broker.submit(request).status, "confirmation_required")
            self.assertEqual(self.desktop.line_duplications, before)
            approved = replace(request, capability_token=self.authority.issue(request))
            result = self.broker.submit(approved)
            self.assertEqual(result.status, "completed")
            self.assertEqual(self.desktop.line_duplications[-1], direction)

    def test_line_moves_require_confirmation_and_exact_direction(self):
        for action, direction in (
            ("desktop.text.move_line_up", "up"),
            ("desktop.text.move_line_down", "down"),
        ):
            request = ActionRequest(action, risk=Risk.MEDIUM)
            before = list(self.desktop.line_moves)
            self.assertEqual(self.broker.submit(request).status, "confirmation_required")
            self.assertEqual(self.desktop.line_moves, before)
            approved = replace(request, capability_token=self.authority.issue(request))
            result = self.broker.submit(approved)
            self.assertEqual(result.status, "completed")
            self.assertEqual(self.desktop.line_moves[-1], direction)

    def test_line_joins_require_confirmation_and_exact_direction(self):
        for action, direction in (
            ("desktop.text.join_previous_line", "previous"),
            ("desktop.text.join_next_line", "next"),
        ):
            request = ActionRequest(action, risk=Risk.MEDIUM)
            before = list(self.desktop.line_joins)
            self.assertEqual(self.broker.submit(request).status, "confirmation_required")
            self.assertEqual(self.desktop.line_joins, before)
            approved = replace(request, capability_token=self.authority.issue(request))
            result = self.broker.submit(approved)
            self.assertEqual(result.status, "completed")
            self.assertEqual(self.desktop.line_joins[-1], direction)

    def test_line_split_requires_confirmation_and_has_no_content(self):
        request = ActionRequest("desktop.text.split_line_at_caret", risk=Risk.MEDIUM)
        self.assertEqual(self.broker.submit(request).status, "confirmation_required")
        self.assertEqual(self.desktop.line_splits, 0)
        approved = replace(request, capability_token=self.authority.issue(request))
        result = self.broker.submit(approved)
        self.assertEqual(result.status, "completed")
        self.assertEqual(self.desktop.line_splits, 1)
        self.assertNotIn("first", result.message)

    def test_line_indentation_requires_confirmation_and_exact_direction(self):
        for action, direction in (
            ("desktop.text.indent_current_line", "indent"),
            ("desktop.text.outdent_current_line", "outdent"),
        ):
            request = ActionRequest(action, risk=Risk.MEDIUM)
            before = list(self.desktop.line_indents)
            self.assertEqual(self.broker.submit(request).status, "confirmation_required")
            self.assertEqual(self.desktop.line_indents, before)
            approved = replace(request, capability_token=self.authority.issue(request))
            result = self.broker.submit(approved)
            self.assertEqual(result.status, "completed")
            self.assertEqual(self.desktop.line_indents[-1], direction)

    def test_character_reads_require_confirmation_and_use_exact_direction(self):
        for action, direction in (
            ("desktop.text.read_previous_character", "previous"),
            ("desktop.text.read_next_character", "next"),
        ):
            calls_before = list(self.desktop.character_reads)
            request = ActionRequest(action, risk=Risk.MEDIUM)
            self.assertEqual(self.broker.submit(request).status, "confirmation_required")
            self.assertEqual(self.desktop.character_reads, calls_before)
            approved = replace(request, capability_token=self.authority.issue(request))
            result = self.broker.submit(approved)
            self.assertEqual(result.status, "completed")
            self.assertEqual(self.desktop.character_reads[-1], direction)
            self.assertIn("🙂", result.message)

    def test_character_read_names_whitespace_without_exposing_more_text(self):
        values = ((" ", "Leerzeichen"), ("\t", "Tabulator"), ("\n", "Zeilenumbruch"))
        for value, spoken in values:
            self.desktop.focused_text_character_at_caret = lambda _direction, value=value: (
                "Notes",
                value,
            )
            request = ActionRequest("desktop.text.read_next_character", risk=Risk.MEDIUM)
            approved = replace(request, capability_token=self.authority.issue(request))
            result = self.broker.submit(approved)
            self.assertIn(spoken, result.message)

    def test_character_read_reports_boundary_without_content(self):
        self.desktop.focused_text_character_at_caret = lambda _direction: ("Notes", "")
        request = ActionRequest("desktop.text.read_previous_character", risk=Risk.MEDIUM)
        approved = replace(request, capability_token=self.authority.issue(request))
        result = self.broker.submit(approved)
        self.assertIn("kein Zeichen vor dem Textcursor", result.message)

    def test_word_reads_require_confirmation_and_use_exact_direction(self):
        for action, direction in (
            ("desktop.text.read_previous_word", "previous"),
            ("desktop.text.read_next_word", "next"),
        ):
            calls_before = list(self.desktop.word_reads)
            request = ActionRequest(action, risk=Risk.MEDIUM)
            self.assertEqual(self.broker.submit(request).status, "confirmation_required")
            self.assertEqual(self.desktop.word_reads, calls_before)
            approved = replace(request, capability_token=self.authority.issue(request))
            result = self.broker.submit(approved)
            self.assertEqual(result.status, "completed")
            self.assertEqual(self.desktop.word_reads[-1], direction)
            self.assertIn("Grüße", result.message)

    def test_word_read_reports_boundary_without_content(self):
        self.desktop.focused_text_word_at_caret = lambda _direction: ("Notes", "")
        request = ActionRequest("desktop.text.read_next_word", risk=Risk.MEDIUM)
        approved = replace(request, capability_token=self.authority.issue(request))
        result = self.broker.submit(approved)
        self.assertIn("kein Wort nach dem Textcursor", result.message)

    def test_selection_replacement_requires_confirmation_and_never_echoes_text(self):
        request = ActionRequest(
            "desktop.text.replace_selection", "private replacement", risk=Risk.MEDIUM
        )
        self.assertEqual(self.broker.submit(request).status, "confirmation_required")
        self.assertEqual(self.desktop.selection_replacements, [])
        approved = replace(request, capability_token=self.authority.issue(request))
        result = self.broker.submit(approved)
        self.assertEqual(result.status, "completed")
        self.assertEqual(self.desktop.selection_replacements, ["private replacement"])
        self.assertNotIn("private replacement", result.message)

    def test_clipboard_paste_is_confirmed_exact_and_never_echoed(self):
        executor = SessionExecutor(
            SafeExecutor(dry_run=False),
            GnomeSemanticExecutor(
                self.desktop, clipboard_read=lambda: "first\n  second"
            ),
        )
        broker = ActionBroker(self.authority, executor)
        request = ActionRequest(
            "desktop.text.paste_focused", risk=Risk.MEDIUM, reversible=False
        )
        self.assertEqual(broker.submit(request).status, "confirmation_required")
        approved = replace(request, capability_token=self.authority.issue(request))
        result = broker.submit(approved)
        self.assertEqual(result.status, "completed")
        self.assertEqual(self.desktop.clipboard_values, ["first\n  second"])
        self.assertNotIn("first", result.message)

    def test_clipboard_paste_content_never_reaches_audit(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "audit.jsonl"
            executor = SessionExecutor(
                SafeExecutor(dry_run=False),
                GnomeSemanticExecutor(
                    self.desktop, clipboard_read=lambda: "private\nclipboard"
                ),
            )
            broker = ActionBroker(
                self.authority, executor, audit_log=AuditLog(path, b"p" * 32)
            )
            request = ActionRequest(
                "desktop.text.paste_focused", risk=Risk.MEDIUM, reversible=False
            )
            broker.submit(request)
            approved = replace(request, capability_token=self.authority.issue(request))
            self.assertEqual(broker.submit(approved).status, "completed")
            audit = path.read_text(encoding="utf-8")
        self.assertNotIn("private", audit)
        self.assertNotIn("clipboard", audit)

    def test_clipboard_read_is_confirmed_spoken_bounded_and_audit_redacted(self):
        secret = "private\n" + "x" * 1200
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "audit.jsonl"
            executor = SessionExecutor(
                SafeExecutor(dry_run=False),
                GnomeSemanticExecutor(self.desktop, clipboard_read=lambda: secret),
            )
            broker = ActionBroker(
                self.authority, executor, audit_log=AuditLog(path, b"r" * 32)
            )
            request = ActionRequest("desktop.clipboard.read_text", risk=Risk.MEDIUM)
            self.assertEqual(broker.submit(request).status, "confirmation_required")
            approved = replace(request, capability_token=self.authority.issue(request))
            result = broker.submit(approved)
            audit = path.read_text(encoding="utf-8")
        self.assertEqual(result.status, "completed")
        self.assertIn("private", result.message)
        self.assertIn("restliche Inhalt wurde gekürzt", result.message)
        self.assertNotIn("private", audit)
        self.assertNotIn("x" * 20, audit)
        self.assertIn("[REDACTED: clipboard text]", audit)

    def test_clipboard_write_is_confirmed_stdin_only_and_audit_redacted(self):
        copied = []
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "audit.jsonl"
            executor = SessionExecutor(
                SafeExecutor(dry_run=False),
                GnomeSemanticExecutor(self.desktop, clipboard_write=copied.append),
            )
            broker = ActionBroker(
                self.authority, executor, audit_log=AuditLog(path, b"w" * 32)
            )
            request = ActionRequest(
                "desktop.clipboard.write_text",
                "private clipboard words",
                risk=Risk.MEDIUM,
                reversible=False,
            )
            self.assertEqual(broker.submit(request).status, "confirmation_required")
            approved = replace(request, capability_token=self.authority.issue(request))
            result = broker.submit(approved)
            audit = path.read_text(encoding="utf-8")
        self.assertEqual(result.status, "completed")
        self.assertEqual(copied, ["private clipboard words"])
        self.assertNotIn(request.target, result.message)
        self.assertNotIn(request.target, audit)
        self.assertIn("[REDACTED: clipboard write text]", audit)

    def test_blank_named_activation_is_denied_by_policy(self):
        request = ActionRequest(
            "desktop.control.activate_named", target=" ", risk=Risk.MEDIUM
        )
        self.assertEqual(self.broker.submit(request).status, "denied")
        self.assertEqual(self.desktop.named_activations, [])

    def test_focus_navigation_is_semantic_and_low_risk(self):
        for action, direction in (
            ("desktop.focus.next", 1),
            ("desktop.focus.previous", -1),
        ):
            self.assertEqual(self.broker.submit(ActionRequest(action)).status, "completed")
            self.assertEqual(self.desktop.focus_cycles[-1], direction)

    def test_text_entry_and_clear_require_confirmation_without_echo(self):
        for action, target, expected in (
            ("desktop.text.set", "private words", "private words"),
            ("desktop.text.clear", "", ""),
        ):
            request = ActionRequest(action, target=target, risk=Risk.MEDIUM)
            self.assertEqual(self.broker.submit(request).status, "confirmation_required")
            approved = replace(request, capability_token=self.authority.issue(request))
            result = self.broker.submit(approved)
            self.assertEqual(result.status, "completed")
            self.assertNotIn("private words", result.message)
            self.assertEqual(self.desktop.text_values[-1], expected)

    def test_named_list_selection_requires_confirmation(self):
        request = ActionRequest(
            "desktop.selection.select_named", target="Second", risk=Risk.MEDIUM
        )
        self.assertEqual(self.broker.submit(request).status, "confirmation_required")
        approved = replace(request, capability_token=self.authority.issue(request))
        self.assertEqual(self.broker.submit(approved).status, "completed")
        self.assertEqual(self.desktop.selected_items, ["Second"])

    def test_visible_file_selection_requires_confirmation_without_committing(self):
        request = ActionRequest(
            "desktop.file_dialog.select_visible", target="report.pdf", risk=Risk.MEDIUM
        )
        self.assertEqual(self.broker.submit(request).status, "confirmation_required")
        approved = replace(request, capability_token=self.authority.issue(request))
        result = self.broker.submit(approved)
        self.assertEqual(result.status, "completed")
        self.assertIn("nicht best", result.message)
        self.assertEqual(self.desktop.selected_files, ["report.pdf"])

    def test_visible_file_selection_rejects_path_instead_of_visible_name(self):
        request = ActionRequest(
            "desktop.file_dialog.select_visible",
            target="folder/report.pdf",
            risk=Risk.MEDIUM,
        )
        self.assertEqual(self.broker.submit(request).status, "denied")
        self.assertEqual(self.desktop.selected_files, [])

    def test_file_name_entry_requires_confirmation_without_saving(self):
        request = ActionRequest(
            "desktop.file_dialog.set_name", target="report.pdf", risk=Risk.MEDIUM
        )
        self.assertEqual(self.broker.submit(request).status, "confirmation_required")
        approved = replace(request, capability_token=self.authority.issue(request))
        result = self.broker.submit(approved)
        self.assertEqual(result.status, "completed")
        self.assertIn("nicht gespeichert", result.message)
        self.assertEqual(self.desktop.file_names, ["report.pdf"])

    def test_file_location_entry_requires_confirmation_without_opening(self):
        request = ActionRequest(
            "desktop.file_dialog.set_location",
            target="/home/clausis/Documents",
            risk=Risk.MEDIUM,
        )
        self.assertEqual(self.broker.submit(request).status, "confirmation_required")
        approved = replace(request, capability_token=self.authority.issue(request))
        result = self.broker.submit(approved)
        self.assertEqual(result.status, "completed")
        self.assertIn("nicht geöffnet", result.message)
        self.assertEqual(self.desktop.file_locations, ["/home/clausis/Documents"])

    def test_file_location_rejects_relative_or_parent_path_before_adapter(self):
        for path in ("home/clausis", "/home/clausis/../root", "//server/share"):
            with self.subTest(path=path):
                request = ActionRequest(
                    "desktop.file_dialog.set_location", target=path, risk=Risk.MEDIUM
                )
                self.assertEqual(self.broker.submit(request).status, "denied")
        self.assertEqual(self.desktop.file_locations, [])

    def test_visible_folder_navigation_requires_confirmation_without_accepting(self):
        request = ActionRequest(
            "desktop.file_dialog.open_visible_folder",
            target="Documents",
            risk=Risk.MEDIUM,
        )
        self.assertEqual(self.broker.submit(request).status, "confirmation_required")
        approved = replace(request, capability_token=self.authority.issue(request))
        result = self.broker.submit(approved)
        self.assertEqual(result.status, "completed")
        self.assertIn("nicht bestätigt", result.message)
        self.assertEqual(self.desktop.opened_folders, ["Documents"])

    def test_file_dialog_decisions_require_confirmation(self):
        for decision in ("accept", "cancel"):
            request = ActionRequest(
                "desktop.file_dialog.decide", target=decision, risk=Risk.MEDIUM
            )
            self.assertEqual(self.broker.submit(request).status, "confirmation_required")
            approved = replace(request, capability_token=self.authority.issue(request))
            result = self.broker.submit(approved)
            self.assertEqual(result.status, "completed")
        self.assertEqual(self.desktop.file_dialog_decisions, ["accept", "cancel"])

    def test_invalid_file_dialog_decision_is_denied_before_adapter(self):
        request = ActionRequest(
            "desktop.file_dialog.decide", target="always", risk=Risk.MEDIUM
        )
        self.assertEqual(self.broker.submit(request).status, "denied")
        self.assertEqual(self.desktop.file_dialog_decisions, [])

    def test_standard_dialog_decisions_require_high_risk_confirmation(self):
        for decision in ("accept", "cancel", "retry", "apply"):
            request = ActionRequest(
                "desktop.standard_dialog.decide", target=decision, risk=Risk.HIGH,
                reversible=False,
            )
            self.assertEqual(self.broker.submit(request).status, "confirmation_required")
            approved = replace(request, capability_token=self.authority.issue(request))
            self.assertEqual(self.broker.submit(approved).status, "completed")
        self.assertEqual(
            self.desktop.standard_dialog_decisions,
            ["accept", "cancel", "retry", "apply"],
        )

    def test_invalid_standard_dialog_decision_is_denied_before_adapter(self):
        request = ActionRequest(
            "desktop.standard_dialog.decide", target="delete", risk=Risk.HIGH,
            reversible=False,
        )
        self.assertEqual(self.broker.submit(request).status, "denied")
        self.assertEqual(self.desktop.standard_dialog_decisions, [])

    def test_standard_dialog_read_requires_confirmation_and_returns_bounded_text(self):
        request = ActionRequest("desktop.standard_dialog.read", risk=Risk.MEDIUM)
        self.assertEqual(self.broker.submit(request).status, "confirmation_required")
        approved = replace(request, capability_token=self.authority.issue(request))
        result = self.broker.submit(approved)
        self.assertEqual(result.status, "completed")
        self.assertEqual(
            result.message,
            "Dialog Warning. The operation failed. Check the connection.",
        )
        self.assertEqual(self.desktop.standard_dialog_reads, 1)

    def test_standard_dialog_dismiss_requires_high_risk_confirmation(self):
        request = ActionRequest(
            "desktop.standard_dialog.dismiss", risk=Risk.HIGH, reversible=False
        )
        self.assertEqual(self.broker.submit(request).status, "confirmation_required")
        approved = replace(request, capability_token=self.authority.issue(request))
        result = self.broker.submit(approved)
        self.assertEqual(result.status, "completed")
        self.assertEqual(result.message, "Standarddialog wurde mit Close geschlossen.")
        self.assertEqual(self.desktop.standard_dialog_dismissals, 1)

    def test_named_tree_change_requires_confirmation(self):
        for action, expanded in (
            ("desktop.tree.expand_named", True),
            ("desktop.tree.collapse_named", False),
        ):
            request = ActionRequest(action, target="Documents", risk=Risk.MEDIUM)
            self.assertEqual(self.broker.submit(request).status, "confirmation_required")
            approved = replace(request, capability_token=self.authority.issue(request))
            self.assertEqual(self.broker.submit(approved).status, "completed")
        self.assertEqual(self.desktop.tree_changes, [("Documents", True), ("Documents", False)])

    def test_table_row_selection_requires_confirmation(self):
        request = ActionRequest(
            "desktop.table.select_row", target="Quarterly", risk=Risk.MEDIUM
        )
        self.assertEqual(self.broker.submit(request).status, "confirmation_required")
        approved = replace(request, capability_token=self.authority.issue(request))
        self.assertEqual(self.broker.submit(approved).status, "completed")
        self.assertEqual(self.desktop.table_rows, ["Quarterly"])

    def test_tab_selection_requires_confirmation(self):
        request = ActionRequest(
            "desktop.tabs.select_named", target="Privacy", risk=Risk.MEDIUM
        )
        self.assertEqual(self.broker.submit(request).status, "confirmation_required")
        approved = replace(request, capability_token=self.authority.issue(request))
        self.assertEqual(self.broker.submit(approved).status, "completed")
        self.assertEqual(self.desktop.tabs, ["Privacy"])

    def test_slider_change_requires_confirmation(self):
        request = ActionRequest(
            "desktop.slider.set_percent",
            target="Zoom",
            arguments={"percent": 60},
            risk=Risk.MEDIUM,
        )
        self.assertEqual(self.broker.submit(request).status, "confirmation_required")
        approved = replace(request, capability_token=self.authority.issue(request))
        result = self.broker.submit(approved)
        self.assertEqual(result.status, "completed")
        self.assertIn("60 Prozent", result.message)
        self.assertEqual(self.desktop.sliders, [("Zoom", 60)])

    def test_checkbox_and_radio_changes_require_confirmation(self):
        requests = (
            ActionRequest(
                "desktop.checkbox.set_checked",
                target="Updates",
                arguments={"checked": True},
                risk=Risk.MEDIUM,
            ),
            ActionRequest(
                "desktop.checkbox.set_checked",
                target="Updates",
                arguments={"checked": False},
                risk=Risk.MEDIUM,
            ),
            ActionRequest(
                "desktop.radio.select_named", target="Dark", risk=Risk.MEDIUM
            ),
        )
        for request in requests:
            self.assertEqual(self.broker.submit(request).status, "confirmation_required")
            approved = replace(request, capability_token=self.authority.issue(request))
            self.assertEqual(self.broker.submit(approved).status, "completed")
        self.assertEqual(self.desktop.checkboxes, [("Updates", True), ("Updates", False)])
        self.assertEqual(self.desktop.radios, ["Dark"])

    def test_switch_changes_require_confirmation(self):
        for enabled in (True, False):
            request = ActionRequest(
                "desktop.switch.set_enabled",
                target="Wi-Fi",
                arguments={"checked": enabled},
                risk=Risk.MEDIUM,
            )
            self.assertEqual(self.broker.submit(request).status, "confirmation_required")
            approved = replace(request, capability_token=self.authority.issue(request))
            self.assertEqual(self.broker.submit(approved).status, "completed")
        self.assertEqual(self.desktop.switches, [("Wi-Fi", True), ("Wi-Fi", False)])

    def test_combo_selection_requires_confirmation(self):
        request = ActionRequest(
            "desktop.combo.select_item",
            target="Language",
            arguments={"item": "Deutsch"},
            risk=Risk.MEDIUM,
        )
        self.assertEqual(self.broker.submit(request).status, "confirmation_required")
        approved = replace(request, capability_token=self.authority.issue(request))
        self.assertEqual(self.broker.submit(approved).status, "completed")
        self.assertEqual(self.desktop.combo_items, [("Language", "Deutsch")])

    def test_spin_button_change_requires_confirmation(self):
        request = ActionRequest(
            "desktop.spin_button.set_value",
            target="Copies",
            arguments={"value": 3.0},
            risk=Risk.MEDIUM,
        )
        self.assertEqual(self.broker.submit(request).status, "confirmation_required")
        approved = replace(request, capability_token=self.authority.issue(request))
        self.assertEqual(self.broker.submit(approved).status, "completed")
        self.assertEqual(self.desktop.spin_values, [("Copies", 3.0)])

    def test_menu_item_activation_requires_confirmation(self):
        request = ActionRequest(
            "desktop.menu.activate_item", target="Save", risk=Risk.MEDIUM
        )
        self.assertEqual(self.broker.submit(request).status, "confirmation_required")
        approved = replace(request, capability_token=self.authority.issue(request))
        self.assertEqual(self.broker.submit(approved).status, "completed")
        self.assertEqual(self.desktop.menu_items, ["Save"])

    def test_permission_decision_requires_confirmation(self):
        for decision in ("allow", "deny"):
            request = ActionRequest(
                "desktop.permission_dialog.decide",
                target=decision,
                risk=Risk.MEDIUM,
            )
            self.assertEqual(self.broker.submit(request).status, "confirmation_required")
            approved = replace(request, capability_token=self.authority.issue(request))
            self.assertEqual(self.broker.submit(approved).status, "completed")
        self.assertEqual(self.desktop.permission_decisions, ["allow", "deny"])

    def test_invalid_permission_decision_is_denied_before_adapter(self):
        request = ActionRequest(
            "desktop.permission_dialog.decide", target="always", risk=Risk.MEDIUM
        )
        self.assertEqual(self.broker.submit(request).status, "denied")
        self.assertEqual(self.desktop.permission_decisions, [])

    def test_window_cycle_uses_semantic_adapter(self):
        result = self.broker.submit(ActionRequest("desktop.window.next"))
        self.assertEqual(result.status, "completed")
        self.assertEqual(self.desktop.cycled, [1])

    def test_window_management_uses_semantic_adapter(self):
        for operation in ("minimize", "maximize", "restore"):
            result = self.broker.submit(ActionRequest(f"desktop.window.{operation}"))
            self.assertEqual(result.status, "completed")
        self.assertEqual(self.desktop.window_actions, ["minimize", "maximize", "restore"])

    def test_window_close_requires_confirmation(self):
        request = ActionRequest("desktop.window.close", risk=Risk.MEDIUM)
        self.assertEqual(self.broker.submit(request).status, "confirmation_required")
        approved = replace(request, capability_token=self.authority.issue(request))
        self.assertEqual(self.broker.submit(approved).status, "completed")
        self.assertEqual(self.desktop.window_actions, ["close"])

    def test_workspace_window_moves_require_confirmation(self):
        for operation in ("workspace_previous", "workspace_next"):
            request = ActionRequest(f"desktop.window.{operation}", risk=Risk.MEDIUM)
            self.assertEqual(self.broker.submit(request).status, "confirmation_required")
            approved = replace(request, capability_token=self.authority.issue(request))
            self.assertEqual(self.broker.submit(approved).status, "completed")
        self.assertEqual(
            self.desktop.window_actions,
            ["workspace_previous", "workspace_next"],
        )

    def test_shell_controls_use_semantic_adapter(self):
        for operation in ("overview", "applications", "quick_settings", "notifications"):
            result = self.broker.submit(ActionRequest(f"desktop.{operation}"))
            self.assertEqual(result.status, "completed")
        self.assertEqual(
            self.desktop.shell_actions,
            ["overview", "applications", "quick_settings", "notifications"],
        )

    def test_notification_read_requires_confirmation_and_redacts_result(self):
        request = ActionRequest("desktop.notifications.read", risk=Risk.MEDIUM)
        self.assertEqual(self.broker.submit(request).status, "confirmation_required")
        approved = replace(request, capability_token=self.authority.issue(request))
        result = self.broker.submit(approved)
        self.assertEqual(result.status, "completed")
        self.assertEqual(
            result.message,
            "Sichtbare Benachrichtigungen. Nummer 1: Backup complete. "
            "Nummer 2: Files are safe.",
        )
        self.assertEqual(self.desktop.notification_reads, 1)

    def test_notification_dismiss_requires_high_risk_confirmation(self):
        request = ActionRequest(
            "desktop.notifications.dismiss", "2", risk=Risk.HIGH, reversible=False
        )
        self.assertEqual(self.broker.submit(request).status, "confirmation_required")
        approved = replace(request, capability_token=self.authority.issue(request))
        result = self.broker.submit(approved)
        self.assertEqual(result.status, "completed")
        self.assertEqual(result.message, "Benachrichtigung Nummer 2 wurde verworfen.")
        self.assertEqual(self.desktop.notification_dismissals, [2])

    def test_real_adapter_selects_exact_atspi_window_action(self):
        action = FakeWindowAction(("activate", "maximize", "close"))
        window = FakeWindow(action)
        desktop = PyAtSpiDesktop.__new__(PyAtSpiDesktop)
        desktop._active_window = lambda: (object(), window)
        self.assertEqual(desktop.window_action("maximize"), "Dokumente")
        self.assertEqual(action.called, [1])

    def test_real_adapter_selects_exact_workspace_action(self):
        action = FakeWindowAction(("maximize", "move to workspace right"))
        window = FakeWindow(action)
        desktop = PyAtSpiDesktop.__new__(PyAtSpiDesktop)
        desktop._active_window = lambda: (object(), window)
        self.assertEqual(desktop.window_action("workspace_next"), "Dokumente")
        self.assertEqual(action.called, [1])

    def test_real_adapter_does_not_infer_workspace_move_from_generic_action(self):
        action = FakeWindowAction(("move", "activate"))
        window = FakeWindow(action)
        desktop = PyAtSpiDesktop.__new__(PyAtSpiDesktop)
        desktop._active_window = lambda: (object(), window)
        with self.assertRaises(GnomeAdapterError):
            desktop.window_action("workspace_previous")
        self.assertEqual(action.called, [])

    def test_real_adapter_fails_closed_without_matching_window_action(self):
        window = FakeWindow(FakeWindowAction(("activate",)))
        desktop = PyAtSpiDesktop.__new__(PyAtSpiDesktop)
        desktop._active_window = lambda: (object(), window)
        with self.assertRaises(GnomeAdapterError):
            desktop.window_action("close")

    def test_real_adapter_rejects_duplicate_window_action_without_invocation(self):
        action = FakeWindowAction(("maximize", "maximieren"))
        window = FakeWindow(action)
        desktop = PyAtSpiDesktop.__new__(PyAtSpiDesktop)
        desktop._active_window = lambda: (object(), window)

        with self.assertRaisesRegex(GnomeAdapterError, "nicht eindeutig"):
            desktop.window_action("maximize")
        self.assertEqual(action.called, [])

    def test_real_back_requires_one_global_exact_action(self):
        action = FakeWindowAction(("activate", "back"))
        back = FakeNode("Zurück", action=action)
        window = FakeNode("Window", children=(back,), role="frame")
        desktop = PyAtSpiDesktop.__new__(PyAtSpiDesktop)
        desktop._active_window = lambda: (object(), window)

        self.assertEqual(desktop.navigate_back(), "Zurück")
        self.assertEqual(action.called, [1])

    def test_real_back_rejects_duplicate_targets_without_invocation(self):
        first = FakeNode("Back", action=FakeWindowAction(("back",)))
        second = FakeNode("Back", action=FakeWindowAction(("go back",)))
        window = FakeNode("Window", children=(first, second), role="frame")
        desktop = PyAtSpiDesktop.__new__(PyAtSpiDesktop)
        desktop._active_window = lambda: (object(), window)

        with self.assertRaisesRegex(GnomeAdapterError, "nicht eindeutig"):
            desktop.navigate_back()
        self.assertEqual(first.action.called, [])
        self.assertEqual(second.action.called, [])

    def test_real_back_rejects_action_that_changed_after_discovery(self):
        discovered = FakeWindowAction(("back",))
        rebound = FakeWindowAction(("delete",))
        back = FakeNode("Back", action=discovered)
        actions = iter((discovered, rebound))
        back.queryAction = lambda: next(actions)
        window = FakeNode("Window", children=(back,), role="frame")
        desktop = PyAtSpiDesktop.__new__(PyAtSpiDesktop)
        desktop._active_window = lambda: (object(), window)

        with self.assertRaisesRegex(GnomeAdapterError, "nicht mehr eindeutig gebunden"):
            desktop.navigate_back()
        self.assertEqual(discovered.called, [])
        self.assertEqual(rebound.called, [])

    def test_named_activation_requires_one_exact_match(self):
        first = FakeNode("Cancel", action=FakeWindowAction(("click",)))
        second = FakeNode("Cancel", action=FakeWindowAction(("click",)))
        desktop = PyAtSpiDesktop.__new__(PyAtSpiDesktop)
        window = object()
        desktop._active_window = lambda: (object(), window)
        desktop._controls = lambda _window: [
            (first, ("click",)),
            (second, ("click",)),
        ]
        with self.assertRaises(GnomeAdapterError):
            desktop.activate_named("Cancel")

    def test_numbered_activation_rebinds_identical_order_before_invocation(self):
        first_action = FakeWindowAction(("click",))
        second_action = FakeWindowAction(("press",))
        first = FakeNode("First", action=first_action)
        second = FakeNode("Second", action=second_action)
        window = object()
        desktop = PyAtSpiDesktop.__new__(PyAtSpiDesktop)
        desktop._active_window = lambda: (object(), window)
        desktop._controls = lambda _window: [
            (first, ("click",)),
            (second, ("press",)),
        ]

        self.assertEqual(desktop.activate(2), "Second")
        self.assertEqual(first_action.called, [])
        self.assertEqual(second_action.called, [0])

    def test_numbered_activation_rejects_active_window_change(self):
        action = FakeWindowAction(("click",))
        control = FakeNode("Continue", action=action)
        windows = iter((object(), object()))
        desktop = PyAtSpiDesktop.__new__(PyAtSpiDesktop)
        desktop._active_window = lambda: (object(), next(windows))
        desktop._controls = lambda _window: [(control, ("click",))]

        with self.assertRaisesRegex(GnomeAdapterError, "Fenster.*gewechselt"):
            desktop.activate(1)
        self.assertEqual(action.called, [])

    def test_numbered_activation_rejects_added_removed_or_reordered_controls(self):
        for rebound in ("added", "removed", "reordered"):
            first_action = FakeWindowAction(("click",))
            second_action = FakeWindowAction(("click",))
            third_action = FakeWindowAction(("click",))
            first = FakeNode("First", action=first_action)
            second = FakeNode("Second", action=second_action)
            third = FakeNode("Third", action=third_action)
            initial = [(first, ("click",)), (second, ("click",))]
            changed = {
                "added": [*initial, (third, ("click",))],
                "removed": [initial[0]],
                "reordered": [initial[1], initial[0]],
            }[rebound]
            snapshots = iter((initial, changed))
            window = object()
            desktop = PyAtSpiDesktop.__new__(PyAtSpiDesktop)
            desktop._active_window = lambda: (object(), window)
            desktop._controls = lambda _window: next(snapshots)

            with self.subTest(rebound=rebound):
                with self.assertRaisesRegex(GnomeAdapterError, "Nummerierung.*geändert"):
                    desktop.activate(1)
                self.assertEqual(first_action.called, [])
                self.assertEqual(second_action.called, [])
                self.assertEqual(third_action.called, [])

    def test_named_activation_invokes_unique_exact_match(self):
        action = FakeWindowAction(("activate", "click"))
        control = FakeNode("Cancel", action=action)
        desktop = PyAtSpiDesktop.__new__(PyAtSpiDesktop)
        window = object()
        desktop._active_window = lambda: (object(), window)
        desktop._controls = lambda _window: [(control, ("activate", "click"))]
        self.assertEqual(desktop.activate_named("cancel"), "Cancel")
        self.assertEqual(action.called, [1])

    def test_named_activation_rejects_unrecognized_action_without_invocation(self):
        action = FakeWindowAction(("delete",))
        control = FakeNode("Document", action=action)
        desktop = PyAtSpiDesktop.__new__(PyAtSpiDesktop)
        window = object()
        desktop._active_window = lambda: (object(), window)
        desktop._controls = lambda _window: [(control, ("delete",))]

        with self.assertRaisesRegex(GnomeAdapterError, "keine erlaubte Aktivierungsaktion"):
            desktop.activate_named("Document")
        self.assertEqual(action.called, [])

    def test_named_activation_rebinds_action_names_before_invocation(self):
        action = FakeWindowAction(("delete", "click"))
        control = FakeNode("Document", action=action)
        desktop = PyAtSpiDesktop.__new__(PyAtSpiDesktop)
        window = object()
        desktop._active_window = lambda: (object(), window)
        desktop._controls = lambda _window: [(control, ("click", "delete"))]

        self.assertEqual(desktop.activate_named("Document"), "Document")
        self.assertEqual(action.called, [1])

    def test_named_activation_rejects_stale_action_that_became_unsafe(self):
        action = FakeWindowAction(("delete",))
        control = FakeNode("Document", action=action)
        desktop = PyAtSpiDesktop.__new__(PyAtSpiDesktop)
        window = object()
        desktop._active_window = lambda: (object(), window)
        desktop._controls = lambda _window: [(control, ("click",))]

        with self.assertRaisesRegex(GnomeAdapterError, "keine erlaubte Aktivierungsaktion"):
            desktop.activate_named("Document")
        self.assertEqual(action.called, [])

    def test_named_activation_rejects_active_window_change_before_invocation(self):
        action = FakeWindowAction(("click",))
        control = FakeNode("Continue", action=action)
        first_window = object()
        second_window = object()
        windows = iter((first_window, second_window))
        desktop = PyAtSpiDesktop.__new__(PyAtSpiDesktop)
        desktop._active_window = lambda: (object(), next(windows))
        desktop._controls = lambda _window: [(control, ("click",))]

        with self.assertRaisesRegex(GnomeAdapterError, "Fenster.*gewechselt"):
            desktop.activate_named("Continue")
        self.assertEqual(action.called, [])

    def test_named_activation_rejects_control_removed_before_invocation(self):
        action = FakeWindowAction(("click",))
        control = FakeNode("Continue", action=action)
        window = object()
        calls = iter(([(control, ("click",))], []))
        desktop = PyAtSpiDesktop.__new__(PyAtSpiDesktop)
        desktop._active_window = lambda: (object(), window)
        desktop._controls = lambda _window: next(calls)

        with self.assertRaisesRegex(GnomeAdapterError, "nicht mehr eindeutig.*gebunden"):
            desktop.activate_named("Continue")
        self.assertEqual(action.called, [])

    def test_real_focus_cycle_uses_component_grab_focus(self):
        first = FakeFocusNode("First", focused=True)
        second = FakeFocusNode("Second")
        first.group = second.group = (first, second)
        desktop = PyAtSpiDesktop.__new__(PyAtSpiDesktop)
        desktop._atspi = type("AtSpi", (), {"STATE_FOCUSED": object()})
        desktop._active_window = lambda: (object(), object())
        desktop._controls = lambda _window: [
            (first, ("click",)),
            (second, ("click",)),
        ]
        self.assertEqual(desktop.cycle_focus(1), "Second")
        self.assertFalse(first.focused)
        self.assertTrue(second.focused)
        self.assertEqual(second.focus_calls, 1)

    def test_real_focus_cycle_rejects_ambiguous_start_without_mutation(self):
        first = FakeFocusNode("First", focused=True)
        second = FakeFocusNode("Second", focused=True)
        first.group = second.group = (first, second)
        desktop = PyAtSpiDesktop.__new__(PyAtSpiDesktop)
        desktop._atspi = type("AtSpi", (), {"STATE_FOCUSED": "focused"})
        desktop._active_window = lambda: (object(), object())
        desktop._controls = lambda _window: [(first, ("click",)), (second, ("click",))]
        with self.assertRaises(GnomeAdapterError):
            desktop.cycle_focus(1)
        self.assertEqual(first.focus_calls, 0)
        self.assertEqual(second.focus_calls, 0)

    def test_real_focus_cycle_restores_previous_focus_on_mismatch(self):
        first = FakeFocusNode("First", focused=True)
        second = FakeFocusNode("Second", partial=True)
        first.group = second.group = (first, second)
        desktop = PyAtSpiDesktop.__new__(PyAtSpiDesktop)
        desktop._atspi = type("AtSpi", (), {"STATE_FOCUSED": "focused"})
        desktop._active_window = lambda: (object(), object())
        desktop._controls = lambda _window: [(first, ("click",)), (second, ("click",))]
        with self.assertRaises(GnomeAdapterError):
            desktop.cycle_focus(1)
        self.assertTrue(first.focused)
        self.assertFalse(second.focused)
        self.assertEqual(second.focus_calls, 1)
        self.assertEqual(first.focus_calls, 1)

    def test_real_focus_cycle_reports_failed_restoration(self):
        first = FakeFocusNode("First", focused=True, accepted=False)
        second = FakeFocusNode("Second", partial=True)
        first.group = second.group = (first, second)
        desktop = PyAtSpiDesktop.__new__(PyAtSpiDesktop)
        desktop._atspi = type("AtSpi", (), {"STATE_FOCUSED": "focused"})
        desktop._active_window = lambda: (object(), object())
        desktop._controls = lambda _window: [(first, ("click",)), (second, ("click",))]
        with self.assertRaisesRegex(GnomeAdapterError, "nicht zurückgesetzt"):
            desktop.cycle_focus(1)

    def test_real_focus_cycle_accepts_verified_transition_from_no_focus(self):
        first = FakeFocusNode("First")
        second = FakeFocusNode("Second")
        first.group = second.group = (first, second)
        desktop = PyAtSpiDesktop.__new__(PyAtSpiDesktop)
        desktop._atspi = type("AtSpi", (), {"STATE_FOCUSED": "focused"})
        desktop._active_window = lambda: (object(), object())
        desktop._controls = lambda _window: [(first, ("click",)), (second, ("click",))]
        self.assertEqual(desktop.cycle_focus(-1), "Second")
        self.assertFalse(first.focused)
        self.assertTrue(second.focused)

    def test_real_named_focus_moves_to_unique_visible_focusable_element(self):
        old = FakeNamedFocusNode("Old", focused=True)
        target = FakeNamedFocusNode("Details")
        old.group = target.group = (old, target)
        window = FakeNode("Window", children=(old, target), role="frame")
        desktop = PyAtSpiDesktop.__new__(PyAtSpiDesktop)
        desktop._atspi = type(
            "AtSpi",
            (),
            {
                "STATE_FOCUSED": "focused",
                "STATE_SHOWING": "showing",
                "STATE_FOCUSABLE": "focusable",
            },
        )
        desktop._active_window = lambda: (object(), window)
        self.assertEqual(desktop.focus_named("Details"), "Details")
        self.assertFalse(old.focused)
        self.assertTrue(target.focused)

    def test_real_named_focus_rejects_duplicate_hidden_and_unfocusable_targets(self):
        first = FakeNamedFocusNode("Details")
        second = FakeNamedFocusNode("Details")
        window = FakeNode("Window", children=(first, second), role="frame")
        desktop = PyAtSpiDesktop.__new__(PyAtSpiDesktop)
        desktop._atspi = type(
            "AtSpi",
            (),
            {
                "STATE_FOCUSED": "focused",
                "STATE_SHOWING": "showing",
                "STATE_FOCUSABLE": "focusable",
            },
        )
        desktop._active_window = lambda: (object(), window)
        with self.assertRaises(GnomeAdapterError):
            desktop.focus_named("Details")
        for target in (
            FakeNamedFocusNode("Details", showing=False),
            FakeNamedFocusNode("Details", focusable=False),
        ):
            window = FakeNode("Window", children=(target,), role="frame")
            desktop._active_window = lambda window=window: (object(), window)
            with self.assertRaises(GnomeAdapterError):
                desktop.focus_named("Details")
        self.assertEqual(first.focus_calls, 0)
        self.assertEqual(second.focus_calls, 0)

    def test_real_named_focus_restores_previous_focus_on_mismatch(self):
        old = FakeNamedFocusNode("Old", focused=True)
        target = FakeNamedFocusNode("Details", mismatch=True)
        old.group = target.group = (old, target)
        window = FakeNode("Window", children=(old, target), role="frame")
        desktop = PyAtSpiDesktop.__new__(PyAtSpiDesktop)
        desktop._atspi = type(
            "AtSpi",
            (),
            {
                "STATE_FOCUSED": "focused",
                "STATE_SHOWING": "showing",
                "STATE_FOCUSABLE": "focusable",
            },
        )
        desktop._active_window = lambda: (object(), window)
        with self.assertRaises(GnomeAdapterError):
            desktop.focus_named("Details")
        self.assertTrue(old.focused)
        self.assertFalse(target.focused)
        self.assertEqual(target.focus_calls, 1)
        self.assertEqual(old.focus_calls, 1)

    def test_real_named_focus_rejects_missing_or_ambiguous_start(self):
        for old_nodes in (
            (FakeNamedFocusNode("Old"),),
            (
                FakeNamedFocusNode("Old one", focused=True),
                FakeNamedFocusNode("Old two", focused=True),
            ),
        ):
            target = FakeNamedFocusNode("Details")
            group = (*old_nodes, target)
            for node in group:
                node.group = group
            window = FakeNode("Window", children=group, role="frame")
            desktop = PyAtSpiDesktop.__new__(PyAtSpiDesktop)
            desktop._atspi = type("AtSpi", (), {
                "STATE_FOCUSED": "focused",
                "STATE_SHOWING": "showing",
                "STATE_FOCUSABLE": "focusable",
            })
            desktop._active_window = lambda window=window: (object(), window)

            with self.assertRaisesRegex(GnomeAdapterError, "Ausgangsfokus.*nicht eindeutig"):
                desktop.focus_named("Details")
            self.assertEqual(target.focus_calls, 0)

    def test_real_named_focus_rolls_back_exception_after_partial_change(self):
        old = FakeNamedFocusNode("Old", focused=True)
        target = FakeNamedFocusNode("Details", raise_after_mutation=True)
        old.group = target.group = (old, target)
        window = FakeNode("Window", children=(old, target), role="frame")
        desktop = PyAtSpiDesktop.__new__(PyAtSpiDesktop)
        desktop._atspi = type("AtSpi", (), {
            "STATE_FOCUSED": "focused",
            "STATE_SHOWING": "showing",
            "STATE_FOCUSABLE": "focusable",
        })
        desktop._active_window = lambda: (object(), window)

        with self.assertRaisesRegex(GnomeAdapterError, "nicht fokussiert"):
            desktop.focus_named("Details")
        self.assertTrue(old.focused)
        self.assertFalse(target.focused)

    def test_real_named_focus_reports_failed_exception_rollback(self):
        old = FakeNamedFocusNode("Old", focused=True, accepted=False)
        target = FakeNamedFocusNode("Details", raise_after_mutation=True)
        old.group = target.group = (old, target)
        window = FakeNode("Window", children=(old, target), role="frame")
        desktop = PyAtSpiDesktop.__new__(PyAtSpiDesktop)
        desktop._atspi = type("AtSpi", (), {
            "STATE_FOCUSED": "focused",
            "STATE_SHOWING": "showing",
            "STATE_FOCUSABLE": "focusable",
        })
        desktop._active_window = lambda: (object(), window)

        with self.assertRaisesRegex(GnomeAdapterError, "nicht zurückgesetzt"):
            desktop.focus_named("Details")

    def test_real_text_entry_verifies_readback(self):
        node = FakeEditableNode()
        desktop = PyAtSpiDesktop.__new__(PyAtSpiDesktop)
        desktop._atspi = type("AtSpi", (), {"STATE_FOCUSED": object()})
        desktop._active_window = lambda: (object(), object())
        desktop._find_state = lambda _window, _state: node
        self.assertEqual(desktop.set_focused_text("hello"), "Search")
        self.assertEqual(node.value, "hello")

    def test_real_focused_text_read_is_bounded_and_normalized(self):
        node = FakeReadableText("first\n  " + "x" * 1000)
        desktop = PyAtSpiDesktop.__new__(PyAtSpiDesktop)
        desktop._atspi = type("AtSpi", (), {"STATE_FOCUSED": object()})
        desktop._active_window = lambda: (object(), object())
        desktop._find_state = lambda _window, _state: node
        name, value = desktop.read_focused_text()
        self.assertEqual(name, "Notes")
        self.assertTrue(value.startswith("first "))
        self.assertTrue(value.endswith(" …"))
        self.assertEqual(node.read_ranges, [(0, 1000)])

    def test_real_focused_text_read_rejects_protected_and_wrong_roles(self):
        desktop = PyAtSpiDesktop.__new__(PyAtSpiDesktop)
        desktop._atspi = type("AtSpi", (), {"STATE_FOCUSED": object()})
        desktop._active_window = lambda: (object(), object())
        for node in (
            FakeReadableText("private", attributes=("text-input-type:password",)),
            FakeReadableText("label", role="label"),
        ):
            desktop._find_state = lambda _window, _state, node=node: node
            with self.assertRaises(GnomeAdapterError):
                desktop.read_focused_text()
            self.assertEqual(node.read_ranges, [])

    def test_real_focused_text_read_rejects_uninspectable_attributes(self):
        node = FakeReadableText("private")
        node.getAttributes = lambda: (_ for _ in ()).throw(RuntimeError("hidden"))
        desktop = PyAtSpiDesktop.__new__(PyAtSpiDesktop)
        desktop._atspi = type("AtSpi", (), {"STATE_FOCUSED": object()})
        desktop._active_window = lambda: (object(), object())
        desktop._find_state = lambda _window, _state: node
        with self.assertRaises(GnomeAdapterError):
            desktop.read_focused_text()
        self.assertEqual(node.read_ranges, [])

    def test_real_focused_text_copy_reads_exact_complete_text(self):
        node = FakeReadableText("first\n  second")
        desktop = PyAtSpiDesktop.__new__(PyAtSpiDesktop)
        desktop._atspi = type("AtSpi", (), {"STATE_FOCUSED": object()})
        desktop._active_window = lambda: (object(), object())
        desktop._find_state = lambda _window, _state: node
        name, value = desktop.focused_text_for_clipboard()
        self.assertEqual(name, "Notes")
        self.assertEqual(value, "first\n  second")
        self.assertEqual(node.read_ranges, [(0, len(value))])

    def test_real_focused_text_copy_rejects_protected_empty_and_oversized(self):
        desktop = PyAtSpiDesktop.__new__(PyAtSpiDesktop)
        desktop._atspi = type("AtSpi", (), {"STATE_FOCUSED": object()})
        desktop._active_window = lambda: (object(), object())
        for node in (
            FakeReadableText("private", attributes=("text-input-type:password",)),
            FakeReadableText(""),
            FakeReadableText("x" * 100_001),
        ):
            desktop._find_state = lambda _window, _state, node=node: node
            with self.assertRaises(GnomeAdapterError):
                desktop.focused_text_for_clipboard()
            self.assertEqual(node.read_ranges, [])

    def test_real_text_selection_copy_reads_exact_single_span(self):
        node = FakeReadableText("zero first\n second end", selections=((5, 18),))
        desktop = PyAtSpiDesktop.__new__(PyAtSpiDesktop)
        desktop._atspi = type("AtSpi", (), {"STATE_FOCUSED": object()})
        desktop._active_window = lambda: (object(), object())
        desktop._find_state = lambda _window, _state: node
        name, value = desktop.selected_text_for_clipboard()
        self.assertEqual(name, "Notes")
        self.assertEqual(value, "first\n second")
        self.assertEqual(node.read_ranges, [(5, 18)])

    def test_real_text_selection_copy_rejects_ambiguous_unsafe_and_oversized(self):
        cases = (
            FakeReadableText("plain", selections=()),
            FakeReadableText("plain", selections=((0, 1), (2, 3))),
            FakeReadableText("private", attributes=("protected:true",), selections=((0, 7),)),
            FakeReadableText("x" * 100_001, selections=((0, 100_001),)),
            FakeReadableText("abc", selections=((2, 2),)),
        )
        desktop = PyAtSpiDesktop.__new__(PyAtSpiDesktop)
        desktop._atspi = type("AtSpi", (), {"STATE_FOCUSED": object()})
        desktop._active_window = lambda: (object(), object())
        for node in cases:
            desktop._find_state = lambda _window, _state, node=node: node
            with self.assertRaises(GnomeAdapterError):
                desktop.selected_text_for_clipboard()
            self.assertEqual(node.read_ranges, [])

    def test_real_select_all_text_replaces_selection_and_verifies_exact_span(self):
        node = FakeReadableText("first second", selections=((2, 5), (7, 9)))
        desktop = PyAtSpiDesktop.__new__(PyAtSpiDesktop)
        desktop._atspi = type("AtSpi", (), {"STATE_FOCUSED": object()})
        desktop._active_window = lambda: (object(), object())
        desktop._find_state = lambda _window, _state: node
        self.assertEqual(desktop.select_all_focused_text(), "Notes")
        self.assertEqual(node.selections, ((0, 12),))

    def test_real_select_all_text_rejects_empty_oversized_and_protected(self):
        desktop = PyAtSpiDesktop.__new__(PyAtSpiDesktop)
        desktop._atspi = type("AtSpi", (), {"STATE_FOCUSED": object()})
        desktop._active_window = lambda: (object(), object())
        for node in (
            FakeReadableText(""),
            FakeReadableText("x" * 100_001),
            FakeReadableText("private", attributes=("protected:true",)),
        ):
            desktop._find_state = lambda _window, _state, node=node: node
            with self.assertRaises(GnomeAdapterError):
                desktop.select_all_focused_text()
            self.assertEqual(node.selections, ())

    def test_real_select_all_text_restores_previous_selection_on_mismatch(self):
        node = FakeReadableText(
            "first second", selections=((2, 5),), selection_mismatch=True
        )
        desktop = PyAtSpiDesktop.__new__(PyAtSpiDesktop)
        desktop._atspi = type("AtSpi", (), {"STATE_FOCUSED": object()})
        desktop._active_window = lambda: (object(), object())
        desktop._find_state = lambda _window, _state: node
        with self.assertRaisesRegex(GnomeAdapterError, "nicht bestätigt"):
            desktop.select_all_focused_text()
        self.assertEqual(node.selections, ((2, 5),))

    def test_real_clear_text_selection_removes_all_spans_and_is_idempotent(self):
        desktop = PyAtSpiDesktop.__new__(PyAtSpiDesktop)
        desktop._atspi = type("AtSpi", (), {"STATE_FOCUSED": object()})
        desktop._active_window = lambda: (object(), object())
        for selections in (((1, 3), (4, 7)), ()):
            node = FakeReadableText("abcdefgh", selections=selections)
            desktop._find_state = lambda _window, _state, node=node: node
            self.assertEqual(desktop.clear_focused_text_selection(), "Notes")
            self.assertEqual(node.selections, ())

    def test_real_clear_text_selection_restores_spans_after_rejection(self):
        node = FakeReadableText(
            "abcdefgh", selections=((1, 3), (4, 7)), reject_remove_once_at=0
        )
        desktop = PyAtSpiDesktop.__new__(PyAtSpiDesktop)
        desktop._atspi = type("AtSpi", (), {"STATE_FOCUSED": object()})
        desktop._active_window = lambda: (object(), object())
        desktop._find_state = lambda _window, _state: node
        with self.assertRaisesRegex(GnomeAdapterError, "nicht bestätigt"):
            desktop.clear_focused_text_selection()
        self.assertEqual(node.selections, ((1, 3), (4, 7)))

    def test_real_clear_text_selection_rejects_protected_and_malformed_spans(self):
        desktop = PyAtSpiDesktop.__new__(PyAtSpiDesktop)
        desktop._atspi = type("AtSpi", (), {"STATE_FOCUSED": object()})
        desktop._active_window = lambda: (object(), object())
        for node in (
            FakeReadableText("private", attributes=("protected:true",), selections=((0, 7),)),
            FakeReadableText("abc", selections=((2, 2),)),
            FakeReadableText("x" * 100_001, selections=((0, 1),)),
        ):
            desktop._find_state = lambda _window, _state, node=node: node
            with self.assertRaises(GnomeAdapterError):
                desktop.clear_focused_text_selection()

    def test_real_delete_text_selection_verifies_exact_post_state(self):
        node = FakeReadableText("zero first end", selections=((5, 10),), caret_offset=10)
        desktop = PyAtSpiDesktop.__new__(PyAtSpiDesktop)
        desktop._atspi = type("AtSpi", (), {"STATE_FOCUSED": object()})
        desktop._active_window = lambda: (object(), object())
        desktop._find_state = lambda _window, _state: node
        self.assertEqual(desktop.delete_focused_text_selection(), "Notes")
        self.assertEqual(node.value, "zero  end")
        self.assertEqual(node.selections, ())

    def test_real_delete_text_selection_restores_on_mismatch(self):
        node = FakeReadableText(
            "zero first end", selections=((5, 10),), caret_offset=10, delete_mismatch=True
        )
        desktop = PyAtSpiDesktop.__new__(PyAtSpiDesktop)
        desktop._atspi = type("AtSpi", (), {"STATE_FOCUSED": object()})
        desktop._active_window = lambda: (object(), object())
        desktop._find_state = lambda _window, _state: node
        with self.assertRaisesRegex(GnomeAdapterError, "nicht bestätigt"):
            desktop.delete_focused_text_selection()
        self.assertEqual(node.value, "zero first end")
        self.assertEqual(node.caretOffset, 10)
        self.assertEqual(node.selections, ((5, 10),))

    def test_real_delete_text_selection_rejects_unsafe_or_ambiguous_inputs(self):
        desktop = PyAtSpiDesktop.__new__(PyAtSpiDesktop)
        desktop._atspi = type("AtSpi", (), {"STATE_FOCUSED": object()})
        desktop._active_window = lambda: (object(), object())
        for node in (
            FakeReadableText("plain", selections=()),
            FakeReadableText("plain", selections=((0, 1), (2, 3))),
            FakeReadableText("private", attributes=("protected:true",), selections=((0, 7),)),
            FakeReadableText("x" * 100_001, selections=((0, 1),)),
        ):
            original = node.value
            desktop._find_state = lambda _window, _state, node=node: node
            with self.assertRaises(GnomeAdapterError):
                desktop.delete_focused_text_selection()
            self.assertEqual(node.value, original)

    def test_real_caret_moves_to_exact_start_and_end(self):
        desktop = PyAtSpiDesktop.__new__(PyAtSpiDesktop)
        desktop._atspi = type("AtSpi", (), {"STATE_FOCUSED": object()})
        desktop._active_window = lambda: (object(), object())
        node = FakeReadableText("abcdefgh", caret_offset=4)
        desktop._find_state = lambda _window, _state: node
        self.assertEqual(desktop.move_focused_text_caret("start"), "Notes")
        self.assertEqual(node.caretOffset, 0)
        self.assertEqual(desktop.move_focused_text_caret("end"), "Notes")
        self.assertEqual(node.caretOffset, 8)

    def test_real_caret_moves_exactly_one_character_and_clamps_at_boundaries(self):
        desktop = PyAtSpiDesktop.__new__(PyAtSpiDesktop)
        desktop._atspi = type("AtSpi", (), {"STATE_FOCUSED": object()})
        desktop._active_window = lambda: (object(), object())
        node = FakeReadableText("aö🙂z", caret_offset=2)
        desktop._find_state = lambda _window, _state: node
        self.assertEqual(desktop.move_focused_text_caret("previous"), "Notes")
        self.assertEqual(node.caretOffset, 1)
        self.assertEqual(desktop.move_focused_text_caret("next"), "Notes")
        self.assertEqual(node.caretOffset, 2)
        node.caretOffset = 0
        self.assertEqual(desktop.move_focused_text_caret("previous"), "Notes")
        self.assertEqual(node.caretOffset, 0)
        node.caretOffset = node.characterCount
        self.assertEqual(desktop.move_focused_text_caret("next"), "Notes")
        self.assertEqual(node.caretOffset, node.characterCount)

    def test_real_caret_move_restores_previous_offset_on_mismatch(self):
        node = FakeReadableText("abcdefgh", caret_offset=4, caret_mismatch_once=True)
        desktop = PyAtSpiDesktop.__new__(PyAtSpiDesktop)
        desktop._atspi = type("AtSpi", (), {"STATE_FOCUSED": object()})
        desktop._active_window = lambda: (object(), object())
        desktop._find_state = lambda _window, _state: node
        with self.assertRaisesRegex(GnomeAdapterError, "nicht bestätigt"):
            desktop.move_focused_text_caret("end")
        self.assertEqual(node.caretOffset, 4)

    def test_real_single_step_caret_move_restores_previous_offset_on_mismatch(self):
        node = FakeReadableText("abcdefgh", caret_offset=4, caret_mismatch_once=True)
        desktop = PyAtSpiDesktop.__new__(PyAtSpiDesktop)
        desktop._atspi = type("AtSpi", (), {"STATE_FOCUSED": object()})
        desktop._active_window = lambda: (object(), object())
        desktop._find_state = lambda _window, _state: node
        with self.assertRaisesRegex(GnomeAdapterError, "nicht bestätigt"):
            desktop.move_focused_text_caret("next")
        self.assertEqual(node.caretOffset, 4)

    def test_real_word_caret_moves_to_exact_unicode_word_starts(self):
        desktop = PyAtSpiDesktop.__new__(PyAtSpiDesktop)
        desktop._atspi = type("AtSpi", (), {"STATE_FOCUSED": object()})
        desktop._active_window = lambda: (object(), object())
        previous = FakeReadableText("alpha  βeta gamma", caret_offset=12)
        desktop._find_state = lambda _window, _state: previous
        self.assertEqual(desktop.move_focused_text_caret_word("previous"), "Notes")
        self.assertEqual(previous.caretOffset, 7)
        self.assertEqual(
            previous.read_ranges,
            [(11, 12), (10, 11), (9, 10), (8, 9), (7, 8), (6, 7)],
        )
        following = FakeReadableText("alpha  βeta gamma", caret_offset=7)
        desktop._find_state = lambda _window, _state: following
        self.assertEqual(desktop.move_focused_text_caret_word("next"), "Notes")
        self.assertEqual(following.caretOffset, 12)
        self.assertEqual(
            following.read_ranges,
            [(7, 8), (8, 9), (9, 10), (10, 11), (11, 12), (12, 13)],
        )
        self.assertTrue(all(end == start + 1 for start, end in following.read_ranges))

    def test_real_word_caret_boundaries_are_content_free_and_idempotent(self):
        desktop = PyAtSpiDesktop.__new__(PyAtSpiDesktop)
        desktop._atspi = type("AtSpi", (), {"STATE_FOCUSED": object()})
        desktop._active_window = lambda: (object(), object())
        for node, direction in (
            (FakeReadableText("word", caret_offset=0), "previous"),
            (FakeReadableText("word", caret_offset=4), "next"),
            (FakeReadableText("", caret_offset=0), "previous"),
            (FakeReadableText("", caret_offset=0), "next"),
        ):
            desktop._find_state = lambda _window, _state, node=node: node
            original = node.caretOffset
            self.assertEqual(desktop.move_focused_text_caret_word(direction), "Notes")
            self.assertEqual(node.caretOffset, original)
            self.assertEqual(node.read_ranges, [])

    def test_real_word_caret_move_restores_previous_offset_on_mismatch(self):
        node = FakeReadableText("alpha beta", caret_offset=0, caret_mismatch_once=True)
        desktop = PyAtSpiDesktop.__new__(PyAtSpiDesktop)
        desktop._atspi = type("AtSpi", (), {"STATE_FOCUSED": object()})
        desktop._active_window = lambda: (object(), object())
        desktop._find_state = lambda _window, _state: node
        with self.assertRaisesRegex(GnomeAdapterError, "nicht bestätigt"):
            desktop.move_focused_text_caret_word("next")
        self.assertEqual(node.caretOffset, 0)

    def test_real_word_caret_move_rejects_unsafe_state_before_mutation(self):
        desktop = PyAtSpiDesktop.__new__(PyAtSpiDesktop)
        desktop._atspi = type("AtSpi", (), {"STATE_FOCUSED": object()})
        desktop._active_window = lambda: (object(), object())
        cases = (
            FakeReadableText("private", attributes=("protected:true",), caret_offset=2),
            FakeReadableText("plain", role="push button", caret_offset=2),
            FakeReadableText("plain", selections=((0, 1),), caret_offset=2),
            FakeReadableText("x" * 100_001, caret_offset=2),
            FakeReadableText("plain", caret_offset=6),
        )
        for node in cases:
            original = node.caretOffset
            desktop._find_state = lambda _window, _state, node=node: node
            with self.assertRaises(GnomeAdapterError):
                desktop.move_focused_text_caret_word("next")
            self.assertEqual(node.caretOffset, original)
            self.assertEqual(node.read_ranges, [])
        with self.assertRaises(GnomeAdapterError):
            desktop.move_focused_text_caret_word("sideways")

    def test_real_word_caret_move_enforces_search_limit_without_mutation(self):
        node = FakeReadableText("." * 257 + "word", caret_offset=0)
        desktop = PyAtSpiDesktop.__new__(PyAtSpiDesktop)
        desktop._atspi = type("AtSpi", (), {"STATE_FOCUSED": object()})
        desktop._active_window = lambda: (object(), object())
        desktop._find_state = lambda _window, _state: node
        with self.assertRaises(GnomeAdapterError):
            desktop.move_focused_text_caret_word("next")
        self.assertEqual(node.caretOffset, 0)
        self.assertEqual(len(node.read_ranges), 256)
        self.assertTrue(all(end == start + 1 for start, end in node.read_ranges))

    def test_real_caret_move_rejects_invalid_protected_and_oversized_objects(self):
        desktop = PyAtSpiDesktop.__new__(PyAtSpiDesktop)
        desktop._atspi = type("AtSpi", (), {"STATE_FOCUSED": object()})
        desktop._active_window = lambda: (object(), object())
        for node in (
            FakeReadableText("private", attributes=("protected:true",), caret_offset=2),
            FakeReadableText("abc", caret_offset=4),
            FakeReadableText("x" * 100_001),
        ):
            desktop._find_state = lambda _window, _state, node=node: node
            with self.assertRaises(GnomeAdapterError):
                desktop.move_focused_text_caret("end")
        with self.assertRaises(GnomeAdapterError):
            desktop.move_focused_text_caret("middle")

    def test_real_caret_position_returns_only_valid_bounded_metadata(self):
        node = FakeReadableText("abcdefgh", caret_offset=4)
        desktop = PyAtSpiDesktop.__new__(PyAtSpiDesktop)
        desktop._atspi = type("AtSpi", (), {"STATE_FOCUSED": object()})
        desktop._active_window = lambda: (object(), object())
        desktop._find_state = lambda _window, _state: node
        self.assertEqual(desktop.focused_text_caret_position(), ("Notes", 4, 8))
        self.assertEqual(node.read_ranges, [])

    def test_real_caret_position_rejects_protected_invalid_and_oversized_objects(self):
        desktop = PyAtSpiDesktop.__new__(PyAtSpiDesktop)
        desktop._atspi = type("AtSpi", (), {"STATE_FOCUSED": object()})
        desktop._active_window = lambda: (object(), object())
        for node in (
            FakeReadableText("private", attributes=("protected:true",), caret_offset=2),
            FakeReadableText("abc", caret_offset=4),
            FakeReadableText("x" * 100_001),
            FakeReadableText("label", role="label"),
        ):
            desktop._find_state = lambda _window, _state, node=node: node
            with self.assertRaises(GnomeAdapterError):
                desktop.focused_text_caret_position()
            self.assertEqual(node.read_ranges, [])

    def test_real_insert_at_caret_verifies_full_content_and_moves_caret(self):
        node = FakeReadableText("first end", caret_offset=6)
        desktop = PyAtSpiDesktop.__new__(PyAtSpiDesktop)
        desktop._atspi = type("AtSpi", (), {"STATE_FOCUSED": object()})
        desktop._active_window = lambda: (object(), object())
        desktop._find_state = lambda _window, _state: node
        self.assertEqual(desktop.insert_focused_text_at_caret("middle "), "Notes")
        self.assertEqual(node.value, "first middle end")
        self.assertEqual(node.caretOffset, 13)
        self.assertEqual(node.selections, ())

    def test_real_insert_at_caret_restores_content_and_caret_on_mismatch(self):
        node = FakeReadableText("first end", caret_offset=6, insert_mismatch=True)
        desktop = PyAtSpiDesktop.__new__(PyAtSpiDesktop)
        desktop._atspi = type("AtSpi", (), {"STATE_FOCUSED": object()})
        desktop._active_window = lambda: (object(), object())
        desktop._find_state = lambda _window, _state: node
        with self.assertRaisesRegex(GnomeAdapterError, "nicht bestätigt"):
            desktop.insert_focused_text_at_caret("middle ")
        self.assertEqual(node.value, "first end")
        self.assertEqual(node.caretOffset, 6)
        self.assertEqual(node.selections, ())

    def test_real_insert_at_caret_rejects_unsafe_state_before_mutation(self):
        desktop = PyAtSpiDesktop.__new__(PyAtSpiDesktop)
        desktop._atspi = type("AtSpi", (), {"STATE_FOCUSED": object()})
        desktop._active_window = lambda: (object(), object())
        cases = (
            (FakeReadableText("plain", attributes=("protected:true",), caret_offset=2), "text"),
            (FakeReadableText("plain", selections=((0, 1),), caret_offset=2), "text"),
            (FakeReadableText("x" * 100_000, caret_offset=2), "more"),
            (FakeReadableText("plain", caret_offset=6), "line\nbreak"),
        )
        for node, value in cases:
            original = node.value
            desktop._find_state = lambda _window, _state, node=node: node
            with self.assertRaises(GnomeAdapterError):
                desktop.insert_focused_text_at_caret(value)
            self.assertEqual(node.value, original)

    def test_real_character_read_fetches_exactly_one_unicode_character(self):
        desktop = PyAtSpiDesktop.__new__(PyAtSpiDesktop)
        desktop._atspi = type("AtSpi", (), {"STATE_FOCUSED": object()})
        desktop._active_window = lambda: (object(), object())
        previous = FakeReadableText("aö🙂z", caret_offset=3)
        desktop._find_state = lambda _window, _state: previous
        self.assertEqual(desktop.focused_text_character_at_caret("previous"), ("Notes", "🙂"))
        self.assertEqual(previous.read_ranges, [(2, 3)])
        following = FakeReadableText("aö🙂z", caret_offset=2)
        desktop._find_state = lambda _window, _state: following
        self.assertEqual(desktop.focused_text_character_at_caret("next"), ("Notes", "🙂"))
        self.assertEqual(following.read_ranges, [(2, 3)])

    def test_real_character_read_boundaries_do_not_read_content(self):
        desktop = PyAtSpiDesktop.__new__(PyAtSpiDesktop)
        desktop._atspi = type("AtSpi", (), {"STATE_FOCUSED": object()})
        desktop._active_window = lambda: (object(), object())
        for node, direction in (
            (FakeReadableText("abc", caret_offset=0), "previous"),
            (FakeReadableText("abc", caret_offset=3), "next"),
            (FakeReadableText("", caret_offset=0), "previous"),
        ):
            desktop._find_state = lambda _window, _state, node=node: node
            self.assertEqual(desktop.focused_text_character_at_caret(direction), ("Notes", ""))
            self.assertEqual(node.read_ranges, [])

    def test_real_character_read_rejects_unsafe_state_before_content_access(self):
        desktop = PyAtSpiDesktop.__new__(PyAtSpiDesktop)
        desktop._atspi = type("AtSpi", (), {"STATE_FOCUSED": object()})
        desktop._active_window = lambda: (object(), object())
        cases = (
            FakeReadableText("private", attributes=("protected:true",), caret_offset=2),
            FakeReadableText("plain", role="push button", caret_offset=2),
            FakeReadableText("x" * 100_001, caret_offset=2),
            FakeReadableText("plain", caret_offset=6),
        )
        for node in cases:
            desktop._find_state = lambda _window, _state, node=node: node
            with self.assertRaises(GnomeAdapterError):
                desktop.focused_text_character_at_caret("next")
            self.assertEqual(node.read_ranges, [])
        with self.assertRaises(GnomeAdapterError):
            desktop.focused_text_character_at_caret("sideways")

    def test_real_word_read_uses_only_bounded_single_character_ranges(self):
        desktop = PyAtSpiDesktop.__new__(PyAtSpiDesktop)
        desktop._atspi = type("AtSpi", (), {"STATE_FOCUSED": object()})
        desktop._active_window = lambda: (object(), object())
        previous = FakeReadableText("alpha  βeta gamma", caret_offset=12)
        desktop._find_state = lambda _window, _state: previous
        self.assertEqual(desktop.focused_text_word_at_caret("previous"), ("Notes", "βeta"))
        self.assertEqual(
            previous.read_ranges,
            [(11, 12), (10, 11), (9, 10), (8, 9), (7, 8), (6, 7)],
        )
        following = FakeReadableText("alpha  βeta gamma", caret_offset=11)
        desktop._find_state = lambda _window, _state: following
        self.assertEqual(desktop.focused_text_word_at_caret("next"), ("Notes", "gamma"))
        self.assertEqual(
            following.read_ranges,
            [(11, 12), (12, 13), (13, 14), (14, 15), (15, 16), (16, 17)],
        )
        self.assertTrue(all(end == start + 1 for start, end in following.read_ranges))

    def test_real_word_read_boundaries_are_content_free(self):
        desktop = PyAtSpiDesktop.__new__(PyAtSpiDesktop)
        desktop._atspi = type("AtSpi", (), {"STATE_FOCUSED": object()})
        desktop._active_window = lambda: (object(), object())
        for node, direction in (
            (FakeReadableText("", caret_offset=0), "previous"),
            (FakeReadableText("word", caret_offset=4), "next"),
            (FakeReadableText("word", caret_offset=0), "previous"),
        ):
            desktop._find_state = lambda _window, _state, node=node: node
            self.assertEqual(desktop.focused_text_word_at_caret(direction), ("Notes", ""))
            self.assertEqual(node.read_ranges, [])

    def test_real_word_read_rejects_unsafe_state_before_content_access(self):
        desktop = PyAtSpiDesktop.__new__(PyAtSpiDesktop)
        desktop._atspi = type("AtSpi", (), {"STATE_FOCUSED": object()})
        desktop._active_window = lambda: (object(), object())
        cases = (
            FakeReadableText("private", attributes=("secret:true",), caret_offset=2),
            FakeReadableText("plain", role="push button", caret_offset=2),
            FakeReadableText("x" * 100_001, caret_offset=2),
            FakeReadableText("plain", caret_offset=6),
        )
        for node in cases:
            desktop._find_state = lambda _window, _state, node=node: node
            with self.assertRaises(GnomeAdapterError):
                desktop.focused_text_word_at_caret("next")
            self.assertEqual(node.read_ranges, [])
        with self.assertRaises(GnomeAdapterError):
            desktop.focused_text_word_at_caret("sideways")

    def test_real_word_read_enforces_search_and_word_length_limits(self):
        desktop = PyAtSpiDesktop.__new__(PyAtSpiDesktop)
        desktop._atspi = type("AtSpi", (), {"STATE_FOCUSED": object()})
        desktop._active_window = lambda: (object(), object())
        for node in (
            FakeReadableText("." * 257 + "word", caret_offset=0),
            FakeReadableText("x" * 129, caret_offset=0),
        ):
            desktop._find_state = lambda _window, _state, node=node: node
            with self.assertRaises(GnomeAdapterError):
                desktop.focused_text_word_at_caret("next")
            self.assertLessEqual(len(node.read_ranges), 256)
            self.assertTrue(all(end == start + 1 for start, end in node.read_ranges))

    def test_real_character_deletion_removes_exactly_one_unicode_character(self):
        desktop = PyAtSpiDesktop.__new__(PyAtSpiDesktop)
        desktop._atspi = type("AtSpi", (), {"STATE_FOCUSED": object()})
        desktop._active_window = lambda: (object(), object())
        previous = FakeReadableText("aö🙂z", caret_offset=3)
        desktop._find_state = lambda _window, _state: previous
        self.assertEqual(desktop.delete_focused_text_character("previous"), "Notes")
        self.assertEqual(previous.value, "aöz")
        self.assertEqual(previous.caretOffset, 2)
        following = FakeReadableText("aö🙂z", caret_offset=2)
        desktop._find_state = lambda _window, _state: following
        self.assertEqual(desktop.delete_focused_text_character("next"), "Notes")
        self.assertEqual(following.value, "aöz")
        self.assertEqual(following.caretOffset, 2)

    def test_real_character_deletion_is_idempotent_at_both_boundaries(self):
        desktop = PyAtSpiDesktop.__new__(PyAtSpiDesktop)
        desktop._atspi = type("AtSpi", (), {"STATE_FOCUSED": object()})
        desktop._active_window = lambda: (object(), object())
        for node, direction in (
            (FakeReadableText("abc", caret_offset=0), "previous"),
            (FakeReadableText("abc", caret_offset=3), "next"),
            (FakeReadableText("", caret_offset=0), "previous"),
            (FakeReadableText("", caret_offset=0), "next"),
        ):
            desktop._find_state = lambda _window, _state, node=node: node
            self.assertEqual(desktop.delete_focused_text_character(direction), "Notes")
            self.assertEqual(node.value, "abc" if node.characterCount else "")

    def test_real_character_deletion_restores_content_and_caret_on_mismatch(self):
        node = FakeReadableText("abcdef", caret_offset=3, delete_mismatch=True)
        desktop = PyAtSpiDesktop.__new__(PyAtSpiDesktop)
        desktop._atspi = type("AtSpi", (), {"STATE_FOCUSED": object()})
        desktop._active_window = lambda: (object(), object())
        desktop._find_state = lambda _window, _state: node
        with self.assertRaisesRegex(GnomeAdapterError, "nicht bestätigt"):
            desktop.delete_focused_text_character("previous")
        self.assertEqual(node.value, "abcdef")
        self.assertEqual(node.caretOffset, 3)

    def test_real_character_deletion_rejects_unsafe_state_before_mutation(self):
        desktop = PyAtSpiDesktop.__new__(PyAtSpiDesktop)
        desktop._atspi = type("AtSpi", (), {"STATE_FOCUSED": object()})
        desktop._active_window = lambda: (object(), object())
        for node in (
            FakeReadableText("private", attributes=("protected:true",), caret_offset=2),
            FakeReadableText("plain", selections=((0, 1),), caret_offset=2),
            FakeReadableText("x" * 100_001, caret_offset=2),
        ):
            original = node.value
            desktop._find_state = lambda _window, _state, node=node: node
            with self.assertRaises(GnomeAdapterError):
                desktop.delete_focused_text_character("next")
            self.assertEqual(node.value, original)
        with self.assertRaises(GnomeAdapterError):
            desktop.delete_focused_text_character("sideways")

    def test_real_word_replacement_writes_exact_content_and_places_caret_after_target(self):
        desktop = PyAtSpiDesktop.__new__(PyAtSpiDesktop)
        desktop._atspi = type("AtSpi", (), {"STATE_FOCUSED": object()})
        desktop._active_window = lambda: (object(), object())
        previous = FakeReadableText("alpha  βeta gamma", caret_offset=12)
        desktop._find_state = lambda _window, _state: previous
        self.assertEqual(desktop.replace_focused_text_word("previous", "NEU"), "Notes")
        self.assertEqual(previous.value, "alpha  NEU gamma")
        self.assertEqual(previous.caretOffset, 10)
        self.assertEqual(previous.selections, ())
        following = FakeReadableText("alpha  βeta gamma", caret_offset=11)
        desktop._find_state = lambda _window, _state: following
        self.assertEqual(desktop.replace_focused_text_word("next", "NEU"), "Notes")
        self.assertEqual(following.value, "alpha  βeta NEU")
        self.assertEqual(following.caretOffset, 15)
        self.assertEqual(following.selections, ())

    def test_real_word_replacement_edges_are_content_free_and_idempotent(self):
        desktop = PyAtSpiDesktop.__new__(PyAtSpiDesktop)
        desktop._atspi = type("AtSpi", (), {"STATE_FOCUSED": object()})
        desktop._active_window = lambda: (object(), object())
        for node, direction in (
            (FakeReadableText("word", caret_offset=0), "previous"),
            (FakeReadableText("word", caret_offset=4), "next"),
            (FakeReadableText("", caret_offset=0), "previous"),
            (FakeReadableText("", caret_offset=0), "next"),
        ):
            desktop._find_state = lambda _window, _state, node=node: node
            original = (node.value, node.caretOffset)
            self.assertEqual(desktop.replace_focused_text_word(direction, "new"), "Notes")
            self.assertEqual((node.value, node.caretOffset), original)
            self.assertEqual(node.read_ranges, [])

    def test_real_word_replacement_restores_content_and_caret_on_mismatch(self):
        node = FakeReadableText("alpha beta", caret_offset=0, set_contents_mismatch=True)
        desktop = PyAtSpiDesktop.__new__(PyAtSpiDesktop)
        desktop._atspi = type("AtSpi", (), {"STATE_FOCUSED": object()})
        desktop._active_window = lambda: (object(), object())
        desktop._find_state = lambda _window, _state: node
        with self.assertRaisesRegex(GnomeAdapterError, "nicht bestätigt"):
            desktop.replace_focused_text_word("next", "new")
        self.assertEqual(node.value, "alpha beta")
        self.assertEqual(node.caretOffset, 0)
        self.assertEqual(node.selections, ())

    def test_real_word_replacement_rejects_unsafe_state_before_mutation(self):
        desktop = PyAtSpiDesktop.__new__(PyAtSpiDesktop)
        desktop._atspi = type("AtSpi", (), {"STATE_FOCUSED": object()})
        desktop._active_window = lambda: (object(), object())
        cases = (
            (FakeReadableText("private", attributes=("secret:true",), caret_offset=2), "new"),
            (FakeReadableText("plain", role="push button", caret_offset=2), "new"),
            (FakeReadableText("plain", selections=((0, 1),), caret_offset=2), "new"),
            (FakeReadableText("x" * 100_001, caret_offset=2), "new"),
            (FakeReadableText("plain", caret_offset=6), "new"),
            (FakeReadableText("plain", caret_offset=0), "line\nbreak"),
        )
        for node, value in cases:
            original = (node.value, node.caretOffset, node.selections)
            desktop._find_state = lambda _window, _state, node=node: node
            with self.assertRaises(GnomeAdapterError):
                desktop.replace_focused_text_word("next", value)
            self.assertEqual((node.value, node.caretOffset, node.selections), original)
        with self.assertRaises(GnomeAdapterError):
            desktop.replace_focused_text_word("sideways", "new")

    def test_real_word_replacement_enforces_search_and_result_limits(self):
        desktop = PyAtSpiDesktop.__new__(PyAtSpiDesktop)
        desktop._atspi = type("AtSpi", (), {"STATE_FOCUSED": object()})
        desktop._active_window = lambda: (object(), object())
        cases = (
            FakeReadableText("." * 257 + "word", caret_offset=0),
            FakeReadableText("x " + "." * 99_998, caret_offset=0),
        )
        for node in cases:
            original = node.value
            desktop._find_state = lambda _window, _state, node=node: node
            with self.assertRaises(GnomeAdapterError):
                desktop.replace_focused_text_word("next", "y" * 500)
            self.assertEqual(node.value, original)
            self.assertEqual(node.caretOffset, 0)

    def test_real_word_deletion_removes_exact_unicode_word_and_verifies_state(self):
        desktop = PyAtSpiDesktop.__new__(PyAtSpiDesktop)
        desktop._atspi = type("AtSpi", (), {"STATE_FOCUSED": object()})
        desktop._active_window = lambda: (object(), object())
        previous = FakeReadableText("alpha  βeta gamma", caret_offset=12)
        desktop._find_state = lambda _window, _state: previous
        self.assertEqual(desktop.delete_focused_text_word("previous"), "Notes")
        self.assertEqual(previous.value, "alpha   gamma")
        self.assertEqual(previous.caretOffset, 8)
        self.assertEqual(previous.selections, ())
        following = FakeReadableText("alpha  βeta gamma", caret_offset=11)
        desktop._find_state = lambda _window, _state: following
        self.assertEqual(desktop.delete_focused_text_word("next"), "Notes")
        self.assertEqual(following.value, "alpha  βeta ")
        self.assertEqual(following.caretOffset, 11)
        self.assertEqual(following.selections, ())

    def test_real_word_deletion_edges_are_content_free_and_idempotent(self):
        desktop = PyAtSpiDesktop.__new__(PyAtSpiDesktop)
        desktop._atspi = type("AtSpi", (), {"STATE_FOCUSED": object()})
        desktop._active_window = lambda: (object(), object())
        for node, direction in (
            (FakeReadableText("word", caret_offset=0), "previous"),
            (FakeReadableText("word", caret_offset=4), "next"),
            (FakeReadableText("", caret_offset=0), "previous"),
            (FakeReadableText("", caret_offset=0), "next"),
        ):
            desktop._find_state = lambda _window, _state, node=node: node
            original = (node.value, node.caretOffset)
            self.assertEqual(desktop.delete_focused_text_word(direction), "Notes")
            self.assertEqual((node.value, node.caretOffset), original)
            self.assertEqual(node.read_ranges, [])

    def test_real_word_deletion_restores_content_and_caret_on_mismatch(self):
        node = FakeReadableText("alpha beta", caret_offset=0, delete_mismatch=True)
        desktop = PyAtSpiDesktop.__new__(PyAtSpiDesktop)
        desktop._atspi = type("AtSpi", (), {"STATE_FOCUSED": object()})
        desktop._active_window = lambda: (object(), object())
        desktop._find_state = lambda _window, _state: node
        with self.assertRaisesRegex(GnomeAdapterError, "nicht bestätigt"):
            desktop.delete_focused_text_word("next")
        self.assertEqual(node.value, "alpha beta")
        self.assertEqual(node.caretOffset, 0)
        self.assertEqual(node.selections, ())

    def test_real_word_deletion_rejects_unsafe_state_before_mutation(self):
        desktop = PyAtSpiDesktop.__new__(PyAtSpiDesktop)
        desktop._atspi = type("AtSpi", (), {"STATE_FOCUSED": object()})
        desktop._active_window = lambda: (object(), object())
        cases = (
            FakeReadableText("private", attributes=("protected:true",), caret_offset=2),
            FakeReadableText("plain", role="push button", caret_offset=2),
            FakeReadableText("plain", selections=((0, 1),), caret_offset=2),
            FakeReadableText("x" * 100_001, caret_offset=2),
            FakeReadableText("plain", caret_offset=6),
        )
        for node in cases:
            original = (node.value, node.caretOffset, node.selections)
            desktop._find_state = lambda _window, _state, node=node: node
            with self.assertRaises(GnomeAdapterError):
                desktop.delete_focused_text_word("next")
            self.assertEqual((node.value, node.caretOffset, node.selections), original)
            self.assertEqual(node.read_ranges, [])
        with self.assertRaises(GnomeAdapterError):
            desktop.delete_focused_text_word("sideways")

    def test_real_word_deletion_enforces_search_limit_without_mutation(self):
        node = FakeReadableText("." * 257 + "word", caret_offset=0)
        desktop = PyAtSpiDesktop.__new__(PyAtSpiDesktop)
        desktop._atspi = type("AtSpi", (), {"STATE_FOCUSED": object()})
        desktop._active_window = lambda: (object(), object())
        desktop._find_state = lambda _window, _state: node
        with self.assertRaises(GnomeAdapterError):
            desktop.delete_focused_text_word("next")
        self.assertEqual(node.value, "." * 257 + "word")
        self.assertEqual(node.caretOffset, 0)
        self.assertEqual(len(node.read_ranges), 256)
        self.assertTrue(all(end == start + 1 for start, end in node.read_ranges))

    def test_real_word_selection_marks_exact_unicode_word_span(self):
        desktop = PyAtSpiDesktop.__new__(PyAtSpiDesktop)
        desktop._atspi = type("AtSpi", (), {"STATE_FOCUSED": object()})
        desktop._active_window = lambda: (object(), object())
        previous = FakeReadableText("alpha  βeta gamma", caret_offset=12)
        desktop._find_state = lambda _window, _state: previous
        self.assertEqual(desktop.select_focused_text_word("previous"), "Notes")
        self.assertEqual(previous.selections, ((7, 11),))
        self.assertEqual(previous.caretOffset, 7)
        self.assertEqual(
            previous.read_ranges,
            [(11, 12), (10, 11), (9, 10), (8, 9), (7, 8), (6, 7)],
        )
        following = FakeReadableText("alpha  βeta gamma", caret_offset=11)
        desktop._find_state = lambda _window, _state: following
        self.assertEqual(desktop.select_focused_text_word("next"), "Notes")
        self.assertEqual(following.selections, ((12, 17),))
        self.assertEqual(following.caretOffset, 17)
        self.assertEqual(
            following.read_ranges,
            [(11, 12), (12, 13), (13, 14), (14, 15), (15, 16), (16, 17)],
        )
        self.assertTrue(all(end == start + 1 for start, end in following.read_ranges))

    def test_real_word_selection_edges_are_content_free_and_idempotent(self):
        desktop = PyAtSpiDesktop.__new__(PyAtSpiDesktop)
        desktop._atspi = type("AtSpi", (), {"STATE_FOCUSED": object()})
        desktop._active_window = lambda: (object(), object())
        for node, direction in (
            (FakeReadableText("word", caret_offset=0), "previous"),
            (FakeReadableText("word", caret_offset=4), "next"),
            (FakeReadableText("", caret_offset=0), "previous"),
            (FakeReadableText("", caret_offset=0), "next"),
        ):
            desktop._find_state = lambda _window, _state, node=node: node
            original = node.caretOffset
            self.assertEqual(desktop.select_focused_text_word(direction), "Notes")
            self.assertEqual(node.selections, ())
            self.assertEqual(node.caretOffset, original)
            self.assertEqual(node.read_ranges, [])

    def test_real_word_selection_restores_empty_state_and_caret_on_mismatch(self):
        node = FakeReadableText(
            "alpha beta", caret_offset=0, selection_mismatch=True
        )
        desktop = PyAtSpiDesktop.__new__(PyAtSpiDesktop)
        desktop._atspi = type("AtSpi", (), {"STATE_FOCUSED": object()})
        desktop._active_window = lambda: (object(), object())
        desktop._find_state = lambda _window, _state: node
        with self.assertRaisesRegex(GnomeAdapterError, "nicht bestätigt"):
            desktop.select_focused_text_word("next")
        self.assertEqual(node.selections, ())
        self.assertEqual(node.caretOffset, 0)

    def test_real_word_selection_rejects_unsafe_state_before_mutation(self):
        desktop = PyAtSpiDesktop.__new__(PyAtSpiDesktop)
        desktop._atspi = type("AtSpi", (), {"STATE_FOCUSED": object()})
        desktop._active_window = lambda: (object(), object())
        cases = (
            FakeReadableText("private", attributes=("secret:true",), caret_offset=2),
            FakeReadableText("plain", role="push button", caret_offset=2),
            FakeReadableText("plain", selections=((0, 1),), caret_offset=2),
            FakeReadableText("x" * 100_001, caret_offset=2),
            FakeReadableText("plain", caret_offset=6),
        )
        for node in cases:
            original = node.caretOffset
            original_selections = node.selections
            desktop._find_state = lambda _window, _state, node=node: node
            with self.assertRaises(GnomeAdapterError):
                desktop.select_focused_text_word("next")
            self.assertEqual(node.selections, original_selections)
            self.assertEqual(node.caretOffset, original)
            self.assertEqual(node.read_ranges, [])
        with self.assertRaises(GnomeAdapterError):
            desktop.select_focused_text_word("sideways")

    def test_real_word_selection_enforces_search_limit_without_mutation(self):
        node = FakeReadableText("." * 257 + "word", caret_offset=0)
        desktop = PyAtSpiDesktop.__new__(PyAtSpiDesktop)
        desktop._atspi = type("AtSpi", (), {"STATE_FOCUSED": object()})
        desktop._active_window = lambda: (object(), object())
        desktop._find_state = lambda _window, _state: node
        with self.assertRaises(GnomeAdapterError):
            desktop.select_focused_text_word("next")
        self.assertEqual(node.selections, ())
        self.assertEqual(node.caretOffset, 0)
        self.assertEqual(len(node.read_ranges), 256)
        self.assertTrue(all(end == start + 1 for start, end in node.read_ranges))

    def test_real_character_selection_marks_exactly_one_unicode_character(self):
        desktop = PyAtSpiDesktop.__new__(PyAtSpiDesktop)
        desktop._atspi = type("AtSpi", (), {"STATE_FOCUSED": object()})
        desktop._active_window = lambda: (object(), object())
        previous = FakeReadableText("aö🙂z", caret_offset=3)
        desktop._find_state = lambda _window, _state: previous
        self.assertEqual(desktop.select_focused_text_character("previous"), "Notes")
        self.assertEqual(previous.selections, ((2, 3),))
        self.assertEqual(previous.caretOffset, 2)
        following = FakeReadableText("aö🙂z", caret_offset=2)
        desktop._find_state = lambda _window, _state: following
        self.assertEqual(desktop.select_focused_text_character("next"), "Notes")
        self.assertEqual(following.selections, ((2, 3),))
        self.assertEqual(following.caretOffset, 3)

    def test_real_character_selection_is_idempotent_at_text_boundaries(self):
        desktop = PyAtSpiDesktop.__new__(PyAtSpiDesktop)
        desktop._atspi = type("AtSpi", (), {"STATE_FOCUSED": object()})
        desktop._active_window = lambda: (object(), object())
        for node, direction in (
            (FakeReadableText("abc", caret_offset=0), "previous"),
            (FakeReadableText("abc", caret_offset=3), "next"),
            (FakeReadableText("", caret_offset=0), "previous"),
            (FakeReadableText("", caret_offset=0), "next"),
        ):
            desktop._find_state = lambda _window, _state, node=node: node
            self.assertEqual(desktop.select_focused_text_character(direction), "Notes")
            self.assertEqual(node.selections, ())

    def test_real_character_selection_restores_empty_state_and_caret_on_mismatch(self):
        node = FakeReadableText("abcdef", caret_offset=3, selection_mismatch=True)
        desktop = PyAtSpiDesktop.__new__(PyAtSpiDesktop)
        desktop._atspi = type("AtSpi", (), {"STATE_FOCUSED": object()})
        desktop._active_window = lambda: (object(), object())
        desktop._find_state = lambda _window, _state: node
        with self.assertRaisesRegex(GnomeAdapterError, "nicht bestätigt"):
            desktop.select_focused_text_character("next")
        self.assertEqual(node.selections, ())
        self.assertEqual(node.caretOffset, 3)

    def test_real_character_selection_rejects_unsafe_state_before_mutation(self):
        desktop = PyAtSpiDesktop.__new__(PyAtSpiDesktop)
        desktop._atspi = type("AtSpi", (), {"STATE_FOCUSED": object()})
        desktop._active_window = lambda: (object(), object())
        for node in (
            FakeReadableText("private", attributes=("protected:true",), caret_offset=2),
            FakeReadableText("plain", selections=((0, 1),), caret_offset=2),
            FakeReadableText("x" * 100_001, caret_offset=2),
        ):
            desktop._find_state = lambda _window, _state, node=node: node
            with self.assertRaises(GnomeAdapterError):
                desktop.select_focused_text_character("next")
        with self.assertRaises(GnomeAdapterError):
            desktop.select_focused_text_character("sideways")

    def test_real_selection_replacement_verifies_content_caret_and_empty_selection(self):
        node = FakeReadableText("first old end", selections=((6, 9),), caret_offset=9)
        desktop = PyAtSpiDesktop.__new__(PyAtSpiDesktop)
        desktop._atspi = type("AtSpi", (), {"STATE_FOCUSED": object()})
        desktop._active_window = lambda: (object(), object())
        desktop._find_state = lambda _window, _state: node
        self.assertEqual(desktop.replace_focused_text_selection("new"), "Notes")
        self.assertEqual(node.value, "first new end")
        self.assertEqual(node.caretOffset, 9)
        self.assertEqual(node.selections, ())

    def test_real_selection_replacement_restores_all_state_on_mismatch(self):
        node = FakeReadableText(
            "first old end",
            selections=((6, 9),),
            caret_offset=9,
            set_contents_mismatch=True,
        )
        desktop = PyAtSpiDesktop.__new__(PyAtSpiDesktop)
        desktop._atspi = type("AtSpi", (), {"STATE_FOCUSED": object()})
        desktop._active_window = lambda: (object(), object())
        desktop._find_state = lambda _window, _state: node
        with self.assertRaisesRegex(GnomeAdapterError, "nicht bestätigt"):
            desktop.replace_focused_text_selection("new")
        self.assertEqual(node.value, "first old end")
        self.assertEqual(node.caretOffset, 9)
        self.assertEqual(node.selections, ((6, 9),))

    def test_real_selection_replacement_rejects_unsafe_state_before_mutation(self):
        desktop = PyAtSpiDesktop.__new__(PyAtSpiDesktop)
        desktop._atspi = type("AtSpi", (), {"STATE_FOCUSED": object()})
        desktop._active_window = lambda: (object(), object())
        cases = (
            (FakeReadableText("plain", selections=(), caret_offset=2), "new"),
            (FakeReadableText("plain", selections=((0, 1), (2, 3)), caret_offset=2), "new"),
            (FakeReadableText("private", attributes=("protected:true",), selections=((0, 1),)), "new"),
            (FakeReadableText("x" * 100_000, selections=((0, 1),), caret_offset=1), "yy"),
            (FakeReadableText("plain", selections=((0, 1),), caret_offset=1), "line\nbreak"),
        )
        for node, value in cases:
            original = node.value
            desktop._find_state = lambda _window, _state, node=node: node
            with self.assertRaises(GnomeAdapterError):
                desktop.replace_focused_text_selection(value)
            self.assertEqual(node.value, original)

    def test_real_clipboard_paste_preserves_multiline_and_verifies_readback(self):
        node = FakeEditableNode()
        node.value = "previous"
        desktop = PyAtSpiDesktop.__new__(PyAtSpiDesktop)
        desktop._atspi = type("AtSpi", (), {"STATE_FOCUSED": object()})
        desktop._active_window = lambda: (object(), object())
        desktop._find_state = lambda _window, _state: node
        self.assertEqual(
            desktop.set_focused_clipboard_text("first\n  second\tvalue"), "Search"
        )
        self.assertEqual(node.value, "first\n  second\tvalue")

    def test_real_clipboard_paste_rejects_unsafe_text_before_mutation(self):
        node = FakeEditableNode()
        desktop = PyAtSpiDesktop.__new__(PyAtSpiDesktop)
        desktop._atspi = type("AtSpi", (), {"STATE_FOCUSED": object()})
        desktop._active_window = lambda: (object(), object())
        desktop._find_state = lambda _window, _state: node
        for value in ("", "a\rb", "a\x00b", "a\x7fb", "x" * 100_001):
            with self.subTest(length=len(value)), self.assertRaises(GnomeAdapterError):
                desktop.set_focused_clipboard_text(value)
            self.assertEqual(node.value, "")

    def test_real_text_entry_rejects_sensitive_field(self):
        node = FakeEditableNode(attributes=("text-input-type:password",))
        desktop = PyAtSpiDesktop.__new__(PyAtSpiDesktop)
        desktop._atspi = type("AtSpi", (), {"STATE_FOCUSED": object()})
        desktop._active_window = lambda: (object(), object())
        desktop._find_state = lambda _window, _state: node
        with self.assertRaises(GnomeAdapterError):
            desktop.set_focused_text("must-not-be-set")
        self.assertEqual(node.value, "")

    def test_real_text_entry_rejects_uninspectable_attributes(self):
        node = FakeEditableNode()
        node.getAttributes = lambda: (_ for _ in ()).throw(RuntimeError("hidden"))
        desktop = PyAtSpiDesktop.__new__(PyAtSpiDesktop)
        desktop._atspi = type("AtSpi", (), {"STATE_FOCUSED": object()})
        desktop._active_window = lambda: (object(), object())
        desktop._find_state = lambda _window, _state: node
        with self.assertRaises(GnomeAdapterError):
            desktop.set_focused_text("must-not-be-set")
        self.assertEqual(node.value, "")

    def test_real_text_entry_fails_on_readback_mismatch(self):
        node = FakeEditableNode(mismatch=True)
        desktop = PyAtSpiDesktop.__new__(PyAtSpiDesktop)
        desktop._atspi = type("AtSpi", (), {"STATE_FOCUSED": object()})
        desktop._active_window = lambda: (object(), object())
        desktop._find_state = lambda _window, _state: node
        with self.assertRaises(GnomeAdapterError):
            desktop.set_focused_text("hello")
        self.assertEqual(node.value, "")

    def test_real_list_selection_replaces_and_verifies_selection(self):
        first = FakeNode("First")
        second = FakeNode("Second")
        selection = FakeSelection((0,))
        container = FakeSelectionContainer((first, second), selection)
        desktop = PyAtSpiDesktop.__new__(PyAtSpiDesktop)
        desktop._atspi = type("AtSpi", (), {"STATE_FOCUSED": object()})
        desktop._active_window = lambda: (object(), object())
        desktop._find_state = lambda _window, _state: second
        self.assertEqual(desktop.select_named_item("Second"), "Second")
        self.assertEqual(selection.selected, {1})

    def test_real_list_selection_rejects_duplicate_name(self):
        first = FakeNode("Same")
        second = FakeNode("Same")
        selection = FakeSelection((0,))
        container = FakeSelectionContainer((first, second), selection)
        desktop = PyAtSpiDesktop.__new__(PyAtSpiDesktop)
        desktop._atspi = type("AtSpi", (), {"STATE_FOCUSED": object()})
        desktop._active_window = lambda: (object(), object())
        desktop._find_state = lambda _window, _state: first
        with self.assertRaises(GnomeAdapterError):
            desktop.select_named_item("Same")
        self.assertEqual(selection.selected, {0})

    def test_real_list_selection_rolls_back_mismatch(self):
        first = FakeNode("First")
        second = FakeNode("Second")
        selection = FakeSelection((0,), ignored_index=1)
        container = FakeSelectionContainer((first, second), selection)
        desktop = PyAtSpiDesktop.__new__(PyAtSpiDesktop)
        desktop._atspi = type("AtSpi", (), {"STATE_FOCUSED": object()})
        desktop._active_window = lambda: (object(), object())
        desktop._find_state = lambda _window, _state: second
        with self.assertRaises(GnomeAdapterError):
            desktop.select_named_item("Second")
        self.assertEqual(selection.selected, {0})

    def test_real_file_dialog_selects_visible_item_without_accepting_dialog(self):
        item = FakeNode("report.pdf")
        selection = FakeSelection()
        choices = FakeSelectionContainer((item,), selection)
        open_action = FakeWindowAction(("click",))
        open_button = FakeNode("Open", action=open_action)
        cancel_button = FakeNode("Cancel", action=FakeWindowAction(("click",)))
        dialog = FakeDialog("Open File", (choices, open_button, cancel_button))
        desktop = PyAtSpiDesktop.__new__(PyAtSpiDesktop)
        desktop._active_window = lambda: (object(), dialog)
        desktop._controls = lambda _window: [
            (open_button, ("click",)),
            (cancel_button, ("click",)),
        ]
        self.assertEqual(desktop.select_visible_file("report.pdf"), "report.pdf")
        self.assertEqual(selection.selected, {0})
        self.assertEqual(open_action.called, [])

    def test_real_file_dialog_rejects_unrecognized_generic_dialog(self):
        item = FakeNode("report.pdf")
        choices = FakeSelectionContainer((item,), FakeSelection())
        dialog = FakeDialog("Preferences", (choices,))
        desktop = PyAtSpiDesktop.__new__(PyAtSpiDesktop)
        desktop._active_window = lambda: (object(), dialog)
        with self.assertRaises(GnomeAdapterError):
            desktop.select_visible_file("report.pdf")

    def test_real_file_dialog_rejects_same_name_in_multiple_lists(self):
        first = FakeSelectionContainer((FakeNode("report.pdf"),), FakeSelection())
        second = FakeSelectionContainer((FakeNode("report.pdf"),), FakeSelection())
        open_button = FakeNode("Open", action=FakeWindowAction(("click",)))
        cancel_button = FakeNode("Cancel", action=FakeWindowAction(("click",)))
        dialog = FakeDialog("Open File", (first, second, open_button, cancel_button))
        desktop = PyAtSpiDesktop.__new__(PyAtSpiDesktop)
        desktop._active_window = lambda: (object(), dialog)
        desktop._controls = lambda _window: [
            (open_button, ("click",)),
            (cancel_button, ("click",)),
        ]
        with self.assertRaises(GnomeAdapterError):
            desktop.select_visible_file("report.pdf")
        self.assertEqual(first.selection.selected, set())
        self.assertEqual(second.selection.selected, set())

    def test_real_save_dialog_sets_name_without_invoking_save(self):
        field = FakeEditableNode("File Name")
        save_action = FakeWindowAction(("click",))
        save_button = FakeNode("Save", action=save_action)
        cancel_button = FakeNode("Cancel", action=FakeWindowAction(("click",)))
        dialog = FakeDialog("Save File", (field, save_button, cancel_button))
        desktop = PyAtSpiDesktop.__new__(PyAtSpiDesktop)
        calls = []
        desktop._active_window = lambda: calls.append(True) or (object(), dialog)
        desktop._controls = lambda _window: [
            (save_button, ("click",)),
            (cancel_button, ("click",)),
        ]
        desktop._atspi = type("AtSpi", (), {"STATE_FOCUSED": object()})
        desktop._find_state = lambda _window, _state: field
        self.assertEqual(desktop.set_file_name("report.pdf"), "File Name")
        self.assertEqual(field.value, "report.pdf")
        self.assertEqual(save_action.called, [])
        self.assertEqual(len(calls), 1)

    def test_real_save_dialog_rejects_wrong_focused_field(self):
        field = FakeEditableNode("Search")
        save_button = FakeNode("Save", action=FakeWindowAction(("click",)))
        cancel_button = FakeNode("Cancel", action=FakeWindowAction(("click",)))
        dialog = FakeDialog("Save File", (field, save_button, cancel_button))
        desktop = PyAtSpiDesktop.__new__(PyAtSpiDesktop)
        desktop._active_window = lambda: (object(), dialog)
        desktop._controls = lambda _window: [
            (save_button, ("click",)),
            (cancel_button, ("click",)),
        ]
        desktop._atspi = type("AtSpi", (), {"STATE_FOCUSED": object()})
        desktop._find_state = lambda _window, _state: field
        with self.assertRaises(GnomeAdapterError):
            desktop.set_file_name("report.pdf")
        self.assertEqual(field.value, "")

    def test_real_file_dialog_sets_bound_location_without_opening(self):
        field = FakeEditableNode("Location")
        open_action = FakeWindowAction(("click",))
        open_button = FakeNode("Open", action=open_action)
        cancel_button = FakeNode("Cancel", action=FakeWindowAction(("click",)))
        dialog = FakeDialog("Open File", (field, open_button, cancel_button))
        desktop = PyAtSpiDesktop.__new__(PyAtSpiDesktop)
        calls = []
        desktop._active_window = lambda: calls.append(True) or (object(), dialog)
        desktop._controls = lambda _window: [
            (open_button, ("click",)),
            (cancel_button, ("click",)),
        ]
        desktop._atspi = type("AtSpi", (), {"STATE_FOCUSED": object()})
        desktop._find_state = lambda _window, _state: field
        self.assertEqual(
            desktop.set_file_location("/home/clausis/Documents"), "Location"
        )
        self.assertEqual(field.value, "/home/clausis/Documents")
        self.assertEqual(open_action.called, [])
        self.assertEqual(len(calls), 1)

    def test_real_file_dialog_location_rejects_wrong_focused_field(self):
        field = FakeEditableNode("File Name")
        open_button = FakeNode("Open", action=FakeWindowAction(("click",)))
        cancel_button = FakeNode("Cancel", action=FakeWindowAction(("click",)))
        dialog = FakeDialog("Open File", (field, open_button, cancel_button))
        desktop = PyAtSpiDesktop.__new__(PyAtSpiDesktop)
        desktop._active_window = lambda: (object(), dialog)
        desktop._controls = lambda _window: [
            (open_button, ("click",)),
            (cancel_button, ("click",)),
        ]
        desktop._atspi = type("AtSpi", (), {"STATE_FOCUSED": object()})
        desktop._find_state = lambda _window, _state: field
        with self.assertRaises(GnomeAdapterError):
            desktop.set_file_location("/home/clausis/Documents")
        self.assertEqual(field.value, "")

    def test_real_file_dialog_location_rejects_noncanonical_path_before_window_lookup(self):
        desktop = PyAtSpiDesktop.__new__(PyAtSpiDesktop)
        calls = []
        desktop._active_window = lambda: calls.append(True) or (object(), object())
        for path in ("relative/path", "/home//clausis", "/home/../root"):
            with self.subTest(path=path), self.assertRaises(GnomeAdapterError):
                desktop.set_file_location(path)
        self.assertEqual(calls, [])

    def test_real_file_dialog_opens_semantic_folder_without_accepting_dialog(self):
        folder_action = FakeWindowAction(("click", "activate"))
        folder = FakeNode("Documents", action=folder_action, role="folder")
        choices = FakeSelectionContainer((folder,), FakeSelection())
        accept_action = FakeWindowAction(("click",))
        accept = FakeNode("Open", action=accept_action)
        cancel = FakeNode("Cancel", action=FakeWindowAction(("click",)))
        dialog = FakeDialog("Open File", (choices, accept, cancel))
        desktop = PyAtSpiDesktop.__new__(PyAtSpiDesktop)
        calls = []
        desktop._active_window = lambda: calls.append(True) or (object(), dialog)
        desktop._controls = lambda _window: [(accept, ("click",)), (cancel, ("click",))]
        self.assertEqual(desktop.open_visible_folder("Documents"), "Documents")
        self.assertEqual(folder_action.called, [1])
        self.assertEqual(accept_action.called, [])
        self.assertEqual(len(calls), 1)

    def test_real_file_dialog_rejects_file_without_folder_evidence(self):
        file_action = FakeWindowAction(("activate",))
        file_node = FakeNode("report.pdf", action=file_action, role="list item")
        choices = FakeSelectionContainer((file_node,), FakeSelection())
        accept = FakeNode("Open", action=FakeWindowAction(("click",)))
        cancel = FakeNode("Cancel", action=FakeWindowAction(("click",)))
        dialog = FakeDialog("Open File", (choices, accept, cancel))
        desktop = PyAtSpiDesktop.__new__(PyAtSpiDesktop)
        desktop._active_window = lambda: (object(), dialog)
        desktop._controls = lambda _window: [(accept, ("click",)), (cancel, ("click",))]
        with self.assertRaises(GnomeAdapterError):
            desktop.open_visible_folder("report.pdf")
        self.assertEqual(file_action.called, [])

    def test_real_file_dialog_rejects_duplicate_semantic_folders(self):
        first = FakeNode(
            "Documents", action=FakeWindowAction(("activate",)), attributes=("is-folder:true",)
        )
        second = FakeNode(
            "Documents", action=FakeWindowAction(("activate",)), role="directory"
        )
        first_list = FakeSelectionContainer((first,), FakeSelection())
        second_list = FakeSelectionContainer((second,), FakeSelection())
        accept = FakeNode("Open", action=FakeWindowAction(("click",)))
        cancel = FakeNode("Cancel", action=FakeWindowAction(("click",)))
        dialog = FakeDialog("Open File", (first_list, second_list, accept, cancel))
        desktop = PyAtSpiDesktop.__new__(PyAtSpiDesktop)
        desktop._active_window = lambda: (object(), dialog)
        desktop._controls = lambda _window: [(accept, ("click",)), (cancel, ("click",))]
        with self.assertRaises(GnomeAdapterError):
            desktop.open_visible_folder("Documents")
        self.assertEqual(first.action.called, [])
        self.assertEqual(second.action.called, [])

    def test_real_file_dialog_folder_requires_exact_navigation_action(self):
        folder_action = FakeWindowAction(("click",))
        folder = FakeNode("Documents", action=folder_action, role="folder")
        choices = FakeSelectionContainer((folder,), FakeSelection())
        accept = FakeNode("Open", action=FakeWindowAction(("click",)))
        cancel = FakeNode("Cancel", action=FakeWindowAction(("click",)))
        dialog = FakeDialog("Open File", (choices, accept, cancel))
        desktop = PyAtSpiDesktop.__new__(PyAtSpiDesktop)
        desktop._active_window = lambda: (object(), dialog)
        desktop._controls = lambda _window: [(accept, ("click",)), (cancel, ("click",))]
        with self.assertRaises(GnomeAdapterError):
            desktop.open_visible_folder("Documents")
        self.assertEqual(folder_action.called, [])

    def test_real_file_dialog_rebinds_then_accepts_exact_pair(self):
        accept = FakeNode("Open", action=FakeWindowAction(("click",)))
        cancel = FakeNode("Cancel", action=FakeWindowAction(("click",)))
        dialog = FakeDialog("Open File", (accept, cancel))
        application = FakeNode("Application", children=(dialog,))
        desktop = PyAtSpiDesktop.__new__(PyAtSpiDesktop)
        calls = []
        desktop._active_window = lambda: calls.append(True) or (application, dialog)
        desktop._controls = lambda _window: [(accept, ("click",)), (cancel, ("click",))]
        original_invoke = desktop._invoke_control

        def invoke(*control):
            application.children = ()
            application.childCount = 0
            return original_invoke(*control)

        desktop._invoke_control = invoke

        self.assertEqual(desktop.decide_file_dialog("accept"), "Open")
        self.assertEqual(accept.action.called, [0])
        self.assertEqual(cancel.action.called, [])
        self.assertEqual(len(calls), 2)

    def test_real_file_dialog_cancels_exact_german_pair(self):
        accept = FakeNode("Speichern", action=FakeWindowAction(("press",)))
        cancel = FakeNode("Abbrechen", action=FakeWindowAction(("press",)))
        dialog = FakeDialog("Datei speichern", (accept, cancel))
        application = FakeNode("Application", children=(dialog,))
        desktop = PyAtSpiDesktop.__new__(PyAtSpiDesktop)
        desktop._active_window = lambda: (application, dialog)
        desktop._controls = lambda _window: [(accept, ("press",)), (cancel, ("press",))]
        original_invoke = desktop._invoke_control

        def invoke(*control):
            application.children = ()
            application.childCount = 0
            return original_invoke(*control)

        desktop._invoke_control = invoke

        self.assertEqual(desktop.decide_file_dialog("cancel"), "Abbrechen")
        self.assertEqual(accept.action.called, [])
        self.assertEqual(cancel.action.called, [0])

    def test_real_file_dialog_decision_rejects_generic_dialog_and_duplicate_pair(self):
        accept = FakeNode("Open", action=FakeWindowAction(("click",)))
        duplicate = FakeNode("Open", action=FakeWindowAction(("click",)))
        cancel = FakeNode("Cancel", action=FakeWindowAction(("click",)))
        desktop = PyAtSpiDesktop.__new__(PyAtSpiDesktop)
        generic = FakeDialog("Preferences", (accept, cancel))
        generic_application = FakeNode("Application", children=(generic,))
        desktop._active_window = lambda: (generic_application, generic)
        desktop._controls = lambda _window: [(accept, ("click",)), (cancel, ("click",))]
        with self.assertRaises(GnomeAdapterError):
            desktop.decide_file_dialog("accept")
        duplicate_dialog = FakeDialog("Open File", (accept, duplicate, cancel))
        duplicate_application = FakeNode("Application", children=(duplicate_dialog,))
        desktop._active_window = lambda: (duplicate_application, duplicate_dialog)
        desktop._controls = lambda _window: [
            (accept, ("click",)), (duplicate, ("click",)), (cancel, ("click",))
        ]
        with self.assertRaises(GnomeAdapterError):
            desktop.decide_file_dialog("cancel")
        self.assertEqual(accept.action.called, [])
        self.assertEqual(duplicate.action.called, [])
        self.assertEqual(cancel.action.called, [])

    def test_real_file_dialog_decision_rejects_window_or_pair_replacement(self):
        old_accept = FakeNode("Open", action=FakeWindowAction(("click",)))
        old_cancel = FakeNode("Cancel", action=FakeWindowAction(("click",)))
        new_accept = FakeNode("Open", action=FakeWindowAction(("click",)))
        new_cancel = FakeNode("Cancel", action=FakeWindowAction(("click",)))
        first = FakeDialog("Open File", (old_accept, old_cancel))
        second = FakeDialog("Open File", (old_accept, old_cancel))
        desktop = PyAtSpiDesktop.__new__(PyAtSpiDesktop)
        windows = iter((first, second))
        application = FakeNode("Application", children=(first, second))
        desktop._active_window = lambda: (application, next(windows))
        desktop._controls = lambda _window: [(old_accept, ("click",)), (old_cancel, ("click",))]
        with self.assertRaisesRegex(GnomeAdapterError, "Dateidialog.*gewechselt"):
            desktop.decide_file_dialog("accept")

        snapshots = iter((
            [(old_accept, ("click",)), (old_cancel, ("click",))],
            [(new_accept, ("click",)), (new_cancel, ("click",))],
        ))
        application.children = (first,)
        application.childCount = 1
        desktop._active_window = lambda: (application, first)
        desktop._controls = lambda _window: next(snapshots)
        with self.assertRaisesRegex(GnomeAdapterError, "Paar.*geändert"):
            desktop.decide_file_dialog("cancel")
        for control in (old_accept, old_cancel, new_accept, new_cancel):
            self.assertEqual(control.action.called, [])

    def test_real_file_dialog_rejects_top_level_window_change_before_decision(self):
        accept = FakeNode("Open", action=FakeWindowAction(("click",)))
        cancel = FakeNode("Cancel", action=FakeWindowAction(("click",)))
        dialog = FakeDialog("Open File", (accept, cancel))
        foreign = FakeDialog("Foreign", ())
        application = FakeNode("Application", children=(dialog,))
        desktop = PyAtSpiDesktop.__new__(PyAtSpiDesktop)
        calls = 0

        def active_window():
            nonlocal calls
            calls += 1
            if calls == 2:
                application.children = (dialog, foreign)
                application.childCount = 2
            return application, dialog

        desktop._active_window = active_window
        desktop._controls = lambda _window: [(accept, ("click",)), (cancel, ("click",))]
        with self.assertRaisesRegex(GnomeAdapterError, "Fensterliste.*geändert"):
            desktop.decide_file_dialog("accept")
        self.assertEqual(accept.action.called, [])
        self.assertEqual(cancel.action.called, [])

    def test_real_file_dialog_reports_unconfirmed_exact_poststate(self):
        accept = FakeNode("Open", action=FakeWindowAction(("click",)))
        cancel = FakeNode("Cancel", action=FakeWindowAction(("click",)))
        dialog = FakeDialog("Open File", (accept, cancel))
        foreign = FakeDialog("Foreign", ())
        application = FakeNode("Application", children=(dialog,))
        desktop = PyAtSpiDesktop.__new__(PyAtSpiDesktop)
        desktop._active_window = lambda: (application, dialog)
        desktop._controls = lambda _window: [(accept, ("click",)), (cancel, ("click",))]

        def invoke(*_control):
            application.children = (foreign,)
            application.childCount = 1
            return "Open"

        desktop._invoke_control = invoke
        with patch("clausis.gnome_adapter.time.monotonic", side_effect=(0.0, 2.1)):
            with self.assertRaisesRegex(GnomeAdapterError, "Nachzustand.*nicht bestätigt"):
                desktop.decide_file_dialog("accept")

    def test_real_standard_dialog_rebinds_then_invokes_exact_ok_cancel_pair(self):
        ok = FakeNode("OK", action=FakeWindowAction(("click",)))
        cancel = FakeNode("Cancel", action=FakeWindowAction(("click",)))
        dialog = FakeDialog("Preferences", (ok, cancel))
        application = FakeNode("Application", children=(dialog,))
        desktop = PyAtSpiDesktop.__new__(PyAtSpiDesktop)
        calls = []
        desktop._active_window = lambda: calls.append(True) or (application, dialog)
        desktop._controls = lambda _window: [(ok, ("click",)), (cancel, ("click",))]
        original_invoke = desktop._invoke_control

        def invoke(*control):
            application.children = ()
            application.childCount = 0
            return original_invoke(*control)

        desktop._invoke_control = invoke

        self.assertEqual(desktop.decide_standard_dialog("accept"), "OK")
        self.assertEqual(ok.action.called, [0])
        self.assertEqual(cancel.action.called, [])
        self.assertEqual(len(calls), 2)

    def test_real_standard_dialog_supports_german_yes_no_and_rejects_permission_pair(self):
        yes = FakeNode("Ja", action=FakeWindowAction(("press",)))
        no = FakeNode("Nein", action=FakeWindowAction(("press",)))
        dialog = FakeDialog("Änderungen verwerfen?", (yes, no))
        application = FakeNode("Application", children=(dialog,))
        desktop = PyAtSpiDesktop.__new__(PyAtSpiDesktop)
        desktop._active_window = lambda: (application, dialog)
        desktop._controls = lambda _window: [(yes, ("press",)), (no, ("press",))]
        original_invoke = desktop._invoke_control

        def invoke(*control):
            application.children = ()
            application.childCount = 0
            return original_invoke(*control)

        desktop._invoke_control = invoke
        self.assertEqual(desktop.decide_standard_dialog("cancel"), "Nein")
        self.assertEqual(yes.action.called, [])
        self.assertEqual(no.action.called, [0])

        allow = FakeNode("Allow", action=FakeWindowAction(("click",)))
        deny = FakeNode("Deny", action=FakeWindowAction(("click",)))
        permission = FakeDialog("Camera", (allow, deny))
        desktop._active_window = lambda: (object(), permission)
        desktop._controls = lambda _window: [(allow, ("click",)), (deny, ("click",))]
        with self.assertRaises(GnomeAdapterError):
            desktop.decide_standard_dialog("accept")
        self.assertEqual(allow.action.called, [])
        self.assertEqual(deny.action.called, [])

    def test_real_standard_dialog_supports_explicit_retry_and_apply_pairs(self):
        desktop = PyAtSpiDesktop.__new__(PyAtSpiDesktop)
        base_invoke = desktop._invoke_control
        for decision, positive_name, cancel_name in (
            ("retry", "Wiederholen", "Abbrechen"),
            ("apply", "Apply", "Cancel"),
        ):
            positive = FakeNode(positive_name, action=FakeWindowAction(("click",)))
            cancel = FakeNode(cancel_name, action=FakeWindowAction(("click",)))
            dialog = FakeDialog("Operation", (positive, cancel))
            application = FakeNode("Application", children=(dialog,))
            desktop._active_window = lambda application=application, dialog=dialog: (
                application, dialog
            )
            desktop._controls = lambda _window, positive=positive, cancel=cancel: [
                (positive, ("click",)), (cancel, ("click",))
            ]
            def invoke(*control, application=application):
                application.children = ()
                application.childCount = 0
                return base_invoke(*control)

            desktop._invoke_control = invoke
            self.assertEqual(desktop.decide_standard_dialog(decision), positive_name)
            self.assertEqual(positive.action.called, [0])
            self.assertEqual(cancel.action.called, [])

    def test_real_standard_dialog_rejects_wrong_explicit_positive_intent(self):
        retry = FakeNode("Retry", action=FakeWindowAction(("click",)))
        cancel = FakeNode("Cancel", action=FakeWindowAction(("click",)))
        dialog = FakeDialog("Operation", (retry, cancel))
        desktop = PyAtSpiDesktop.__new__(PyAtSpiDesktop)
        desktop._active_window = lambda: (object(), dialog)
        desktop._controls = lambda _window: [(retry, ("click",)), (cancel, ("click",))]
        with self.assertRaisesRegex(GnomeAdapterError, "angeforderte Entscheidung"):
            desktop.decide_standard_dialog("apply")
        self.assertEqual(retry.action.called, [])
        self.assertEqual(cancel.action.called, [])

    def test_real_standard_dialog_rejects_file_dialog_and_multiple_groups(self):
        ok = FakeNode("OK", action=FakeWindowAction(("click",)))
        cancel = FakeNode("Cancel", action=FakeWindowAction(("click",)))
        file_dialog = FakeDialog("Open File", (ok, cancel))
        desktop = PyAtSpiDesktop.__new__(PyAtSpiDesktop)
        desktop._active_window = lambda: (object(), file_dialog)
        desktop._controls = lambda _window: [(ok, ("click",)), (cancel, ("click",))]
        with self.assertRaises(GnomeAdapterError):
            desktop.decide_standard_dialog("accept")

        yes = FakeNode("Yes", action=FakeWindowAction(("click",)))
        no = FakeNode("No", action=FakeWindowAction(("click",)))
        ambiguous = FakeDialog("Question", (ok, cancel, yes, no))
        desktop._active_window = lambda: (object(), ambiguous)
        desktop._controls = lambda _window: [
            (ok, ("click",)), (cancel, ("click",)), (yes, ("click",)), (no, ("click",))
        ]
        with self.assertRaises(GnomeAdapterError):
            desktop.decide_standard_dialog("cancel")
        for control in (ok, cancel, yes, no):
            self.assertEqual(control.action.called, [])

    def test_real_standard_dialog_rejects_window_or_pair_replacement(self):
        old_ok = FakeNode("OK", action=FakeWindowAction(("click",)))
        old_cancel = FakeNode("Cancel", action=FakeWindowAction(("click",)))
        new_ok = FakeNode("OK", action=FakeWindowAction(("click",)))
        new_cancel = FakeNode("Cancel", action=FakeWindowAction(("click",)))
        first = FakeDialog("Question", (old_ok, old_cancel))
        second = FakeDialog("Question", (old_ok, old_cancel))
        application = FakeNode("Application", children=(first, second))
        desktop = PyAtSpiDesktop.__new__(PyAtSpiDesktop)
        windows = iter((first, second))
        desktop._active_window = lambda: (application, next(windows))
        desktop._controls = lambda _window: [(old_ok, ("click",)), (old_cancel, ("click",))]
        with self.assertRaisesRegex(GnomeAdapterError, "Standarddialog.*gewechselt"):
            desktop.decide_standard_dialog("accept")

        snapshots = iter((
            [(old_ok, ("click",)), (old_cancel, ("click",))],
            [(new_ok, ("click",)), (new_cancel, ("click",))],
        ))
        application.children = (first,)
        application.childCount = 1
        desktop._active_window = lambda: (application, first)
        desktop._controls = lambda _window: next(snapshots)
        with self.assertRaisesRegex(GnomeAdapterError, "Standarddialogpaar.*geändert"):
            desktop.decide_standard_dialog("cancel")
        for control in (old_ok, old_cancel, new_ok, new_cancel):
            self.assertEqual(control.action.called, [])

    def test_real_standard_dialog_rejects_top_level_window_change_before_decision(self):
        ok = FakeNode("OK", action=FakeWindowAction(("click",)))
        cancel = FakeNode("Cancel", action=FakeWindowAction(("click",)))
        dialog = FakeDialog("Question", (ok, cancel))
        foreign = FakeDialog("Foreign", ())
        application = FakeNode("Application", children=(dialog,))
        desktop = PyAtSpiDesktop.__new__(PyAtSpiDesktop)
        calls = 0

        def active_window():
            nonlocal calls
            calls += 1
            if calls == 2:
                application.children = (dialog, foreign)
                application.childCount = 2
            return application, dialog

        desktop._active_window = active_window
        desktop._controls = lambda _window: [(ok, ("click",)), (cancel, ("click",))]
        with self.assertRaisesRegex(GnomeAdapterError, "Fensterliste.*geändert"):
            desktop.decide_standard_dialog("accept")
        self.assertEqual(ok.action.called, [])
        self.assertEqual(cancel.action.called, [])

    def test_real_standard_dialog_reports_unconfirmed_exact_poststate(self):
        ok = FakeNode("OK", action=FakeWindowAction(("click",)))
        cancel = FakeNode("Cancel", action=FakeWindowAction(("click",)))
        dialog = FakeDialog("Question", (ok, cancel))
        foreign = FakeDialog("Foreign", ())
        application = FakeNode("Application", children=(dialog,))
        desktop = PyAtSpiDesktop.__new__(PyAtSpiDesktop)
        desktop._active_window = lambda: (application, dialog)
        desktop._controls = lambda _window: [(ok, ("click",)), (cancel, ("click",))]

        def invoke(*_control):
            application.children = (foreign,)
            application.childCount = 1
            return "OK"

        desktop._invoke_control = invoke
        with patch("clausis.gnome_adapter.time.monotonic", side_effect=(0.0, 2.1)):
            with self.assertRaisesRegex(GnomeAdapterError, "Nachzustand.*nicht bestätigt"):
                desktop.decide_standard_dialog("accept")

    def test_real_standard_dialog_read_returns_only_unique_static_text(self):
        first = FakeNode("Operation failed", role="label")
        duplicate = FakeNode("Operation failed", role="paragraph")
        protected = FakeNode("hidden value", role="label", attributes=("protected:true",))
        entry = FakeNode("typed secret", role="entry")
        dialog = FakeDialog("Warning", (first, duplicate, protected, entry))
        desktop = PyAtSpiDesktop.__new__(PyAtSpiDesktop)
        desktop._active_window = lambda: (object(), dialog)
        self.assertEqual(
            desktop.read_standard_dialog(),
            ("Warning", ("Operation failed",)),
        )

    def test_real_standard_dialog_read_rejects_file_dialog_and_oversized_text(self):
        desktop = PyAtSpiDesktop.__new__(PyAtSpiDesktop)
        file_dialog = FakeDialog("Open File", (FakeNode("Choose a file", role="label"),))
        desktop._active_window = lambda: (object(), file_dialog)
        with self.assertRaisesRegex(GnomeAdapterError, "kein lesbarer Standarddialog"):
            desktop.read_standard_dialog()

        labels = tuple(FakeNode(str(index) * 200, role="label") for index in range(10))
        dialog = FakeDialog("Warning", labels)
        desktop._active_window = lambda: (object(), dialog)
        with self.assertRaisesRegex(GnomeAdapterError, "sichere Grenze"):
            desktop.read_standard_dialog()

    def test_real_standard_dialog_dismiss_rebinds_sole_close_control(self):
        close = FakeNode("Schließen", action=FakeWindowAction(("click",)))
        dialog = FakeDialog("Fehler", (close,))
        application = FakeNode("Application", children=(dialog,))
        desktop = PyAtSpiDesktop.__new__(PyAtSpiDesktop)
        calls = []
        desktop._active_window = lambda: calls.append(True) or (application, dialog)
        desktop._controls = lambda _window: [(close, ("click",))]
        def invoke(*control):
            application.children = ()
            application.childCount = 0
            return desktop._invoke_control_original(*control)
        desktop._invoke_control_original = desktop._invoke_control
        desktop._invoke_control = invoke
        self.assertEqual(desktop.dismiss_standard_dialog(), "Schließen")
        self.assertEqual(close.action.called, [0])
        self.assertEqual(len(calls), 2)

    def test_real_standard_dialog_dismiss_rejects_pairs_and_file_choosers(self):
        close = FakeNode("Close", action=FakeWindowAction(("click",)))
        help_control = FakeNode("Help", action=FakeWindowAction(("click",)))
        dialog = FakeDialog("Error", (close, help_control))
        application = FakeNode("Application", children=(dialog,))
        desktop = PyAtSpiDesktop.__new__(PyAtSpiDesktop)
        desktop._active_window = lambda: (application, dialog)
        desktop._controls = lambda _window: [
            (close, ("click",)), (help_control, ("click",))
        ]
        with self.assertRaisesRegex(GnomeAdapterError, "kein eindeutiger"):
            desktop.dismiss_standard_dialog()

        file_dialog = FakeDialog("Open File", (close,))
        application.children = (file_dialog,)
        application.childCount = 1
        desktop._active_window = lambda: (application, file_dialog)
        desktop._controls = lambda _window: [(close, ("click",))]
        with self.assertRaisesRegex(GnomeAdapterError, "kein erkannter Standarddialog"):
            desktop.dismiss_standard_dialog()
        self.assertEqual(close.action.called, [])

    def test_real_standard_dialog_dismiss_rejects_window_or_control_replacement(self):
        old_close = FakeNode("Close", action=FakeWindowAction(("click",)))
        new_close = FakeNode("Close", action=FakeWindowAction(("click",)))
        first = FakeDialog("Error", (old_close,))
        second = FakeDialog("Error", (old_close,))
        application = FakeNode("Application", children=(first, second))
        desktop = PyAtSpiDesktop.__new__(PyAtSpiDesktop)
        windows = iter((first, second))
        desktop._active_window = lambda: (application, next(windows))
        desktop._controls = lambda _window: [(old_close, ("click",))]
        with self.assertRaisesRegex(GnomeAdapterError, "vor dem Schließen gewechselt"):
            desktop.dismiss_standard_dialog()

        snapshots = iter(([(old_close, ("click",))], [(new_close, ("click",))]))
        application.children = (first,)
        application.childCount = 1
        desktop._active_window = lambda: (application, first)
        desktop._controls = lambda _window: next(snapshots)
        with self.assertRaisesRegex(GnomeAdapterError, "Bedienelement.*geändert"):
            desktop.dismiss_standard_dialog()
        self.assertEqual(old_close.action.called, [])
        self.assertEqual(new_close.action.called, [])

    def test_real_standard_dialog_dismiss_reports_unconfirmed_exact_poststate(self):
        close = FakeNode("Close", action=FakeWindowAction(("click",)))
        dialog = FakeDialog("Error", (close,))
        foreign = FakeDialog("Foreign", ())
        application = FakeNode("Application", children=(dialog,))
        desktop = PyAtSpiDesktop.__new__(PyAtSpiDesktop)
        desktop._active_window = lambda: (application, dialog)
        desktop._controls = lambda _window: [(close, ("click",))]

        def invoke(*_control):
            application.children = (foreign,)
            application.childCount = 1
            return "Close"

        desktop._invoke_control = invoke
        with patch("clausis.gnome_adapter.time.monotonic", side_effect=(0.0, 2.1)):
            with self.assertRaisesRegex(GnomeAdapterError, "Nachzustand.*nicht bestätigt"):
                desktop.dismiss_standard_dialog()

    def test_real_standard_dialog_dismiss_rejects_top_level_window_change(self):
        close = FakeNode("Close", action=FakeWindowAction(("click",)))
        dialog = FakeDialog("Error", (close,))
        foreign = FakeDialog("Foreign", ())
        application = FakeNode("Application", children=(dialog,))
        desktop = PyAtSpiDesktop.__new__(PyAtSpiDesktop)
        calls = 0

        def active_window():
            nonlocal calls
            calls += 1
            if calls == 2:
                application.children = (dialog, foreign)
                application.childCount = 2
            return application, dialog

        desktop._active_window = active_window
        desktop._controls = lambda _window: [(close, ("click",))]
        with self.assertRaisesRegex(GnomeAdapterError, "Fensterliste.*geändert"):
            desktop.dismiss_standard_dialog()
        self.assertEqual(close.action.called, [])

    def test_real_tree_item_expand_and_collapse_verify_state(self):
        item = FakeTreeItem("Documents", focused=True)
        tree = FakeTree((item,))
        window = FakeNode("Files", children=(tree,), role="frame")
        tree.parent = window
        desktop = PyAtSpiDesktop.__new__(PyAtSpiDesktop)
        desktop._atspi = type(
            "AtSpi",
            (),
            {
                "STATE_FOCUSED": "focused",
                "STATE_EXPANDED": "expanded",
                "STATE_EXPANDABLE": "expandable",
            },
        )
        desktop._active_window = lambda: (object(), window)
        self.assertEqual(
            desktop.set_named_tree_item_expanded("Documents", True), "Documents"
        )
        self.assertTrue(item.expanded)
        self.assertEqual(
            desktop.set_named_tree_item_expanded("Documents", False), "Documents"
        )
        self.assertFalse(item.expanded)
        self.assertEqual(item.action.called, [0, 1])

    def test_real_tree_rejects_duplicate_named_items_without_action(self):
        first = FakeTreeItem("Same", focused=True)
        second = FakeTreeItem("Same")
        tree = FakeTree((first, second))
        window = FakeNode("Files", children=(tree,), role="frame")
        tree.parent = window
        desktop = PyAtSpiDesktop.__new__(PyAtSpiDesktop)
        desktop._atspi = type(
            "AtSpi",
            (),
            {
                "STATE_FOCUSED": "focused",
                "STATE_EXPANDED": "expanded",
                "STATE_EXPANDABLE": "expandable",
            },
        )
        desktop._active_window = lambda: (object(), window)
        with self.assertRaises(GnomeAdapterError):
            desktop.set_named_tree_item_expanded("Same", True)
        self.assertEqual(first.action.called, [])
        self.assertEqual(second.action.called, [])

    def test_real_tree_requires_exact_expand_action(self):
        item = FakeTreeItem("Documents", focused=True, actions=("click", "toggle"))
        tree = FakeTree((item,))
        window = FakeNode("Files", children=(tree,), role="frame")
        tree.parent = window
        desktop = PyAtSpiDesktop.__new__(PyAtSpiDesktop)
        desktop._atspi = type(
            "AtSpi",
            (),
            {
                "STATE_FOCUSED": "focused",
                "STATE_EXPANDED": "expanded",
                "STATE_EXPANDABLE": "expandable",
            },
        )
        desktop._active_window = lambda: (object(), window)
        with self.assertRaises(GnomeAdapterError):
            desktop.set_named_tree_item_expanded("Documents", True)
        self.assertEqual(item.action.called, [])

    def test_real_tree_fails_when_post_state_does_not_change(self):
        item = FakeTreeItem("Documents", focused=True, mutate=False)
        tree = FakeTree((item,))
        window = FakeNode("Files", children=(tree,), role="frame")
        tree.parent = window
        desktop = PyAtSpiDesktop.__new__(PyAtSpiDesktop)
        desktop._atspi = type(
            "AtSpi",
            (),
            {
                "STATE_FOCUSED": "focused",
                "STATE_EXPANDED": "expanded",
                "STATE_EXPANDABLE": "expandable",
            },
        )
        desktop._active_window = lambda: (object(), window)
        with self.assertRaises(GnomeAdapterError):
            desktop.set_named_tree_item_expanded("Documents", True)
        self.assertEqual(item.action.called, [0])

    def test_real_tree_rolls_back_after_exceptional_partial_change(self):
        item = FakeTreeItem(
            "Documents", focused=True, raise_after_mutation=True
        )
        tree = FakeTree((item,))
        window = FakeNode("Files", children=(tree,), role="frame")
        tree.parent = window
        desktop = PyAtSpiDesktop.__new__(PyAtSpiDesktop)
        desktop._atspi = type("AtSpi", (), {
            "STATE_FOCUSED": "focused", "STATE_EXPANDED": "expanded",
            "STATE_EXPANDABLE": "expandable",
        })
        desktop._active_window = lambda: (object(), window)
        with self.assertRaisesRegex(GnomeAdapterError, "hat die Zustands"):
            desktop.set_named_tree_item_expanded("Documents", True)
        self.assertFalse(item.expanded)
        self.assertEqual(item.action.called, [0, 1])

    def test_real_tree_reports_unrestorable_partial_change(self):
        item = FakeTreeItem(
            "Documents", focused=True, raise_after_mutation=True,
            fail_rollback=True
        )
        tree = FakeTree((item,))
        window = FakeNode("Files", children=(tree,), role="frame")
        tree.parent = window
        desktop = PyAtSpiDesktop.__new__(PyAtSpiDesktop)
        desktop._atspi = type("AtSpi", (), {
            "STATE_FOCUSED": "focused", "STATE_EXPANDED": "expanded",
            "STATE_EXPANDABLE": "expandable",
        })
        desktop._active_window = lambda: (object(), window)
        with self.assertRaisesRegex(GnomeAdapterError, "nicht zurückgesetzt"):
            desktop.set_named_tree_item_expanded("Documents", True)
        self.assertTrue(item.expanded)

    def test_real_tree_collapse_rolls_back_after_exceptional_partial_change(self):
        item = FakeTreeItem(
            "Documents", focused=True, expanded=True,
            raise_after_mutation=True
        )
        tree = FakeTree((item,))
        window = FakeNode("Files", children=(tree,), role="frame")
        tree.parent = window
        desktop = PyAtSpiDesktop.__new__(PyAtSpiDesktop)
        desktop._atspi = type("AtSpi", (), {
            "STATE_FOCUSED": "focused", "STATE_EXPANDED": "expanded",
            "STATE_EXPANDABLE": "expandable",
        })
        desktop._active_window = lambda: (object(), window)
        with self.assertRaises(GnomeAdapterError):
            desktop.set_named_tree_item_expanded("Documents", False)
        self.assertTrue(item.expanded)
        self.assertEqual(item.action.called, [1, 0])

    def test_real_table_selects_unique_row_by_exact_cell_name(self):
        first_cell = FakeFocusNode("Annual", role="table cell")
        second_cell = FakeFocusNode("Quarterly", focused=True, role="table cell")
        first = FakeTableRow("", (first_cell,))
        second = FakeTableRow("", (second_cell,))
        selection = FakeSelection((0,))
        table = FakeTable((first, second), selection)
        window = FakeNode("Reports", children=(table,), role="frame")
        table.parent = window
        desktop = PyAtSpiDesktop.__new__(PyAtSpiDesktop)
        desktop._atspi = type("AtSpi", (), {"STATE_FOCUSED": object()})
        desktop._active_window = lambda: (object(), window)
        self.assertEqual(desktop.select_table_row("Quarterly"), "Quarterly")
        self.assertEqual(selection.selected, {1})

    def test_real_table_rejects_duplicate_cell_name_without_mutation(self):
        first_cell = FakeFocusNode("Same", focused=True, role="table cell")
        second_cell = FakeFocusNode("Same", role="table cell")
        first = FakeTableRow("", (first_cell,))
        second = FakeTableRow("", (second_cell,))
        selection = FakeSelection((0,))
        table = FakeTable((first, second), selection)
        window = FakeNode("Reports", children=(table,), role="frame")
        table.parent = window
        desktop = PyAtSpiDesktop.__new__(PyAtSpiDesktop)
        desktop._atspi = type("AtSpi", (), {"STATE_FOCUSED": object()})
        desktop._active_window = lambda: (object(), window)
        with self.assertRaises(GnomeAdapterError):
            desktop.select_table_row("Same")
        self.assertEqual(selection.selected, {0})

    def test_real_table_selection_rolls_back_mismatch(self):
        first_cell = FakeFocusNode("Annual", role="table cell")
        second_cell = FakeFocusNode("Quarterly", focused=True, role="table cell")
        first = FakeTableRow("", (first_cell,))
        second = FakeTableRow("", (second_cell,))
        selection = FakeSelection((0,), ignored_index=1)
        table = FakeTable((first, second), selection)
        window = FakeNode("Reports", children=(table,), role="frame")
        table.parent = window
        desktop = PyAtSpiDesktop.__new__(PyAtSpiDesktop)
        desktop._atspi = type("AtSpi", (), {"STATE_FOCUSED": object()})
        desktop._active_window = lambda: (object(), window)
        with self.assertRaises(GnomeAdapterError):
            desktop.select_table_row("Quarterly")
        self.assertEqual(selection.selected, {0})

    def test_real_table_command_rejects_focused_generic_list(self):
        cell = FakeFocusNode("Quarterly", focused=True, role="list item")
        choices = FakeSelectionContainer((cell,), FakeSelection())
        choices.role = "list"
        window = FakeNode("Reports", children=(choices,), role="frame")
        choices.parent = window
        desktop = PyAtSpiDesktop.__new__(PyAtSpiDesktop)
        desktop._atspi = type("AtSpi", (), {"STATE_FOCUSED": object()})
        desktop._active_window = lambda: (object(), window)
        with self.assertRaises(GnomeAdapterError):
            desktop.select_table_row("Quarterly")
        self.assertEqual(choices.selection.selected, set())

    def test_real_tab_list_selects_unique_exact_tab(self):
        general = FakeFocusNode("General", role="page tab")
        privacy = FakeFocusNode("Privacy", focused=True, role="page tab")
        selection = FakeSelection((0,))
        tabs = FakeTabList((general, privacy), selection)
        window = FakeNode("Settings", children=(tabs,), role="frame")
        tabs.parent = window
        desktop = PyAtSpiDesktop.__new__(PyAtSpiDesktop)
        desktop._atspi = type("AtSpi", (), {"STATE_FOCUSED": object()})
        desktop._active_window = lambda: (object(), window)
        self.assertEqual(desktop.select_named_tab("Privacy"), "Privacy")
        self.assertEqual(selection.selected, {1})

    def test_real_tab_list_rejects_duplicate_name_without_mutation(self):
        first = FakeFocusNode("Same", focused=True, role="page tab")
        second = FakeFocusNode("Same", role="page tab")
        selection = FakeSelection((0,))
        tabs = FakeTabList((first, second), selection)
        window = FakeNode("Settings", children=(tabs,), role="frame")
        tabs.parent = window
        desktop = PyAtSpiDesktop.__new__(PyAtSpiDesktop)
        desktop._atspi = type("AtSpi", (), {"STATE_FOCUSED": object()})
        desktop._active_window = lambda: (object(), window)
        with self.assertRaises(GnomeAdapterError):
            desktop.select_named_tab("Same")
        self.assertEqual(selection.selected, {0})

    def test_real_tab_selection_rolls_back_mismatch(self):
        general = FakeFocusNode("General", role="page tab")
        privacy = FakeFocusNode("Privacy", focused=True, role="page tab")
        selection = FakeSelection((0,), ignored_index=1)
        tabs = FakeTabList((general, privacy), selection)
        window = FakeNode("Settings", children=(tabs,), role="frame")
        tabs.parent = window
        desktop = PyAtSpiDesktop.__new__(PyAtSpiDesktop)
        desktop._atspi = type("AtSpi", (), {"STATE_FOCUSED": object()})
        desktop._active_window = lambda: (object(), window)
        with self.assertRaises(GnomeAdapterError):
            desktop.select_named_tab("Privacy")
        self.assertEqual(selection.selected, {0})

    def test_real_tab_command_rejects_focused_generic_list(self):
        item = FakeFocusNode("Privacy", focused=True, role="list item")
        choices = FakeSelectionContainer((item,), FakeSelection())
        choices.role = "list"
        window = FakeNode("Settings", children=(choices,), role="frame")
        choices.parent = window
        desktop = PyAtSpiDesktop.__new__(PyAtSpiDesktop)
        desktop._atspi = type("AtSpi", (), {"STATE_FOCUSED": object()})
        desktop._active_window = lambda: (object(), window)
        with self.assertRaises(GnomeAdapterError):
            desktop.select_named_tab("Privacy")
        self.assertEqual(choices.selection.selected, set())

    def test_real_slider_sets_unique_exact_name_and_maps_range(self):
        slider = FakeSlider("Zoom", current=1.0, minimum=1.0, maximum=3.0)
        window = FakeNode("Accessibility", children=(slider,), role="frame")
        desktop = PyAtSpiDesktop.__new__(PyAtSpiDesktop)
        desktop._active_window = lambda: (object(), window)
        self.assertEqual(desktop.set_named_slider("Zoom", 50), "Zoom")
        self.assertEqual(slider.currentValue, 2.0)
        self.assertEqual(slider.set_calls, [2.0])

    def test_named_progress_read_is_low_risk_and_immediate(self):
        result = self.broker.submit(
            ActionRequest("desktop.progress.read_named", target="Download")
        )
        self.assertEqual(result.status, "completed")
        self.assertIn("42 Prozent", result.message)
        self.assertEqual(self.desktop.progress_reads, ["Download"])

    def test_real_progress_read_maps_finite_range_without_mutation(self):
        progress = FakeSlider(
            "Download", current=7.5, minimum=5.0, maximum=10.0, role="progress bar"
        )
        window = FakeNode("Downloads", children=(progress,), role="frame")
        desktop = PyAtSpiDesktop.__new__(PyAtSpiDesktop)
        desktop._active_window = lambda: (object(), window)
        self.assertEqual(desktop.read_named_progress("Download"), ("Download", 50))
        self.assertEqual(progress.set_calls, [])

    def test_real_progress_read_rejects_duplicate_wrong_role_and_invalid_range(self):
        desktop = PyAtSpiDesktop.__new__(PyAtSpiDesktop)
        for controls in (
            (
                FakeSlider("Download", role="progress bar"),
                FakeSlider("Download", role="progress bar"),
            ),
            (FakeSlider("Download", role="slider"),),
            (FakeSlider("Download", current=101, role="progress bar"),),
            (FakeSlider("Download", minimum=1, maximum=1, role="progress bar"),),
        ):
            window = FakeNode("Downloads", children=controls, role="frame")
            desktop._active_window = lambda window=window: (object(), window)
            with self.assertRaises(GnomeAdapterError):
                desktop.read_named_progress("Download")
            self.assertTrue(all(not control.set_calls for control in controls))

    def test_real_slider_honors_declared_value_increment(self):
        slider = FakeSlider(
            "Brightness", current=0.0, minimum=0.0, maximum=10.0, increment=2.0
        )
        window = FakeNode("Display", children=(slider,), role="frame")
        desktop = PyAtSpiDesktop.__new__(PyAtSpiDesktop)
        desktop._active_window = lambda: (object(), window)
        self.assertEqual(desktop.set_named_slider("Brightness", 50), "Brightness")
        self.assertEqual(slider.currentValue, 6.0)
        self.assertEqual(slider.set_calls, [6.0])

    def test_real_slider_rejects_duplicate_name_without_mutation(self):
        first = FakeSlider("Zoom", current=20.0)
        second = FakeSlider("Zoom", current=30.0)
        window = FakeNode("Accessibility", children=(first, second), role="frame")
        desktop = PyAtSpiDesktop.__new__(PyAtSpiDesktop)
        desktop._active_window = lambda: (object(), window)
        with self.assertRaises(GnomeAdapterError):
            desktop.set_named_slider("Zoom", 50)
        self.assertEqual(first.set_calls, [])
        self.assertEqual(second.set_calls, [])

    def test_real_slider_rolls_back_unconfirmed_value(self):
        slider = FakeSlider("Zoom", current=20.0, mismatch=True)
        window = FakeNode("Accessibility", children=(slider,), role="frame")
        desktop = PyAtSpiDesktop.__new__(PyAtSpiDesktop)
        desktop._active_window = lambda: (object(), window)
        with self.assertRaises(GnomeAdapterError):
            desktop.set_named_slider("Zoom", 50)
        self.assertEqual(slider.currentValue, 20.0)
        self.assertEqual(slider.set_calls, [50.0, 20.0])

    def test_real_slider_rolls_back_after_exceptional_partial_mutation(self):
        slider = FakeSlider("Zoom", current=20.0, raise_after_mutation=True)
        window = FakeNode("Accessibility", children=(slider,), role="frame")
        desktop = PyAtSpiDesktop.__new__(PyAtSpiDesktop)
        desktop._active_window = lambda: (object(), window)
        with self.assertRaisesRegex(GnomeAdapterError, "hat die Änderung abgelehnt"):
            desktop.set_named_slider("Zoom", 50)
        self.assertEqual(slider.currentValue, 20.0)
        self.assertEqual(slider.set_calls, [50.0, 20.0])

    def test_real_slider_reports_unrestorable_partial_value(self):
        slider = FakeSlider(
            "Zoom", current=20.0, mismatch=True, restore_rejected=True
        )
        window = FakeNode("Accessibility", children=(slider,), role="frame")
        desktop = PyAtSpiDesktop.__new__(PyAtSpiDesktop)
        desktop._active_window = lambda: (object(), window)
        with self.assertRaisesRegex(GnomeAdapterError, "nicht zurückgesetzt"):
            desktop.set_named_slider("Zoom", 50)
        self.assertNotEqual(slider.currentValue, 20.0)

    def test_real_slider_rejects_non_slider_role(self):
        control = FakeSlider("Zoom", role="spin button")
        window = FakeNode("Accessibility", children=(control,), role="frame")
        desktop = PyAtSpiDesktop.__new__(PyAtSpiDesktop)
        desktop._active_window = lambda: (object(), window)
        with self.assertRaises(GnomeAdapterError):
            desktop.set_named_slider("Zoom", 50)
        self.assertEqual(control.set_calls, [])

    def test_real_checkbox_sets_and_verifies_exact_control(self):
        control = FakeCheckedControl("Automatic Updates")
        window = FakeNode("Settings", children=(control,), role="frame")
        desktop = PyAtSpiDesktop.__new__(PyAtSpiDesktop)
        desktop._atspi = type("AtSpi", (), {"STATE_CHECKED": "checked"})
        desktop._active_window = lambda: (object(), window)
        self.assertEqual(
            desktop.set_named_checkbox("Automatic Updates", True), "Automatic Updates"
        )
        self.assertTrue(control.checked)
        self.assertEqual(control.action.called, [0])
        desktop.set_named_checkbox("Automatic Updates", True)
        self.assertEqual(control.action.called, [0])

    def test_real_checkbox_rejects_duplicate_without_mutation(self):
        first = FakeCheckedControl("Updates")
        second = FakeCheckedControl("Updates")
        window = FakeNode("Settings", children=(first, second), role="frame")
        desktop = PyAtSpiDesktop.__new__(PyAtSpiDesktop)
        desktop._atspi = type("AtSpi", (), {"STATE_CHECKED": "checked"})
        desktop._active_window = lambda: (object(), window)
        with self.assertRaises(GnomeAdapterError):
            desktop.set_named_checkbox("Updates", True)
        self.assertEqual(first.action.called, [])
        self.assertEqual(second.action.called, [])

    def test_real_checkbox_requires_exact_toggle_and_post_state(self):
        wrong = FakeCheckedControl("Updates", actions=("click",))
        window = FakeNode("Settings", children=(wrong,), role="frame")
        desktop = PyAtSpiDesktop.__new__(PyAtSpiDesktop)
        desktop._atspi = type("AtSpi", (), {"STATE_CHECKED": "checked"})
        desktop._active_window = lambda: (object(), window)
        with self.assertRaises(GnomeAdapterError):
            desktop.set_named_checkbox("Updates", True)
        self.assertFalse(wrong.checked)
        stuck = FakeCheckedControl("Updates", mutate=False)
        window = FakeNode("Settings", children=(stuck,), role="frame")
        desktop._active_window = lambda: (object(), window)
        with self.assertRaises(GnomeAdapterError):
            desktop.set_named_checkbox("Updates", True)
        self.assertEqual(stuck.action.called, [0])

    def test_real_checkbox_rolls_back_after_exceptional_partial_toggle(self):
        control = FakeCheckedControl("Updates", raise_after_mutation=True)
        window = FakeNode("Settings", children=(control,), role="frame")
        desktop = PyAtSpiDesktop.__new__(PyAtSpiDesktop)
        desktop._atspi = type("AtSpi", (), {"STATE_CHECKED": "checked"})
        desktop._active_window = lambda: (object(), window)
        with self.assertRaisesRegex(GnomeAdapterError, "hat die Änderung abgelehnt"):
            desktop.set_named_checkbox("Updates", True)
        self.assertFalse(control.checked)
        self.assertEqual(control.action.called, [0, 0])

    def test_real_checkbox_reports_unrestorable_partial_toggle(self):
        control = FakeCheckedControl(
            "Updates", raise_after_mutation=True, fail_rollback=True
        )
        window = FakeNode("Settings", children=(control,), role="frame")
        desktop = PyAtSpiDesktop.__new__(PyAtSpiDesktop)
        desktop._atspi = type("AtSpi", (), {"STATE_CHECKED": "checked"})
        desktop._active_window = lambda: (object(), window)
        with self.assertRaisesRegex(GnomeAdapterError, "nicht zurückgesetzt"):
            desktop.set_named_checkbox("Updates", True)
        self.assertTrue(control.checked)

    def test_real_switch_sets_exact_role_and_is_idempotent(self):
        control = FakeCheckedControl("Wi-Fi", role="switch")
        window = FakeNode("Network", children=(control,), role="frame")
        desktop = PyAtSpiDesktop.__new__(PyAtSpiDesktop)
        desktop._atspi = type("AtSpi", (), {"STATE_CHECKED": "checked"})
        desktop._active_window = lambda: (object(), window)
        self.assertEqual(desktop.set_named_switch("Wi-Fi", True), "Wi-Fi")
        self.assertTrue(control.checked)
        desktop.set_named_switch("Wi-Fi", True)
        self.assertEqual(control.action.called, [0])

    def test_real_switch_rolls_back_after_exceptional_partial_toggle(self):
        control = FakeCheckedControl(
            "Wi-Fi", role="switch", raise_after_mutation=True
        )
        window = FakeNode("Network", children=(control,), role="frame")
        desktop = PyAtSpiDesktop.__new__(PyAtSpiDesktop)
        desktop._atspi = type("AtSpi", (), {"STATE_CHECKED": "checked"})
        desktop._active_window = lambda: (object(), window)
        with self.assertRaises(GnomeAdapterError):
            desktop.set_named_switch("Wi-Fi", True)
        self.assertFalse(control.checked)
        self.assertEqual(control.action.called, [0, 0])

    def test_real_switch_rejects_checkbox_duplicate_and_unconfirmed_state(self):
        checkbox = FakeCheckedControl("Wi-Fi", role="check box")
        window = FakeNode("Network", children=(checkbox,), role="frame")
        desktop = PyAtSpiDesktop.__new__(PyAtSpiDesktop)
        desktop._atspi = type("AtSpi", (), {"STATE_CHECKED": "checked"})
        desktop._active_window = lambda: (object(), window)
        with self.assertRaises(GnomeAdapterError):
            desktop.set_named_switch("Wi-Fi", True)
        first = FakeCheckedControl("Wi-Fi", role="switch")
        second = FakeCheckedControl("Wi-Fi", role="switch")
        window = FakeNode("Network", children=(first, second), role="frame")
        desktop._active_window = lambda: (object(), window)
        with self.assertRaises(GnomeAdapterError):
            desktop.set_named_switch("Wi-Fi", True)
        stuck = FakeCheckedControl("Wi-Fi", role="switch", mutate=False)
        window = FakeNode("Network", children=(stuck,), role="frame")
        desktop._active_window = lambda: (object(), window)
        with self.assertRaises(GnomeAdapterError):
            desktop.set_named_switch("Wi-Fi", True)
        self.assertEqual(stuck.action.called, [0])

    def test_real_radio_selects_exact_control_and_updates_group(self):
        light = FakeCheckedControl("Light", role="radio button", checked=True, actions=("select",))
        dark = FakeCheckedControl("Dark", role="radio button", actions=("select",))
        light.group = dark.group = (light, dark)
        window = FakeNode("Appearance", children=(light, dark), role="frame")
        desktop = PyAtSpiDesktop.__new__(PyAtSpiDesktop)
        desktop._atspi = type("AtSpi", (), {"STATE_CHECKED": "checked"})
        desktop._active_window = lambda: (object(), window)
        self.assertEqual(desktop.select_named_radio("Dark"), "Dark")
        self.assertFalse(light.checked)
        self.assertTrue(dark.checked)

    def test_real_radio_restores_previous_selection_on_mismatch(self):
        light = FakeCheckedControl("Light", role="radio button", checked=True, actions=("select",))
        dark = FakeCheckedControl(
            "Dark", role="radio button", actions=("select",), mismatch=True
        )
        light.group = dark.group = (light, dark)
        window = FakeNode("Appearance", children=(light, dark), role="frame")
        desktop = PyAtSpiDesktop.__new__(PyAtSpiDesktop)
        desktop._atspi = type("AtSpi", (), {"STATE_CHECKED": "checked"})
        desktop._active_window = lambda: (object(), window)
        with self.assertRaises(GnomeAdapterError):
            desktop.select_named_radio("Dark")
        self.assertTrue(light.checked)
        self.assertFalse(dark.checked)

    def test_real_radio_rejects_multiple_checked_start_without_mutation(self):
        light = FakeCheckedControl(
            "Light", role="radio button", checked=True, actions=("select",)
        )
        dark = FakeCheckedControl(
            "Dark", role="radio button", checked=True, actions=("select",)
        )
        light.group = dark.group = (light, dark)
        window = FakeNode("Appearance", children=(light, dark), role="frame")
        desktop = PyAtSpiDesktop.__new__(PyAtSpiDesktop)
        desktop._atspi = type("AtSpi", (), {"STATE_CHECKED": "checked"})
        desktop._active_window = lambda: (object(), window)
        with self.assertRaises(GnomeAdapterError):
            desktop.select_named_radio("Dark")
        self.assertEqual(light.action.called, [])
        self.assertEqual(dark.action.called, [])

    def test_real_radio_rolls_back_after_exceptional_partial_selection(self):
        light = FakeCheckedControl(
            "Light", role="radio button", checked=True, actions=("select",)
        )
        dark = FakeCheckedControl(
            "Dark", role="radio button", actions=("select",),
            raise_after_mutation=True
        )
        light.group = dark.group = (light, dark)
        window = FakeNode("Appearance", children=(light, dark), role="frame")
        desktop = PyAtSpiDesktop.__new__(PyAtSpiDesktop)
        desktop._atspi = type("AtSpi", (), {"STATE_CHECKED": "checked"})
        desktop._active_window = lambda: (object(), window)
        with self.assertRaisesRegex(GnomeAdapterError, "hat die Auswahl abgelehnt"):
            desktop.select_named_radio("Dark")
        self.assertTrue(light.checked)
        self.assertFalse(dark.checked)

    def test_real_radio_reports_failed_group_restoration(self):
        light = FakeCheckedControl(
            "Light", role="radio button", checked=True, actions=("select",)
        )
        light.action.accepted = False
        dark = FakeCheckedControl(
            "Dark", role="radio button", actions=("select",),
            raise_after_mutation=True
        )
        light.group = dark.group = (light, dark)
        window = FakeNode("Appearance", children=(light, dark), role="frame")
        desktop = PyAtSpiDesktop.__new__(PyAtSpiDesktop)
        desktop._atspi = type("AtSpi", (), {"STATE_CHECKED": "checked"})
        desktop._active_window = lambda: (object(), window)
        with self.assertRaisesRegex(GnomeAdapterError, "nicht zurückgesetzt"):
            desktop.select_named_radio("Dark")
        self.assertFalse(light.checked)
        self.assertTrue(dark.checked)

    def test_real_combo_selects_unique_exact_direct_item(self):
        english = FakeNode("English", role="menu item")
        german = FakeNode("Deutsch", role="menu item")
        selection = FakeSelection((0,))
        combo = FakeComboBox("Language", (english, german), selection)
        window = FakeNode("Settings", children=(combo,), role="frame")
        desktop = PyAtSpiDesktop.__new__(PyAtSpiDesktop)
        desktop._active_window = lambda: (object(), window)
        self.assertEqual(desktop.select_combo_item("Language", "Deutsch"), "Deutsch")
        self.assertEqual(selection.selected, {1})

    def test_real_combo_rejects_duplicate_item_without_mutation(self):
        first = FakeNode("Same", role="list item")
        second = FakeNode("Same", role="list item")
        selection = FakeSelection((0,))
        combo = FakeComboBox("Mode", (first, second), selection)
        window = FakeNode("Settings", children=(combo,), role="frame")
        desktop = PyAtSpiDesktop.__new__(PyAtSpiDesktop)
        desktop._active_window = lambda: (object(), window)
        with self.assertRaises(GnomeAdapterError):
            desktop.select_combo_item("Mode", "Same")
        self.assertEqual(selection.selected, {0})

    def test_real_combo_rolls_back_unconfirmed_selection(self):
        first = FakeNode("English", role="option")
        second = FakeNode("Deutsch", role="option")
        selection = FakeSelection((0,), ignored_index=1)
        combo = FakeComboBox("Language", (first, second), selection)
        window = FakeNode("Settings", children=(combo,), role="frame")
        desktop = PyAtSpiDesktop.__new__(PyAtSpiDesktop)
        desktop._active_window = lambda: (object(), window)
        with self.assertRaises(GnomeAdapterError):
            desktop.select_combo_item("Language", "Deutsch")
        self.assertEqual(selection.selected, {0})

    def test_real_combo_rejects_generic_list_and_wrong_child_role(self):
        item = FakeNode("Deutsch", role="menu item")
        generic = FakeSelectionContainer((item,), FakeSelection())
        generic.name = "Language"
        generic.role = "list"
        window = FakeNode("Settings", children=(generic,), role="frame")
        desktop = PyAtSpiDesktop.__new__(PyAtSpiDesktop)
        desktop._active_window = lambda: (object(), window)
        with self.assertRaises(GnomeAdapterError):
            desktop.select_combo_item("Language", "Deutsch")

    def test_real_spin_button_sets_exact_value_with_step(self):
        spin = FakeSlider(
            "Copies", role="spin button", current=1.0, minimum=1.0, maximum=10.0, increment=1.0
        )
        window = FakeNode("Print", children=(spin,), role="frame")
        desktop = PyAtSpiDesktop.__new__(PyAtSpiDesktop)
        desktop._active_window = lambda: (object(), window)
        self.assertEqual(desktop.set_named_spin_button("Copies", 3.0), "Copies")
        self.assertEqual(spin.currentValue, 3.0)
        self.assertEqual(spin.set_calls, [3.0])

    def test_real_spin_button_rejects_range_and_incompatible_step_without_mutation(self):
        spin = FakeSlider(
            "Copies", role="spin button", current=2.0, minimum=0.0, maximum=10.0, increment=2.0
        )
        window = FakeNode("Print", children=(spin,), role="frame")
        desktop = PyAtSpiDesktop.__new__(PyAtSpiDesktop)
        desktop._active_window = lambda: (object(), window)
        for number in (11.0, 3.0):
            with self.subTest(number=number), self.assertRaises(GnomeAdapterError):
                desktop.set_named_spin_button("Copies", number)
        self.assertEqual(spin.set_calls, [])

    def test_real_spin_button_rolls_back_unconfirmed_value(self):
        spin = FakeSlider(
            "Copies", role="spin button", current=2.0, minimum=0.0, maximum=10.0, mismatch=True
        )
        window = FakeNode("Print", children=(spin,), role="frame")
        desktop = PyAtSpiDesktop.__new__(PyAtSpiDesktop)
        desktop._active_window = lambda: (object(), window)
        with self.assertRaises(GnomeAdapterError):
            desktop.set_named_spin_button("Copies", 4.0)
        self.assertEqual(spin.currentValue, 2.0)
        self.assertEqual(spin.set_calls, [4.0, 2.0])

    def test_real_spin_button_rolls_back_after_exceptional_partial_mutation(self):
        spin = FakeSlider(
            "Copies", role="spin button", current=2.0, minimum=0.0,
            maximum=10.0, raise_after_mutation=True
        )
        window = FakeNode("Print", children=(spin,), role="frame")
        desktop = PyAtSpiDesktop.__new__(PyAtSpiDesktop)
        desktop._active_window = lambda: (object(), window)
        with self.assertRaisesRegex(GnomeAdapterError, "hat die Änderung abgelehnt"):
            desktop.set_named_spin_button("Copies", 4.0)
        self.assertEqual(spin.currentValue, 2.0)
        self.assertEqual(spin.set_calls, [4.0, 2.0])

    def test_real_spin_button_reports_unrestorable_partial_value(self):
        spin = FakeSlider(
            "Copies", role="spin button", current=2.0, minimum=0.0,
            maximum=10.0, mismatch=True, restore_rejected=True
        )
        window = FakeNode("Print", children=(spin,), role="frame")
        desktop = PyAtSpiDesktop.__new__(PyAtSpiDesktop)
        desktop._active_window = lambda: (object(), window)
        with self.assertRaisesRegex(GnomeAdapterError, "nicht zurückgesetzt"):
            desktop.set_named_spin_button("Copies", 4.0)
        self.assertNotEqual(spin.currentValue, 2.0)

    def test_real_spin_button_rejects_duplicate_and_slider_role(self):
        first = FakeSlider("Copies", role="spin button")
        second = FakeSlider("Copies", role="spin button")
        window = FakeNode("Print", children=(first, second), role="frame")
        desktop = PyAtSpiDesktop.__new__(PyAtSpiDesktop)
        desktop._active_window = lambda: (object(), window)
        with self.assertRaises(GnomeAdapterError):
            desktop.set_named_spin_button("Copies", 2.0)
        slider = FakeSlider("Copies", role="slider")
        window = FakeNode("Print", children=(slider,), role="frame")
        desktop._active_window = lambda: (object(), window)
        with self.assertRaises(GnomeAdapterError):
            desktop.set_named_spin_button("Copies", 2.0)
        self.assertEqual(first.set_calls, [])
        self.assertEqual(second.set_calls, [])
        self.assertEqual(slider.set_calls, [])

    def test_real_menu_activates_unique_exact_direct_item(self):
        open_item = FakeFocusNode("Open", role="menu item")
        save_action = FakeWindowAction(("activate",))
        save_item = FakeFocusNode("Save", focused=True, role="menu item")
        save_item.action = save_action
        menu = FakeMenu((open_item, save_item))
        window = FakeNode("Editor", children=(menu,), role="frame")
        menu.parent = window
        desktop = PyAtSpiDesktop.__new__(PyAtSpiDesktop)
        desktop._atspi = type("AtSpi", (), {"STATE_FOCUSED": "focused"})
        desktop._active_window = lambda: (object(), window)
        self.assertEqual(desktop.activate_menu_item("Save"), "Save")
        self.assertEqual(save_action.called, [0])

    def test_real_menu_rejects_duplicate_and_ambiguous_action_without_invocation(self):
        first = FakeFocusNode("Save", focused=True, role="menu item")
        second = FakeFocusNode("Save", role="menu item")
        menu = FakeMenu((first, second))
        window = FakeNode("Editor", children=(menu,), role="frame")
        menu.parent = window
        desktop = PyAtSpiDesktop.__new__(PyAtSpiDesktop)
        desktop._atspi = type("AtSpi", (), {"STATE_FOCUSED": "focused"})
        desktop._active_window = lambda: (object(), window)
        with self.assertRaises(GnomeAdapterError):
            desktop.activate_menu_item("Save")
        self.assertEqual(first.action.called, [])
        self.assertEqual(second.action.called, [])
        ambiguous = FakeFocusNode("Save", focused=True, role="menu item")
        ambiguous.action = FakeWindowAction(("activate", "click"))
        menu = FakeMenu((ambiguous,))
        window = FakeNode("Editor", children=(menu,), role="frame")
        menu.parent = window
        desktop._active_window = lambda: (object(), window)
        with self.assertRaises(GnomeAdapterError):
            desktop.activate_menu_item("Save")
        self.assertEqual(ambiguous.action.called, [])

    def test_real_menu_rejects_focused_generic_list(self):
        item = FakeFocusNode("Save", focused=True, role="menu item")
        generic = FakeNode("Choices", children=(item,), role="list")
        item.parent = generic
        window = FakeNode("Editor", children=(generic,), role="frame")
        generic.parent = window
        desktop = PyAtSpiDesktop.__new__(PyAtSpiDesktop)
        desktop._atspi = type("AtSpi", (), {"STATE_FOCUSED": "focused"})
        desktop._active_window = lambda: (object(), window)
        with self.assertRaises(GnomeAdapterError):
            desktop.activate_menu_item("Save")
        wrong = FakeNode("Deutsch", role="push button")
        combo = FakeComboBox("Language", (wrong,), FakeSelection())
        window = FakeNode("Settings", children=(combo,), role="frame")
        desktop._active_window = lambda: (object(), window)
        with self.assertRaises(GnomeAdapterError):
            desktop.select_combo_item("Language", "Deutsch")

    def test_real_menu_rejects_active_window_change_before_invocation(self):
        action = FakeWindowAction(("activate",))
        item = FakeFocusNode("Save", focused=True, role="menu item")
        item.action = action
        menu = FakeMenu((item,))
        first = FakeNode("Editor", children=(menu,), role="frame")
        second = FakeNode("Other", children=(menu,), role="frame")
        menu.parent = first
        windows = iter((first, second))
        desktop = PyAtSpiDesktop.__new__(PyAtSpiDesktop)
        desktop._atspi = type("AtSpi", (), {"STATE_FOCUSED": "focused"})
        desktop._active_window = lambda: (object(), next(windows))

        with self.assertRaisesRegex(GnomeAdapterError, "Fenster.*gewechselt"):
            desktop.activate_menu_item("Save")
        self.assertEqual(action.called, [])

    def test_real_menu_rejects_replaced_focused_menu_before_invocation(self):
        old_action = FakeWindowAction(("activate",))
        new_action = FakeWindowAction(("activate",))
        old_item = FakeFocusNode("Save", focused=True, role="menu item")
        new_item = FakeFocusNode("Save", focused=True, role="menu item")
        old_item.action = old_action
        new_item.action = new_action
        old_menu = FakeMenu((old_item,))
        new_menu = FakeMenu((new_item,))
        window = FakeNode("Editor", children=(old_menu, new_menu), role="frame")
        old_menu.parent = new_menu.parent = window
        focused = iter((old_item, new_item))
        desktop = PyAtSpiDesktop.__new__(PyAtSpiDesktop)
        desktop._atspi = type("AtSpi", (), {"STATE_FOCUSED": "focused"})
        desktop._active_window = lambda: (object(), window)
        desktop._find_state = lambda _window, _state: next(focused)

        with self.assertRaisesRegex(GnomeAdapterError, "Menü.*geändert"):
            desktop.activate_menu_item("Save")
        self.assertEqual(old_action.called, [])
        self.assertEqual(new_action.called, [])

    def test_real_permission_dialog_rebinds_then_invokes_only_bound_allow_control(self):
        allow_action = FakeWindowAction(("click",))
        deny_action = FakeWindowAction(("click",))
        allow = FakeNode("Allow", action=allow_action)
        deny = FakeNode("Don't Allow", action=deny_action)
        dialog = FakeDialog("Camera", (allow, deny))
        application = FakeNode("Application", children=(dialog,))
        desktop = PyAtSpiDesktop.__new__(PyAtSpiDesktop)
        calls = []
        desktop._active_window = lambda: calls.append(True) or (application, dialog)
        desktop._controls = lambda _window: [(allow, ("click",)), (deny, ("click",))]
        original_invoke = desktop._invoke_control
        def invoke(*control):
            application.children = ()
            application.childCount = 0
            return original_invoke(*control)
        desktop._invoke_control = invoke
        self.assertEqual(desktop.decide_permission("allow"), "Allow")
        self.assertEqual(allow_action.called, [0])
        self.assertEqual(deny_action.called, [])
        self.assertEqual(len(calls), 2)

    def test_real_permission_dialog_rejects_generic_ok_cancel_dialog(self):
        ok = FakeNode("OK", action=FakeWindowAction(("click",)))
        cancel = FakeNode("Cancel", action=FakeWindowAction(("click",)))
        dialog = FakeDialog("Preferences", (ok, cancel))
        desktop = PyAtSpiDesktop.__new__(PyAtSpiDesktop)
        desktop._active_window = lambda: (object(), dialog)
        desktop._controls = lambda _window: [(ok, ("click",)), (cancel, ("click",))]
        with self.assertRaises(GnomeAdapterError):
            desktop.decide_permission("allow")

    def test_real_permission_dialog_rejects_duplicate_decision(self):
        first = FakeNode("Allow", action=FakeWindowAction(("click",)))
        second = FakeNode("Allow", action=FakeWindowAction(("click",)))
        deny = FakeNode("Don't Allow", action=FakeWindowAction(("click",)))
        dialog = FakeDialog("Microphone", (first, second, deny))
        desktop = PyAtSpiDesktop.__new__(PyAtSpiDesktop)
        desktop._active_window = lambda: (object(), dialog)
        desktop._controls = lambda _window: [
            (first, ("click",)),
            (second, ("click",)),
            (deny, ("click",)),
        ]
        with self.assertRaises(GnomeAdapterError):
            desktop.decide_permission("deny")
        self.assertEqual(deny.action.called, [])

    def test_real_permission_dialog_invokes_exact_german_deny_control(self):
        allow_action = FakeWindowAction(("press",))
        deny_action = FakeWindowAction(("press",))
        allow = FakeNode("Zugriff gewähren", action=allow_action)
        deny = FakeNode("Zugriff verweigern", action=deny_action)
        dialog = FakeDialog("Bildschirmfreigabe", (allow, deny))
        application = FakeNode("Application", children=(dialog,))
        desktop = PyAtSpiDesktop.__new__(PyAtSpiDesktop)
        desktop._active_window = lambda: (application, dialog)
        desktop._controls = lambda _window: [(allow, ("press",)), (deny, ("press",))]
        original_invoke = desktop._invoke_control
        def invoke(*control):
            application.children = ()
            application.childCount = 0
            return original_invoke(*control)
        desktop._invoke_control = invoke
        self.assertEqual(desktop.decide_permission("deny"), "Zugriff verweigern")
        self.assertEqual(allow_action.called, [])
        self.assertEqual(deny_action.called, [0])

    def test_real_permission_dialog_rejects_active_dialog_change_before_decision(self):
        allow_action = FakeWindowAction(("click",))
        deny_action = FakeWindowAction(("click",))
        allow = FakeNode("Allow", action=allow_action)
        deny = FakeNode("Don't Allow", action=deny_action)
        first = FakeDialog("Microphone", (allow, deny))
        second = FakeDialog("Camera", (allow, deny))
        application = FakeNode("Application", children=(first, second))
        dialogs = iter((first, second))
        desktop = PyAtSpiDesktop.__new__(PyAtSpiDesktop)
        desktop._active_window = lambda: (application, next(dialogs))
        desktop._controls = lambda _window: [(allow, ("click",)), (deny, ("click",))]

        with self.assertRaisesRegex(GnomeAdapterError, "Berechtigungsdialog.*gewechselt"):
            desktop.decide_permission("allow")
        self.assertEqual(allow_action.called, [])
        self.assertEqual(deny_action.called, [])

    def test_real_permission_dialog_rejects_replaced_pair_before_decision(self):
        old_allow = FakeNode("Allow", action=FakeWindowAction(("click",)))
        old_deny = FakeNode("Don't Allow", action=FakeWindowAction(("click",)))
        new_allow = FakeNode("Allow", action=FakeWindowAction(("click",)))
        new_deny = FakeNode("Don't Allow", action=FakeWindowAction(("click",)))
        snapshots = iter((
            [(old_allow, ("click",)), (old_deny, ("click",))],
            [(new_allow, ("click",)), (new_deny, ("click",))],
        ))
        dialog = FakeDialog("Microphone", (old_allow, old_deny))
        application = FakeNode("Application", children=(dialog,))
        desktop = PyAtSpiDesktop.__new__(PyAtSpiDesktop)
        desktop._active_window = lambda: (application, dialog)
        desktop._controls = lambda _window: next(snapshots)

        with self.assertRaisesRegex(GnomeAdapterError, "Paar.*geändert"):
            desktop.decide_permission("deny")
        for control in (old_allow, old_deny, new_allow, new_deny):
            self.assertEqual(control.action.called, [])

    def test_real_permission_dialog_rejects_top_level_window_change(self):
        allow = FakeNode("Allow", action=FakeWindowAction(("click",)))
        deny = FakeNode("Don't Allow", action=FakeWindowAction(("click",)))
        dialog = FakeDialog("Microphone", (allow, deny))
        foreign = FakeDialog("Foreign", ())
        application = FakeNode("Application", children=(dialog,))
        desktop = PyAtSpiDesktop.__new__(PyAtSpiDesktop)
        calls = 0

        def active_window():
            nonlocal calls
            calls += 1
            if calls == 2:
                application.children = (dialog, foreign)
                application.childCount = 2
            return application, dialog

        desktop._active_window = active_window
        desktop._controls = lambda _window: [(allow, ("click",)), (deny, ("click",))]
        with self.assertRaisesRegex(GnomeAdapterError, "Fensterliste.*geändert"):
            desktop.decide_permission("deny")
        self.assertEqual(allow.action.called, [])
        self.assertEqual(deny.action.called, [])

    def test_real_permission_dialog_reports_unconfirmed_exact_poststate(self):
        allow = FakeNode("Allow", action=FakeWindowAction(("click",)))
        deny = FakeNode("Don't Allow", action=FakeWindowAction(("click",)))
        dialog = FakeDialog("Microphone", (allow, deny))
        foreign = FakeDialog("Foreign", ())
        application = FakeNode("Application", children=(dialog,))
        desktop = PyAtSpiDesktop.__new__(PyAtSpiDesktop)
        desktop._active_window = lambda: (application, dialog)
        desktop._controls = lambda _window: [(allow, ("click",)), (deny, ("click",))]

        def invoke(*_control):
            application.children = (foreign,)
            application.childCount = 1
            return "Allow"

        desktop._invoke_control = invoke
        with patch("clausis.gnome_adapter.time.monotonic", side_effect=(0.0, 2.1)):
            with self.assertRaisesRegex(GnomeAdapterError, "Nachzustand.*nicht bestätigt"):
                desktop.decide_permission("allow")

    def test_real_permission_dialog_rejects_permission_pair_in_regular_window(self):
        allow = FakeNode("Allow", action=FakeWindowAction(("click",)))
        deny = FakeNode("Don't Allow", action=FakeWindowAction(("click",)))
        window = FakeNode("Browser", children=(allow, deny))
        window.getRoleName = lambda: "frame"
        desktop = PyAtSpiDesktop.__new__(PyAtSpiDesktop)
        desktop._active_window = lambda: (object(), window)
        desktop._controls = lambda _window: [(allow, ("click",)), (deny, ("click",))]
        with self.assertRaises(GnomeAdapterError):
            desktop.decide_permission("allow")
        self.assertEqual(allow.action.called, [])

    def test_real_adapter_selects_exact_gnome_shell_control(self):
        action = FakeWindowAction(("click",))
        control = FakeNode("Anwendungen anzeigen", action=action)
        shell = FakeNode("GNOME Shell", children=(control,))
        root = FakeNode("Desktop", children=(shell,))
        desktop = PyAtSpiDesktop.__new__(PyAtSpiDesktop)
        desktop._atspi = type("AtSpi", (), {"Registry": FakeRegistry(root)})
        self.assertEqual(desktop.shell_action("applications"), "Anwendungen anzeigen")
        self.assertEqual(action.called, [0])

    def test_real_shell_action_rejects_duplicate_targets_without_invocation(self):
        first = FakeNode("Activities", action=FakeWindowAction(("click",)))
        second = FakeNode("Overview", action=FakeWindowAction(("press",)))
        shell = FakeNode("GNOME Shell", children=(first, second))
        root = FakeNode("Desktop", children=(shell,))
        desktop = PyAtSpiDesktop.__new__(PyAtSpiDesktop)
        desktop._atspi = type("AtSpi", (), {"Registry": FakeRegistry(root)})

        with self.assertRaisesRegex(GnomeAdapterError, "nicht eindeutig"):
            desktop.shell_action("overview")
        self.assertEqual(first.action.called, [])
        self.assertEqual(second.action.called, [])

    def test_real_notification_read_uses_only_visible_notification_roles(self):
        title = FakeNode("Backup complete", role="label")
        duplicate = FakeNode("Backup complete", role="paragraph")
        protected = FakeNode("private detail", role="label", attributes=("secret:true",))
        editable = FakeNode("typed value", role="entry")
        notification = FakeNode(
            "Files", children=(title, duplicate, protected, editable), role="notification"
        )
        calendar = FakeNode("Tuesday 11 August", role="label")
        shell = FakeNode("GNOME Shell", children=(notification, calendar))
        root = FakeNode("Desktop", children=(shell,))
        desktop = PyAtSpiDesktop.__new__(PyAtSpiDesktop)
        desktop._atspi = type(
            "AtSpi", (), {"Registry": FakeRegistry(root), "STATE_SHOWING": "showing"}
        )
        desktop._has_state = lambda node, _state: node is notification
        self.assertEqual(
            desktop.read_notifications(),
            ("Files — Backup complete",),
        )

    def test_real_notification_read_rejects_ambiguous_shell_and_excess_count(self):
        first_shell = FakeNode("GNOME Shell")
        second_shell = FakeNode("gnome-shell")
        root = FakeNode("Desktop", children=(first_shell, second_shell))
        desktop = PyAtSpiDesktop.__new__(PyAtSpiDesktop)
        desktop._atspi = type(
            "AtSpi", (), {"Registry": FakeRegistry(root), "STATE_SHOWING": "showing"}
        )
        with self.assertRaisesRegex(GnomeAdapterError, "nicht eindeutig"):
            desktop.read_notifications()

        notifications = tuple(
            FakeNode(f"Notice {index}", role="notification") for index in range(21)
        )
        shell = FakeNode("GNOME Shell", children=notifications)
        root = FakeNode("Desktop", children=(shell,))
        desktop._atspi = type(
            "AtSpi", (), {"Registry": FakeRegistry(root), "STATE_SHOWING": "showing"}
        )
        desktop._has_state = lambda _node, _state: True
        with self.assertRaisesRegex(GnomeAdapterError, "zu viele"):
            desktop.read_notifications()

    def test_real_notification_dismiss_rebinds_full_order_and_exact_action(self):
        first = FakeNode(
            "First", role="notification", action=FakeWindowAction(("activate", "dismiss"))
        )
        second = FakeNode(
            "Second", role="notification", action=FakeWindowAction(("close",))
        )
        shell = FakeNode("GNOME Shell")
        desktop = PyAtSpiDesktop.__new__(PyAtSpiDesktop)
        snapshots = iter((
            (shell, (first, second)),
            (shell, (first, second)),
            (shell, (second,)),
        ))
        desktop._visible_notifications = lambda: next(snapshots)
        self.assertEqual(desktop.dismiss_notification(1), 1)
        self.assertEqual(first.action.called, [1])
        self.assertEqual(second.action.called, [])

    def test_real_notification_dismiss_rejects_reordered_snapshot_and_wrong_action(self):
        first = FakeNode("First", role="notification", action=FakeWindowAction(("dismiss",)))
        second = FakeNode("Second", role="notification", action=FakeWindowAction(("dismiss",)))
        shell = FakeNode("GNOME Shell")
        desktop = PyAtSpiDesktop.__new__(PyAtSpiDesktop)
        snapshots = iter(((shell, (first, second)), (shell, (second, first))))
        desktop._visible_notifications = lambda: next(snapshots)
        with self.assertRaisesRegex(GnomeAdapterError, "reihenfolge.*geändert"):
            desktop.dismiss_notification(1)
        self.assertEqual(first.action.called, [])
        self.assertEqual(second.action.called, [])

        wrong = FakeNode("Notice", role="notification", action=FakeWindowAction(("activate",)))
        desktop._visible_notifications = lambda: (shell, (wrong,))
        with self.assertRaisesRegex(GnomeAdapterError, "keine eindeutige"):
            desktop.dismiss_notification(1)
        self.assertEqual(wrong.action.called, [])

    def test_real_notification_dismiss_reports_unconfirmed_exact_poststate(self):
        first = FakeNode("First", role="notification", action=FakeWindowAction(("dismiss",)))
        second = FakeNode("Second", role="notification", action=FakeWindowAction(("dismiss",)))
        shell = FakeNode("GNOME Shell")
        desktop = PyAtSpiDesktop.__new__(PyAtSpiDesktop)
        # The wrong remaining object means some mutation happened, but not the
        # exact original sequence minus the selected notification.
        snapshots = iter((
            (shell, (first, second)),
            (shell, (first, second)),
            (shell, (first,)),
        ))
        desktop._visible_notifications = lambda: next(snapshots)
        with patch("clausis.gnome_adapter.time.monotonic", side_effect=(0.0, 2.1)):
            with self.assertRaisesRegex(GnomeAdapterError, "Nachzustand.*nicht bestätigt"):
                desktop.dismiss_notification(1)
        self.assertEqual(first.action.called, [0])
        self.assertEqual(second.action.called, [])

    def test_real_window_cycle_verifies_exact_active_target(self):
        first = FakeCyclingWindow("Erstes Fenster", active=True)
        second = FakeCyclingWindow("Zweites Fenster")
        first.group = second.group = (first, second)
        root = FakeNode("Desktop", children=(FakeNode("App", children=(first, second)),))
        desktop = PyAtSpiDesktop.__new__(PyAtSpiDesktop)
        desktop._atspi = type("AtSpi", (), {
            "Registry": FakeRegistry(root),
            "STATE_ACTIVE": "active",
            "STATE_SHOWING": "showing",
        })
        self.assertEqual(desktop.cycle_window(1), "Zweites Fenster")
        self.assertFalse(first.active)
        self.assertTrue(second.active)
        self.assertEqual(second.focus_calls, 1)

    def test_real_active_window_never_falls_back_to_showing_window(self):
        showing = FakeCyclingWindow("Nur sichtbar")
        root = FakeNode("Desktop", children=(FakeNode("App", children=(showing,)),))
        desktop = PyAtSpiDesktop.__new__(PyAtSpiDesktop)
        desktop._atspi = type("AtSpi", (), {
            "Registry": FakeRegistry(root),
            "STATE_ACTIVE": "active",
            "STATE_SHOWING": "showing",
        })

        with self.assertRaisesRegex(GnomeAdapterError, "aktive GNOME-Fenster.*nicht eindeutig"):
            desktop._active_window()

    def test_real_orientation_allows_only_one_unique_showing_fallback(self):
        showing = FakeCyclingWindow("Nur sichtbar")
        application = FakeNode("App", children=(showing,))
        root = FakeNode("Desktop", children=(application,))
        desktop = PyAtSpiDesktop.__new__(PyAtSpiDesktop)
        desktop._atspi = type("AtSpi", (), {
            "Registry": FakeRegistry(root),
            "STATE_ACTIVE": "active",
            "STATE_SHOWING": "showing",
        })

        self.assertEqual(desktop._orientation_window(), (application, showing))

        second = FakeCyclingWindow("Auch sichtbar")
        root.children = (FakeNode("App", children=(showing, second)),)
        root.childCount = 1
        with self.assertRaisesRegex(GnomeAdapterError, "Orientierung.*nicht eindeutig"):
            desktop._orientation_window()

    def test_real_active_and_orientation_reject_multiple_active_windows(self):
        first = FakeCyclingWindow("Eins", active=True)
        second = FakeCyclingWindow("Zwei", active=True)
        root = FakeNode("Desktop", children=(FakeNode("App", children=(first, second)),))
        desktop = PyAtSpiDesktop.__new__(PyAtSpiDesktop)
        desktop._atspi = type("AtSpi", (), {
            "Registry": FakeRegistry(root),
            "STATE_ACTIVE": "active",
            "STATE_SHOWING": "showing",
        })

        with self.assertRaises(GnomeAdapterError):
            desktop._active_window()
        with self.assertRaises(GnomeAdapterError):
            desktop._orientation_window()

    def test_real_window_cycle_refuses_ambiguous_active_state(self):
        first = FakeCyclingWindow("Erstes Fenster", active=True)
        second = FakeCyclingWindow("Zweites Fenster", active=True)
        first.group = second.group = (first, second)
        root = FakeNode("Desktop", children=(FakeNode("App", children=(first, second)),))
        desktop = PyAtSpiDesktop.__new__(PyAtSpiDesktop)
        desktop._atspi = type("AtSpi", (), {
            "Registry": FakeRegistry(root),
            "STATE_ACTIVE": "active",
            "STATE_SHOWING": "showing",
        })
        with self.assertRaises(GnomeAdapterError):
            desktop.cycle_window(1)
        self.assertEqual(first.focus_calls, 0)
        self.assertEqual(second.focus_calls, 0)

    def test_real_window_cycle_restores_previous_focus_on_mismatch(self):
        first = FakeCyclingWindow("Erstes Fenster", active=True)
        second = FakeCyclingWindow("Zweites Fenster", partial=True)
        first.group = second.group = (first, second)
        root = FakeNode("Desktop", children=(FakeNode("App", children=(first, second)),))
        desktop = PyAtSpiDesktop.__new__(PyAtSpiDesktop)
        desktop._atspi = type("AtSpi", (), {
            "Registry": FakeRegistry(root),
            "STATE_ACTIVE": "active",
            "STATE_SHOWING": "showing",
        })
        with self.assertRaises(GnomeAdapterError):
            desktop.cycle_window(1)
        self.assertTrue(first.active)
        self.assertFalse(second.active)
        self.assertEqual(second.focus_calls, 1)
        self.assertEqual(first.focus_calls, 1)

    def test_real_window_cycle_reports_failed_focus_restoration(self):
        first = FakeCyclingWindow("Erstes Fenster", active=True, accepted=False)
        second = FakeCyclingWindow("Zweites Fenster", partial=True)
        first.group = second.group = (first, second)
        root = FakeNode("Desktop", children=(FakeNode("App", children=(first, second)),))
        desktop = PyAtSpiDesktop.__new__(PyAtSpiDesktop)
        desktop._atspi = type("AtSpi", (), {
            "Registry": FakeRegistry(root),
            "STATE_ACTIVE": "active",
            "STATE_SHOWING": "showing",
        })
        with self.assertRaisesRegex(GnomeAdapterError, "nicht zurückgesetzt"):
            desktop.cycle_window(1)

    def test_real_adapter_ignores_similarly_named_non_shell_control(self):
        control = FakeNode("Activities", action=FakeWindowAction(("click",)))
        other = FakeNode("Browser", children=(control,))
        root = FakeNode("Desktop", children=(other,))
        desktop = PyAtSpiDesktop.__new__(PyAtSpiDesktop)
        desktop._atspi = type("AtSpi", (), {"Registry": FakeRegistry(root)})
        with self.assertRaises(GnomeAdapterError):
            desktop.shell_action("overview")

    def test_real_adapter_selects_exact_quick_settings_control(self):
        action = FakeWindowAction(("toggle",))
        control = FakeNode("Quick Settings", action=action)
        shell = FakeNode("gnome-shell", children=(control,))
        root = FakeNode("Desktop", children=(shell,))
        desktop = PyAtSpiDesktop.__new__(PyAtSpiDesktop)
        desktop._atspi = type("AtSpi", (), {"Registry": FakeRegistry(root)})
        self.assertEqual(desktop.shell_action("quick_settings"), "Quick Settings")
        self.assertEqual(action.called, [0])

    def test_non_semantic_action_still_uses_fixed_command_executor(self):
        broker = ActionBroker(
            self.authority,
            SessionExecutor(
                SafeExecutor(dry_run=True), GnomeSemanticExecutor(self.desktop)
            ),
        )
        result = broker.submit(ActionRequest("audio.volume.up"))
        self.assertEqual(result.status, "dry_run")
        self.assertEqual(result.details["argv"][0], "wpctl")

    def test_semantic_mutation_respects_developer_dry_run(self):
        broker = ActionBroker(
            self.authority,
            SessionExecutor(
                SafeExecutor(dry_run=True), GnomeSemanticExecutor(self.desktop)
            ),
        )
        result = broker.submit(ActionRequest("desktop.window.next"))
        self.assertEqual(result.status, "dry_run")
        self.assertEqual(self.desktop.cycled, [])

    def test_semantic_action_partition_is_complete_and_disjoint(self):
        self.assertTrue(SEMANTIC_READ_ONLY)
        self.assertTrue(SEMANTIC_MUTATIONS)
        self.assertEqual(SEMANTIC_READ_ONLY | SEMANTIC_MUTATIONS, SEMANTIC_ACTIONS)
        self.assertFalse(SEMANTIC_READ_ONLY & SEMANTIC_MUTATIONS)
        self.assertTrue(SEMANTIC_READ_ONLY <= SEMANTIC_ACTIONS)
        self.assertTrue(
            {"desktop.standard_dialog.read", "desktop.notifications.read"}
            <= SEMANTIC_READ_ONLY
        )

    def test_every_semantic_mutation_is_blocked_before_adapter_in_dry_run(self):
        calls = []

        class RecordingSemanticExecutor:
            def execute(self, request, policy):
                calls.append((request, policy))
                return type("Result", (), {"status": "completed"})()

        executor = SessionExecutor(
            SafeExecutor(dry_run=True), RecordingSemanticExecutor()
        )
        for action in sorted(SEMANTIC_MUTATIONS):
            result = executor.execute(ActionRequest(action), None)
            self.assertEqual(result.status, "dry_run", action)
        self.assertEqual(calls, [])

    def test_previously_omitted_text_mutations_are_now_dry_run_guarded(self):
        expected = {
            "desktop.text.delete_previous_word",
            "desktop.text.delete_next_word",
            "desktop.text.replace_previous_word",
            "desktop.text.replace_next_word",
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
            "desktop.text.caret_previous_word",
            "desktop.text.caret_next_word",
            "desktop.text.caret_line_start",
            "desktop.text.caret_line_end",
        }
        self.assertTrue(expected <= SEMANTIC_MUTATIONS)
        self.assertFalse(expected & SEMANTIC_READ_ONLY)

    def test_read_only_semantic_actions_still_reach_adapter_in_dry_run(self):
        calls = []

        class RecordingSemanticExecutor:
            def execute(self, request, policy):
                calls.append(request.action)
                return type("Result", (), {"status": "completed"})()

        executor = SessionExecutor(
            SafeExecutor(dry_run=True), RecordingSemanticExecutor()
        )
        for action in sorted(SEMANTIC_READ_ONLY):
            self.assertEqual(
                executor.execute(ActionRequest(action), None).status,
                "completed",
                action,
            )
        self.assertEqual(calls, sorted(SEMANTIC_READ_ONLY))

    def test_shell_mutations_respect_developer_dry_run(self):
        broker = ActionBroker(
            self.authority,
            SessionExecutor(
                SafeExecutor(dry_run=True), GnomeSemanticExecutor(self.desktop)
            ),
        )
        for action in (
            "desktop.overview",
            "desktop.applications",
            "desktop.quick_settings",
            "desktop.notifications",
        ):
            self.assertEqual(broker.submit(ActionRequest(action)).status, "dry_run")
        self.assertEqual(self.desktop.shell_actions, [])

    def test_text_mutation_respects_developer_dry_run(self):
        broker = ActionBroker(
            self.authority,
            SessionExecutor(
                SafeExecutor(dry_run=True), GnomeSemanticExecutor(self.desktop)
            ),
        )
        request = ActionRequest(
            "desktop.text.set", target="not written", risk=Risk.MEDIUM
        )
        approved = replace(request, capability_token=self.authority.issue(request))
        result = broker.submit(approved)
        self.assertEqual(result.status, "dry_run")
        self.assertNotIn(request.target, result.message)
        self.assertEqual(self.desktop.text_values, [])

    def test_selection_mutation_respects_developer_dry_run(self):
        broker = ActionBroker(
            self.authority,
            SessionExecutor(
                SafeExecutor(dry_run=True), GnomeSemanticExecutor(self.desktop)
            ),
        )
        request = ActionRequest(
            "desktop.selection.select_named", target="Second", risk=Risk.MEDIUM
        )
        approved = replace(request, capability_token=self.authority.issue(request))
        self.assertEqual(broker.submit(approved).status, "dry_run")
        self.assertEqual(self.desktop.selected_items, [])

    def test_file_dialog_selection_respects_developer_dry_run(self):
        broker = ActionBroker(
            self.authority,
            SessionExecutor(
                SafeExecutor(dry_run=True), GnomeSemanticExecutor(self.desktop)
            ),
        )
        request = ActionRequest(
            "desktop.file_dialog.select_visible", target="report.pdf", risk=Risk.MEDIUM
        )
        approved = replace(request, capability_token=self.authority.issue(request))
        self.assertEqual(broker.submit(approved).status, "dry_run")
        self.assertEqual(self.desktop.selected_files, [])

    def test_file_name_entry_respects_developer_dry_run(self):
        broker = ActionBroker(
            self.authority,
            SessionExecutor(
                SafeExecutor(dry_run=True), GnomeSemanticExecutor(self.desktop)
            ),
        )
        request = ActionRequest(
            "desktop.file_dialog.set_name", target="report.pdf", risk=Risk.MEDIUM
        )
        approved = replace(request, capability_token=self.authority.issue(request))
        self.assertEqual(broker.submit(approved).status, "dry_run")
        self.assertEqual(self.desktop.file_names, [])

    def test_file_location_entry_respects_developer_dry_run(self):
        broker = ActionBroker(
            self.authority,
            SessionExecutor(
                SafeExecutor(dry_run=True), GnomeSemanticExecutor(self.desktop)
            ),
        )
        request = ActionRequest(
            "desktop.file_dialog.set_location",
            target="/home/clausis/Documents",
            risk=Risk.MEDIUM,
        )
        approved = replace(request, capability_token=self.authority.issue(request))
        self.assertEqual(broker.submit(approved).status, "dry_run")
        self.assertEqual(self.desktop.file_locations, [])

    def test_folder_navigation_respects_developer_dry_run(self):
        broker = ActionBroker(
            self.authority,
            SessionExecutor(
                SafeExecutor(dry_run=True), GnomeSemanticExecutor(self.desktop)
            ),
        )
        request = ActionRequest(
            "desktop.file_dialog.open_visible_folder",
            target="Documents",
            risk=Risk.MEDIUM,
        )
        approved = replace(request, capability_token=self.authority.issue(request))
        self.assertEqual(broker.submit(approved).status, "dry_run")
        self.assertEqual(self.desktop.opened_folders, [])

    def test_tree_mutation_respects_developer_dry_run(self):
        broker = ActionBroker(
            self.authority,
            SessionExecutor(
                SafeExecutor(dry_run=True), GnomeSemanticExecutor(self.desktop)
            ),
        )
        request = ActionRequest(
            "desktop.tree.expand_named", target="Documents", risk=Risk.MEDIUM
        )
        approved = replace(request, capability_token=self.authority.issue(request))
        self.assertEqual(broker.submit(approved).status, "dry_run")
        self.assertEqual(self.desktop.tree_changes, [])

    def test_table_selection_respects_developer_dry_run(self):
        broker = ActionBroker(
            self.authority,
            SessionExecutor(
                SafeExecutor(dry_run=True), GnomeSemanticExecutor(self.desktop)
            ),
        )
        request = ActionRequest(
            "desktop.table.select_row", target="Quarterly", risk=Risk.MEDIUM
        )
        approved = replace(request, capability_token=self.authority.issue(request))
        self.assertEqual(broker.submit(approved).status, "dry_run")
        self.assertEqual(self.desktop.table_rows, [])

    def test_tab_selection_respects_developer_dry_run(self):
        broker = ActionBroker(
            self.authority,
            SessionExecutor(
                SafeExecutor(dry_run=True), GnomeSemanticExecutor(self.desktop)
            ),
        )
        request = ActionRequest(
            "desktop.tabs.select_named", target="Privacy", risk=Risk.MEDIUM
        )
        approved = replace(request, capability_token=self.authority.issue(request))
        self.assertEqual(broker.submit(approved).status, "dry_run")
        self.assertEqual(self.desktop.tabs, [])

    def test_slider_change_respects_developer_dry_run(self):
        broker = ActionBroker(
            self.authority,
            SessionExecutor(
                SafeExecutor(dry_run=True), GnomeSemanticExecutor(self.desktop)
            ),
        )
        request = ActionRequest(
            "desktop.slider.set_percent",
            target="Zoom",
            arguments={"percent": 60},
            risk=Risk.MEDIUM,
        )
        approved = replace(request, capability_token=self.authority.issue(request))
        self.assertEqual(broker.submit(approved).status, "dry_run")
        self.assertEqual(self.desktop.sliders, [])

    def test_checkbox_and_radio_respect_developer_dry_run(self):
        broker = ActionBroker(
            self.authority,
            SessionExecutor(
                SafeExecutor(dry_run=True), GnomeSemanticExecutor(self.desktop)
            ),
        )
        requests = (
            ActionRequest(
                "desktop.checkbox.set_checked",
                target="Updates",
                arguments={"checked": True},
                risk=Risk.MEDIUM,
            ),
            ActionRequest("desktop.radio.select_named", target="Dark", risk=Risk.MEDIUM),
        )
        for request in requests:
            approved = replace(request, capability_token=self.authority.issue(request))
            self.assertEqual(broker.submit(approved).status, "dry_run")
        self.assertEqual(self.desktop.checkboxes, [])
        self.assertEqual(self.desktop.radios, [])

    def test_switch_change_respects_developer_dry_run(self):
        broker = ActionBroker(
            self.authority,
            SessionExecutor(
                SafeExecutor(dry_run=True), GnomeSemanticExecutor(self.desktop)
            ),
        )
        request = ActionRequest(
            "desktop.switch.set_enabled",
            target="Wi-Fi",
            arguments={"checked": True},
            risk=Risk.MEDIUM,
        )
        approved = replace(request, capability_token=self.authority.issue(request))
        self.assertEqual(broker.submit(approved).status, "dry_run")
        self.assertEqual(self.desktop.switches, [])

    def test_combo_selection_respects_developer_dry_run(self):
        broker = ActionBroker(
            self.authority,
            SessionExecutor(
                SafeExecutor(dry_run=True), GnomeSemanticExecutor(self.desktop)
            ),
        )
        request = ActionRequest(
            "desktop.combo.select_item",
            target="Language",
            arguments={"item": "Deutsch"},
            risk=Risk.MEDIUM,
        )
        approved = replace(request, capability_token=self.authority.issue(request))
        self.assertEqual(broker.submit(approved).status, "dry_run")
        self.assertEqual(self.desktop.combo_items, [])

    def test_spin_button_change_respects_developer_dry_run(self):
        broker = ActionBroker(
            self.authority,
            SessionExecutor(
                SafeExecutor(dry_run=True), GnomeSemanticExecutor(self.desktop)
            ),
        )
        request = ActionRequest(
            "desktop.spin_button.set_value",
            target="Copies",
            arguments={"value": 3.0},
            risk=Risk.MEDIUM,
        )
        approved = replace(request, capability_token=self.authority.issue(request))
        self.assertEqual(broker.submit(approved).status, "dry_run")
        self.assertEqual(self.desktop.spin_values, [])

    def test_menu_item_activation_respects_developer_dry_run(self):
        broker = ActionBroker(
            self.authority,
            SessionExecutor(
                SafeExecutor(dry_run=True), GnomeSemanticExecutor(self.desktop)
            ),
        )
        request = ActionRequest(
            "desktop.menu.activate_item", target="Save", risk=Risk.MEDIUM
        )
        approved = replace(request, capability_token=self.authority.issue(request))
        self.assertEqual(broker.submit(approved).status, "dry_run")
        self.assertEqual(self.desktop.menu_items, [])

    def test_named_focus_respects_developer_dry_run(self):
        broker = ActionBroker(
            self.authority,
            SessionExecutor(
                SafeExecutor(dry_run=True), GnomeSemanticExecutor(self.desktop)
            ),
        )
        result = broker.submit(ActionRequest("desktop.focus.named", target="Details"))
        self.assertEqual(result.status, "dry_run")
        self.assertEqual(self.desktop.named_focuses, [])

    def test_permission_decision_respects_developer_dry_run(self):
        broker = ActionBroker(
            self.authority,
            SessionExecutor(
                SafeExecutor(dry_run=True), GnomeSemanticExecutor(self.desktop)
            ),
        )
        request = ActionRequest(
            "desktop.permission_dialog.decide", target="allow", risk=Risk.MEDIUM
        )
        approved = replace(request, capability_token=self.authority.issue(request))
        self.assertEqual(broker.submit(approved).status, "dry_run")
        self.assertEqual(self.desktop.permission_decisions, [])

    def test_real_current_line_read_uses_exact_single_character_ranges(self):
        desktop = PyAtSpiDesktop.__new__(PyAtSpiDesktop)
        desktop._atspi = type("AtSpi", (), {"STATE_FOCUSED": object()})
        desktop._active_window = lambda: (object(), object())
        node = FakeReadableText("first\nβeta line\nthird", caret_offset=9)
        desktop._find_state = lambda _window, _state: node
        self.assertEqual(desktop.focused_text_line_at_caret(), ("Notes", "βeta line"))
        self.assertEqual(
            node.read_ranges,
            [(8, 9), (7, 8), (6, 7), (5, 6), (9, 10), (10, 11),
             (11, 12), (12, 13), (13, 14), (14, 15), (15, 16)],
        )

    def test_real_line_caret_moves_to_both_boundaries(self):
        desktop = PyAtSpiDesktop.__new__(PyAtSpiDesktop)
        desktop._atspi = type("AtSpi", (), {"STATE_FOCUSED": object()})
        desktop._active_window = lambda: (object(), object())
        for boundary, expected in (("start", 6), ("end", 15)):
            node = FakeReadableText("first\nβeta line\nthird", caret_offset=9)
            desktop._find_state = lambda _window, _state, node=node: node
            self.assertEqual(desktop.move_focused_text_caret_line(boundary), "Notes")
            self.assertEqual(node.caretOffset, expected)

    def test_real_line_operations_reject_unsafe_state_before_reading(self):
        desktop = PyAtSpiDesktop.__new__(PyAtSpiDesktop)
        desktop._atspi = type("AtSpi", (), {"STATE_FOCUSED": object()})
        desktop._active_window = lambda: (object(), object())
        for node in (
            FakeReadableText("private", attributes=("protected:true",), caret_offset=2),
            FakeReadableText("plain", role="push button", caret_offset=2),
            FakeReadableText("x" * 100_001, caret_offset=2),
            FakeReadableText("plain", caret_offset=6),
        ):
            desktop._find_state = lambda _window, _state, node=node: node
            with self.assertRaises(GnomeAdapterError):
                desktop.focused_text_line_at_caret()
            self.assertEqual(node.read_ranges, [])
        selected = FakeReadableText("plain", selections=((0, 1),), caret_offset=2)
        desktop._find_state = lambda _window, _state: selected
        with self.assertRaises(GnomeAdapterError):
            desktop.move_focused_text_caret_line("start")
        self.assertEqual(selected.read_ranges, [])

    def test_real_line_navigation_rolls_back_on_mismatch(self):
        desktop = PyAtSpiDesktop.__new__(PyAtSpiDesktop)
        desktop._atspi = type("AtSpi", (), {"STATE_FOCUSED": object()})
        desktop._active_window = lambda: (object(), object())
        node = FakeReadableText("first\nsecond", caret_offset=9, caret_mismatch_once=True)
        desktop._find_state = lambda _window, _state: node
        with self.assertRaisesRegex(GnomeAdapterError, "nicht bestätigt"):
            desktop.move_focused_text_caret_line("start")
        self.assertEqual(node.caretOffset, 9)

    def test_real_current_line_selection_excludes_newline_and_sets_end_caret(self):
        desktop = PyAtSpiDesktop.__new__(PyAtSpiDesktop)
        desktop._atspi = type("AtSpi", (), {"STATE_FOCUSED": object()})
        desktop._active_window = lambda: (object(), object())
        node = FakeReadableText("first\nβeta line\nthird", caret_offset=9)
        desktop._find_state = lambda _window, _state: node
        self.assertEqual(desktop.select_focused_text_line(), "Notes")
        self.assertEqual(node.selections, ((6, 15),))
        self.assertEqual(node.caretOffset, 15)

    def test_real_current_line_selection_rejects_empty_and_existing_selection(self):
        desktop = PyAtSpiDesktop.__new__(PyAtSpiDesktop)
        desktop._atspi = type("AtSpi", (), {"STATE_FOCUSED": object()})
        desktop._active_window = lambda: (object(), object())
        empty = FakeReadableText("a\n\nb", caret_offset=2)
        desktop._find_state = lambda _window, _state: empty
        with self.assertRaisesRegex(GnomeAdapterError, "leer"):
            desktop.select_focused_text_line()
        self.assertEqual(empty.selections, ())
        selected = FakeReadableText("line", caret_offset=2, selections=((0, 1),))
        desktop._find_state = lambda _window, _state: selected
        with self.assertRaises(GnomeAdapterError):
            desktop.select_focused_text_line()
        self.assertEqual(selected.read_ranges, [])

    def test_real_current_line_selection_rolls_back_on_mismatch(self):
        desktop = PyAtSpiDesktop.__new__(PyAtSpiDesktop)
        desktop._atspi = type("AtSpi", (), {"STATE_FOCUSED": object()})
        desktop._active_window = lambda: (object(), object())
        node = FakeReadableText("first\nsecond", caret_offset=9, selection_mismatch=True)
        desktop._find_state = lambda _window, _state: node
        with self.assertRaisesRegex(GnomeAdapterError, "nicht bestätigt"):
            desktop.select_focused_text_line()
        self.assertEqual(node.selections, ())
        self.assertEqual(node.caretOffset, 9)

    def test_real_current_line_deletion_removes_one_matching_delimiter(self):
        desktop = PyAtSpiDesktop.__new__(PyAtSpiDesktop)
        desktop._atspi = type("AtSpi", (), {"STATE_FOCUSED": object()})
        desktop._active_window = lambda: (object(), object())
        cases = (
            ("first\nsecond\nthird", 8, "first\nthird", 6),
            ("first\nlast", 8, "first", 5),
            ("only", 2, "", 0),
        )
        for original, caret, expected, expected_caret in cases:
            node = FakeReadableText(original, caret_offset=caret)
            desktop._find_state = lambda _window, _state, node=node: node
            self.assertEqual(desktop.delete_focused_text_line(), "Notes")
            self.assertEqual(node.value, expected)
            self.assertEqual(node.caretOffset, expected_caret)
            self.assertEqual(node.selections, ())

    def test_real_current_line_deletion_rejects_empty_and_selected_state(self):
        desktop = PyAtSpiDesktop.__new__(PyAtSpiDesktop)
        desktop._atspi = type("AtSpi", (), {"STATE_FOCUSED": object()})
        desktop._active_window = lambda: (object(), object())
        empty = FakeReadableText("a\n\nb", caret_offset=2)
        desktop._find_state = lambda _window, _state: empty
        with self.assertRaisesRegex(GnomeAdapterError, "leer"):
            desktop.delete_focused_text_line()
        self.assertEqual(empty.value, "a\n\nb")
        selected = FakeReadableText("line", caret_offset=2, selections=((0, 1),))
        desktop._find_state = lambda _window, _state: selected
        with self.assertRaises(GnomeAdapterError):
            desktop.delete_focused_text_line()
        self.assertEqual(selected.read_ranges, [])

    def test_real_current_line_deletion_restores_text_and_caret_on_mismatch(self):
        desktop = PyAtSpiDesktop.__new__(PyAtSpiDesktop)
        desktop._atspi = type("AtSpi", (), {"STATE_FOCUSED": object()})
        desktop._active_window = lambda: (object(), object())
        node = FakeReadableText("first\nsecond\nthird", caret_offset=8, delete_mismatch=True)
        desktop._find_state = lambda _window, _state: node
        with self.assertRaisesRegex(GnomeAdapterError, "nicht bestätigt"):
            desktop.delete_focused_text_line()
        self.assertEqual(node.value, "first\nsecond\nthird")
        self.assertEqual(node.caretOffset, 8)
        self.assertEqual(node.selections, ())

    def test_real_current_line_replacement_preserves_delimiters_and_sets_caret(self):
        desktop = PyAtSpiDesktop.__new__(PyAtSpiDesktop)
        desktop._atspi = type("AtSpi", (), {"STATE_FOCUSED": object()})
        desktop._active_window = lambda: (object(), object())
        node = FakeReadableText("first\nold line\nthird", caret_offset=9)
        desktop._find_state = lambda _window, _state: node
        self.assertEqual(desktop.replace_focused_text_line("neue Zeile"), "Notes")
        self.assertEqual(node.value, "first\nneue Zeile\nthird")
        self.assertEqual(node.caretOffset, 16)
        self.assertEqual(node.selections, ())

    def test_real_current_line_replacement_rejects_unsafe_inputs_before_mutation(self):
        desktop = PyAtSpiDesktop.__new__(PyAtSpiDesktop)
        desktop._atspi = type("AtSpi", (), {"STATE_FOCUSED": object()})
        desktop._active_window = lambda: (object(), object())
        for node, value in (
            (FakeReadableText("line", caret_offset=2), ""),
            (FakeReadableText("line", caret_offset=2), "x" * 501),
            (FakeReadableText("line", caret_offset=2), "line\nbreak"),
            (FakeReadableText("a\n\nb", caret_offset=2), "new"),
            (FakeReadableText("line", caret_offset=2, selections=((0, 1),)), "new"),
            (FakeReadableText("secret", caret_offset=2, attributes=("protected:true",)), "new"),
        ):
            desktop._find_state = lambda _window, _state, node=node: node
            with self.assertRaises(GnomeAdapterError):
                desktop.replace_focused_text_line(value)
            self.assertEqual(node.value, node.value)

    def test_real_current_line_replacement_restores_full_state_on_mismatch(self):
        desktop = PyAtSpiDesktop.__new__(PyAtSpiDesktop)
        desktop._atspi = type("AtSpi", (), {"STATE_FOCUSED": object()})
        desktop._active_window = lambda: (object(), object())
        node = FakeReadableText(
            "first\nold line\nthird", caret_offset=9, set_contents_mismatch=True
        )
        desktop._find_state = lambda _window, _state: node
        with self.assertRaisesRegex(GnomeAdapterError, "nicht bestätigt"):
            desktop.replace_focused_text_line("new")
        self.assertEqual(node.value, "first\nold line\nthird")
        self.assertEqual(node.caretOffset, 9)
        self.assertEqual(node.selections, ())

    def test_real_line_insertions_preserve_current_line_and_set_new_caret(self):
        desktop = PyAtSpiDesktop.__new__(PyAtSpiDesktop)
        desktop._atspi = type("AtSpi", (), {"STATE_FOCUSED": object()})
        desktop._active_window = lambda: (object(), object())
        for direction, expected, expected_caret in (
            ("above", "first\nnew line\nsecond\nthird", 14),
            ("below", "first\nsecond\nnew line\nthird", 21),
        ):
            node = FakeReadableText("first\nsecond\nthird", caret_offset=9)
            desktop._find_state = lambda _window, _state, node=node: node
            self.assertEqual(desktop.insert_focused_text_line(direction, "new line"), "Notes")
            self.assertEqual(node.value, expected)
            self.assertEqual(node.caretOffset, expected_caret)
            self.assertEqual(node.selections, ())

    def test_real_line_insertion_supports_empty_field_and_rejects_unsafe_input(self):
        desktop = PyAtSpiDesktop.__new__(PyAtSpiDesktop)
        desktop._atspi = type("AtSpi", (), {"STATE_FOCUSED": object()})
        desktop._active_window = lambda: (object(), object())
        empty = FakeReadableText("", caret_offset=0)
        desktop._find_state = lambda _window, _state: empty
        self.assertEqual(desktop.insert_focused_text_line("below", "first"), "Notes")
        self.assertEqual((empty.value, empty.caretOffset), ("first", 5))
        for direction, value in (("sideways", "new"), ("above", ""), ("below", "x" * 501), ("above", "two\nlines")):
            node = FakeReadableText("line", caret_offset=2)
            desktop._find_state = lambda _window, _state, node=node: node
            with self.assertRaises(GnomeAdapterError):
                desktop.insert_focused_text_line(direction, value)
            self.assertEqual(node.value, "line")

    def test_real_line_insertion_restores_full_state_on_mismatch(self):
        desktop = PyAtSpiDesktop.__new__(PyAtSpiDesktop)
        desktop._atspi = type("AtSpi", (), {"STATE_FOCUSED": object()})
        desktop._active_window = lambda: (object(), object())
        node = FakeReadableText("first\nsecond", caret_offset=8, set_contents_mismatch=True)
        desktop._find_state = lambda _window, _state: node
        with self.assertRaisesRegex(GnomeAdapterError, "nicht bestätigt"):
            desktop.insert_focused_text_line("above", "new")
        self.assertEqual(node.value, "first\nsecond")
        self.assertEqual(node.caretOffset, 8)

    def test_real_line_duplication_copies_exact_line_above_and_below(self):
        desktop = PyAtSpiDesktop.__new__(PyAtSpiDesktop)
        desktop._atspi = type("AtSpi", (), {"STATE_FOCUSED": object()})
        desktop._active_window = lambda: (object(), object())
        for direction, expected, expected_caret in (
            ("above", "first\nsecond\nsecond\nthird", 12),
            ("below", "first\nsecond\nsecond\nthird", 19),
        ):
            node = FakeReadableText("first\nsecond\nthird", caret_offset=9)
            desktop._find_state = lambda _window, _state, node=node: node
            self.assertEqual(desktop.duplicate_focused_text_line(direction), "Notes")
            self.assertEqual(node.value, expected)
            self.assertEqual(node.caretOffset, expected_caret)
            self.assertEqual(node.selections, ())

    def test_real_line_duplication_rejects_empty_selected_and_invalid_direction(self):
        desktop = PyAtSpiDesktop.__new__(PyAtSpiDesktop)
        desktop._atspi = type("AtSpi", (), {"STATE_FOCUSED": object()})
        desktop._active_window = lambda: (object(), object())
        for node, direction, original in (
            (FakeReadableText("a\n\nb", caret_offset=2), "above", "a\n\nb"),
            (FakeReadableText("line", caret_offset=2, selections=((0, 1),)), "below", "line"),
            (FakeReadableText("line", caret_offset=2), "sideways", "line"),
        ):
            desktop._find_state = lambda _window, _state, node=node: node
            with self.assertRaises(GnomeAdapterError):
                desktop.duplicate_focused_text_line(direction)
            self.assertEqual(node.value, original)

    def test_real_line_duplication_restores_full_state_on_mismatch(self):
        desktop = PyAtSpiDesktop.__new__(PyAtSpiDesktop)
        desktop._atspi = type("AtSpi", (), {"STATE_FOCUSED": object()})
        desktop._active_window = lambda: (object(), object())
        node = FakeReadableText("first\nsecond", caret_offset=8, set_contents_mismatch=True)
        desktop._find_state = lambda _window, _state: node
        with self.assertRaisesRegex(GnomeAdapterError, "nicht bestätigt"):
            desktop.duplicate_focused_text_line("below")
        self.assertEqual(node.value, "first\nsecond")
        self.assertEqual(node.caretOffset, 8)

    def test_real_line_moves_swap_neighbors_and_preserve_relative_caret(self):
        desktop = PyAtSpiDesktop.__new__(PyAtSpiDesktop)
        desktop._atspi = type("AtSpi", (), {"STATE_FOCUSED": object()})
        desktop._active_window = lambda: (object(), object())
        for direction, expected, expected_caret in (
            ("up", "second\nfirst\nthird", 3),
            ("down", "first\nthird\nsecond", 15),
        ):
            node = FakeReadableText("first\nsecond\nthird", caret_offset=9)
            desktop._find_state = lambda _window, _state, node=node: node
            self.assertEqual(desktop.move_focused_text_line(direction), "Notes")
            self.assertEqual(node.value, expected)
            self.assertEqual(node.caretOffset, expected_caret)
            self.assertEqual(node.selections, ())

    def test_real_line_moves_reject_boundaries_selection_and_long_neighbor(self):
        desktop = PyAtSpiDesktop.__new__(PyAtSpiDesktop)
        desktop._atspi = type("AtSpi", (), {"STATE_FOCUSED": object()})
        desktop._active_window = lambda: (object(), object())
        cases = (
            (FakeReadableText("first\nsecond", caret_offset=2), "up"),
            (FakeReadableText("first\nsecond", caret_offset=8), "down"),
            (FakeReadableText("first\nsecond", caret_offset=8, selections=((0, 1),)), "up"),
            (FakeReadableText("x" * 1001 + "\nshort", caret_offset=1003), "up"),
            (FakeReadableText("short\n" + "x" * 1001, caret_offset=2), "down"),
            (FakeReadableText("first\nsecond", caret_offset=8), "sideways"),
        )
        for node, direction in cases:
            original = node.value
            desktop._find_state = lambda _window, _state, node=node: node
            with self.assertRaises(GnomeAdapterError):
                desktop.move_focused_text_line(direction)
            self.assertEqual(node.value, original)

    def test_real_line_move_restores_full_state_on_mismatch(self):
        desktop = PyAtSpiDesktop.__new__(PyAtSpiDesktop)
        desktop._atspi = type("AtSpi", (), {"STATE_FOCUSED": object()})
        desktop._active_window = lambda: (object(), object())
        node = FakeReadableText("first\nsecond\nthird", caret_offset=9, set_contents_mismatch=True)
        desktop._find_state = lambda _window, _state: node
        with self.assertRaisesRegex(GnomeAdapterError, "nicht bestätigt"):
            desktop.move_focused_text_line("up")
        self.assertEqual(node.value, "first\nsecond\nthird")
        self.assertEqual(node.caretOffset, 9)

    def test_real_line_joins_remove_exactly_one_delimiter_and_preserve_caret(self):
        desktop = PyAtSpiDesktop.__new__(PyAtSpiDesktop)
        desktop._atspi = type("AtSpi", (), {"STATE_FOCUSED": object()})
        desktop._active_window = lambda: (object(), object())
        for direction, expected, expected_caret in (
            ("previous", "firstsecond\nthird", 8),
            ("next", "first\nsecondthird", 9),
        ):
            node = FakeReadableText("first\nsecond\nthird", caret_offset=9)
            desktop._find_state = lambda _window, _state, node=node: node
            self.assertEqual(desktop.join_focused_text_line(direction), "Notes")
            self.assertEqual(node.value, expected)
            self.assertEqual(node.caretOffset, expected_caret)
            self.assertEqual(node.selections, ())

    def test_real_line_joins_reject_boundaries_selection_and_long_neighbor(self):
        desktop = PyAtSpiDesktop.__new__(PyAtSpiDesktop)
        desktop._atspi = type("AtSpi", (), {"STATE_FOCUSED": object()})
        desktop._active_window = lambda: (object(), object())
        cases = (
            (FakeReadableText("first\nsecond", caret_offset=2), "previous"),
            (FakeReadableText("first\nsecond", caret_offset=8), "next"),
            (FakeReadableText("first\nsecond", caret_offset=8, selections=((0, 1),)), "previous"),
            (FakeReadableText("x" * 1001 + "\nshort", caret_offset=1003), "previous"),
            (FakeReadableText("short\n" + "x" * 1001, caret_offset=2), "next"),
            (FakeReadableText("first\nsecond", caret_offset=8), "sideways"),
        )
        for node, direction in cases:
            original = node.value
            desktop._find_state = lambda _window, _state, node=node: node
            with self.assertRaises(GnomeAdapterError):
                desktop.join_focused_text_line(direction)
            self.assertEqual(node.value, original)

    def test_real_line_join_restores_full_state_on_mismatch(self):
        desktop = PyAtSpiDesktop.__new__(PyAtSpiDesktop)
        desktop._atspi = type("AtSpi", (), {"STATE_FOCUSED": object()})
        desktop._active_window = lambda: (object(), object())
        node = FakeReadableText("first\nsecond\nthird", caret_offset=9, delete_mismatch=True)
        desktop._find_state = lambda _window, _state: node
        with self.assertRaisesRegex(GnomeAdapterError, "nicht bestätigt"):
            desktop.join_focused_text_line("previous")
        self.assertEqual(node.value, "first\nsecond\nthird")
        self.assertEqual(node.caretOffset, 9)

    def test_real_line_split_inserts_exactly_one_newline_and_advances_caret(self):
        desktop = PyAtSpiDesktop.__new__(PyAtSpiDesktop)
        desktop._atspi = type("AtSpi", (), {"STATE_FOCUSED": object()})
        desktop._active_window = lambda: (object(), object())
        for value, caret, expected in (
            ("first second", 5, "first\n second"),
            ("first", 0, "\nfirst"),
            ("first", 5, "first\n"),
            ("", 0, "\n"),
        ):
            node = FakeReadableText(value, caret_offset=caret)
            desktop._find_state = lambda _window, _state, node=node: node
            self.assertEqual(desktop.split_focused_text_line(), "Notes")
            self.assertEqual(node.value, expected)
            self.assertEqual(node.caretOffset, caret + 1)
            self.assertEqual(node.selections, ())

    def test_real_line_split_rejects_selection_and_restores_on_mismatch(self):
        desktop = PyAtSpiDesktop.__new__(PyAtSpiDesktop)
        desktop._atspi = type("AtSpi", (), {"STATE_FOCUSED": object()})
        desktop._active_window = lambda: (object(), object())
        selected = FakeReadableText("first second", caret_offset=5, selections=((0, 1),))
        desktop._find_state = lambda _window, _state: selected
        with self.assertRaises(GnomeAdapterError):
            desktop.split_focused_text_line()
        self.assertEqual(selected.value, "first second")

        mismatch = FakeReadableText("first second", caret_offset=5, insert_mismatch=True)
        desktop._find_state = lambda _window, _state: mismatch
        with self.assertRaisesRegex(GnomeAdapterError, "nicht best\u00e4tigt"):
            desktop.split_focused_text_line()
        self.assertEqual(mismatch.value, "first second")
        self.assertEqual(mismatch.caretOffset, 5)

    def test_real_line_indent_inserts_four_spaces_and_preserves_logical_caret(self):
        desktop = PyAtSpiDesktop.__new__(PyAtSpiDesktop)
        desktop._atspi = type("AtSpi", (), {"STATE_FOCUSED": object()})
        desktop._active_window = lambda: (object(), object())
        node = FakeReadableText("first\nsecond\nthird", caret_offset=9)
        desktop._find_state = lambda _window, _state: node
        self.assertEqual(desktop.indent_focused_text_line("indent"), "Notes")
        self.assertEqual(node.value, "first\n    second\nthird")
        self.assertEqual(node.caretOffset, 13)
        self.assertEqual(node.selections, ())

    def test_real_line_outdent_removes_tab_or_up_to_four_spaces(self):
        desktop = PyAtSpiDesktop.__new__(PyAtSpiDesktop)
        desktop._atspi = type("AtSpi", (), {"STATE_FOCUSED": object()})
        desktop._active_window = lambda: (object(), object())
        for value, caret, expected, expected_caret in (
            ("first\n    second\nthird", 12, "first\nsecond\nthird", 8),
            ("first\n  second\nthird", 10, "first\nsecond\nthird", 8),
            ("first\n\tsecond\nthird", 9, "first\nsecond\nthird", 8),
            ("first\n    second\nthird", 7, "first\nsecond\nthird", 6),
        ):
            node = FakeReadableText(value, caret_offset=caret)
            desktop._find_state = lambda _window, _state, node=node: node
            self.assertEqual(desktop.indent_focused_text_line("outdent"), "Notes")
            self.assertEqual(node.value, expected)
            self.assertEqual(node.caretOffset, expected_caret)
            self.assertEqual(node.selections, ())

    def test_real_line_indentation_rejects_invalid_state_and_rolls_back(self):
        desktop = PyAtSpiDesktop.__new__(PyAtSpiDesktop)
        desktop._atspi = type("AtSpi", (), {"STATE_FOCUSED": object()})
        desktop._active_window = lambda: (object(), object())
        cases = (
            (FakeReadableText("plain", caret_offset=2), "outdent"),
            (FakeReadableText("plain", caret_offset=2, selections=((0, 1),)), "indent"),
            (FakeReadableText("x" * 997, caret_offset=2), "indent"),
            (FakeReadableText("plain", caret_offset=2), "sideways"),
        )
        for node, direction in cases:
            original = node.value
            desktop._find_state = lambda _window, _state, node=node: node
            with self.assertRaises(GnomeAdapterError):
                desktop.indent_focused_text_line(direction)
            self.assertEqual(node.value, original)

        mismatch = FakeReadableText("  second", caret_offset=4, delete_mismatch=True)
        desktop._find_state = lambda _window, _state: mismatch
        with self.assertRaisesRegex(GnomeAdapterError, "nicht best\u00e4tigt"):
            desktop.indent_focused_text_line("outdent")
        self.assertEqual(mismatch.value, "  second")
        self.assertEqual(mismatch.caretOffset, 4)


if __name__ == "__main__":
    unittest.main()
