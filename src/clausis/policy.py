"""Action allowlist, argument validation and confirmation policy."""

from __future__ import annotations

from dataclasses import dataclass
import math
import re
from typing import Any, Callable, Dict, Mapping, Optional

from .models import ActionRequest, Origin, Risk


Validator = Callable[[ActionRequest], None]


@dataclass(frozen=True)
class ActionPolicy:
    minimum_risk: Risk
    reversible: bool
    command: Optional[tuple] = None
    validator: Optional[Validator] = None
    privileged: bool = False


SAFE_IDENTIFIER = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._+@:-]{0,127}$")
SAFE_SETTING = re.compile(r"^[a-z][a-z0-9-]{0,63}$")


def _target_required(request: ActionRequest) -> None:
    if not request.target:
        raise ValueError("target is required")


def _no_parameters(request: ActionRequest) -> None:
    if request.target or request.arguments:
        raise ValueError("action accepts no target or arguments")


def _safe_identifier(request: ActionRequest) -> None:
    _target_required(request)
    if not SAFE_IDENTIFIER.fullmatch(request.target):
        raise ValueError("target is not an allowed identifier")


def _path(request: ActionRequest) -> None:
    _target_required(request)
    if not request.target.startswith("/") or "\x00" in request.target:
        raise ValueError("target must be an absolute path")


def _percentage(request: ActionRequest) -> None:
    value = request.arguments.get("percent")
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not 0 <= value <= 150:
        raise ValueError("percent must be between 0 and 150")


def _slider_percentage(request: ActionRequest) -> None:
    _accessible_name(request)
    value = request.arguments.get("percent")
    if isinstance(value, bool) or not isinstance(value, int) or not 0 <= value <= 100:
        raise ValueError("slider percent must be an integer between 0 and 100")
    if set(request.arguments) != {"percent"}:
        raise ValueError("slider action accepts only percent")


def _magnifier_percentage(request: ActionRequest) -> None:
    if request.target:
        raise ValueError("magnifier zoom accepts no target")
    value = request.arguments.get("percent")
    if isinstance(value, bool) or not isinstance(value, int) or not 100 <= value <= 3200:
        raise ValueError("magnifier percent must be an integer between 100 and 3200")
    if set(request.arguments) != {"percent"}:
        raise ValueError("magnifier zoom accepts only percent")


def _magnifier_saturation(request: ActionRequest) -> None:
    if request.target:
        raise ValueError("magnifier saturation accepts no target")
    value = request.arguments.get("percent")
    if isinstance(value, bool) or not isinstance(value, int) or not 0 <= value <= 100:
        raise ValueError("magnifier saturation must be an integer between 0 and 100")
    if set(request.arguments) != {"percent"}:
        raise ValueError("magnifier saturation accepts only percent")


def _magnifier_filter_percentage(request: ActionRequest) -> None:
    if request.target:
        raise ValueError("magnifier filter accepts no target")
    value = request.arguments.get("percent")
    if isinstance(value, bool) or not isinstance(value, int) or not -75 <= value <= 75:
        raise ValueError("magnifier filter percent must be an integer between -75 and 75")
    if set(request.arguments) != {"percent"}:
        raise ValueError("magnifier filter accepts only percent")


def _magnifier_cross_hairs_opacity(request: ActionRequest) -> None:
    if request.target:
        raise ValueError("magnifier crosshairs opacity accepts no target")
    value = request.arguments.get("percent")
    if isinstance(value, bool) or not isinstance(value, int) or not 0 <= value <= 100:
        raise ValueError("magnifier crosshairs opacity must be an integer between 0 and 100")
    if set(request.arguments) != {"percent"}:
        raise ValueError("magnifier crosshairs opacity accepts only percent")


def _magnifier_cross_hairs_length(request: ActionRequest) -> None:
    if request.target:
        raise ValueError("magnifier crosshairs length accepts no target")
    value = request.arguments.get("pixels")
    if isinstance(value, bool) or not isinstance(value, int) or not 20 <= value <= 4096:
        raise ValueError("magnifier crosshairs length must be an integer between 20 and 4096")
    if set(request.arguments) != {"pixels"}:
        raise ValueError("magnifier crosshairs length accepts only pixels")


def _magnifier_cross_hairs_thickness(request: ActionRequest) -> None:
    if request.target:
        raise ValueError("magnifier crosshairs thickness accepts no target")
    value = request.arguments.get("pixels")
    if isinstance(value, bool) or not isinstance(value, int) or not 1 <= value <= 100:
        raise ValueError("magnifier crosshairs thickness must be an integer between 1 and 100")
    if set(request.arguments) != {"pixels"}:
        raise ValueError("magnifier crosshairs thickness accepts only pixels")


def _magnifier_cross_hairs_color(request: ActionRequest) -> None:
    if request.target:
        raise ValueError("magnifier crosshairs color accepts no target")
    if set(request.arguments) != {"red", "green", "blue"}:
        raise ValueError("magnifier crosshairs color accepts only red, green and blue")
    for channel in ("red", "green", "blue"):
        value = request.arguments[channel]
        if isinstance(value, bool) or not isinstance(value, int) or not 0 <= value <= 255:
            raise ValueError(f"magnifier crosshairs {channel} must be an integer between 0 and 255")


def _magnifier_screen_position(request: ActionRequest) -> None:
    if request.target:
        raise ValueError("magnifier screen position accepts no target")
    if set(request.arguments) != {"position"}:
        raise ValueError("magnifier screen position accepts only position")
    if request.arguments.get("position") not in {
        "full-screen",
        "top-half",
        "bottom-half",
        "left-half",
        "right-half",
    }:
        raise ValueError("invalid magnifier screen position")


def _magnifier_focus_tracking(request: ActionRequest) -> None:
    if request.target:
        raise ValueError("magnifier focus tracking accepts no target")
    if set(request.arguments) != {"mode"}:
        raise ValueError("magnifier focus tracking accepts only mode")
    if request.arguments.get("mode") not in {"none", "centered", "proportional", "push"}:
        raise ValueError("invalid magnifier focus tracking mode")


def _magnifier_caret_tracking(request: ActionRequest) -> None:
    if request.target:
        raise ValueError("magnifier caret tracking accepts no target")
    if set(request.arguments) != {"mode"}:
        raise ValueError("magnifier caret tracking accepts only mode")
    if request.arguments.get("mode") not in {"none", "centered", "proportional", "push"}:
        raise ValueError("invalid magnifier caret tracking mode")


def _magnifier_mouse_tracking(request: ActionRequest) -> None:
    if request.target:
        raise ValueError("magnifier mouse tracking accepts no target")
    if set(request.arguments) != {"mode"}:
        raise ValueError("magnifier mouse tracking accepts only mode")
    if request.arguments.get("mode") not in {"none", "centered", "proportional", "push"}:
        raise ValueError("invalid magnifier mouse tracking mode")


def _checkbox_state(request: ActionRequest) -> None:
    _accessible_name(request)
    if set(request.arguments) != {"checked"} or not isinstance(
        request.arguments.get("checked"), bool
    ):
        raise ValueError("checkbox action requires one boolean checked argument")


def _radio_name(request: ActionRequest) -> None:
    _accessible_name(request)
    if request.arguments:
        raise ValueError("radio action accepts no arguments")


def _combo_item(request: ActionRequest) -> None:
    _accessible_name(request)
    if set(request.arguments) != {"item"}:
        raise ValueError("combo action requires one item argument")
    item = request.arguments.get("item")
    if not isinstance(item, str):
        raise ValueError("combo item must be a string")
    normalized = " ".join(item.split())
    if not normalized or len(normalized) > 120 or any(ord(character) < 32 for character in normalized):
        raise ValueError("combo item must be between 1 and 120 printable characters")


def _spin_value(request: ActionRequest) -> None:
    _accessible_name(request)
    if set(request.arguments) != {"value"}:
        raise ValueError("spin-button action requires one value argument")
    value = request.arguments.get("value")
    if (
        isinstance(value, bool)
        or not isinstance(value, (int, float))
        or not math.isfinite(float(value))
        or abs(float(value)) > 1_000_000_000_000
    ):
        raise ValueError("spin-button value must be a finite bounded number")


def _setting(request: ActionRequest) -> None:
    if request.target and not SAFE_SETTING.fullmatch(request.target):
        raise ValueError("invalid settings panel")


def _control_number(request: ActionRequest) -> None:
    if not request.target.isdigit() or not 1 <= int(request.target) <= 30:
        raise ValueError("control number must be between 1 and 30")


def _notification_number(request: ActionRequest) -> None:
    if request.arguments or not request.target.isdigit() or not 1 <= int(request.target) <= 20:
        raise ValueError("notification number must be between 1 and 20 without arguments")


def _accessible_name(request: ActionRequest) -> None:
    _target_required(request)
    normalized = " ".join(request.target.split())
    if not normalized or len(normalized) > 120 or any(
        ord(character) < 32 for character in normalized
    ):
        raise ValueError("accessible name must be between 1 and 120 printable characters")


def _spoken_text(request: ActionRequest) -> None:
    _target_required(request)
    if len(request.target) > 500 or any(not character.isprintable() for character in request.target):
        raise ValueError("spoken text must be between 1 and 500 printable characters")
    if request.arguments:
        raise ValueError("spoken text action accepts no arguments")


def _visible_file_name(request: ActionRequest) -> None:
    _target_required(request)
    normalized = " ".join(request.target.split())
    if (
        not normalized
        or len(normalized) > 255
        or "/" in normalized
        or normalized in {".", ".."}
    ):
        raise ValueError("visible file name must be a single 1 to 255 character name")


def _permission_decision(request: ActionRequest) -> None:
    if request.target not in {"allow", "deny"}:
        raise ValueError("permission decision must be allow or deny")


def _file_dialog_decision(request: ActionRequest) -> None:
    if request.target not in {"accept", "cancel"} or request.arguments:
        raise ValueError("file-dialog decision must be accept or cancel without arguments")


def _standard_dialog_decision(request: ActionRequest) -> None:
    if request.target not in {"accept", "cancel", "retry", "apply"} or request.arguments:
        raise ValueError(
            "standard-dialog decision must be accept, cancel, retry or apply without arguments"
        )


def _canonical_absolute_path(request: ActionRequest) -> None:
    _target_required(request)
    path = request.target
    if (
        len(path) > 4096
        or not path.startswith("/")
        or path.startswith("//")
        or "//" in path
        or any(ord(character) < 32 for character in path)
        or any(part in {".", ".."} for part in path.split("/"))
    ):
        raise ValueError("path must be an absolute canonical POSIX path")


ACTION_POLICIES: Mapping[str, ActionPolicy] = {
    "app.launch": ActionPolicy(Risk.LOW, True, ("gtk-launch",), _safe_identifier),
    "app.close": ActionPolicy(Risk.MEDIUM, True, None, _safe_identifier),
    "desktop.overview": ActionPolicy(Risk.LOW, True),
    "desktop.applications": ActionPolicy(Risk.LOW, True),
    "desktop.quick_settings": ActionPolicy(Risk.LOW, True),
    "desktop.notifications": ActionPolicy(Risk.LOW, True),
    "desktop.notifications.read": ActionPolicy(Risk.MEDIUM, True, None, _no_parameters),
    "desktop.notifications.dismiss": ActionPolicy(Risk.HIGH, False, None, _notification_number),
    "desktop.window.next": ActionPolicy(Risk.LOW, True),
    "desktop.window.previous": ActionPolicy(Risk.LOW, True),
    "desktop.window.minimize": ActionPolicy(Risk.LOW, True),
    "desktop.window.maximize": ActionPolicy(Risk.LOW, True),
    "desktop.window.restore": ActionPolicy(Risk.LOW, True),
    "desktop.window.close": ActionPolicy(Risk.MEDIUM, True),
    "desktop.window.workspace_previous": ActionPolicy(Risk.MEDIUM, True),
    "desktop.window.workspace_next": ActionPolicy(Risk.MEDIUM, True),
    "desktop.context.describe": ActionPolicy(Risk.LOW, True),
    "desktop.controls.list": ActionPolicy(Risk.LOW, True),
    "desktop.control.activate": ActionPolicy(Risk.MEDIUM, True, None, _control_number),
    "desktop.control.activate_named": ActionPolicy(Risk.MEDIUM, True, None, _accessible_name),
    "desktop.focus.next": ActionPolicy(Risk.LOW, True),
    "desktop.focus.previous": ActionPolicy(Risk.LOW, True),
    "desktop.focus.named": ActionPolicy(Risk.LOW, True, None, _accessible_name),
    "desktop.text.read_focused": ActionPolicy(Risk.LOW, True),
    "desktop.text.copy_focused": ActionPolicy(Risk.MEDIUM, False, None, _no_parameters),
    "desktop.text.copy_selection": ActionPolicy(Risk.MEDIUM, False, None, _no_parameters),
    "desktop.text.read_selection": ActionPolicy(Risk.MEDIUM, True, None, _no_parameters),
    "desktop.text.select_all": ActionPolicy(Risk.LOW, True, None, _no_parameters),
    "desktop.text.clear_selection": ActionPolicy(Risk.LOW, True, None, _no_parameters),
    "desktop.text.delete_selection": ActionPolicy(Risk.MEDIUM, True, None, _no_parameters),
    "desktop.text.insert_at_caret": ActionPolicy(Risk.MEDIUM, True, None, _spoken_text),
    "desktop.text.delete_previous_character": ActionPolicy(Risk.MEDIUM, True, None, _no_parameters),
    "desktop.text.delete_next_character": ActionPolicy(Risk.MEDIUM, True, None, _no_parameters),
    "desktop.text.delete_previous_word": ActionPolicy(Risk.MEDIUM, True, None, _no_parameters),
    "desktop.text.delete_next_word": ActionPolicy(Risk.MEDIUM, True, None, _no_parameters),
    "desktop.text.replace_previous_word": ActionPolicy(Risk.MEDIUM, True, None, _spoken_text),
    "desktop.text.replace_next_word": ActionPolicy(Risk.MEDIUM, True, None, _spoken_text),
    "desktop.text.select_previous_character": ActionPolicy(Risk.LOW, True, None, _no_parameters),
    "desktop.text.select_next_character": ActionPolicy(Risk.LOW, True, None, _no_parameters),
    "desktop.text.select_previous_word": ActionPolicy(Risk.LOW, True, None, _no_parameters),
    "desktop.text.select_next_word": ActionPolicy(Risk.LOW, True, None, _no_parameters),
    "desktop.text.replace_selection": ActionPolicy(Risk.MEDIUM, True, None, _spoken_text),
    "desktop.text.read_previous_character": ActionPolicy(Risk.MEDIUM, True, None, _no_parameters),
    "desktop.text.read_next_character": ActionPolicy(Risk.MEDIUM, True, None, _no_parameters),
    "desktop.text.read_previous_word": ActionPolicy(Risk.MEDIUM, True, None, _no_parameters),
    "desktop.text.read_next_word": ActionPolicy(Risk.MEDIUM, True, None, _no_parameters),
    "desktop.text.read_current_line": ActionPolicy(Risk.MEDIUM, True, None, _no_parameters),
    "desktop.text.caret_start": ActionPolicy(Risk.LOW, True, None, _no_parameters),
    "desktop.text.caret_end": ActionPolicy(Risk.LOW, True, None, _no_parameters),
    "desktop.text.caret_previous": ActionPolicy(Risk.LOW, True, None, _no_parameters),
    "desktop.text.caret_next": ActionPolicy(Risk.LOW, True, None, _no_parameters),
    "desktop.text.caret_previous_word": ActionPolicy(Risk.LOW, True, None, _no_parameters),
    "desktop.text.caret_next_word": ActionPolicy(Risk.LOW, True, None, _no_parameters),
    "desktop.text.caret_line_start": ActionPolicy(Risk.LOW, True, None, _no_parameters),
    "desktop.text.caret_line_end": ActionPolicy(Risk.LOW, True, None, _no_parameters),
    "desktop.text.select_current_line": ActionPolicy(Risk.LOW, True, None, _no_parameters),
    "desktop.text.delete_current_line": ActionPolicy(Risk.MEDIUM, True, None, _no_parameters),
    "desktop.text.replace_current_line": ActionPolicy(Risk.MEDIUM, True, None, _spoken_text),
    "desktop.text.insert_line_above": ActionPolicy(Risk.MEDIUM, True, None, _spoken_text),
    "desktop.text.insert_line_below": ActionPolicy(Risk.MEDIUM, True, None, _spoken_text),
    "desktop.text.duplicate_line_above": ActionPolicy(Risk.MEDIUM, True, None, _no_parameters),
    "desktop.text.duplicate_line_below": ActionPolicy(Risk.MEDIUM, True, None, _no_parameters),
    "desktop.text.move_line_up": ActionPolicy(Risk.MEDIUM, True, None, _no_parameters),
    "desktop.text.move_line_down": ActionPolicy(Risk.MEDIUM, True, None, _no_parameters),
    "desktop.text.join_previous_line": ActionPolicy(Risk.MEDIUM, True, None, _no_parameters),
    "desktop.text.join_next_line": ActionPolicy(Risk.MEDIUM, True, None, _no_parameters),
    "desktop.text.split_line_at_caret": ActionPolicy(Risk.MEDIUM, True, None, _no_parameters),
    "desktop.text.indent_current_line": ActionPolicy(Risk.MEDIUM, True, None, _no_parameters),
    "desktop.text.outdent_current_line": ActionPolicy(Risk.MEDIUM, True, None, _no_parameters),
    "desktop.text.caret_describe": ActionPolicy(Risk.LOW, True, None, _no_parameters),
    "desktop.text.paste_focused": ActionPolicy(Risk.MEDIUM, False, None, _no_parameters),
    "desktop.text.set": ActionPolicy(Risk.MEDIUM, True, None, _spoken_text),
    "desktop.text.clear": ActionPolicy(Risk.MEDIUM, True),
    "desktop.selection.select_named": ActionPolicy(Risk.MEDIUM, True, None, _accessible_name),
    "desktop.file_dialog.select_visible": ActionPolicy(Risk.MEDIUM, True, None, _visible_file_name),
    "desktop.file_dialog.set_name": ActionPolicy(Risk.MEDIUM, True, None, _visible_file_name),
    "desktop.file_dialog.set_location": ActionPolicy(Risk.MEDIUM, True, None, _canonical_absolute_path),
    "desktop.file_dialog.open_visible_folder": ActionPolicy(Risk.MEDIUM, True, None, _visible_file_name),
    "desktop.file_dialog.decide": ActionPolicy(Risk.MEDIUM, True, None, _file_dialog_decision),
    "desktop.standard_dialog.decide": ActionPolicy(Risk.HIGH, False, None, _standard_dialog_decision),
    "desktop.standard_dialog.read": ActionPolicy(Risk.MEDIUM, True, None, _no_parameters),
    "desktop.standard_dialog.dismiss": ActionPolicy(Risk.HIGH, False, None, _no_parameters),
    "desktop.tree.expand_named": ActionPolicy(Risk.MEDIUM, True, None, _accessible_name),
    "desktop.tree.collapse_named": ActionPolicy(Risk.MEDIUM, True, None, _accessible_name),
    "desktop.table.select_row": ActionPolicy(Risk.MEDIUM, True, None, _accessible_name),
    "desktop.tabs.select_named": ActionPolicy(Risk.MEDIUM, True, None, _accessible_name),
    "desktop.slider.set_percent": ActionPolicy(Risk.MEDIUM, True, None, _slider_percentage),
    "desktop.progress.read_named": ActionPolicy(Risk.LOW, True, None, _accessible_name),
    "desktop.checkbox.set_checked": ActionPolicy(Risk.MEDIUM, True, None, _checkbox_state),
    "desktop.switch.set_enabled": ActionPolicy(Risk.MEDIUM, True, None, _checkbox_state),
    "desktop.radio.select_named": ActionPolicy(Risk.MEDIUM, True, None, _radio_name),
    "desktop.combo.select_item": ActionPolicy(Risk.MEDIUM, True, None, _combo_item),
    "desktop.spin_button.set_value": ActionPolicy(Risk.MEDIUM, True, None, _spin_value),
    "desktop.menu.activate_item": ActionPolicy(Risk.MEDIUM, True, None, _accessible_name),
    "desktop.permission_dialog.decide": ActionPolicy(Risk.MEDIUM, True, None, _permission_decision),
    "desktop.navigate.back": ActionPolicy(Risk.LOW, True),
    "desktop.clipboard.clear": ActionPolicy(
        Risk.MEDIUM,
        False,
        ("wl-copy", "--clear"),
        _no_parameters,
    ),
    "desktop.clipboard.read_text": ActionPolicy(Risk.MEDIUM, True, None, _no_parameters),
    "desktop.clipboard.write_text": ActionPolicy(Risk.MEDIUM, False, None, _spoken_text),
    "desktop.settings.open": ActionPolicy(Risk.LOW, True, ("gnome-control-center",), _setting),
    "accessibility.screen_keyboard.enable": ActionPolicy(
        Risk.MEDIUM,
        True,
        ("gsettings", "set", "org.gnome.desktop.a11y.applications", "screen-keyboard-enabled", "true"),
        _no_parameters,
    ),
    "accessibility.screen_reader.enable": ActionPolicy(
        Risk.MEDIUM,
        True,
        ("gsettings", "set", "org.gnome.desktop.a11y.applications", "screen-reader-enabled", "true"),
        _no_parameters,
    ),
    "accessibility.screen_reader.restart_with_speech": ActionPolicy(
        Risk.MEDIUM,
        True,
        ("clausis-orca-control", "restart"),
        _no_parameters,
    ),
    "accessibility.screen_magnifier.enable": ActionPolicy(
        Risk.MEDIUM,
        True,
        ("gsettings", "set", "org.gnome.desktop.a11y.applications", "screen-magnifier-enabled", "true"),
        _no_parameters,
    ),
    "accessibility.screen_magnifier.disable": ActionPolicy(
        Risk.MEDIUM,
        True,
        ("gsettings", "set", "org.gnome.desktop.a11y.applications", "screen-magnifier-enabled", "false"),
        _no_parameters,
    ),
    "accessibility.screen_magnifier.set_percent": ActionPolicy(
        Risk.MEDIUM,
        True,
        ("gsettings", "set", "org.gnome.desktop.a11y.magnifier", "mag-factor"),
        _magnifier_percentage,
    ),
    "accessibility.screen_magnifier.invert_lightness.enable": ActionPolicy(
        Risk.MEDIUM,
        True,
        ("gsettings", "set", "org.gnome.desktop.a11y.magnifier", "invert-lightness", "true"),
        _no_parameters,
    ),
    "accessibility.screen_magnifier.invert_lightness.disable": ActionPolicy(
        Risk.MEDIUM,
        True,
        ("gsettings", "set", "org.gnome.desktop.a11y.magnifier", "invert-lightness", "false"),
        _no_parameters,
    ),
    "accessibility.screen_magnifier.set_saturation": ActionPolicy(
        Risk.MEDIUM,
        True,
        ("gsettings", "set", "org.gnome.desktop.a11y.magnifier", "color-saturation"),
        _magnifier_saturation,
    ),
    "accessibility.screen_magnifier.set_brightness": ActionPolicy(
        Risk.MEDIUM,
        True,
        ("clausis-magnifier-filter", "brightness"),
        _magnifier_filter_percentage,
    ),
    "accessibility.screen_magnifier.set_contrast": ActionPolicy(
        Risk.MEDIUM,
        True,
        ("clausis-magnifier-filter", "contrast"),
        _magnifier_filter_percentage,
    ),
    "accessibility.screen_magnifier.set_screen_position": ActionPolicy(
        Risk.MEDIUM,
        True,
        ("gsettings", "set", "org.gnome.desktop.a11y.magnifier", "screen-position"),
        _magnifier_screen_position,
    ),
    "accessibility.screen_magnifier.cross_hairs.enable": ActionPolicy(
        Risk.MEDIUM,
        True,
        ("gsettings", "set", "org.gnome.desktop.a11y.magnifier", "show-cross-hairs", "true"),
        _no_parameters,
    ),
    "accessibility.screen_magnifier.cross_hairs.disable": ActionPolicy(
        Risk.MEDIUM,
        True,
        ("gsettings", "set", "org.gnome.desktop.a11y.magnifier", "show-cross-hairs", "false"),
        _no_parameters,
    ),
    "accessibility.screen_magnifier.cross_hairs.set_opacity": ActionPolicy(
        Risk.MEDIUM,
        True,
        ("gsettings", "set", "org.gnome.desktop.a11y.magnifier", "cross-hairs-opacity"),
        _magnifier_cross_hairs_opacity,
    ),
    "accessibility.screen_magnifier.cross_hairs.clip.enable": ActionPolicy(
        Risk.MEDIUM,
        True,
        ("gsettings", "set", "org.gnome.desktop.a11y.magnifier", "cross-hairs-clip", "true"),
        _no_parameters,
    ),
    "accessibility.screen_magnifier.cross_hairs.clip.disable": ActionPolicy(
        Risk.MEDIUM,
        True,
        ("gsettings", "set", "org.gnome.desktop.a11y.magnifier", "cross-hairs-clip", "false"),
        _no_parameters,
    ),
    "accessibility.screen_magnifier.cross_hairs.set_length": ActionPolicy(
        Risk.MEDIUM,
        True,
        ("gsettings", "set", "org.gnome.desktop.a11y.magnifier", "cross-hairs-length"),
        _magnifier_cross_hairs_length,
    ),
    "accessibility.screen_magnifier.cross_hairs.set_thickness": ActionPolicy(
        Risk.MEDIUM,
        True,
        ("gsettings", "set", "org.gnome.desktop.a11y.magnifier", "cross-hairs-thickness"),
        _magnifier_cross_hairs_thickness,
    ),
    "accessibility.screen_magnifier.cross_hairs.set_color": ActionPolicy(
        Risk.MEDIUM,
        True,
        ("gsettings", "set", "org.gnome.desktop.a11y.magnifier", "cross-hairs-color"),
        _magnifier_cross_hairs_color,
    ),
    "accessibility.screen_magnifier.set_focus_tracking": ActionPolicy(
        Risk.MEDIUM,
        True,
        ("gsettings", "set", "org.gnome.desktop.a11y.magnifier", "focus-tracking"),
        _magnifier_focus_tracking,
    ),
    "accessibility.screen_magnifier.set_caret_tracking": ActionPolicy(
        Risk.MEDIUM,
        True,
        ("gsettings", "set", "org.gnome.desktop.a11y.magnifier", "caret-tracking"),
        _magnifier_caret_tracking,
    ),
    "accessibility.screen_magnifier.set_mouse_tracking": ActionPolicy(
        Risk.MEDIUM,
        True,
        ("gsettings", "set", "org.gnome.desktop.a11y.magnifier", "mouse-tracking"),
        _magnifier_mouse_tracking,
    ),
    "accessibility.screen_magnifier.lens_mode.enable": ActionPolicy(
        Risk.MEDIUM,
        True,
        ("gsettings", "set", "org.gnome.desktop.a11y.magnifier", "lens-mode", "true"),
        _no_parameters,
    ),
    "accessibility.screen_magnifier.lens_mode.disable": ActionPolicy(
        Risk.MEDIUM,
        True,
        ("gsettings", "set", "org.gnome.desktop.a11y.magnifier", "lens-mode", "false"),
        _no_parameters,
    ),
    "accessibility.screen_magnifier.scroll_at_edges.enable": ActionPolicy(
        Risk.MEDIUM,
        True,
        ("gsettings", "set", "org.gnome.desktop.a11y.magnifier", "scroll-at-edges", "true"),
        _no_parameters,
    ),
    "accessibility.screen_magnifier.scroll_at_edges.disable": ActionPolicy(
        Risk.MEDIUM,
        True,
        ("gsettings", "set", "org.gnome.desktop.a11y.magnifier", "scroll-at-edges", "false"),
        _no_parameters,
    ),
    "file.open": ActionPolicy(Risk.LOW, True, ("gio", "open"), _path),
    "file.search": ActionPolicy(Risk.LOW, True, None, _target_required),
    "file.move_to_trash": ActionPolicy(Risk.HIGH, True, ("gio", "trash"), _path),
    "file.delete": ActionPolicy(Risk.CRITICAL, False, None, _path),
    "audio.volume.set": ActionPolicy(Risk.LOW, True, ("wpctl", "set-volume", "@DEFAULT_AUDIO_SINK@"), _percentage),
    "audio.volume.up": ActionPolicy(Risk.LOW, True, ("wpctl", "set-volume", "@DEFAULT_AUDIO_SINK@", "5%+")),
    "audio.volume.down": ActionPolicy(Risk.LOW, True, ("wpctl", "set-volume", "@DEFAULT_AUDIO_SINK@", "5%-")),
    "audio.mute.toggle": ActionPolicy(Risk.LOW, True, ("wpctl", "set-mute", "@DEFAULT_AUDIO_SINK@", "toggle")),
    "network.status": ActionPolicy(Risk.LOW, True, ("nmcli", "general", "status")),
    "network.wifi.enable": ActionPolicy(Risk.MEDIUM, True, ("nmcli", "radio", "wifi", "on")),
    "network.wifi.disable": ActionPolicy(Risk.MEDIUM, True, ("nmcli", "radio", "wifi", "off")),
    "system.status": ActionPolicy(Risk.LOW, True),
    "system.lock": ActionPolicy(Risk.LOW, True, ("loginctl", "lock-session")),
    "system.logout": ActionPolicy(Risk.HIGH, True, ("gnome-session-quit", "--logout", "--no-prompt")),
    "system.reboot": ActionPolicy(Risk.CRITICAL, False, ("systemctl", "reboot"), privileged=True),
    "system.poweroff": ActionPolicy(Risk.CRITICAL, False, ("systemctl", "poweroff"), privileged=True),
    "package.install": ActionPolicy(Risk.HIGH, True, None, _safe_identifier, privileged=True),
    "package.remove": ActionPolicy(Risk.CRITICAL, False, None, _safe_identifier, privileged=True),
    "update.check": ActionPolicy(Risk.LOW, True),
    "update.install_security": ActionPolicy(Risk.HIGH, True, None, privileged=True),
}


class PolicyDecision:
    def __init__(self, *, allowed: bool, confirmation_required: bool, reason: str, policy: ActionPolicy) -> None:
        self.allowed = allowed
        self.confirmation_required = confirmation_required
        self.reason = reason
        self.policy = policy


def evaluate(request: ActionRequest) -> PolicyDecision:
    policy = ACTION_POLICIES.get(request.action)
    if policy is None:
        raise ValueError("action is not allowlisted")
    if policy.validator:
        policy.validator(request)
    if request.risk.rank < policy.minimum_risk.rank:
        raise ValueError("caller attempted to understate action risk")
    if request.reversible and not policy.reversible:
        raise ValueError("caller incorrectly marked an irreversible action reversible")
    tainted = request.origin in {Origin.EXTERNAL_CONTENT, Origin.HERMES}
    needs_confirmation = (
        policy.minimum_risk.rank >= Risk.MEDIUM.rank
        or not policy.reversible
        or policy.privileged
        or tainted
    )
    reason = "confirmation required by risk and provenance policy" if needs_confirmation else "safe local action"
    return PolicyDecision(
        allowed=True,
        confirmation_required=needs_confirmation,
        reason=reason,
        policy=policy,
    )
