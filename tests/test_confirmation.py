import unittest

from clausis.capabilities import CapabilityAuthority
from clausis.confirmation import (
    ConfirmationResponse,
    PinVerifier,
    TrustedConfirmer,
    canonicalize_untrusted_request,
)
from clausis.models import ActionRequest, Origin, Risk


class ConfirmationTests(unittest.TestCase):
    def setUp(self):
        self.authority = CapabilityAuthority(b"b" * 32)
        self.pin = PinVerifier.enroll("123456")
        self.confirmer = TrustedConfirmer(
            self.authority,
            self.pin,
            words=("eins", "zwei", "drei", "vier", "fuenf", "sechs", "sieben", "acht"),
        )
        self.request = ActionRequest(
            "system.reboot", origin=Origin.HERMES, risk=Risk.CRITICAL, reversible=False
        )

    def test_approval_issues_valid_token(self):
        pending = self.confirmer.begin(self.request)
        token = self.confirmer.approve(pending.confirmation_id, pending.phrase, "123456")
        self.authority.verify(token, self.request)

    def test_wrong_phrase_rejected(self):
        pending = self.confirmer.begin(self.request)
        with self.assertRaisesRegex(ValueError, "phrase"):
            self.confirmer.approve(pending.confirmation_id, "wrong phrase", "123456")

    def test_wrong_pin_rejected(self):
        pending = self.confirmer.begin(self.request)
        with self.assertRaisesRegex(ValueError, "PIN"):
            self.confirmer.approve(pending.confirmation_id, pending.phrase, "654321")

    def test_three_attempt_limit(self):
        pending = self.confirmer.begin(self.request)
        for _ in range(3):
            with self.assertRaises(ValueError):
                self.confirmer.approve(pending.confirmation_id, "wrong", "123456")
        with self.assertRaisesRegex(ValueError, "too many"):
            self.confirmer.approve(pending.confirmation_id, "wrong", "123456")

    def test_pin_export_round_trip(self):
        exported = self.pin.export()
        restored = PinVerifier.from_hex(exported["salt"], exported["digest"])
        self.assertTrue(restored.verify("123456"))
        self.assertFalse(restored.verify("000000"))

    def test_short_pin_rejected(self):
        with self.assertRaises(ValueError):
            PinVerifier.enroll("1234")

    def test_trusted_input_is_the_only_production_approval_path(self):
        class LocalInput:
            seen_summary = ""
            seen_challenge = ""

            def collect(inner_self, summary, challenge):
                inner_self.seen_summary = summary
                inner_self.seen_challenge = challenge
                return ConfirmationResponse(challenge + ".", "123456")

        local_input = LocalInput()
        approved = self.confirmer.approve_from_trusted_input(
            self.request, local_input
        )
        self.assertIn(local_input.seen_challenge, local_input.seen_summary)
        self.assertIsNotNone(approved.capability_token)
        self.authority.verify(approved.capability_token, self.request)

    def test_caller_cannot_smuggle_a_capability_into_confirmation(self):
        forged = ActionRequest(
            "system.reboot",
            origin=Origin.LOCAL_VOICE,
            risk=Risk.CRITICAL,
            reversible=False,
            capability_token="forged",
        )
        with self.assertRaisesRegex(ValueError, "caller-supplied"):
            canonicalize_untrusted_request(forged)

    def test_public_bus_origin_is_never_trusted_local_input(self):
        canonical = canonicalize_untrusted_request(self.request)
        self.assertEqual(canonical.origin, Origin.HERMES)

    def test_low_risk_action_cannot_misuse_confirmation_endpoint(self):
        class UnusedInput:
            def collect(self, summary, challenge):
                raise AssertionError("must not ask the user")

        with self.assertRaisesRegex(ValueError, "does not require"):
            self.confirmer.approve_from_trusted_input(
                ActionRequest("audio.volume.up"), UnusedInput()
            )

    def test_text_entry_summary_does_not_speak_the_text(self):
        request = ActionRequest(
            "desktop.text.set",
            target="private dictated content",
            risk=Risk.MEDIUM,
        )
        pending = self.confirmer.begin(request)
        summary = self.confirmer.canonical_summary(pending)
        self.assertNotIn(request.target, summary)
        self.assertIn("fokussierte Textfeld", summary)
        self.assertIn(pending.phrase, summary)

    def test_workspace_move_summary_names_direction(self):
        for action, direction in (
            ("desktop.window.workspace_previous", "vorherige Arbeitsfläche"),
            ("desktop.window.workspace_next", "nächste Arbeitsfläche"),
        ):
            request = ActionRequest(action, risk=Risk.MEDIUM)
            pending = self.confirmer.begin(request)
            self.assertIn(direction, self.confirmer.canonical_summary(pending))

    def test_clipboard_clear_summary_names_scope_and_irreversibility(self):
        request = ActionRequest(
            "desktop.clipboard.clear", risk=Risk.MEDIUM, reversible=False
        )
        summary = self.confirmer.canonical_summary(self.confirmer.begin(request))
        self.assertIn("dauerhaft löschen", summary)
        self.assertIn("primäre Auswahl bleibt unverändert", summary)
        self.assertIn("nicht rückgängig", summary)

    def test_clipboard_read_summary_warns_about_spoken_disclosure(self):
        request = ActionRequest("desktop.clipboard.read_text", risk=Risk.MEDIUM)
        summary = self.confirmer.canonical_summary(self.confirmer.begin(request))
        self.assertIn("laut vorlesen", summary)
        self.assertIn("noch im Audit gespeichert", summary)
        self.assertNotIn("private clipboard", summary)

    def test_clipboard_write_summary_never_repeats_dictation(self):
        request = ActionRequest(
            "desktop.clipboard.write_text",
            "private clipboard words",
            risk=Risk.MEDIUM,
            reversible=False,
        )
        summary = self.confirmer.canonical_summary(self.confirmer.begin(request))
        self.assertIn("diktierten Text", summary)
        self.assertIn("weder wiederholt", summary)
        self.assertIn("nicht rückgängig", summary)
        self.assertNotIn(request.target, summary)

    def test_focused_text_copy_summary_never_contains_content(self):
        request = ActionRequest(
            "desktop.text.copy_focused", risk=Risk.MEDIUM, reversible=False
        )
        summary = self.confirmer.canonical_summary(self.confirmer.begin(request))
        self.assertIn("nicht geschützten Textfelds", summary)
        self.assertIn("Inhalt wird nicht wiederholt", summary)
        self.assertIn("überschrieben", summary)
        self.assertNotIn("Quarterly report", summary)

    def test_text_selection_copy_summary_names_exact_scope_without_content(self):
        request = ActionRequest(
            "desktop.text.copy_selection", risk=Risk.MEDIUM, reversible=False
        )
        summary = self.confirmer.canonical_summary(self.confirmer.begin(request))
        self.assertIn("eindeutig ausgewählte Textspanne", summary)
        self.assertIn("nicht geschützten Textfeld", summary)
        self.assertIn("Inhalt wird nicht wiederholt", summary)
        self.assertIn("nicht rückgängig", summary)

    def test_text_selection_read_summary_warns_about_spoken_disclosure(self):
        request = ActionRequest("desktop.text.read_selection", risk=Risk.MEDIUM)
        summary = self.confirmer.canonical_summary(self.confirmer.begin(request))
        self.assertIn("eindeutig ausgewählte Textspanne", summary)
        self.assertIn("laut vorlesen", summary)
        self.assertIn("noch im Audit gespeichert", summary)
        self.assertIn("rückgängig machbar", summary)

    def test_text_selection_delete_summary_names_rollback_without_content(self):
        request = ActionRequest("desktop.text.delete_selection", risk=Risk.MEDIUM)
        summary = self.confirmer.canonical_summary(self.confirmer.begin(request))
        self.assertIn("Textspanne", summary)
        self.assertIn("wiederhergestellt", summary)
        self.assertNotIn("selected words", summary)

    def test_current_line_delete_summary_names_scope_and_rollback_without_content(self):
        request = ActionRequest("desktop.text.delete_current_line", risk=Risk.MEDIUM)
        summary = self.confirmer.canonical_summary(self.confirmer.begin(request))
        self.assertIn("Zeilenumbruchs", summary)
        self.assertIn("wiederhergestellt", summary)
        self.assertNotIn("private", summary)

    def test_focused_text_paste_summary_names_overwrite_without_content(self):
        request = ActionRequest(
            "desktop.text.paste_focused", risk=Risk.MEDIUM, reversible=False
        )
        summary = self.confirmer.canonical_summary(self.confirmer.begin(request))
        self.assertIn("nicht geschützte", summary)
        self.assertIn("Inhalt wird nicht wiederholt", summary)
        self.assertIn("Feldinhalt wird überschrieben", summary)
        self.assertIn("nicht rückgängig", summary)

    def test_insert_at_caret_summary_names_position_and_rollback_without_content(self):
        request = ActionRequest(
            "desktop.text.insert_at_caret", "private words", risk=Risk.MEDIUM
        )
        summary = self.confirmer.canonical_summary(self.confirmer.begin(request))
        self.assertIn("Textcursorposition", summary)
        self.assertIn("wiederhergestellt", summary)
        self.assertNotIn("private words", summary)

    def test_character_deletion_summaries_name_exact_side_and_rollback(self):
        for action, side in (
            ("desktop.text.delete_previous_character", "vor dem Textcursor"),
            ("desktop.text.delete_next_character", "nach dem Textcursor"),
        ):
            request = ActionRequest(action, risk=Risk.MEDIUM)
            summary = self.confirmer.canonical_summary(self.confirmer.begin(request))
            self.assertIn(side, summary)
            self.assertIn("genau ein", summary)
            self.assertIn("wiederhergestellt", summary)

    def test_word_deletion_summaries_name_exact_side_and_rollback(self):
        for action, side in (
            ("desktop.text.delete_previous_word", "vor dem Textcursor"),
            ("desktop.text.delete_next_word", "nach dem Textcursor"),
        ):
            request = ActionRequest(action, risk=Risk.MEDIUM)
            summary = self.confirmer.canonical_summary(self.confirmer.begin(request))
            self.assertIn(side, summary)
            self.assertIn("genau ein", summary)
            self.assertIn("wiederhergestellt", summary)

    def test_word_replacement_summaries_omit_target_and_name_rollback(self):
        for action, side in (
            ("desktop.text.replace_previous_word", "vor dem Textcursor"),
            ("desktop.text.replace_next_word", "nach dem Textcursor"),
        ):
            request = ActionRequest(action, "private replacement", risk=Risk.MEDIUM)
            summary = self.confirmer.canonical_summary(self.confirmer.begin(request))
            self.assertIn(side, summary)
            self.assertIn("genau ein", summary)
            self.assertIn("wiederhergestellt", summary)
            self.assertNotIn("private replacement", summary)

    def test_character_read_summaries_name_exact_side_and_content_redaction(self):
        for action, side in (
            ("desktop.text.read_previous_character", "vor dem Textcursor"),
            ("desktop.text.read_next_character", "nach dem Textcursor"),
        ):
            request = ActionRequest(action, risk=Risk.MEDIUM)
            summary = self.confirmer.canonical_summary(self.confirmer.begin(request))
            self.assertIn(side, summary)
            self.assertIn("genau ein", summary)
            self.assertIn("weder in dieser Bestätigung noch im Audit", summary)

    def test_word_read_summaries_name_exact_side_and_content_redaction(self):
        for action, side in (
            ("desktop.text.read_previous_word", "vor dem Textcursor"),
            ("desktop.text.read_next_word", "nach dem Textcursor"),
        ):
            request = ActionRequest(action, risk=Risk.MEDIUM)
            summary = self.confirmer.canonical_summary(self.confirmer.begin(request))
            self.assertIn(side, summary)
            self.assertIn("genau ein", summary)
            self.assertIn("begrenzten Suche", summary)
            self.assertIn("weder in dieser Bestätigung noch im Audit", summary)

    def test_selection_replacement_summary_omits_both_contents_and_names_rollback(self):
        request = ActionRequest(
            "desktop.text.replace_selection", "private replacement", risk=Risk.MEDIUM
        )
        summary = self.confirmer.canonical_summary(self.confirmer.begin(request))
        self.assertIn("eindeutig ausgewählte Textspanne", summary)
        self.assertIn("diktierten Text ersetzen", summary)
        self.assertIn("wiederhergestellt", summary)
        self.assertNotIn("private replacement", summary)

    def test_current_line_replacement_summary_omits_contents_and_names_rollback(self):
        request = ActionRequest(
            "desktop.text.replace_current_line", "private replacement", risk=Risk.MEDIUM
        )
        summary = self.confirmer.canonical_summary(self.confirmer.begin(request))
        self.assertIn("begrenzte Zeile", summary)
        self.assertIn("Zeilenumbruch bleibt erhalten", summary)
        self.assertIn("wiederhergestellt", summary)
        self.assertNotIn("private replacement", summary)

    def test_line_insertion_summaries_name_direction_and_omit_content(self):
        for action, direction in (
            ("desktop.text.insert_line_above", "oberhalb"),
            ("desktop.text.insert_line_below", "unterhalb"),
        ):
            request = ActionRequest(action, "private line", risk=Risk.MEDIUM)
            summary = self.confirmer.canonical_summary(self.confirmer.begin(request))
            self.assertIn(direction, summary)
            self.assertIn("wiederhergestellt", summary)
            self.assertNotIn("private line", summary)

    def test_line_duplication_summaries_name_direction_and_privacy(self):
        for action, direction in (
            ("desktop.text.duplicate_line_above", "oberhalb"),
            ("desktop.text.duplicate_line_below", "unterhalb"),
        ):
            request = ActionRequest(action, risk=Risk.MEDIUM)
            summary = self.confirmer.canonical_summary(self.confirmer.begin(request))
            self.assertIn(direction, summary)
            self.assertIn("weder wiederholt noch auditiert", summary)
            self.assertIn("wiederhergestellt", summary)

    def test_line_move_summaries_name_direction_cursor_and_privacy(self):
        for action, direction in (
            ("desktop.text.move_line_up", "darüber"),
            ("desktop.text.move_line_down", "darunter"),
        ):
            request = ActionRequest(action, risk=Risk.MEDIUM)
            summary = self.confirmer.canonical_summary(self.confirmer.begin(request))
            self.assertIn(direction, summary)
            self.assertIn("relative Cursorposition", summary)
            self.assertIn("weder wiederholt noch auditiert", summary)

    def test_line_join_summaries_name_exact_delimiter_and_privacy(self):
        for action, direction in (
            ("desktop.text.join_previous_line", "davor"),
            ("desktop.text.join_next_line", "danach"),
        ):
            request = ActionRequest(action, risk=Risk.MEDIUM)
            summary = self.confirmer.canonical_summary(self.confirmer.begin(request))
            self.assertIn(direction, summary)
            self.assertIn("genau den Zeilenumbruch", summary)
            self.assertIn("weder wiederholt noch auditiert", summary)

    def test_line_split_summary_names_exact_newline_and_privacy(self):
        request = ActionRequest("desktop.text.split_line_at_caret", risk=Risk.MEDIUM)
        summary = self.confirmer.canonical_summary(self.confirmer.begin(request))
        self.assertIn("genau einen Zeilenumbruch", summary)
        self.assertIn("Textcursorposition", summary)
        self.assertIn("weder wiederholt noch auditiert", summary)
        self.assertIn("wiederhergestellt", summary)

    def test_line_indentation_summaries_name_exact_whitespace_and_privacy(self):
        for action, detail in (
            ("desktop.text.indent_current_line", "genau vier Leerzeichen"),
            ("desktop.text.outdent_current_line", "genau einen führenden Tabulator"),
        ):
            request = ActionRequest(action, risk=Risk.MEDIUM)
            summary = self.confirmer.canonical_summary(self.confirmer.begin(request))
            self.assertIn(detail, summary)
            self.assertIn("weder wiederholt noch auditiert", summary)
            self.assertIn("wiederhergestellt", summary)

    def test_accessibility_enable_summary_names_rescue_tool(self):
        for action, tool in (
            ("accessibility.screen_keyboard.enable", "Bildschirmtastatur"),
            ("accessibility.screen_reader.enable", "Orca-Screenreader"),
            ("accessibility.screen_magnifier.enable", "Bildschirmvergrößerung"),
            ("accessibility.screen_magnifier.disable", "Orca und Bildschirmtastatur bleiben eingeschaltet"),
        ):
            request = ActionRequest(action, risk=Risk.MEDIUM)
            pending = self.confirmer.begin(request)
            self.assertIn(tool, self.confirmer.canonical_summary(pending))

    def test_orca_recovery_summary_requires_speech_restart(self):
        request = ActionRequest(
            "accessibility.screen_reader.restart_with_speech", risk=Risk.MEDIUM
        )
        pending = self.confirmer.begin(request)
        summary = self.confirmer.canonical_summary(pending)
        self.assertIn("Orca-Screenreader", summary)
        self.assertIn("Sprachausgabe", summary)
        self.assertIn("neu starten", summary)

    def test_magnifier_zoom_summary_names_exact_percentage(self):
        request = ActionRequest(
            "accessibility.screen_magnifier.set_percent",
            arguments={"percent": 225},
            risk=Risk.MEDIUM,
        )
        pending = self.confirmer.begin(request)
        summary = self.confirmer.canonical_summary(pending)
        self.assertIn("Bildschirmvergrößerung", summary)
        self.assertIn("225 Prozent", summary)

    def test_magnifier_inversion_summary_names_exact_state(self):
        for action, state in (
            ("accessibility.screen_magnifier.invert_lightness.enable", "einschalten"),
            ("accessibility.screen_magnifier.invert_lightness.disable", "ausschalten"),
        ):
            request = ActionRequest(action, risk=Risk.MEDIUM)
            pending = self.confirmer.begin(request)
            summary = self.confirmer.canonical_summary(pending)
            self.assertIn("Farbinvertierung", summary)
            self.assertIn(state, summary)

    def test_magnifier_lens_mode_and_edge_scrolling_summaries_name_state(self):
        for action, feature, state in (
            ("accessibility.screen_magnifier.lens_mode.enable", "Linsenmodus", "einschalten"),
            ("accessibility.screen_magnifier.lens_mode.disable", "Linsenmodus", "ausschalten"),
            ("accessibility.screen_magnifier.scroll_at_edges.enable", "Scrollen am Bildschirmrand", "einschalten"),
            ("accessibility.screen_magnifier.scroll_at_edges.disable", "Scrollen am Bildschirmrand", "ausschalten"),
        ):
            with self.subTest(action=action):
                request = ActionRequest(action, risk=Risk.MEDIUM)
                pending = self.confirmer.begin(request)
                summary = self.confirmer.canonical_summary(pending)
                self.assertIn(feature, summary)
                self.assertIn(state, summary)

    def test_magnifier_saturation_summary_names_exact_percentage(self):
        request = ActionRequest(
            "accessibility.screen_magnifier.set_saturation",
            arguments={"percent": 35},
            risk=Risk.MEDIUM,
        )
        pending = self.confirmer.begin(request)
        summary = self.confirmer.canonical_summary(pending)
        self.assertIn("Farbsättigung", summary)
        self.assertIn("35 Prozent", summary)

    def test_magnifier_brightness_and_contrast_summaries_name_signed_percentage(self):
        for action, feature, percent, wording in (
            ("accessibility.screen_magnifier.set_brightness", "Helligkeit", -30, "-30 Prozent"),
            ("accessibility.screen_magnifier.set_contrast", "Kontrast", 45, "+45 Prozent"),
        ):
            with self.subTest(action=action):
                request = ActionRequest(action, arguments={"percent": percent}, risk=Risk.MEDIUM)
                pending = self.confirmer.begin(request)
                summary = self.confirmer.canonical_summary(pending)
                self.assertIn(feature, summary)
                self.assertIn(wording, summary)

    def test_magnifier_screen_position_summary_names_exact_region(self):
        request = ActionRequest(
            "accessibility.screen_magnifier.set_screen_position",
            arguments={"position": "right-half"},
            risk=Risk.MEDIUM,
        )
        pending = self.confirmer.begin(request)
        summary = self.confirmer.canonical_summary(pending)
        self.assertIn("Bildschirmvergrößerung", summary)
        self.assertIn("rechte Bildschirmhälfte", summary)

    def test_magnifier_cross_hair_summary_names_exact_state(self):
        for action, state in (
            ("accessibility.screen_magnifier.cross_hairs.enable", "einschalten"),
            ("accessibility.screen_magnifier.cross_hairs.disable", "ausschalten"),
        ):
            with self.subTest(action=action):
                request = ActionRequest(action, risk=Risk.MEDIUM)
                pending = self.confirmer.begin(request)
                summary = self.confirmer.canonical_summary(pending)
                self.assertIn("Fadenkreuz", summary)
                self.assertIn(state, summary)

    def test_magnifier_cross_hair_opacity_summary_names_exact_percentage(self):
        request = ActionRequest(
            "accessibility.screen_magnifier.cross_hairs.set_opacity",
            arguments={"percent": 42},
            risk=Risk.MEDIUM,
        )
        pending = self.confirmer.begin(request)
        summary = self.confirmer.canonical_summary(pending)
        self.assertIn("Lupen-Fadenkreuzes", summary)
        self.assertIn("42 Prozent", summary)

    def test_magnifier_cross_hair_clip_summary_names_exact_state(self):
        for action, wording in (
            ("accessibility.screen_magnifier.cross_hairs.clip.enable", "Mitte"),
            ("accessibility.screen_magnifier.cross_hairs.clip.disable", "Aussparung"),
        ):
            with self.subTest(action=action):
                request = ActionRequest(action, risk=Risk.MEDIUM)
                pending = self.confirmer.begin(request)
                summary = self.confirmer.canonical_summary(pending)
                self.assertIn("Lupen-Fadenkreuzes", summary)
                self.assertIn(wording, summary)

    def test_magnifier_cross_hair_length_summary_names_exact_pixels(self):
        request = ActionRequest(
            "accessibility.screen_magnifier.cross_hairs.set_length",
            arguments={"pixels": 640},
            risk=Risk.MEDIUM,
        )
        pending = self.confirmer.begin(request)
        summary = self.confirmer.canonical_summary(pending)
        self.assertIn("Länge des Lupen-Fadenkreuzes", summary)
        self.assertIn("640 Pixel", summary)

    def test_magnifier_cross_hair_thickness_summary_names_exact_pixels(self):
        request = ActionRequest(
            "accessibility.screen_magnifier.cross_hairs.set_thickness",
            arguments={"pixels": 12},
            risk=Risk.MEDIUM,
        )
        pending = self.confirmer.begin(request)
        summary = self.confirmer.canonical_summary(pending)
        self.assertIn("Dicke des Lupen-Fadenkreuzes", summary)
        self.assertIn("12 Pixel", summary)

    def test_magnifier_cross_hair_color_summary_names_exact_rgb(self):
        request = ActionRequest(
            "accessibility.screen_magnifier.cross_hairs.set_color",
            arguments={"red": 12, "green": 34, "blue": 56},
            risk=Risk.MEDIUM,
        )
        pending = self.confirmer.begin(request)
        summary = self.confirmer.canonical_summary(pending)
        self.assertIn("Farbe des Lupen-Fadenkreuzes", summary)
        self.assertIn("RGB 12, 34, 56", summary)

    def test_magnifier_focus_tracking_summary_names_exact_mode(self):
        request = ActionRequest(
            "accessibility.screen_magnifier.set_focus_tracking",
            arguments={"mode": "push"},
            risk=Risk.MEDIUM,
        )
        pending = self.confirmer.begin(request)
        summary = self.confirmer.canonical_summary(pending)
        self.assertIn("Fokusverfolgung", summary)
        self.assertIn("schiebend", summary)

    def test_magnifier_caret_and_mouse_tracking_summaries_name_mode(self):
        for action, label in (
            ("accessibility.screen_magnifier.set_caret_tracking", "Textcursorverfolgung"),
            ("accessibility.screen_magnifier.set_mouse_tracking", "Mausverfolgung"),
        ):
            with self.subTest(action=action):
                request = ActionRequest(action, arguments={"mode": "centered"}, risk=Risk.MEDIUM)
                pending = self.confirmer.begin(request)
                summary = self.confirmer.canonical_summary(pending)
                self.assertIn(label, summary)
                self.assertIn("zentriert", summary)


if __name__ == "__main__":
    unittest.main()
