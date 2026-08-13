import unittest

from clausis.models import ActionRequest, Origin, Risk
from clausis.policy import evaluate


class PolicyTests(unittest.TestCase):
    def test_file_dialog_decisions_are_confirmed_and_bounded(self):
        for target in ("accept", "cancel"):
            decision = evaluate(
                ActionRequest("desktop.file_dialog.decide", target, risk=Risk.MEDIUM)
            )
            self.assertTrue(decision.confirmation_required)
        for request in (
            ActionRequest("desktop.file_dialog.decide", "always", risk=Risk.MEDIUM),
            ActionRequest(
                "desktop.file_dialog.decide",
                "accept",
                arguments={"force": True},
                risk=Risk.MEDIUM,
            ),
        ):
            with self.assertRaises(ValueError):
                evaluate(request)

    def test_standard_dialog_decisions_are_high_risk_nonreversible_and_bounded(self):
        for target in ("accept", "cancel", "retry", "apply"):
            decision = evaluate(
                ActionRequest(
                    "desktop.standard_dialog.decide",
                    target,
                    risk=Risk.HIGH,
                    reversible=False,
                )
            )
            self.assertTrue(decision.confirmation_required)
            self.assertFalse(decision.policy.reversible)
        for request in (
            ActionRequest(
                "desktop.standard_dialog.decide", "delete", risk=Risk.HIGH,
                reversible=False,
            ),
            ActionRequest(
                "desktop.standard_dialog.decide", "accept",
                arguments={"force": True}, risk=Risk.HIGH, reversible=False,
            ),
        ):
            with self.assertRaises(ValueError):
                evaluate(request)

    def test_standard_dialog_read_is_confirmed_and_parameterless(self):
        decision = evaluate(ActionRequest("desktop.standard_dialog.read", risk=Risk.MEDIUM))
        self.assertTrue(decision.confirmation_required)
        for request in (
            ActionRequest("desktop.standard_dialog.read", "Dialog", risk=Risk.MEDIUM),
            ActionRequest(
                "desktop.standard_dialog.read", arguments={"all": True}, risk=Risk.MEDIUM
            ),
        ):
            with self.assertRaises(ValueError):
                evaluate(request)

    def test_standard_dialog_dismiss_is_high_risk_nonreversible_and_parameterless(self):
        request = ActionRequest(
            "desktop.standard_dialog.dismiss", risk=Risk.HIGH, reversible=False
        )
        decision = evaluate(request)
        self.assertTrue(decision.confirmation_required)
        self.assertFalse(decision.policy.reversible)
        for invalid in (
            ActionRequest(
                "desktop.standard_dialog.dismiss", "Close", risk=Risk.HIGH,
                reversible=False,
            ),
            ActionRequest(
                "desktop.standard_dialog.dismiss", arguments={"force": True},
                risk=Risk.HIGH, reversible=False,
            ),
        ):
            with self.assertRaises(ValueError):
                evaluate(invalid)

    def test_notification_read_is_confirmed_and_parameterless(self):
        decision = evaluate(ActionRequest("desktop.notifications.read", risk=Risk.MEDIUM))
        self.assertTrue(decision.confirmation_required)
        for request in (
            ActionRequest("desktop.notifications.read", "all", risk=Risk.MEDIUM),
            ActionRequest(
                "desktop.notifications.read", arguments={"limit": 5}, risk=Risk.MEDIUM
            ),
        ):
            with self.assertRaises(ValueError):
                evaluate(request)

    def test_notification_dismiss_is_high_risk_nonreversible_and_number_bounded(self):
        for target in ("1", "20"):
            decision = evaluate(
                ActionRequest(
                    "desktop.notifications.dismiss", target, risk=Risk.HIGH,
                    reversible=False,
                )
            )
            self.assertTrue(decision.confirmation_required)
            self.assertFalse(decision.policy.reversible)
        for target in ("0", "21", "one", ""):
            with self.assertRaises(ValueError):
                evaluate(
                    ActionRequest(
                        "desktop.notifications.dismiss", target, risk=Risk.HIGH,
                        reversible=False,
                    )
                )

    def test_safe_local_action_needs_no_confirmation(self):
        decision = evaluate(ActionRequest("audio.volume.up"))
        self.assertFalse(decision.confirmation_required)

    def test_focused_text_read_is_allowlisted_as_low_risk(self):
        decision = evaluate(ActionRequest("desktop.text.read_focused"))
        self.assertFalse(decision.confirmation_required)

    def test_named_progress_read_is_allowlisted_as_low_risk(self):
        decision = evaluate(ActionRequest("desktop.progress.read_named", "Download"))
        self.assertFalse(decision.confirmation_required)

    def test_accessibility_enable_actions_require_confirmation_and_no_parameters(self):
        for action in (
            "accessibility.screen_keyboard.enable",
            "accessibility.screen_reader.enable",
            "accessibility.screen_reader.restart_with_speech",
            "accessibility.screen_magnifier.enable",
            "accessibility.screen_magnifier.disable",
            "accessibility.screen_magnifier.invert_lightness.enable",
            "accessibility.screen_magnifier.invert_lightness.disable",
            "accessibility.screen_magnifier.cross_hairs.enable",
            "accessibility.screen_magnifier.cross_hairs.disable",
            "accessibility.screen_magnifier.cross_hairs.clip.enable",
            "accessibility.screen_magnifier.cross_hairs.clip.disable",
            "accessibility.screen_magnifier.lens_mode.enable",
            "accessibility.screen_magnifier.lens_mode.disable",
            "accessibility.screen_magnifier.scroll_at_edges.enable",
            "accessibility.screen_magnifier.scroll_at_edges.disable",
        ):
            self.assertTrue(
                evaluate(ActionRequest(action, risk=Risk.MEDIUM)).confirmation_required
            )
            for request in (
                ActionRequest(action, "unexpected", risk=Risk.MEDIUM),
                ActionRequest(action, arguments={"enabled": True}, risk=Risk.MEDIUM),
            ):
                with self.assertRaises(ValueError):
                    evaluate(request)

    def test_magnifier_zoom_requires_exact_bounded_integer_percentage(self):
        action = "accessibility.screen_magnifier.set_percent"
        valid = ActionRequest(action, arguments={"percent": 3200}, risk=Risk.MEDIUM)
        self.assertTrue(evaluate(valid).confirmation_required)
        for request in (
            ActionRequest(action, "target", arguments={"percent": 200}, risk=Risk.MEDIUM),
            ActionRequest(action, arguments={"percent": 99}, risk=Risk.MEDIUM),
            ActionRequest(action, arguments={"percent": 3201}, risk=Risk.MEDIUM),
            ActionRequest(action, arguments={"percent": 200.0}, risk=Risk.MEDIUM),
            ActionRequest(action, arguments={"percent": True}, risk=Risk.MEDIUM),
            ActionRequest(action, arguments={"percent": 200, "extra": 1}, risk=Risk.MEDIUM),
        ):
            with self.subTest(request=request), self.assertRaises(ValueError):
                evaluate(request)

    def test_magnifier_saturation_requires_exact_bounded_integer_percentage(self):
        action = "accessibility.screen_magnifier.set_saturation"
        valid = ActionRequest(action, arguments={"percent": 0}, risk=Risk.MEDIUM)
        self.assertTrue(evaluate(valid).confirmation_required)
        for request in (
            ActionRequest(action, "target", arguments={"percent": 50}, risk=Risk.MEDIUM),
            ActionRequest(action, arguments={"percent": -1}, risk=Risk.MEDIUM),
            ActionRequest(action, arguments={"percent": 101}, risk=Risk.MEDIUM),
            ActionRequest(action, arguments={"percent": 50.0}, risk=Risk.MEDIUM),
            ActionRequest(action, arguments={"percent": False}, risk=Risk.MEDIUM),
            ActionRequest(action, arguments={"percent": 50, "extra": 1}, risk=Risk.MEDIUM),
        ):
            with self.subTest(request=request), self.assertRaises(ValueError):
                evaluate(request)

    def test_magnifier_brightness_and_contrast_require_ui_bounded_integer(self):
        for action in (
            "accessibility.screen_magnifier.set_brightness",
            "accessibility.screen_magnifier.set_contrast",
        ):
            for percent in (-75, 0, 75):
                with self.subTest(action=action, percent=percent):
                    request = ActionRequest(action, arguments={"percent": percent}, risk=Risk.MEDIUM)
                    self.assertTrue(evaluate(request).confirmation_required)
            for request in (
                ActionRequest(action, "target", arguments={"percent": 20}, risk=Risk.MEDIUM),
                ActionRequest(action, risk=Risk.MEDIUM),
                ActionRequest(action, arguments={"percent": -76}, risk=Risk.MEDIUM),
                ActionRequest(action, arguments={"percent": 76}, risk=Risk.MEDIUM),
                ActionRequest(action, arguments={"percent": 20.0}, risk=Risk.MEDIUM),
                ActionRequest(action, arguments={"percent": True}, risk=Risk.MEDIUM),
                ActionRequest(action, arguments={"percent": 20, "extra": 1}, risk=Risk.MEDIUM),
            ):
                with self.subTest(action=action, request=request), self.assertRaises(ValueError):
                    evaluate(request)

    def test_magnifier_screen_position_requires_one_known_schema_value(self):
        action = "accessibility.screen_magnifier.set_screen_position"
        for position in (
            "full-screen", "top-half", "bottom-half", "left-half", "right-half"
        ):
            with self.subTest(position=position):
                request = ActionRequest(
                    action, arguments={"position": position}, risk=Risk.MEDIUM
                )
                self.assertTrue(evaluate(request).confirmation_required)
        for request in (
            ActionRequest(action, "display", arguments={"position": "full-screen"}, risk=Risk.MEDIUM),
            ActionRequest(action, risk=Risk.MEDIUM),
            ActionRequest(action, arguments={"position": "centered"}, risk=Risk.MEDIUM),
            ActionRequest(action, arguments={"position": True}, risk=Risk.MEDIUM),
            ActionRequest(action, arguments={"position": "full-screen", "extra": 1}, risk=Risk.MEDIUM),
        ):
            with self.subTest(request=request), self.assertRaises(ValueError):
                evaluate(request)

    def test_magnifier_cross_hairs_opacity_requires_exact_bounded_integer(self):
        action = "accessibility.screen_magnifier.cross_hairs.set_opacity"
        for percent in (0, 100):
            with self.subTest(percent=percent):
                request = ActionRequest(
                    action, arguments={"percent": percent}, risk=Risk.MEDIUM
                )
                self.assertTrue(evaluate(request).confirmation_required)
        for request in (
            ActionRequest(action, "target", arguments={"percent": 50}, risk=Risk.MEDIUM),
            ActionRequest(action, arguments={"percent": -1}, risk=Risk.MEDIUM),
            ActionRequest(action, arguments={"percent": 101}, risk=Risk.MEDIUM),
            ActionRequest(action, arguments={"percent": 50.0}, risk=Risk.MEDIUM),
            ActionRequest(action, arguments={"percent": False}, risk=Risk.MEDIUM),
            ActionRequest(action, arguments={"percent": 50, "extra": 1}, risk=Risk.MEDIUM),
        ):
            with self.subTest(request=request), self.assertRaises(ValueError):
                evaluate(request)

    def test_magnifier_cross_hairs_length_requires_exact_schema_bounded_integer(self):
        action = "accessibility.screen_magnifier.cross_hairs.set_length"
        for pixels in (20, 4096):
            with self.subTest(pixels=pixels):
                request = ActionRequest(
                    action, arguments={"pixels": pixels}, risk=Risk.MEDIUM
                )
                self.assertTrue(evaluate(request).confirmation_required)
        for request in (
            ActionRequest(action, "target", arguments={"pixels": 100}, risk=Risk.MEDIUM),
            ActionRequest(action, arguments={"pixels": 19}, risk=Risk.MEDIUM),
            ActionRequest(action, arguments={"pixels": 4097}, risk=Risk.MEDIUM),
            ActionRequest(action, arguments={"pixels": 100.0}, risk=Risk.MEDIUM),
            ActionRequest(action, arguments={"pixels": True}, risk=Risk.MEDIUM),
            ActionRequest(action, arguments={"pixels": 100, "extra": 1}, risk=Risk.MEDIUM),
        ):
            with self.subTest(request=request), self.assertRaises(ValueError):
                evaluate(request)

    def test_magnifier_cross_hairs_thickness_requires_control_center_bounds(self):
        action = "accessibility.screen_magnifier.cross_hairs.set_thickness"
        for pixels in (1, 100):
            with self.subTest(pixels=pixels):
                request = ActionRequest(action, arguments={"pixels": pixels}, risk=Risk.MEDIUM)
                self.assertTrue(evaluate(request).confirmation_required)
        for request in (
            ActionRequest(action, "target", arguments={"pixels": 8}, risk=Risk.MEDIUM),
            ActionRequest(action, risk=Risk.MEDIUM),
            ActionRequest(action, arguments={"pixels": 0}, risk=Risk.MEDIUM),
            ActionRequest(action, arguments={"pixels": 101}, risk=Risk.MEDIUM),
            ActionRequest(action, arguments={"pixels": 8.0}, risk=Risk.MEDIUM),
            ActionRequest(action, arguments={"pixels": True}, risk=Risk.MEDIUM),
            ActionRequest(action, arguments={"pixels": 8, "extra": 1}, risk=Risk.MEDIUM),
        ):
            with self.subTest(request=request), self.assertRaises(ValueError):
                evaluate(request)

    def test_magnifier_cross_hairs_color_requires_exact_rgb_channels(self):
        action = "accessibility.screen_magnifier.cross_hairs.set_color"
        for channels in (
            {"red": 0, "green": 0, "blue": 0},
            {"red": 255, "green": 255, "blue": 255},
        ):
            with self.subTest(channels=channels):
                self.assertTrue(
                    evaluate(ActionRequest(action, arguments=channels, risk=Risk.MEDIUM)).confirmation_required
                )
        for request in (
            ActionRequest(action, "target", arguments={"red": 1, "green": 2, "blue": 3}, risk=Risk.MEDIUM),
            ActionRequest(action, risk=Risk.MEDIUM),
            ActionRequest(action, arguments={"red": -1, "green": 2, "blue": 3}, risk=Risk.MEDIUM),
            ActionRequest(action, arguments={"red": 1, "green": 2, "blue": 256}, risk=Risk.MEDIUM),
            ActionRequest(action, arguments={"red": 1.0, "green": 2, "blue": 3}, risk=Risk.MEDIUM),
            ActionRequest(action, arguments={"red": True, "green": 2, "blue": 3}, risk=Risk.MEDIUM),
            ActionRequest(action, arguments={"red": 1, "green": 2}, risk=Risk.MEDIUM),
            ActionRequest(action, arguments={"red": 1, "green": 2, "blue": 3, "extra": 4}, risk=Risk.MEDIUM),
        ):
            with self.subTest(request=request), self.assertRaises(ValueError):
                evaluate(request)

    def test_magnifier_focus_tracking_requires_one_known_schema_mode(self):
        action = "accessibility.screen_magnifier.set_focus_tracking"
        for mode in ("none", "centered", "proportional", "push"):
            with self.subTest(mode=mode):
                request = ActionRequest(action, arguments={"mode": mode}, risk=Risk.MEDIUM)
                self.assertTrue(evaluate(request).confirmation_required)
        for request in (
            ActionRequest(action, "target", arguments={"mode": "centered"}, risk=Risk.MEDIUM),
            ActionRequest(action, risk=Risk.MEDIUM),
            ActionRequest(action, arguments={"mode": "follow"}, risk=Risk.MEDIUM),
            ActionRequest(action, arguments={"mode": True}, risk=Risk.MEDIUM),
            ActionRequest(action, arguments={"mode": "centered", "extra": 1}, risk=Risk.MEDIUM),
        ):
            with self.subTest(request=request), self.assertRaises(ValueError):
                evaluate(request)

    def test_magnifier_caret_and_mouse_tracking_require_known_schema_mode(self):
        for action in (
            "accessibility.screen_magnifier.set_caret_tracking",
            "accessibility.screen_magnifier.set_mouse_tracking",
        ):
            for mode in ("none", "centered", "proportional", "push"):
                with self.subTest(action=action, mode=mode):
                    request = ActionRequest(action, arguments={"mode": mode}, risk=Risk.MEDIUM)
                    self.assertTrue(evaluate(request).confirmation_required)
            for request in (
                ActionRequest(action, "target", arguments={"mode": "centered"}, risk=Risk.MEDIUM),
                ActionRequest(action, risk=Risk.MEDIUM),
                ActionRequest(action, arguments={"mode": "follow"}, risk=Risk.MEDIUM),
                ActionRequest(action, arguments={"mode": True}, risk=Risk.MEDIUM),
                ActionRequest(action, arguments={"mode": "centered", "extra": 1}, risk=Risk.MEDIUM),
            ):
                with self.subTest(action=action, request=request), self.assertRaises(ValueError):
                    evaluate(request)

    def test_hermes_action_is_tainted(self):
        decision = evaluate(ActionRequest("audio.volume.up", origin=Origin.HERMES))
        self.assertTrue(decision.confirmation_required)

    def test_external_content_action_is_tainted(self):
        decision = evaluate(ActionRequest("file.open", "/tmp/a", origin=Origin.EXTERNAL_CONTENT))
        self.assertTrue(decision.confirmation_required)

    def test_risk_cannot_be_understated(self):
        with self.assertRaisesRegex(ValueError, "understate"):
            evaluate(ActionRequest("system.reboot", risk=Risk.LOW, reversible=False))

    def test_irreversible_cannot_be_marked_reversible(self):
        with self.assertRaisesRegex(ValueError, "irreversible"):
            evaluate(ActionRequest("system.reboot", risk=Risk.CRITICAL, reversible=True))

    def test_clipboard_clear_is_parameterless_confirmed_and_irreversible(self):
        decision = evaluate(
            ActionRequest("desktop.clipboard.clear", risk=Risk.MEDIUM, reversible=False)
        )
        self.assertTrue(decision.confirmation_required)
        self.assertFalse(decision.policy.reversible)
        for request in (
            ActionRequest("desktop.clipboard.clear", "clipboard", risk=Risk.MEDIUM, reversible=False),
            ActionRequest("desktop.clipboard.clear", arguments={"selection": "primary"}, risk=Risk.MEDIUM, reversible=False),
            ActionRequest("desktop.clipboard.clear", risk=Risk.MEDIUM, reversible=True),
        ):
            with self.assertRaises(ValueError):
                evaluate(request)

    def test_clipboard_read_is_parameterless_and_confirmation_gated(self):
        action = "desktop.clipboard.read_text"
        decision = evaluate(ActionRequest(action, risk=Risk.MEDIUM))
        self.assertTrue(decision.confirmation_required)
        self.assertTrue(decision.policy.reversible)
        for request in (
            ActionRequest(action, "clipboard", risk=Risk.MEDIUM),
            ActionRequest(action, arguments={"limit": 10}, risk=Risk.MEDIUM),
        ):
            with self.assertRaises(ValueError):
                evaluate(request)

    def test_clipboard_write_requires_only_bounded_printable_dictation(self):
        action = "desktop.clipboard.write_text"
        decision = evaluate(
            ActionRequest(action, "private words", risk=Risk.MEDIUM, reversible=False)
        )
        self.assertTrue(decision.confirmation_required)
        self.assertFalse(decision.policy.reversible)
        for request in (
            ActionRequest(action, risk=Risk.MEDIUM, reversible=False),
            ActionRequest(action, "a\x7fb", risk=Risk.MEDIUM, reversible=False),
            ActionRequest(action, "x" * 501, risk=Risk.MEDIUM, reversible=False),
            ActionRequest(action, "text", arguments={"extra": "secret"}, risk=Risk.MEDIUM, reversible=False),
            ActionRequest(action, "text", risk=Risk.MEDIUM, reversible=True),
        ):
            with self.assertRaises(ValueError):
                evaluate(request)

    def test_spoken_text_entry_rejects_extra_arguments(self):
        with self.assertRaises(ValueError):
            evaluate(
                ActionRequest(
                    "desktop.text.set",
                    "private words",
                    arguments={"extra": "secret"},
                    risk=Risk.MEDIUM,
                )
            )

    def test_focused_text_copy_is_parameterless_confirmed_and_irreversible(self):
        action = "desktop.text.copy_focused"
        decision = evaluate(ActionRequest(action, risk=Risk.MEDIUM, reversible=False))
        self.assertTrue(decision.confirmation_required)
        self.assertFalse(decision.policy.reversible)
        for request in (
            ActionRequest(action, "text", risk=Risk.MEDIUM, reversible=False),
            ActionRequest(action, arguments={"text": "secret"}, risk=Risk.MEDIUM, reversible=False),
            ActionRequest(action, risk=Risk.MEDIUM, reversible=True),
        ):
            with self.assertRaises(ValueError):
                evaluate(request)

    def test_text_selection_copy_is_parameterless_confirmed_and_irreversible(self):
        action = "desktop.text.copy_selection"
        decision = evaluate(ActionRequest(action, risk=Risk.MEDIUM, reversible=False))
        self.assertTrue(decision.confirmation_required)
        self.assertFalse(decision.policy.reversible)
        for request in (
            ActionRequest(action, "selection", risk=Risk.MEDIUM, reversible=False),
            ActionRequest(action, arguments={"index": 0}, risk=Risk.MEDIUM, reversible=False),
            ActionRequest(action, risk=Risk.MEDIUM, reversible=True),
        ):
            with self.assertRaises(ValueError):
                evaluate(request)

    def test_select_all_text_is_parameterless_low_risk_and_reversible(self):
        action = "desktop.text.select_all"
        decision = evaluate(ActionRequest(action))
        self.assertFalse(decision.confirmation_required)
        self.assertTrue(decision.policy.reversible)
        for request in (
            ActionRequest(action, "text"),
            ActionRequest(action, arguments={"range": "all"}),
        ):
            with self.assertRaises(ValueError):
                evaluate(request)

    def test_text_selection_read_is_parameterless_confirmed_and_reversible(self):
        action = "desktop.text.read_selection"
        decision = evaluate(ActionRequest(action, risk=Risk.MEDIUM))
        self.assertTrue(decision.confirmation_required)
        self.assertTrue(decision.policy.reversible)
        for request in (
            ActionRequest(action, "selection", risk=Risk.MEDIUM),
            ActionRequest(action, arguments={"index": 0}, risk=Risk.MEDIUM),
        ):
            with self.assertRaises(ValueError):
                evaluate(request)

    def test_clear_text_selection_is_parameterless_low_risk_and_reversible(self):
        action = "desktop.text.clear_selection"
        decision = evaluate(ActionRequest(action))
        self.assertFalse(decision.confirmation_required)
        self.assertTrue(decision.policy.reversible)
        for request in (
            ActionRequest(action, "selection"),
            ActionRequest(action, arguments={"all": True}),
        ):
            with self.assertRaises(ValueError):
                evaluate(request)

    def test_delete_text_selection_is_parameterless_confirmed_and_reversible(self):
        action = "desktop.text.delete_selection"
        decision = evaluate(ActionRequest(action, risk=Risk.MEDIUM))
        self.assertTrue(decision.confirmation_required)
        self.assertTrue(decision.policy.reversible)
        for request in (
            ActionRequest(action, "selection", risk=Risk.MEDIUM),
            ActionRequest(action, arguments={"index": 0}, risk=Risk.MEDIUM),
        ):
            with self.assertRaises(ValueError):
                evaluate(request)

    def test_insert_at_caret_requires_one_bounded_printable_target(self):
        action = "desktop.text.insert_at_caret"
        decision = evaluate(ActionRequest(action, "inserted words", risk=Risk.MEDIUM))
        self.assertTrue(decision.confirmation_required)
        self.assertTrue(decision.policy.reversible)
        for request in (
            ActionRequest(action, risk=Risk.MEDIUM),
            ActionRequest(action, "hidden\u200bseparator", risk=Risk.MEDIUM),
            ActionRequest(action, "x" * 501, risk=Risk.MEDIUM),
            ActionRequest(action, "text", arguments={"offset": 1}, risk=Risk.MEDIUM),
        ):
            with self.assertRaises(ValueError):
                evaluate(request)

    def test_character_deletions_are_parameterless_confirmed_and_reversible(self):
        for action in (
            "desktop.text.delete_previous_character",
            "desktop.text.delete_next_character",
        ):
            decision = evaluate(ActionRequest(action, risk=Risk.MEDIUM))
            self.assertTrue(decision.confirmation_required)
            self.assertTrue(decision.policy.reversible)
            for request in (
                ActionRequest(action, "offset", risk=Risk.MEDIUM),
                ActionRequest(action, arguments={"count": 1}, risk=Risk.MEDIUM),
            ):
                with self.assertRaises(ValueError):
                    evaluate(request)

    def test_word_deletions_are_parameterless_confirmed_and_reversible(self):
        for action in (
            "desktop.text.delete_previous_word",
            "desktop.text.delete_next_word",
        ):
            decision = evaluate(ActionRequest(action, risk=Risk.MEDIUM))
            self.assertTrue(decision.confirmation_required)
            self.assertTrue(decision.policy.reversible)
            for request in (
                ActionRequest(action, "word", risk=Risk.MEDIUM),
                ActionRequest(action, arguments={"count": 1}, risk=Risk.MEDIUM),
            ):
                with self.assertRaises(ValueError):
                    evaluate(request)

    def test_word_replacements_require_one_bounded_printable_target(self):
        for action in (
            "desktop.text.replace_previous_word",
            "desktop.text.replace_next_word",
        ):
            decision = evaluate(ActionRequest(action, "replacement", risk=Risk.MEDIUM))
            self.assertTrue(decision.confirmation_required)
            self.assertTrue(decision.policy.reversible)
            for request in (
                ActionRequest(action, risk=Risk.MEDIUM),
                ActionRequest(action, "hidden\u200bseparator", risk=Risk.MEDIUM),
                ActionRequest(action, "x" * 501, risk=Risk.MEDIUM),
                ActionRequest(action, "text", arguments={"count": 1}, risk=Risk.MEDIUM),
            ):
                with self.assertRaises(ValueError):
                    evaluate(request)

    def test_character_selections_are_parameterless_low_risk_and_reversible(self):
        for action in (
            "desktop.text.select_previous_character",
            "desktop.text.select_next_character",
        ):
            decision = evaluate(ActionRequest(action))
            self.assertFalse(decision.confirmation_required)
            self.assertTrue(decision.policy.reversible)
            for request in (
                ActionRequest(action, "offset"),
                ActionRequest(action, arguments={"count": 1}),
            ):
                with self.assertRaises(ValueError):
                    evaluate(request)

    def test_word_selections_are_parameterless_low_risk_and_reversible(self):
        for action in (
            "desktop.text.select_previous_word",
            "desktop.text.select_next_word",
        ):
            decision = evaluate(ActionRequest(action))
            self.assertFalse(decision.confirmation_required)
            self.assertTrue(decision.policy.reversible)
            for request in (
                ActionRequest(action, "word"),
                ActionRequest(action, arguments={"count": 1}),
            ):
                with self.assertRaises(ValueError):
                    evaluate(request)

    def test_current_line_selection_is_parameterless_low_risk_and_reversible(self):
        action = "desktop.text.select_current_line"
        decision = evaluate(ActionRequest(action))
        self.assertFalse(decision.confirmation_required)
        self.assertTrue(decision.policy.reversible)
        for request in (
            ActionRequest(action, "line"),
            ActionRequest(action, arguments={"include_newline": True}),
        ):
            with self.assertRaises(ValueError):
                evaluate(request)

    def test_current_line_deletion_is_parameterless_confirmed_and_reversible(self):
        action = "desktop.text.delete_current_line"
        decision = evaluate(ActionRequest(action, risk=Risk.MEDIUM))
        self.assertTrue(decision.confirmation_required)
        self.assertTrue(decision.policy.reversible)
        for request in (
            ActionRequest(action, "line", risk=Risk.MEDIUM),
            ActionRequest(action, arguments={"count": 1}, risk=Risk.MEDIUM),
        ):
            with self.assertRaises(ValueError):
                evaluate(request)

    def test_current_line_replacement_requires_bounded_printable_target(self):
        action = "desktop.text.replace_current_line"
        decision = evaluate(ActionRequest(action, "replacement", risk=Risk.MEDIUM))
        self.assertTrue(decision.confirmation_required)
        self.assertTrue(decision.policy.reversible)
        for target in ("", "x" * 501, "line\nbreak", "hidden\u200bseparator"):
            with self.assertRaises(ValueError):
                evaluate(ActionRequest(action, target, risk=Risk.MEDIUM))

    def test_line_insertions_require_bounded_printable_targets(self):
        for action in ("desktop.text.insert_line_above", "desktop.text.insert_line_below"):
            decision = evaluate(ActionRequest(action, "new line", risk=Risk.MEDIUM))
            self.assertTrue(decision.confirmation_required)
            self.assertTrue(decision.policy.reversible)
            for target in ("", "x" * 501, "two\nlines", "hidden\u200bseparator"):
                with self.assertRaises(ValueError):
                    evaluate(ActionRequest(action, target, risk=Risk.MEDIUM))

    def test_line_duplications_are_parameterless_confirmed_and_reversible(self):
        for action in (
            "desktop.text.duplicate_line_above",
            "desktop.text.duplicate_line_below",
        ):
            decision = evaluate(ActionRequest(action, risk=Risk.MEDIUM))
            self.assertTrue(decision.confirmation_required)
            self.assertTrue(decision.policy.reversible)
            for request in (
                ActionRequest(action, "content", risk=Risk.MEDIUM),
                ActionRequest(action, arguments={"count": 1}, risk=Risk.MEDIUM),
            ):
                with self.assertRaises(ValueError):
                    evaluate(request)

    def test_line_moves_are_parameterless_confirmed_and_reversible(self):
        for action in ("desktop.text.move_line_up", "desktop.text.move_line_down"):
            decision = evaluate(ActionRequest(action, risk=Risk.MEDIUM))
            self.assertTrue(decision.confirmation_required)
            self.assertTrue(decision.policy.reversible)
            for request in (
                ActionRequest(action, "content", risk=Risk.MEDIUM),
                ActionRequest(action, arguments={"count": 1}, risk=Risk.MEDIUM),
            ):
                with self.assertRaises(ValueError):
                    evaluate(request)

    def test_line_joins_are_parameterless_confirmed_and_reversible(self):
        for action in (
            "desktop.text.join_previous_line",
            "desktop.text.join_next_line",
        ):
            decision = evaluate(ActionRequest(action, risk=Risk.MEDIUM))
            self.assertTrue(decision.confirmation_required)
            self.assertTrue(decision.policy.reversible)
            for request in (
                ActionRequest(action, "content", risk=Risk.MEDIUM),
                ActionRequest(action, arguments={"count": 1}, risk=Risk.MEDIUM),
            ):
                with self.assertRaises(ValueError):
                    evaluate(request)

    def test_line_split_is_parameterless_confirmed_and_reversible(self):
        action = "desktop.text.split_line_at_caret"
        decision = evaluate(ActionRequest(action, risk=Risk.MEDIUM))
        self.assertTrue(decision.confirmation_required)
        self.assertTrue(decision.policy.reversible)
        for request in (
            ActionRequest(action, "content", risk=Risk.MEDIUM),
            ActionRequest(action, arguments={"count": 1}, risk=Risk.MEDIUM),
        ):
            with self.assertRaises(ValueError):
                evaluate(request)

    def test_line_indentation_is_parameterless_confirmed_and_reversible(self):
        for action in (
            "desktop.text.indent_current_line",
            "desktop.text.outdent_current_line",
        ):
            decision = evaluate(ActionRequest(action, risk=Risk.MEDIUM))
            self.assertTrue(decision.confirmation_required)
            self.assertTrue(decision.policy.reversible)
            for request in (
                ActionRequest(action, "content", risk=Risk.MEDIUM),
                ActionRequest(action, arguments={"count": 1}, risk=Risk.MEDIUM),
            ):
                with self.assertRaises(ValueError):
                    evaluate(request)

    def test_character_reads_are_parameterless_confirmed_and_reversible(self):
        for action in (
            "desktop.text.read_previous_character",
            "desktop.text.read_next_character",
        ):
            decision = evaluate(ActionRequest(action, risk=Risk.MEDIUM))
            self.assertTrue(decision.confirmation_required)
            self.assertTrue(decision.policy.reversible)
            for request in (
                ActionRequest(action, "content", risk=Risk.MEDIUM),
                ActionRequest(action, arguments={"count": 1}, risk=Risk.MEDIUM),
            ):
                with self.assertRaises(ValueError):
                    evaluate(request)

    def test_word_reads_are_parameterless_confirmed_and_reversible(self):
        for action in (
            "desktop.text.read_previous_word",
            "desktop.text.read_next_word",
        ):
            decision = evaluate(ActionRequest(action, risk=Risk.MEDIUM))
            self.assertTrue(decision.confirmation_required)
            self.assertTrue(decision.policy.reversible)
            for request in (
                ActionRequest(action, "content", risk=Risk.MEDIUM),
                ActionRequest(action, arguments={"limit": 5}, risk=Risk.MEDIUM),
            ):
                with self.assertRaises(ValueError):
                    evaluate(request)

    def test_selection_replacement_requires_one_bounded_printable_target(self):
        action = "desktop.text.replace_selection"
        decision = evaluate(ActionRequest(action, "replacement", risk=Risk.MEDIUM))
        self.assertTrue(decision.confirmation_required)
        self.assertTrue(decision.policy.reversible)
        for request in (
            ActionRequest(action, risk=Risk.MEDIUM),
            ActionRequest(action, "hidden\u200bseparator", risk=Risk.MEDIUM),
            ActionRequest(action, "x" * 501, risk=Risk.MEDIUM),
            ActionRequest(action, "text", arguments={"range": "selection"}, risk=Risk.MEDIUM),
        ):
            with self.assertRaises(ValueError):
                evaluate(request)

    def test_caret_boundary_moves_are_parameterless_low_risk_and_reversible(self):
        for action in (
            "desktop.text.caret_start",
            "desktop.text.caret_end",
            "desktop.text.caret_previous",
            "desktop.text.caret_next",
        ):
            decision = evaluate(ActionRequest(action))
            self.assertFalse(decision.confirmation_required)
            self.assertTrue(decision.policy.reversible)
            for request in (
                ActionRequest(action, "offset"),
                ActionRequest(action, arguments={"offset": 1}),
            ):
                with self.assertRaises(ValueError):
                    evaluate(request)

    def test_word_caret_moves_are_parameterless_low_risk_and_reversible(self):
        for action in (
            "desktop.text.caret_previous_word",
            "desktop.text.caret_next_word",
        ):
            decision = evaluate(ActionRequest(action))
            self.assertFalse(decision.confirmation_required)
            self.assertTrue(decision.policy.reversible)
            for request in (
                ActionRequest(action, "offset"),
                ActionRequest(action, arguments={"words": 2}),
            ):
                with self.assertRaises(ValueError):
                    evaluate(request)

    def test_caret_position_read_is_parameterless_low_risk_and_reversible(self):
        action = "desktop.text.caret_describe"
        decision = evaluate(ActionRequest(action))
        self.assertFalse(decision.confirmation_required)
        self.assertTrue(decision.policy.reversible)
        for request in (
            ActionRequest(action, "position"),
            ActionRequest(action, arguments={"include_text": True}),
        ):
            with self.assertRaises(ValueError):
                evaluate(request)

    def test_focused_text_paste_is_parameterless_confirmed_and_irreversible(self):
        action = "desktop.text.paste_focused"
        decision = evaluate(ActionRequest(action, risk=Risk.MEDIUM, reversible=False))
        self.assertTrue(decision.confirmation_required)
        self.assertFalse(decision.policy.reversible)
        for request in (
            ActionRequest(action, "text", risk=Risk.MEDIUM, reversible=False),
            ActionRequest(action, arguments={"text": "secret"}, risk=Risk.MEDIUM, reversible=False),
            ActionRequest(action, risk=Risk.MEDIUM, reversible=True),
        ):
            with self.assertRaises(ValueError):
                evaluate(request)

    def test_shell_like_app_identifier_rejected(self):
        with self.assertRaises(ValueError):
            evaluate(ActionRequest("app.launch", "firefox;rm"))

    def test_relative_path_rejected(self):
        with self.assertRaisesRegex(ValueError, "absolute"):
            evaluate(ActionRequest("file.open", "relative.txt"))

    def test_unknown_action_rejected(self):
        with self.assertRaisesRegex(ValueError, "allowlisted"):
            evaluate(ActionRequest("shell.execute"))

    def test_volume_range(self):
        with self.assertRaises(ValueError):
            evaluate(ActionRequest("audio.volume.set", arguments={"percent": 999}))

    def test_slider_requires_exact_integer_percentage_and_name(self):
        for request in (
            ActionRequest("desktop.slider.set_percent", "", arguments={"percent": 50}, risk=Risk.MEDIUM),
            ActionRequest("desktop.slider.set_percent", "Zoom", arguments={"percent": 101}, risk=Risk.MEDIUM),
            ActionRequest("desktop.slider.set_percent", "Zoom", arguments={"percent": 50.0}, risk=Risk.MEDIUM),
            ActionRequest("desktop.slider.set_percent", "Zoom", arguments={"percent": 50, "extra": 1}, risk=Risk.MEDIUM),
        ):
            with self.subTest(request=request), self.assertRaises(ValueError):
                evaluate(request)

    def test_checkbox_requires_exact_boolean_argument(self):
        for arguments in ({}, {"checked": 1}, {"checked": True, "extra": False}):
            with self.subTest(arguments=arguments), self.assertRaises(ValueError):
                evaluate(
                    ActionRequest(
                        "desktop.checkbox.set_checked",
                        "Updates",
                        arguments=arguments,
                        risk=Risk.MEDIUM,
                    )
                )

    def test_switch_requires_exact_boolean_argument(self):
        with self.assertRaises(ValueError):
            evaluate(
                ActionRequest(
                    "desktop.switch.set_enabled",
                    "Wi-Fi",
                    arguments={"checked": 1},
                    risk=Risk.MEDIUM,
                )
            )

    def test_radio_rejects_arguments(self):
        with self.assertRaises(ValueError):
            evaluate(
                ActionRequest(
                    "desktop.radio.select_named",
                    "Dark",
                    arguments={"checked": True},
                    risk=Risk.MEDIUM,
                )
            )

    def test_combo_requires_exact_printable_item_argument(self):
        for arguments in ({}, {"item": 1}, {"item": ""}, {"item": "Deutsch", "extra": 1}):
            with self.subTest(arguments=arguments), self.assertRaises(ValueError):
                evaluate(
                    ActionRequest(
                        "desktop.combo.select_item",
                        "Language",
                        arguments=arguments,
                        risk=Risk.MEDIUM,
                    )
                )

    def test_spin_button_requires_one_finite_bounded_number(self):
        for arguments in ({}, {"value": True}, {"value": float("inf")}, {"value": 10**13}, {"value": 2, "extra": 1}):
            with self.subTest(arguments=arguments), self.assertRaises(ValueError):
                evaluate(
                    ActionRequest(
                        "desktop.spin_button.set_value",
                        "Copies",
                        arguments=arguments,
                        risk=Risk.MEDIUM,
                    )
                )


if __name__ == "__main__":
    unittest.main()

