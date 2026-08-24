"""File chooser navigation, driven against a fake accessibility tree.

The safety property under test: nothing a voice user says in a file dialog can
open or run a file.  Listing is read-only, selecting only moves focus, and
opening a folder is restricted to sidebar tree items — because AT-SPI cannot
prove that a row inside the file grid is a folder rather than a file.
"""

from __future__ import annotations

import unittest
from dataclasses import replace

from clausis.broker import ActionBroker, SafeExecutor
from clausis.capabilities import CapabilityAuthority
from clausis.executors import SessionExecutor
from clausis.gnome_adapter import GnomeAdapterError, GnomeSemanticExecutor
from clausis.models import ActionRequest, Risk
from clausis.policy import evaluate
from clausis.router import OfflineRouter

from tests.test_dictation import (
    STATE_ACTIVE,
    STATE_SHOWING,
    DesktopHarness,
    FakeNode,
)
from tests.test_dialogs import FakeButton


class ActivatableEntry(FakeNode):
    """A sidebar tree item or grid row with a real AT-SPI action."""

    def __init__(self, name, role, *, accept=True):
        super().__init__(name, role, {STATE_SHOWING})
        self.pressed = 0
        self._accepts = accept

    def queryAction(self):
        entry = self

        class Action:
            nActions = 1

            def getName(self, index):
                return "activate"

            def doAction(self, index):
                if not entry._accepts:
                    return False
                entry.pressed += 1
                return True

        return Action()


def file_dialog(children):
    window = FakeNode(
        "Datei öffnen", "file chooser", {STATE_SHOWING, STATE_ACTIVE}, children
    )
    application = FakeNode("Anwendung", "application", set(), [window])
    return FakeNode("desktop", "desktop frame", set(), [application])


def sidebar():
    return FakeNode(
        "Seitenleiste",
        "panel",
        {STATE_SHOWING},
        [
            ActivatableEntry("Persönlicher Ordner", "tree item"),
            ActivatableEntry("Dokumente", "tree item"),
            ActivatableEntry("Bilder", "tree item"),
        ],
    )


def grid():
    return FakeNode(
        "Dateien",
        "grid",
        {STATE_SHOWING},
        [
            FakeNode("Urlaub", "grid child", {STATE_SHOWING}),
            ActivatableEntry("Bericht.pdf", "grid child"),
            ActivatableEntry("Foto.png", "grid child"),
        ],
    )


class FileListTests(DesktopHarness):
    def test_entries_are_listed_numbered_and_in_walk_order(self):
        desktop = self.desktop_for(file_dialog([sidebar(), grid()]))
        spoken = desktop.list_files()
        self.assertIn("Nummer 1: Persönlicher Ordner", spoken)
        self.assertIn("Nummer 2: Dokumente", spoken)
        self.assertIn("Nummer 3: Bilder", spoken)
        self.assertIn("Urlaub", spoken)
        self.assertIn("Bericht.pdf", spoken)

    def test_listing_activates_nothing(self):
        side, files = sidebar(), grid()
        desktop = self.desktop_for(file_dialog([side, files]))
        desktop.list_files()
        for node in (*side.children, *files.children):
            if isinstance(node, ActivatableEntry):
                self.assertEqual(node.pressed, 0)

    def test_a_dialog_without_entries_is_reported(self):
        desktop = self.desktop_for(file_dialog([]))
        with self.assertRaisesRegex(GnomeAdapterError, "keine zugänglichen Einträge"):
            desktop.list_files()

    def test_only_a_file_chooser_counts(self):
        desktop = self.desktop_for(
            file_dialog([FakeButton("OK")])
        )
        # rebuild with a plain dialog role: the same walk must refuse
        window = FakeNode(
            "Nachricht", "dialog", {STATE_SHOWING, STATE_ACTIVE}, [FakeButton("OK")]
        )
        application = FakeNode("Anwendung", "application", set(), [window])
        desktop = self.desktop_for(FakeNode("desktop", "desktop frame", set(), [application]))
        with self.assertRaisesRegex(GnomeAdapterError, "kein Dateidialog"):
            desktop.list_files()


class FileSelectTests(DesktopHarness):
    def test_selecting_focuses_without_committing(self):
        files = grid()
        desktop = self.desktop_for(file_dialog([sidebar(), files]))
        name = desktop.select_file(5)
        self.assertEqual(name, "Bericht.pdf")
        for child in files.children:
            if isinstance(child, ActivatableEntry):
                self.assertEqual(child.pressed, 0)

    def test_out_of_range_numbers_are_refused(self):
        desktop = self.desktop_for(file_dialog([sidebar()]))
        with self.assertRaisesRegex(GnomeAdapterError, "außerhalb"):
            desktop.select_file(0)
        with self.assertRaisesRegex(GnomeAdapterError, "nicht vorhanden"):
            desktop.select_file(9)

    def test_entry_that_refuses_focus_is_reported(self):
        stubborn = FakeNode("Eigen", "grid child", {STATE_SHOWING}, focus_accepts=False)
        container = FakeNode("Dateien", "grid", {STATE_SHOWING}, [stubborn])
        desktop = self.desktop_for(file_dialog([container]))
        with self.assertRaisesRegex(GnomeAdapterError, "fokussieren"):
            desktop.select_file(1)


class FolderOpenTests(DesktopHarness):
    def test_sidebar_folder_is_opened_through_its_own_action(self):
        side = sidebar()
        desktop = self.desktop_for(file_dialog([side]))
        name = desktop.open_folder(2)
        self.assertEqual(name, "Dokumente")
        self.assertEqual(side.children[1].pressed, 1)
        self.assertEqual(side.children[0].pressed, 0)

    def test_a_grid_row_is_never_activated_even_with_the_right_number(self):
        files = grid()
        desktop = self.desktop_for(file_dialog([sidebar(), files]))
        # Number 4 is the "Urlaub" grid row — AT-SPI cannot prove it is a
        # folder, so it must be refused, not opened.
        with self.assertRaisesRegex(GnomeAdapterError, "kein nachweisbarer Ordner"):
            desktop.open_folder(4)
        for child in files.children:
            if isinstance(child, ActivatableEntry):
                self.assertEqual(child.pressed, 0)

    def test_a_list_item_is_not_treated_as_a_provable_folder(self):
        # GTK file lists in list mode expose plain files as list items; only
        # tree items from the sidebar are provable folders.
        listing = FakeNode(
            "Dateiliste",
            "list",
            {STATE_SHOWING},
            [ActivatableEntry("Bericht.pdf", "list item")],
        )
        desktop = self.desktop_for(file_dialog([listing]))
        with self.assertRaisesRegex(GnomeAdapterError, "kein nachweisbarer Ordner"):
            desktop.open_folder(1)

    def test_entry_without_action_is_reported(self):
        plain = FakeNode("Ohne", "tree item", {STATE_SHOWING})
        desktop = self.desktop_for(file_dialog([plain]))
        with self.assertRaisesRegex(GnomeAdapterError, "lässt sich nicht öffnen"):
            desktop.open_folder(1)

    def test_folder_that_refuses_the_action_is_reported(self):
        stubborn = ActivatableEntry("Sperrig", "tree item", accept=False)
        desktop = self.desktop_for(file_dialog([stubborn]))
        with self.assertRaisesRegex(GnomeAdapterError, "lässt sich nicht öffnen"):
            desktop.open_folder(1)


class FileDialogPolicyTests(unittest.TestCase):
    def setUp(self):
        self.authority = CapabilityAuthority(b"f" * 32)

    def _broker(self, desktop):
        return ActionBroker(
            self.authority,
            SessionExecutor(SafeExecutor(dry_run=False), GnomeSemanticExecutor(desktop)),
        )

    def test_navigation_stays_low_risk_and_immediate(self):
        for action, target in (
            ("dialog.file.list", ""),
            ("dialog.file.select", "3"),
            ("dialog.folder.open", "2"),
        ):
            with self.subTest(action=action):
                decision = evaluate(ActionRequest(action, target))
                self.assertFalse(decision.confirmation_required)

    def test_select_rejects_a_non_number_target(self):
        for target in ("", "eins", "0", "21", "999", "-1"):
            with self.subTest(target=target):
                with self.assertRaises(ValueError):
                    evaluate(ActionRequest("dialog.file.select", target))

    def test_folder_open_rejects_a_non_number_target(self):
        with self.assertRaises(ValueError):
            evaluate(ActionRequest("dialog.folder.open", target="Dokumente"))

    def test_committing_stays_medium_risk(self):
        decision = evaluate(ActionRequest("dialog.accept", risk=Risk.MEDIUM))
        self.assertTrue(decision.confirmation_required)

    def test_spoken_commands_route_to_the_file_dialog_actions(self):
        router = OfflineRouter()
        cases = {
            "liste dateien auf": "dialog.file.list",
            "was ist im dateidialog": "dialog.file.list",
            "welche dateien gibt es": "dialog.file.list",
            "zeige die dateien": "dialog.file.list",
            "list files": "dialog.file.list",
            "wähle datei drei": "dialog.file.select",
            "select file three": "dialog.file.select",
            "öffne ordner zwei": "dialog.folder.open",
            "open folder two": "dialog.folder.open",
        }
        for spoken, action in cases.items():
            with self.subTest(spoken=spoken):
                request = router.route(spoken)
                self.assertTrue(request is not None and request.action == action, spoken)

    def test_bare_folder_number_still_means_generic_control_activation(self):
        request = OfflineRouter().route("nummer zwei")
        self.assertTrue(request is not None and request.action == "desktop.control.activate")

    def test_select_reaches_the_adapter_without_confirmation(self):
        class Recorder:
            def __init__(self):
                self.selected = []

            def select_file(self, number):
                self.selected.append(number)
                return "Bericht.pdf"

        recorder = Recorder()
        result = self._broker(recorder).submit(ActionRequest("dialog.file.select", "3"))
        self.assertEqual(result.status, "completed")
        self.assertEqual(recorder.selected, [3])
        self.assertIn("Bericht.pdf", result.message)

    def test_folder_open_reaches_the_adapter_without_confirmation(self):
        class Recorder:
            def __init__(self):
                self.opened = []

            def open_folder(self, number):
                self.opened.append(number)
                return "Dokumente"

        recorder = Recorder()
        result = self._broker(recorder).submit(ActionRequest("dialog.folder.open", "2"))
        self.assertEqual(result.status, "completed")
        self.assertEqual(recorder.opened, [2])
        self.assertIn("Dokumente", result.message)

    def test_accept_still_needs_a_capability(self):
        class Recorder:
            def __init__(self):
                self.accepted = 0

            def accept_dialog(self):
                self.accepted += 1
                return "Öffnen"

        recorder = Recorder()
        request = ActionRequest("dialog.accept", risk=Risk.MEDIUM)
        self.assertEqual(self._broker(recorder).submit(request).status, "confirmation_required")
        self.assertEqual(recorder.accepted, 0)
        approved = replace(request, capability_token=self.authority.issue(request))
        self.assertEqual(self._broker(recorder).submit(approved).status, "completed")
        self.assertEqual(recorder.accepted, 1)


if __name__ == "__main__":
    unittest.main()
