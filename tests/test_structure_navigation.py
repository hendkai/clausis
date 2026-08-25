"""Structure navigation (heading/link/list/landmark) against fake trees.

These tests drive the real :class:`PyAtSpiDesktop` logic by injecting a
stand-in ``pyatspi`` module (same harness as the dictation tests).  The
 GTK probe app cannot provide headings or links — GTK exposes none of its
 widgets with those roles — so the fake tree is the honest place to verify
 the matching itself; the real-bus coverage of the list unit lives in the
 GTK session smoke (``tests/fixtures/atspi_session_client.py``).
"""

from __future__ import annotations

import unittest

from clausis.broker import ActionBroker, SafeExecutor
from clausis.capabilities import CapabilityAuthority
from clausis.executors import SessionExecutor, unadapted_actions
from clausis.gnome_adapter import (
    GnomeAdapterError,
    GnomeSemanticExecutor,
    PyAtSpiDesktop,
    SEMANTIC_ACTIONS,
    SEMANTIC_MUTATIONS,
)
from clausis.models import ActionRequest
from clausis.policy import ACTION_POLICIES, evaluate
from clausis.router import OfflineRouter

from tests.test_dictation import (
    DesktopHarness,
    FakeNode,
    STATE_ACTIVE,
    STATE_FOCUSED,
    STATE_SHOWING,
)


def build_structure_desktop(*children):
    """Window whose children appear in walk order (matches = tree order).

    ``build_structure_desktop(field, first, second)`` puts the focused
    field first, so a forward jump finds ``first``; reversing the order
    exercises backward jumps and exhausted directions.
    """

    window = FakeNode("Dokument", "frame", {STATE_SHOWING, STATE_ACTIVE}, list(children))
    application = FakeNode("Editor", "application", set(), [window])
    return FakeNode("desktop", "desktop frame", set(), [application])


def focused_field():
    return FakeNode("Eingabefeld", "text", {STATE_SHOWING, STATE_FOCUSED})


class LandmarkNode(FakeNode):
    """A node whose object attributes carry the ``xml-roles`` value.

    Browsers publish the ARIA role there; both the mapping shape and the
    legacy list of ``key:value`` strings occur in the wild, so the tests
    cover both.
    """

    def __init__(self, name, xml_roles, **kwargs):
        super().__init__(name, "panel", {STATE_SHOWING}, **kwargs)
        if isinstance(xml_roles, dict):
            self._attributes = xml_roles
        else:
            self._attributes = list(xml_roles)

    def getAttributes(self):
        return self._attributes


class JumpTargetTests(DesktopHarness):
    def test_next_heading_is_focused_and_announced_with_name(self):
        heading = FakeNode("Einstellungen", "heading", {STATE_SHOWING})
        desktop = self.desktop_for(build_structure_desktop(focused_field(), heading))
        spoken = desktop.jump_to_structure("heading", backward=False)
        self.assertTrue(heading.focused)
        self.assertIn("Überschrift", spoken)
        self.assertIn("Einstellungen", spoken)

    def test_next_link_is_focused_but_never_activated(self):
        link = FakeNode("Weitere Informationen", "link", {STATE_SHOWING})
        desktop = self.desktop_for(build_structure_desktop(focused_field(), link))
        spoken = desktop.jump_to_structure("link", backward=False)
        self.assertTrue(link.focused)
        self.assertIn("Link", spoken)
        self.assertIn("Weitere Informationen", spoken)

    def test_next_list_matches_the_list_role(self):
        listing = FakeNode("Dateien", "list", {STATE_SHOWING})
        desktop = self.desktop_for(build_structure_desktop(focused_field(), listing))
        spoken = desktop.jump_to_structure("list", backward=False)
        self.assertTrue(listing.focused)
        self.assertIn("Liste", spoken)
        self.assertIn("Dateien", spoken)

    def test_previous_heading_lands_on_the_last_element_before_the_focus(self):
        first = FakeNode("Anfang", "heading", {STATE_SHOWING})
        second = FakeNode("Mitte", "heading", {STATE_SHOWING})
        field = focused_field()
        # Walk order = child order: both headings sit before the focus.
        desktop = self.desktop_for(
            build_structure_desktop(first, second, field)
        )
        spoken = desktop.jump_to_structure("heading", backward=True)
        self.assertTrue(second.focused)
        self.assertFalse(first.focused)
        self.assertIn("Mitte", spoken)

    def test_repeated_next_jumps_advance_instead_of_repeating(self):
        field = focused_field()
        first = FakeNode("Anfang", "heading", {STATE_SHOWING})
        second = FakeNode("Mitte", "heading", {STATE_SHOWING})
        third = FakeNode("Ende", "heading", {STATE_SHOWING})
        desktop = self.desktop_for(build_structure_desktop(field, first, second, third))
        desktop.jump_to_structure("heading", backward=False)
        # A real bus moves STATE_FOCUSED with the focus grab; the fake only
        # sets the flag, so the test mirrors the bus behaviour by hand.
        first.states.add(STATE_FOCUSED)
        field.states.discard(STATE_FOCUSED)
        first.focused = False
        spoken = desktop.jump_to_structure("heading", backward=False)
        self.assertTrue(second.focused)
        self.assertFalse(first.focused)
        self.assertIn("Mitte", spoken)

    def test_landmark_matches_xml_roles_object_attribute(self):
        region = LandmarkNode("Hauptbereich", {"xml-roles": "main"})
        desktop = self.desktop_for(build_structure_desktop(focused_field(), region))
        spoken = desktop.jump_to_structure("landmark", backward=False)
        self.assertTrue(region.focused)
        self.assertIn("main", spoken)
        self.assertIn("Hauptbereich", spoken)

    def test_landmark_also_matches_the_legacy_attribute_list_shape(self):
        navigation = LandmarkNode("Navigation", ["xml-roles:navigation"])
        desktop = self.desktop_for(build_structure_desktop(focused_field(), navigation))
        spoken = desktop.jump_to_structure("landmark", backward=False)
        self.assertTrue(navigation.focused)
        self.assertIn("navigation", spoken)

    def test_non_landmark_xml_roles_do_not_match(self):
        article = LandmarkNode("Artikel", {"xml-roles": "article"})
        desktop = self.desktop_for(build_structure_desktop(focused_field(), article))
        with self.assertRaisesRegex(GnomeAdapterError, "(?i)keine Landmarken"):
            desktop.jump_to_structure("landmark", backward=False)
        self.assertFalse(article.focused)

    def test_a_later_landmark_token_is_recognised_despite_inherited_roles(self):
        node = LandmarkNode("Bereich", {"xml-roles": "article navigation"})
        desktop = self.desktop_for(build_structure_desktop(focused_field(), node))
        spoken = desktop.jump_to_structure("landmark", backward=False)
        self.assertIn("navigation", spoken)


class HonestRefusalTests(DesktopHarness):
    def test_no_structure_in_a_plain_gtk_window_refuses_without_moving(self):
        field = focused_field()
        desktop = self.desktop_for(build_structure_desktop(field))
        for unit, word in (
            ("heading", "Überschriften"),
            ("link", "Links"),
            ("list", "Listen"),
            ("landmark", "Landmarken"),
        ):
            with self.subTest(unit=unit):
                with self.assertRaisesRegex(GnomeAdapterError, word):
                    desktop.jump_to_structure(unit, backward=False)
        self.assertTrue(field.focused is False)

    def test_exhausted_direction_refuses_and_keeps_the_position(self):
        field = focused_field()
        heading = FakeNode("Anfang", "heading", {STATE_SHOWING})
        desktop = self.desktop_for(build_structure_desktop(field, heading))
        desktop.jump_to_structure("heading", backward=False)
        # Mirror the bus: STATE_FOCUSED follows the grab.
        heading.states.add(STATE_FOCUSED)
        field.states.discard(STATE_FOCUSED)
        with self.assertRaisesRegex(GnomeAdapterError, "Keine weiteren"):
            desktop.jump_to_structure("heading", backward=False)

    def test_backward_before_the_first_element_refuses(self):
        heading = FakeNode("Anfang", "heading", {STATE_SHOWING})
        desktop = self.desktop_for(
            build_structure_desktop(focused_field(), heading)
        )
        with self.assertRaisesRegex(GnomeAdapterError, "vor dieser Stelle"):
            desktop.jump_to_structure("heading", backward=True)

    def test_a_widget_that_rejects_the_focus_fails_honestly(self):
        stubborn = FakeNode("Stur", "list", {STATE_SHOWING}, focus_accepts=False)
        desktop = self.desktop_for(build_structure_desktop(focused_field(), stubborn))
        with self.assertRaisesRegex(GnomeAdapterError, "Fokus"):
            desktop.jump_to_structure("list", backward=False)

    def test_unknown_unit_is_refused(self):
        desktop = self.desktop_for(build_structure_desktop(focused_field()))
        with self.assertRaisesRegex(GnomeAdapterError, "Unbekannte Struktureinheit"):
            desktop.jump_to_structure("table", backward=False)


class RegistrationTests(unittest.TestCase):
    def test_structure_jump_is_registered_read_only_everywhere(self):
        self.assertIn("structure.jump", SEMANTIC_ACTIONS)
        self.assertNotIn("structure.jump", SEMANTIC_MUTATIONS)
        self.assertIn("structure.jump", ACTION_POLICIES)
        self.assertEqual(unadapted_actions(), frozenset())

    def test_router_builds_both_directions_and_all_units(self):
        router = OfflineRouter()
        cases = [
            ("nächste überschrift", "heading", False),
            ("nächster link", "link", False),
            ("nächste liste", "list", False),
            ("nächste landmarke", "landmark", False),
            ("vorherige überschrift", "heading", True),
            ("vorheriger link", "link", True),
            ("vorherige liste", "list", True),
            ("vorherige landmarke", "landmark", True),
            ("next heading", "heading", False),
            ("previous link", "link", True),
            ("next list", "list", False),
            ("previous landmark", "landmark", True),
        ]
        for phrase, unit, backward in cases:
            with self.subTest(phrase=phrase):
                request = router.route(phrase)
                self.assertIsNotNone(request, phrase)
                assert request is not None  # narrow for the type checker
                self.assertEqual(request.action, "structure.jump")
                self.assertEqual(
                    request.arguments, {"unit": unit, "backward": backward}
                )

    def test_counter_words_are_not_part_of_v1(self):
        router = OfflineRouter()
        self.assertIsNone(router.route("drei überschriften weiter"))
        self.assertIsNone(router.route("two headings further"))

    def test_policy_rejects_target_text_and_bad_values(self):
        for arguments, target in (
            ({"unit": "heading", "backward": False}, "beliebiger text"),
            ({"unit": "table", "backward": False}, ""),
            ({"unit": "heading", "backward": "ja", }, ""),
            ({"unit": "heading"}, ""),
        ):
            with self.subTest(arguments=arguments, target=target):
                request = ActionRequest(
                    "structure.jump", target=target, arguments=arguments
                )
                with self.assertRaises(ValueError):
                    evaluate(request)

    def test_valid_request_passes_the_policy(self):
        request = ActionRequest(
            "structure.jump", arguments={"unit": "heading", "backward": False}
        )
        decision = evaluate(request)
        self.assertTrue(decision.allowed)
        self.assertFalse(decision.confirmation_required)
        self.assertEqual(decision.policy.minimum_risk.name, "LOW")


class ExecutionTests(unittest.TestCase):
    def _broker(self, desktop):
        authority = CapabilityAuthority(b"s" * 32)
        executor = SessionExecutor(
            SafeExecutor(dry_run=False), GnomeSemanticExecutor(desktop)
        )
        return ActionBroker(authority, executor)

    def test_end_to_end_request_announces_the_heading(self):
        class HeadingDesktop:
            def jump_to_structure(self, unit, backward):
                return "Überschrift Einstellungen."

        broker = self._broker(HeadingDesktop())
        result = broker.submit(
            ActionRequest(
                "structure.jump", arguments={"unit": "heading", "backward": False}
            )
        )
        self.assertEqual(result.status, "completed")
        self.assertIn("Einstellungen", result.message)

    def test_end_to_end_refusal_is_a_failed_result_not_a_crash(self):
        class EmptyDesktop:
            def jump_to_structure(self, unit, backward):
                raise GnomeAdapterError(
                    "In diesem Fenster gibt es keine Überschriften."
                )

        broker = self._broker(EmptyDesktop())
        result = broker.submit(
            ActionRequest(
                "structure.jump", arguments={"unit": "heading", "backward": False}
            )
        )
        self.assertEqual(result.status, "failed")
        self.assertIn("keine Überschriften", result.message)

    def test_dry_run_still_executes_the_read_only_jump(self):
        class HeadingDesktop:
            def jump_to_structure(self, unit, backward):
                return "Überschrift Einstellungen."

        authority = CapabilityAuthority(b"s" * 32)
        broker = ActionBroker(
            authority,
            SessionExecutor(
                SafeExecutor(dry_run=True), GnomeSemanticExecutor(HeadingDesktop())
            ),
        )
        result = broker.submit(
            ActionRequest(
                "structure.jump", arguments={"unit": "heading", "backward": False}
            )
        )
        self.assertEqual(result.status, "completed")


if __name__ == "__main__":
    unittest.main()
