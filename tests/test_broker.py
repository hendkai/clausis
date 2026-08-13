import tempfile
import unittest
from dataclasses import replace
from datetime import timedelta
from pathlib import Path

from clausis.audit import AuditLog
from clausis.broker import ActionBroker, SafeExecutor
from clausis.capabilities import CapabilityAuthority
from clausis.models import ActionRequest, Origin, Risk, utc_now


class BrokerTests(unittest.TestCase):
    def setUp(self):
        self.authority = CapabilityAuthority(b"c" * 32)
        self.broker = ActionBroker(self.authority, SafeExecutor(dry_run=True))

    def test_safe_action_dry_runs(self):
        result = self.broker.submit(ActionRequest("audio.volume.up"))
        self.assertEqual(result.status, "dry_run")
        self.assertEqual(result.details["argv"][-1], "5%+")

    def test_clipboard_clear_uses_fixed_wayland_argv(self):
        request = ActionRequest(
            "desktop.clipboard.clear", risk=Risk.MEDIUM, reversible=False
        )
        approved = replace(request, capability_token=self.authority.issue(request))
        result = self.broker.submit(approved)
        self.assertEqual(result.status, "dry_run")
        self.assertEqual(result.details["argv"], ["wl-copy", "--clear"])

    def test_risky_action_requires_confirmation(self):
        request = ActionRequest("network.wifi.disable", risk=Risk.MEDIUM)
        result = self.broker.submit(request)
        self.assertEqual(result.status, "confirmation_required")

    def test_accessibility_toggle_commands_use_fixed_gsettings_argv(self):
        expected = {
            "accessibility.screen_keyboard.enable": ("screen-keyboard-enabled", "true"),
            "accessibility.screen_reader.enable": ("screen-reader-enabled", "true"),
            "accessibility.screen_magnifier.enable": ("screen-magnifier-enabled", "true"),
            "accessibility.screen_magnifier.disable": ("screen-magnifier-enabled", "false"),
        }
        for action, (key, value) in expected.items():
            request = ActionRequest(action, risk=Risk.MEDIUM)
            approved = replace(request, capability_token=self.authority.issue(request))
            result = self.broker.submit(approved)
            self.assertEqual(result.status, "dry_run")
            self.assertEqual(
                result.details["argv"],
                [
                    "gsettings",
                    "set",
                    "org.gnome.desktop.a11y.applications",
                    key,
                    value,
                ],
            )

    def test_orca_speech_recovery_uses_fixed_adapter_argv(self):
        request = ActionRequest(
            "accessibility.screen_reader.restart_with_speech", risk=Risk.MEDIUM
        )
        approved = replace(request, capability_token=self.authority.issue(request))
        result = self.broker.submit(approved)
        self.assertEqual(result.status, "dry_run")
        self.assertEqual(result.details["argv"], ["clausis-orca-control", "restart"])

    def test_magnifier_zoom_uses_validated_gsettings_double(self):
        request = ActionRequest(
            "accessibility.screen_magnifier.set_percent",
            arguments={"percent": 225},
            risk=Risk.MEDIUM,
        )
        approved = replace(request, capability_token=self.authority.issue(request))
        result = self.broker.submit(approved)
        self.assertEqual(result.status, "dry_run")
        self.assertEqual(
            result.details["argv"],
            [
                "gsettings",
                "set",
                "org.gnome.desktop.a11y.magnifier",
                "mag-factor",
                "2.25",
            ],
        )

    def test_magnifier_inversion_uses_fixed_boolean_gsettings_argv(self):
        for action, value in (
            ("accessibility.screen_magnifier.invert_lightness.enable", "true"),
            ("accessibility.screen_magnifier.invert_lightness.disable", "false"),
        ):
            request = ActionRequest(action, risk=Risk.MEDIUM)
            approved = replace(request, capability_token=self.authority.issue(request))
            result = self.broker.submit(approved)
            self.assertEqual(result.status, "dry_run")
            self.assertEqual(
                result.details["argv"],
                [
                    "gsettings",
                    "set",
                    "org.gnome.desktop.a11y.magnifier",
                    "invert-lightness",
                    value,
                ],
            )

    def test_magnifier_saturation_uses_validated_gsettings_double(self):
        request = ActionRequest(
            "accessibility.screen_magnifier.set_saturation",
            arguments={"percent": 35},
            risk=Risk.MEDIUM,
        )
        approved = replace(request, capability_token=self.authority.issue(request))
        result = self.broker.submit(approved)
        self.assertEqual(result.status, "dry_run")
        self.assertEqual(
            result.details["argv"],
            [
                "gsettings",
                "set",
                "org.gnome.desktop.a11y.magnifier",
                "color-saturation",
                "0.35",
            ],
        )

    def test_magnifier_brightness_and_contrast_use_fixed_adapter_argv(self):
        for action, kind, percent, fraction in (
            ("accessibility.screen_magnifier.set_brightness", "brightness", -30, "-0.30"),
            ("accessibility.screen_magnifier.set_contrast", "contrast", 45, "0.45"),
        ):
            with self.subTest(action=action):
                request = ActionRequest(action, arguments={"percent": percent}, risk=Risk.MEDIUM)
                approved = replace(request, capability_token=self.authority.issue(request))
                result = self.broker.submit(approved)
                self.assertEqual(result.status, "dry_run")
                self.assertEqual(
                    result.details["argv"],
                    ["clausis-magnifier-filter", kind, fraction],
                )
    def test_magnifier_screen_position_uses_validated_schema_enum(self):
        request = ActionRequest(
            "accessibility.screen_magnifier.set_screen_position",
            arguments={"position": "left-half"},
            risk=Risk.MEDIUM,
        )
        approved = replace(request, capability_token=self.authority.issue(request))
        result = self.broker.submit(approved)
        self.assertEqual(result.status, "dry_run")
        self.assertEqual(
            result.details["argv"],
            [
                "gsettings", "set", "org.gnome.desktop.a11y.magnifier",
                "screen-position", "left-half",
            ],
        )

    def test_magnifier_cross_hairs_use_fixed_boolean_gsettings_argv(self):
        for action, value in (
            ("accessibility.screen_magnifier.cross_hairs.enable", "true"),
            ("accessibility.screen_magnifier.cross_hairs.disable", "false"),
        ):
            with self.subTest(action=action):
                request = ActionRequest(action, risk=Risk.MEDIUM)
                approved = replace(request, capability_token=self.authority.issue(request))
                result = self.broker.submit(approved)
                self.assertEqual(result.status, "dry_run")
                self.assertEqual(
                    result.details["argv"],
                    [
                        "gsettings", "set", "org.gnome.desktop.a11y.magnifier",
                        "show-cross-hairs", value,
                    ],
                )

    def test_magnifier_lens_mode_and_edge_scrolling_use_fixed_boolean_argv(self):
        for action, key, value in (
            ("accessibility.screen_magnifier.lens_mode.enable", "lens-mode", "true"),
            ("accessibility.screen_magnifier.lens_mode.disable", "lens-mode", "false"),
            ("accessibility.screen_magnifier.scroll_at_edges.enable", "scroll-at-edges", "true"),
            ("accessibility.screen_magnifier.scroll_at_edges.disable", "scroll-at-edges", "false"),
        ):
            with self.subTest(action=action):
                request = ActionRequest(action, risk=Risk.MEDIUM)
                approved = replace(request, capability_token=self.authority.issue(request))
                result = self.broker.submit(approved)
                self.assertEqual(result.status, "dry_run")
                self.assertEqual(
                    result.details["argv"],
                    ["gsettings", "set", "org.gnome.desktop.a11y.magnifier", key, value],
                )

    def test_magnifier_cross_hairs_opacity_uses_validated_gsettings_double(self):
        request = ActionRequest(
            "accessibility.screen_magnifier.cross_hairs.set_opacity",
            arguments={"percent": 42},
            risk=Risk.MEDIUM,
        )
        approved = replace(request, capability_token=self.authority.issue(request))
        result = self.broker.submit(approved)
        self.assertEqual(result.status, "dry_run")
        self.assertEqual(
            result.details["argv"],
            [
                "gsettings", "set", "org.gnome.desktop.a11y.magnifier",
                "cross-hairs-opacity", "0.42",
            ],
        )

    def test_magnifier_cross_hairs_clip_uses_fixed_boolean_gsettings_argv(self):
        for action, value in (
            ("accessibility.screen_magnifier.cross_hairs.clip.enable", "true"),
            ("accessibility.screen_magnifier.cross_hairs.clip.disable", "false"),
        ):
            with self.subTest(action=action):
                request = ActionRequest(action, risk=Risk.MEDIUM)
                approved = replace(request, capability_token=self.authority.issue(request))
                result = self.broker.submit(approved)
                self.assertEqual(result.status, "dry_run")
                self.assertEqual(
                    result.details["argv"],
                    [
                        "gsettings", "set", "org.gnome.desktop.a11y.magnifier",
                        "cross-hairs-clip", value,
                    ],
                )

    def test_magnifier_cross_hairs_length_uses_validated_integer_argv(self):
        request = ActionRequest(
            "accessibility.screen_magnifier.cross_hairs.set_length",
            arguments={"pixels": 640},
            risk=Risk.MEDIUM,
        )
        approved = replace(request, capability_token=self.authority.issue(request))
        result = self.broker.submit(approved)
        self.assertEqual(result.status, "dry_run")
        self.assertEqual(
            result.details["argv"],
            [
                "gsettings", "set", "org.gnome.desktop.a11y.magnifier",
                "cross-hairs-length", "640",
            ],
        )

    def test_magnifier_cross_hairs_thickness_uses_validated_integer_argv(self):
        request = ActionRequest(
            "accessibility.screen_magnifier.cross_hairs.set_thickness",
            arguments={"pixels": 12},
            risk=Risk.MEDIUM,
        )
        approved = replace(request, capability_token=self.authority.issue(request))
        result = self.broker.submit(approved)
        self.assertEqual(result.status, "dry_run")
        self.assertEqual(
            result.details["argv"],
            [
                "gsettings", "set", "org.gnome.desktop.a11y.magnifier",
                "cross-hairs-thickness", "12",
            ],
        )

    def test_magnifier_cross_hairs_color_uses_canonical_hex_argv(self):
        request = ActionRequest(
            "accessibility.screen_magnifier.cross_hairs.set_color",
            arguments={"red": 12, "green": 34, "blue": 255},
            risk=Risk.MEDIUM,
        )
        approved = replace(request, capability_token=self.authority.issue(request))
        result = self.broker.submit(approved)
        self.assertEqual(result.status, "dry_run")
        self.assertEqual(
            result.details["argv"],
            [
                "gsettings", "set", "org.gnome.desktop.a11y.magnifier",
                "cross-hairs-color", "#0c22ff",
            ],
        )

    def test_magnifier_focus_tracking_uses_validated_schema_enum(self):
        request = ActionRequest(
            "accessibility.screen_magnifier.set_focus_tracking",
            arguments={"mode": "push"},
            risk=Risk.MEDIUM,
        )
        approved = replace(request, capability_token=self.authority.issue(request))
        result = self.broker.submit(approved)
        self.assertEqual(result.status, "dry_run")
        self.assertEqual(
            result.details["argv"],
            [
                "gsettings", "set", "org.gnome.desktop.a11y.magnifier",
                "focus-tracking", "push",
            ],
        )

    def test_magnifier_caret_and_mouse_tracking_use_validated_schema_enum(self):
        for action, key in (
            ("accessibility.screen_magnifier.set_caret_tracking", "caret-tracking"),
            ("accessibility.screen_magnifier.set_mouse_tracking", "mouse-tracking"),
        ):
            with self.subTest(action=action):
                request = ActionRequest(action, arguments={"mode": "centered"}, risk=Risk.MEDIUM)
                approved = replace(request, capability_token=self.authority.issue(request))
                result = self.broker.submit(approved)
                self.assertEqual(result.status, "dry_run")
                self.assertEqual(
                    result.details["argv"],
                    [
                        "gsettings", "set", "org.gnome.desktop.a11y.magnifier",
                        key, "centered",
                    ],
                )

    def test_confirmed_action_runs(self):
        request = ActionRequest("network.wifi.disable", origin=Origin.HERMES, risk=Risk.MEDIUM)
        token = self.authority.issue(request)
        result = self.broker.submit(replace(request, capability_token=token))
        self.assertEqual(result.status, "dry_run")

    def test_replayed_action_denied(self):
        request = ActionRequest("network.wifi.disable", origin=Origin.HERMES, risk=Risk.MEDIUM)
        approved = replace(request, capability_token=self.authority.issue(request))
        self.assertEqual(self.broker.submit(approved).status, "dry_run")
        self.assertEqual(self.broker.submit(approved).status, "denied")

    def test_unsupported_platform_adapter_fails_closed(self):
        request = ActionRequest("app.close", "firefox", risk=Risk.MEDIUM)
        approved = replace(request, capability_token=self.authority.issue(request))
        self.assertEqual(self.broker.submit(approved).status, "failed")

    def test_audit_is_written_and_valid(self):
        with tempfile.TemporaryDirectory() as directory:
            audit = AuditLog(Path(directory) / "audit.jsonl", b"d" * 32)
            broker = ActionBroker(self.authority, SafeExecutor(dry_run=True), audit_log=audit)
            broker.submit(ActionRequest("audio.volume.up"))
            self.assertTrue(audit.verify())

    def test_expired_low_risk_request_is_denied(self):
        request = ActionRequest(
            "audio.volume.up",
            expires_at=(utc_now() - timedelta(seconds=1)).isoformat(),
        )
        self.assertEqual(self.broker.submit(request).status, "denied")


if __name__ == "__main__":
    unittest.main()
