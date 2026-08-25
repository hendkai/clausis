"""Correction slot — „nein, ich meinte …" replaces the last dictation.

The voice-only editing loop needs a correction that does not append: the
remembered span of the last dictation in the focused field is selected
through the AT-SPI text interface and replaced.  The properties under test
are the honesty rules — no memory, focus change, field edits under the hand
and missing selection interfaces all refuse instead of guessing — plus the
router placement (the correction trigger wins over every dictation verb)
and the payload contract (printable-only, ≤512, control bytes refuse).
"""

from __future__ import annotations

import unittest

from clausis.broker import ActionBroker, SafeExecutor
from clausis.capabilities import CapabilityAuthority
from clausis.executors import SessionExecutor, unadapted_actions
from clausis.gnome_adapter import GnomeAdapterError, GnomeSemanticExecutor, PyAtSpiDesktop
from clausis.models import ActionRequest, Origin, Risk
from clausis.policy import ACTION_POLICIES, evaluate
from clausis.router import OfflineRouter

from tests.test_dictation import (
    STATE_ACTIVE,
    STATE_EDITABLE,
    STATE_FOCUSED,
    STATE_SHOWING,
    DesktopHarness,
    FakeNode,
    build_desktop,
    fake_pyatspi,
)
from tests.test_text_editing import SelectableField


class CorrectionRoutingTests(unittest.TestCase):
    def test_german_trigger_replaces_instead_of_appending(self):
        request = OfflineRouter().route("nein ich meinte Hendrik Kaiser")
        self.assertIsNotNone(request)
        self.assertEqual(request.action, "text.replace_last_dictation")
        self.assertEqual(request.target, "Hendrik Kaiser")

    def test_german_trigger_tolerates_comma_and_colon(self):
        for utterance in ("Nein, ich meinte guten Tag", "Nein, ich meinte: guten Tag"):
            with self.subTest(utterance=utterance):
                request = OfflineRouter().route(utterance)
                self.assertIsNotNone(request)
                self.assertEqual(request.action, "text.replace_last_dictation")
                self.assertEqual(request.target, "guten Tag")

    def test_english_trigger_routes(self):
        request = OfflineRouter().route("no i meant good morning")
        self.assertIsNotNone(request)
        self.assertEqual(request.action, "text.replace_last_dictation")
        self.assertEqual(request.target, "good morning")

    def test_correction_wins_over_the_dictation_verbs(self):
        # "nein, ich meinte diktiere foo" must correct, not append: the
        # pattern sits before every dictation verb, so the trailing verb is
        # payload, not a trigger.
        request = OfflineRouter().route("nein ich meinte diktiere foo")
        self.assertIsNotNone(request)
        self.assertEqual(request.action, "text.replace_last_dictation")
        self.assertEqual(request.target, "diktiere foo")

    def test_control_bytes_in_the_payload_refuse_before_any_adapter(self):
        self.assertIsNone(OfflineRouter().route("nein ich meinte poison\u0000ed"))
        self.assertIsNone(OfflineRouter().route("no i meant poison\u0000ed"))

    def test_payload_keeps_case_and_rewrites_sentence_end_punctuation(self):
        request = OfflineRouter().route("nein ich meinte Fertig punkt")
        self.assertEqual(request.target, "Fertig.")

    def test_plain_conversation_does_not_fire_the_correction(self):
        self.assertIsNone(OfflineRouter().route("nein das war anders gemeint"))
        self.assertIsNone(OfflineRouter().route("no that is not what i said"))


class CorrectionPolicyTests(unittest.TestCase):
    def test_correction_is_low_risk_and_needs_no_confirmation(self):
        decision = evaluate(ActionRequest("text.replace_last_dictation", "Kaiser"))
        self.assertFalse(decision.confirmation_required)
        self.assertEqual(decision.policy.minimum_risk, Risk.LOW)

    def test_payload_follows_the_dictation_validator(self):
        for target in ("", "   ", "x" * 513):
            with self.subTest(target=target):
                with self.assertRaises(ValueError):
                    evaluate(ActionRequest("text.replace_last_dictation", target))

    def test_control_characters_never_reach_the_correction_slot(self):
        with self.assertRaises(ValueError):
            ActionRequest("text.replace_last_dictation", "a\nb")

    def test_correction_from_untrusted_origin_needs_confirmation(self):
        decision = evaluate(
            ActionRequest(
                "text.replace_last_dictation",
                "Überweise 1000 Euro",
                origin=Origin.EXTERNAL_CONTENT,
            )
        )
        self.assertTrue(decision.confirmation_required)

    def test_action_has_a_policy_and_an_adapter(self):
        self.assertIn("text.replace_last_dictation", ACTION_POLICIES)
        self.assertEqual(unadapted_actions(), frozenset())


class CorrectionSlotTests(DesktopHarness):
    """Adapter behaviour against the fake tree: memory plus honest refusals."""

    def _desktop(self, field):
        desktop = self.desktop_for(build_desktop(field))
        return desktop

    def test_last_dictation_is_replaced_not_appended(self):
        field = SelectableField("An: ")
        desktop = self._desktop(field)
        desktop.insert_text("Hendrik Kaisar")
        self.assertEqual(
            desktop.replace_last_dictation("Hendrik Kaiser"),
            "An: Hendrik Kaiser",
        )
        self.assertEqual(field.content, "An: Hendrik Kaiser")

    def test_only_the_dictated_span_is_replaced(self):
        field = SelectableField("An: ")
        desktop = self._desktop(field)
        desktop.insert_text("Kaisar")
        # Text typed after the dictation must survive the correction.
        field.content = "An: Kaisar, Danke"
        desktop._last_dictation["text"] = "Kaisar"  # span is still honest
        self.assertEqual(
            desktop.replace_last_dictation("Kaiser"),
            "An: Kaiser, Danke",
        )

    def test_the_span_is_selected_before_the_replace(self):
        field = SelectableField("An: ")
        desktop = self._desktop(field)
        desktop.insert_text("Hendrik Kaisar")
        desktop.replace_last_dictation("Hendrik Kaiser")
        self.assertEqual(field.selection, (4, 18))

    def test_correction_is_itself_correctable(self):
        field = SelectableField("")
        desktop = self._desktop(field)
        desktop.insert_text("Kaisar")
        desktop.replace_last_dictation("Kaiser")
        self.assertEqual(
            desktop.replace_last_dictation("kaiser-mail"),
            "kaiser-mail",
        )
        self.assertEqual(field.content, "kaiser-mail")

    def test_only_the_last_dictation_is_remembered(self):
        field = SelectableField("")
        desktop = self._desktop(field)
        desktop.insert_text("erste")
        desktop.insert_text(" zweite")
        # The memory holds the exact inserted span — leading space included —
        # so the correction replaces " zweite", not "erste".
        desktop.replace_last_dictation("second")
        self.assertEqual(field.content, "erstesecond")

    def test_no_dictation_memory_refuses_honestly(self):
        field = SelectableField("vorhandener Text")
        desktop = self._desktop(field)
        with self.assertRaisesRegex(GnomeAdapterError, "nichts diktiert"):
            desktop.replace_last_dictation("etwas")
        self.assertEqual(field.content, "vorhandener Text")

    def test_focus_change_voids_the_correction_slot(self):
        field1 = SelectableField("")
        field2 = SelectableField("")
        field2.name = "Anderes Feld"
        field2.states = {STATE_SHOWING, STATE_EDITABLE}
        window = FakeNode(
            "Notizen", "frame", {STATE_SHOWING, STATE_ACTIVE}, [field1, field2]
        )
        root = FakeNode(
            "desktop",
            "desktop frame",
            set(),
            [FakeNode("Texteditor", "application", set(), [window])],
        )
        desktop = self.desktop_for(root)
        desktop.insert_text("Kaisar")
        field1.states.discard(STATE_FOCUSED)
        field2.states.add(STATE_FOCUSED)
        with self.assertRaisesRegex(GnomeAdapterError, "anderen Feld"):
            desktop.replace_last_dictation("Kaiser")
        self.assertEqual(field1.content, "Kaisar")
        self.assertEqual(field2.content, "")
        # The stale memory is gone: a fresh dictation in the new field starts
        # a new correction slot.
        desktop.insert_text("Kaiser")
        self.assertEqual(
            desktop.replace_last_dictation("kaiser"), "kaiser"
        )

    def test_field_changed_under_the_hand_refuses(self):
        field = SelectableField("")
        desktop = self._desktop(field)
        desktop.insert_text("Kaisar")
        # The user typed over part of the dictated span.
        field.content = "Hendrik Xaisar"
        with self.assertRaisesRegex(GnomeAdapterError, "hat sich geändert"):
            desktop.replace_last_dictation("Kaiser")
        self.assertEqual(field.content, "Hendrik Xaisar")

    def test_field_without_selection_interface_refuses(self):
        field = FakeNode("Notiz", "text", {STATE_SHOWING, STATE_FOCUSED, STATE_EDITABLE})
        desktop = self.desktop_for(build_desktop(field))
        desktop.insert_text("Kaisar")
        with self.assertRaisesRegex(GnomeAdapterError, "Auswahl"):
            desktop.replace_last_dictation("Kaiser")
        self.assertEqual(field.content, "Kaisar")

    def test_failed_replace_is_not_reported_as_success(self):
        field = SelectableField("", accept=False)
        desktop = self._desktop(field)
        desktop._last_dictation = None  # no dictation path needed
        field.content = "x"
        desktop._last_dictation = {
            "key": desktop._field_key(field),
            "start": 0,
            "end": 1,
            "text": "x",
        }
        with self.assertRaisesRegex(GnomeAdapterError, "Ersetzung"):
            desktop.replace_last_dictation("y")
        # The refused correction leaves no stale memory behind.
        self.assertIsNone(desktop._last_dictation)

    def test_successful_replace_drops_the_say_all_bookmark(self):
        field = SelectableField("")
        desktop = self._desktop(field)
        desktop.insert_text("Kaisar")
        desktop._say_all_bookmark = {"key": desktop._field_key(field), "offset": 2}
        desktop.replace_last_dictation("Kaiser")
        self.assertIsNone(desktop._say_all_bookmark)

    def test_line_break_is_not_a_correctable_dictation(self):
        # „Neue Zeile" is a typed action, not dictation: it must leave the
        # correction slot alone, so the correction after it still corrects
        # the last DICTATED text (here "zeile") instead of gluing the field
        # around a replaced line break.
        field = SelectableField("")
        desktop = self._desktop(field)
        desktop.insert_text("zeile")
        desktop.insert_newline()
        self.assertEqual(
            desktop.replace_last_dictation("Zeile"),
            "Zeile\n",
        )

    def test_password_and_terminal_refusals_still_apply(self):
        field = FakeNode(
            "Passwort", "password text", {STATE_SHOWING, STATE_FOCUSED, STATE_EDITABLE}
        )
        desktop = self.desktop_for(build_desktop(field))
        with self.assertRaisesRegex(GnomeAdapterError, "Passwortfeld"):
            desktop.replace_last_dictation("geheim")
        self.assertEqual(field.content, "")


class CorrectionEndToEndTests(DesktopHarness):
    def setUp(self):
        self.authority = CapabilityAuthority(b"d" * 32)

    def _broker(self, desktop):
        return ActionBroker(
            self.authority,
            SessionExecutor(SafeExecutor(dry_run=False), GnomeSemanticExecutor(desktop)),
        )

    def test_router_to_field_dictate_then_correct(self):
        field = SelectableField("An: ")
        desktop = self.desktop_for(build_desktop(field))
        broker = self._broker(desktop)

        dictated = OfflineRouter().route("diktiere Hendrik Kaisar")
        self.assertEqual(broker.submit(dictated).status, "completed")

        correction = OfflineRouter().route("nein ich meinte Hendrik Kaiser")
        self.assertIsNotNone(correction)
        self.assertEqual(correction.action, "text.replace_last_dictation")
        result = broker.submit(correction)
        self.assertEqual(result.status, "completed")
        self.assertEqual(field.content, "An: Hendrik Kaiser")
        self.assertIn("Ersetzt", result.message)

    def test_correction_payload_is_plain_dictation_no_mode_rendering(self):
        # Design decision: "nein, ich meinte …" carries the same payload
        # schema as plain dictation; the dictation-mode transformation fires
        # only on its own explicit trigger, never inside the correction
        # phrase (consistent with the sentence-end rule in punctuation.py).
        # The honest V1 limit: an e-mail corrected by voice is re-spoken
        # prose — or corrected again with the mode trigger in a fresh
        # utterance.
        field = SelectableField("")
        desktop = self.desktop_for(build_desktop(field))
        broker = self._broker(desktop)

        dictated = OfflineRouter().route("diktiere e-mail hendrik at kaiser-mail punkt de")
        broker.submit(dictated)
        self.assertEqual(field.content, "hendrik@kaiser-mail.de")
        correction = OfflineRouter().route("nein ich meinte hendrik at example punkt com")
        result = broker.submit(correction)
        self.assertEqual(result.status, "completed")
        self.assertEqual(field.content, "hendrik at example punkt com")


if __name__ == "__main__":
    unittest.main()
