"""Deterministic offline command router for German and English."""

from __future__ import annotations

from dataclasses import dataclass
import re
from typing import Callable, List, Match, Optional, Pattern, Sequence

from .models import ActionRequest, Origin, Risk


Builder = Callable[[Match[str]], ActionRequest]


@dataclass(frozen=True)
class CommandPattern:
    name: str
    patterns: Sequence[Pattern[str]]
    builder: Builder


def _simple(action: str, risk: Risk = Risk.LOW, reversible: bool = True) -> Builder:
    return lambda _: ActionRequest(action, risk=risk, reversible=reversible)


def _target(action: str, risk: Risk = Risk.LOW, reversible: bool = True) -> Builder:
    return lambda match: ActionRequest(
        action,
        target=match.group("target").strip(),
        risk=risk,
        reversible=reversible,
    )


def _volume(match: Match[str]) -> ActionRequest:
    return ActionRequest(
        "audio.volume.set",
        arguments={"percent": int(match.group("percent"))},
    )


_SPOKEN_NUMBERS = {
    "eins": 1,
    "one": 1,
    "zwei": 2,
    "two": 2,
    "drei": 3,
    "three": 3,
    "vier": 4,
    "four": 4,
    "fünf": 5,
    "five": 5,
    "sechs": 6,
    "six": 6,
    "sieben": 7,
    "seven": 7,
    "acht": 8,
    "eight": 8,
    "neun": 9,
    "nine": 9,
    "zehn": 10,
    "ten": 10,
}


def _control_number(match: Match[str]) -> ActionRequest:
    value = match.group("number").casefold()
    number = int(value) if value.isdigit() else _SPOKEN_NUMBERS[value]
    return ActionRequest(
        "desktop.control.activate",
        target=str(number),
        risk=Risk.MEDIUM,
    )


def _notification_number(match: Match[str]) -> ActionRequest:
    value = match.group("number").casefold()
    number = int(value) if value.isdigit() else _SPOKEN_NUMBERS[value]
    return ActionRequest(
        "desktop.notifications.dismiss",
        target=str(number),
        risk=Risk.HIGH,
        reversible=False,
    )


def _slider(match: Match[str]) -> ActionRequest:
    return ActionRequest(
        "desktop.slider.set_percent",
        target=match.group("target").strip(),
        arguments={"percent": int(match.group("percent"))},
        risk=Risk.MEDIUM,
    )


def _checkbox(checked: bool) -> Builder:
    return lambda match: ActionRequest(
        "desktop.checkbox.set_checked",
        target=match.group("target").strip(),
        arguments={"checked": checked},
        risk=Risk.MEDIUM,
    )


def _switch(enabled: bool) -> Builder:
    return lambda match: ActionRequest(
        "desktop.switch.set_enabled",
        target=match.group("target").strip(),
        arguments={"checked": enabled},
        risk=Risk.MEDIUM,
    )


def _combo(match: Match[str]) -> ActionRequest:
    return ActionRequest(
        "desktop.combo.select_item",
        target=match.group("target").strip(),
        arguments={"item": match.group("item").strip()},
        risk=Risk.MEDIUM,
    )


def _spin(match: Match[str]) -> ActionRequest:
    raw = match.group("value").replace(",", ".")
    return ActionRequest(
        "desktop.spin_button.set_value",
        target=match.group("target").strip(),
        arguments={"value": float(raw)},
        risk=Risk.MEDIUM,
    )


def _permission_decision(value: str) -> Builder:
    return lambda _match: ActionRequest(
        "desktop.permission_dialog.decide",
        target=value,
        risk=Risk.MEDIUM,
    )


def _file_dialog_decision(value: str) -> Builder:
    return lambda _match: ActionRequest(
        "desktop.file_dialog.decide",
        target=value,
        risk=Risk.MEDIUM,
    )


def _standard_dialog_decision(value: str) -> Builder:
    return lambda _match: ActionRequest(
        "desktop.standard_dialog.decide",
        target=value,
        risk=Risk.HIGH,
        reversible=False,
    )


_MAGNIFIER_POSITIONS = {
    "vollbild": "full-screen",
    "obere hälfte": "top-half",
    "untere hälfte": "bottom-half",
    "linke hälfte": "left-half",
    "rechte hälfte": "right-half",
    "full screen": "full-screen",
    "top half": "top-half",
    "bottom half": "bottom-half",
    "left half": "left-half",
    "right half": "right-half",
}

_MAGNIFIER_FOCUS_TRACKING = {
    "aus": "none",
    "zentriert": "centered",
    "proportional": "proportional",
    "schiebend": "push",
    "off": "none",
    "centered": "centered",
    "proportional": "proportional",
    "push": "push",
}

_MAGNIFIER_CROSS_HAIR_COLORS = {
    "schwarz": (0, 0, 0),
    "black": (0, 0, 0),
    "weiß": (255, 255, 255),
    "weiss": (255, 255, 255),
    "white": (255, 255, 255),
    "rot": (255, 0, 0),
    "red": (255, 0, 0),
    "grün": (0, 255, 0),
    "gruen": (0, 255, 0),
    "green": (0, 255, 0),
    "blau": (0, 0, 255),
    "blue": (0, 0, 255),
    "gelb": (255, 255, 0),
    "yellow": (255, 255, 0),
    "cyan": (0, 255, 255),
    "magenta": (255, 0, 255),
}


def _magnifier_screen_position(match: Match[str]) -> ActionRequest:
    position = _MAGNIFIER_POSITIONS[match.group("position").casefold()]
    return ActionRequest(
        "accessibility.screen_magnifier.set_screen_position",
        arguments={"position": position},
        risk=Risk.MEDIUM,
    )


def _magnifier_focus_tracking(match: Match[str]) -> ActionRequest:
    mode = _MAGNIFIER_FOCUS_TRACKING[match.group("mode").casefold()]
    return ActionRequest(
        "accessibility.screen_magnifier.set_focus_tracking",
        arguments={"mode": mode},
        risk=Risk.MEDIUM,
    )


def _magnifier_tracking(action: str) -> Builder:
    def build(match: Match[str]) -> ActionRequest:
        mode = _MAGNIFIER_FOCUS_TRACKING[match.group("mode").casefold()]
        return ActionRequest(action, arguments={"mode": mode}, risk=Risk.MEDIUM)

    return build


def _magnifier_cross_hairs_named_color(match: Match[str]) -> ActionRequest:
    red, green, blue = _MAGNIFIER_CROSS_HAIR_COLORS[match.group("color").casefold()]
    return ActionRequest(
        "accessibility.screen_magnifier.cross_hairs.set_color",
        arguments={"red": red, "green": green, "blue": blue},
        risk=Risk.MEDIUM,
    )


def _magnifier_cross_hairs_rgb_color(match: Match[str]) -> ActionRequest:
    return ActionRequest(
        "accessibility.screen_magnifier.cross_hairs.set_color",
        arguments={
            "red": int(match.group("red")),
            "green": int(match.group("green")),
            "blue": int(match.group("blue")),
        },
        risk=Risk.MEDIUM,
    )


def _magnifier_filter(action: str) -> Builder:
    def build(match: Match[str]) -> ActionRequest:
        magnitude = int(match.group("percent"))
        sign = match.group("sign").casefold().strip() if match.group("sign") else "plus"
        percent = -magnitude if sign in {"minus", "negative"} else magnitude
        return ActionRequest(action, arguments={"percent": percent}, risk=Risk.MEDIUM)

    return build


def _rx(*values: str) -> Sequence[Pattern[str]]:
    return tuple(re.compile(rf"^(?:{value})[.!?]*$", re.IGNORECASE) for value in values)


COMMANDS: Sequence[CommandPattern] = (
    CommandPattern("stop", _rx(r"stopp (?:hermes|clausis)", r"(?:hermes|clausis) stopp", r"stop (?:hermes|clausis)"), _simple("voice.stop")),
    CommandPattern("where-am-i", _rx(r"wo bin ich", r"where am i"), _simple("desktop.context.describe")),
    CommandPattern("read-window", _rx(r"lies (?:das )?fenster vor", r"read (?:the )?window"), _simple("desktop.context.describe")),
    CommandPattern("read-focused-text", _rx(r"lies (?:das )?textfeld vor", r"read (?:the )?text field"), _simple("desktop.text.read_focused")),
    CommandPattern("copy-focused-text", _rx(r"kopiere (?:das )?textfeld", r"copy (?:the )?text field"), _simple("desktop.text.copy_focused", Risk.MEDIUM, False)),
    CommandPattern("copy-text-selection", _rx(r"kopiere (?:die )?textauswahl", r"copy (?:the )?text selection"), _simple("desktop.text.copy_selection", Risk.MEDIUM, False)),
    CommandPattern("read-text-selection", _rx(r"lies (?:die )?textauswahl vor", r"read (?:the )?text selection"), _simple("desktop.text.read_selection", Risk.MEDIUM)),
    CommandPattern("select-all-text", _rx(r"wähle (?:den )?ganzen text (?:im|in dem) textfeld aus", r"alles im textfeld auswählen", r"select all (?:the )?text(?: in (?:the )?text field)?"), _simple("desktop.text.select_all")),
    CommandPattern("clear-text-selection", _rx(r"hebe (?:die )?textauswahl auf", r"textauswahl aufheben", r"clear (?:the )?text selection", r"deselect (?:the )?text"), _simple("desktop.text.clear_selection")),
    CommandPattern("delete-text-selection", _rx(r"lösche (?:die )?textauswahl", r"ausgewählten text löschen", r"delete (?:the )?(?:selected text|text selection)"), _simple("desktop.text.delete_selection", Risk.MEDIUM)),
    CommandPattern("caret-to-start", _rx(r"(?:setze |bewege )?(?:den )?(?:text)?cursor an (?:den )?anfang", r"move (?:the )?(?:text )?cursor to (?:the )?(?:start|beginning)"), _simple("desktop.text.caret_start")),
    CommandPattern("caret-to-end", _rx(r"(?:setze |bewege )?(?:den )?(?:text)?cursor an (?:das )?ende", r"move (?:the )?(?:text )?cursor to (?:the )?end"), _simple("desktop.text.caret_end")),
    CommandPattern("caret-previous-character", _rx(r"(?:bewege )?(?:den )?(?:text)?cursor (?:ein zeichen )?(?:zurück|nach links)", r"move (?:the )?(?:text )?cursor (?:one character )?(?:back|left)"), _simple("desktop.text.caret_previous")),
    CommandPattern("caret-next-character", _rx(r"(?:bewege )?(?:den )?(?:text)?cursor (?:ein zeichen )?(?:vor|nach rechts)", r"move (?:the )?(?:text )?cursor (?:one character )?(?:forward|right)"), _simple("desktop.text.caret_next")),
    CommandPattern("caret-previous-word", _rx(r"(?:bewege )?(?:den )?(?:text)?cursor (?:ein wort )?(?:zurück|zum vorherigen wort)", r"move (?:the )?(?:text )?cursor (?:one word back|to (?:the )?previous word)"), _simple("desktop.text.caret_previous_word")),
    CommandPattern("caret-next-word", _rx(r"(?:bewege )?(?:den )?(?:text)?cursor (?:ein wort vor|zum nächsten wort)", r"move (?:the )?(?:text )?cursor (?:one word forward|to (?:the )?next word)"), _simple("desktop.text.caret_next_word")),
    CommandPattern("caret-line-start", _rx(r"(?:bewege )?(?:den )?(?:text)?cursor an (?:den )?zeilenanfang", r"move (?:the )?(?:text )?cursor to (?:the )?(?:start|beginning) of (?:the )?(?:current )?line"), _simple("desktop.text.caret_line_start")),
    CommandPattern("caret-line-end", _rx(r"(?:bewege )?(?:den )?(?:text)?cursor an (?:das )?zeilenende", r"move (?:the )?(?:text )?cursor to (?:the )?end of (?:the )?(?:current )?line"), _simple("desktop.text.caret_line_end")),
    CommandPattern("describe-caret-position", _rx(r"wo ist (?:der )?(?:text)?cursor", r"lies (?:die )?(?:text)?cursorposition vor", r"where is (?:the )?(?:text )?cursor", r"read (?:the )?(?:text )?cursor position"), _simple("desktop.text.caret_describe")),
    CommandPattern("insert-text-at-caret", _rx(r"füge (?:am|an dem) (?:text)?cursor (?P<target>.+) ein", r"insert (?P<target>.+) at (?:the )?(?:text )?cursor"), _target("desktop.text.insert_at_caret", Risk.MEDIUM)),
    CommandPattern("delete-previous-character", _rx(r"lösche (?:das )?zeichen vor (?:dem )?(?:text)?cursor", r"lösche rückwärts am (?:text)?cursor", r"delete (?:the )?character before (?:the )?(?:text )?cursor", r"backspace at (?:the )?(?:text )?cursor"), _simple("desktop.text.delete_previous_character", Risk.MEDIUM)),
    CommandPattern("delete-next-character", _rx(r"lösche (?:das )?zeichen nach (?:dem )?(?:text)?cursor", r"lösche vorwärts am (?:text)?cursor", r"delete (?:the )?character after (?:the )?(?:text )?cursor", r"delete forward at (?:the )?(?:text )?cursor"), _simple("desktop.text.delete_next_character", Risk.MEDIUM)),
    CommandPattern("delete-previous-word", _rx(r"lösche (?:das )?wort vor (?:dem )?(?:text)?cursor", r"delete (?:the )?word before (?:the )?(?:text )?cursor"), _simple("desktop.text.delete_previous_word", Risk.MEDIUM)),
    CommandPattern("delete-next-word", _rx(r"lösche (?:das )?wort nach (?:dem )?(?:text)?cursor", r"delete (?:the )?word after (?:the )?(?:text )?cursor"), _simple("desktop.text.delete_next_word", Risk.MEDIUM)),
    CommandPattern("replace-previous-word", _rx(r"ersetze (?:das )?wort vor (?:dem )?(?:text)?cursor durch (?P<target>.+)", r"replace (?:the )?word before (?:the )?(?:text )?cursor with (?P<target>.+)"), _target("desktop.text.replace_previous_word", Risk.MEDIUM)),
    CommandPattern("replace-next-word", _rx(r"ersetze (?:das )?wort nach (?:dem )?(?:text)?cursor durch (?P<target>.+)", r"replace (?:the )?word after (?:the )?(?:text )?cursor with (?P<target>.+)"), _target("desktop.text.replace_next_word", Risk.MEDIUM)),
    CommandPattern("select-previous-character", _rx(r"wähle (?:das )?zeichen vor (?:dem )?(?:text)?cursor aus", r"select (?:the )?character before (?:the )?(?:text )?cursor"), _simple("desktop.text.select_previous_character")),
    CommandPattern("select-next-character", _rx(r"wähle (?:das )?zeichen nach (?:dem )?(?:text)?cursor aus", r"select (?:the )?character after (?:the )?(?:text )?cursor"), _simple("desktop.text.select_next_character")),
    CommandPattern("select-previous-word", _rx(r"wähle (?:das )?wort vor (?:dem )?(?:text)?cursor aus", r"select (?:the )?word before (?:the )?(?:text )?cursor"), _simple("desktop.text.select_previous_word")),
    CommandPattern("select-next-word", _rx(r"wähle (?:das )?wort nach (?:dem )?(?:text)?cursor aus", r"select (?:the )?word after (?:the )?(?:text )?cursor"), _simple("desktop.text.select_next_word")),
    CommandPattern("select-current-line", _rx(r"wähle (?:die )?aktuelle zeile aus", r"wähle (?:die )?zeile am (?:text)?cursor aus", r"select (?:the )?current line", r"select (?:the )?line at (?:the )?(?:text )?cursor"), _simple("desktop.text.select_current_line")),
    CommandPattern("delete-current-line", _rx(r"lösche (?:die )?aktuelle zeile", r"lösche (?:die )?zeile am (?:text)?cursor", r"delete (?:the )?current line", r"delete (?:the )?line at (?:the )?(?:text )?cursor"), _simple("desktop.text.delete_current_line", Risk.MEDIUM)),
    CommandPattern("replace-current-line", _rx(r"ersetze (?:die )?aktuelle zeile durch (?P<target>.+)", r"ersetze (?:die )?zeile am (?:text)?cursor durch (?P<target>.+)", r"replace (?:the )?current line with (?P<target>.+)", r"replace (?:the )?line at (?:the )?(?:text )?cursor with (?P<target>.+)"), _target("desktop.text.replace_current_line", Risk.MEDIUM)),
    CommandPattern("insert-line-above", _rx(r"füge (?:die )?zeile (?P<target>.+) (?:oberhalb|über) (?:der )?aktuellen zeile ein", r"füge oberhalb (?:der )?aktuellen zeile (?P<target>.+) ein", r"insert (?:the )?line (?P<target>.+) above (?:the )?current line"), _target("desktop.text.insert_line_above", Risk.MEDIUM)),
    CommandPattern("insert-line-below", _rx(r"füge (?:die )?zeile (?P<target>.+) unterhalb (?:der )?aktuellen zeile ein", r"füge unterhalb (?:der )?aktuellen zeile (?P<target>.+) ein", r"insert (?:the )?line (?P<target>.+) below (?:the )?current line"), _target("desktop.text.insert_line_below", Risk.MEDIUM)),
    CommandPattern("duplicate-line-above", _rx(r"dupliziere (?:die )?aktuelle zeile (?:oberhalb|nach oben)", r"duplicate (?:the )?current line above"), _simple("desktop.text.duplicate_line_above", Risk.MEDIUM)),
    CommandPattern("duplicate-line-below", _rx(r"dupliziere (?:die )?aktuelle zeile (?:unterhalb|nach unten)", r"duplicate (?:the )?current line below"), _simple("desktop.text.duplicate_line_below", Risk.MEDIUM)),
    CommandPattern("move-line-up", _rx(r"verschiebe (?:die )?aktuelle zeile nach oben", r"move (?:the )?current line up"), _simple("desktop.text.move_line_up", Risk.MEDIUM)),
    CommandPattern("move-line-down", _rx(r"verschiebe (?:die )?aktuelle zeile nach unten", r"move (?:the )?current line down"), _simple("desktop.text.move_line_down", Risk.MEDIUM)),
    CommandPattern("join-previous-line", _rx(r"verbinde (?:die )?aktuelle zeile mit (?:der )?vorherigen", r"join (?:the )?current line with (?:the )?previous line"), _simple("desktop.text.join_previous_line", Risk.MEDIUM)),
    CommandPattern("join-next-line", _rx(r"verbinde (?:die )?aktuelle zeile mit (?:der )?nächsten", r"join (?:the )?current line with (?:the )?next line"), _simple("desktop.text.join_next_line", Risk.MEDIUM)),
    CommandPattern("split-line-at-caret", _rx(r"teile (?:die )?aktuelle zeile am (?:text)?cursor", r"split (?:the )?current line at (?:the )?(?:text )?cursor"), _simple("desktop.text.split_line_at_caret", Risk.MEDIUM)),
    CommandPattern("indent-current-line", _rx(r"rücke (?:die )?aktuelle zeile ein", r"indent (?:the )?current line"), _simple("desktop.text.indent_current_line", Risk.MEDIUM)),
    CommandPattern("outdent-current-line", _rx(r"rücke (?:die )?aktuelle zeile aus", r"outdent (?:the )?current line"), _simple("desktop.text.outdent_current_line", Risk.MEDIUM)),
    CommandPattern("replace-text-selection", _rx(r"ersetze (?:die )?textauswahl durch (?P<target>.+)", r"replace (?:the )?text selection with (?P<target>.+)"), _target("desktop.text.replace_selection", Risk.MEDIUM)),
    CommandPattern("read-previous-character", _rx(r"lies (?:das )?zeichen vor (?:dem )?(?:text)?cursor vor", r"read (?:the )?character before (?:the )?(?:text )?cursor"), _simple("desktop.text.read_previous_character", Risk.MEDIUM)),
    CommandPattern("read-next-character", _rx(r"lies (?:das )?zeichen nach (?:dem )?(?:text)?cursor vor", r"read (?:the )?character after (?:the )?(?:text )?cursor"), _simple("desktop.text.read_next_character", Risk.MEDIUM)),
    CommandPattern("read-previous-word", _rx(r"lies (?:das )?wort vor (?:dem )?(?:text)?cursor vor", r"read (?:the )?word before (?:the )?(?:text )?cursor"), _simple("desktop.text.read_previous_word", Risk.MEDIUM)),
    CommandPattern("read-next-word", _rx(r"lies (?:das )?wort nach (?:dem )?(?:text)?cursor vor", r"read (?:the )?word after (?:the )?(?:text )?cursor"), _simple("desktop.text.read_next_word", Risk.MEDIUM)),
    CommandPattern("read-current-line", _rx(r"lies (?:die )?aktuelle zeile vor", r"lies (?:die )?zeile am (?:text)?cursor vor", r"read (?:the )?current line", r"read (?:the )?line at (?:the )?(?:text )?cursor"), _simple("desktop.text.read_current_line", Risk.MEDIUM)),
    CommandPattern("paste-focused-text", _rx(r"füge (?:die )?zwischenablage (?:in das )?textfeld ein", r"paste (?:the )?clipboard (?:into|in) (?:the )?text field"), _simple("desktop.text.paste_focused", Risk.MEDIUM, False)),
    CommandPattern("read-named-progress", _rx(r"lies fortschritt (?P<target>.+) vor", r"read progress (?P<target>.+)"), _target("desktop.progress.read_named")),
    CommandPattern("available-controls", _rx(r"was kann ich hier tun", r"was kann ich tun", r"what can i do here"), _simple("desktop.controls.list")),
    CommandPattern(
        "activate-number",
        _rx(
            r"(?:nummer )?(?P<number>\d{1,2}|eins|zwei|drei|vier|fünf|sechs|sieben|acht|neun|zehn)",
            r"(?:number )?(?P<number>\d{1,2}|one|two|three|four|five|six|seven|eight|nine|ten)",
        ),
        _control_number,
    ),
    CommandPattern("back", _rx(r"zurück", r"go back", r"back"), _simple("desktop.navigate.back")),
    CommandPattern("allow-permission", _rx(r"berechtigung erlauben", r"allow (?:the )?permission"), _permission_decision("allow")),
    CommandPattern("deny-permission", _rx(r"berechtigung ablehnen", r"deny (?:the )?permission"), _permission_decision("deny")),
    CommandPattern("set-file-name", _rx(r"setze dateiname (?P<target>.+)", r"set file name (?P<target>.+)"), _target("desktop.file_dialog.set_name", Risk.MEDIUM)),
    CommandPattern("set-file-location", _rx(r"setze pfad (?P<target>/.+|/)", r"set (?:the )?(?:file )?(?:location|path) (?P<target>/.+|/)"), _target("desktop.file_dialog.set_location", Risk.MEDIUM)),
    CommandPattern("select-visible-file", _rx(r"w\u00e4hle sichtbare (?:datei|ordner) (?P<target>.+)", r"select visible (?:file|folder) (?P<target>.+)"), _target("desktop.file_dialog.select_visible", Risk.MEDIUM)),
    CommandPattern("open-visible-folder", _rx(r"\u00f6ffne sichtbaren ordner (?P<target>.+)", r"open visible folder (?P<target>.+)"), _target("desktop.file_dialog.open_visible_folder", Risk.MEDIUM)),
    CommandPattern("accept-file-dialog", _rx(r"(?:bestätige|akzeptiere) (?:den )?dateidialog", r"(?:confirm|accept) (?:the )?file dialog"), _file_dialog_decision("accept")),
    CommandPattern("cancel-file-dialog", _rx(r"brich (?:den )?dateidialog ab", r"cancel (?:the )?file dialog"), _file_dialog_decision("cancel")),
    CommandPattern("accept-standard-dialog", _rx(r"(?:bestätige|akzeptiere) (?:den )?dialog", r"(?:confirm|accept) (?:the )?dialog"), _standard_dialog_decision("accept")),
    CommandPattern("cancel-standard-dialog", _rx(r"brich (?:den )?dialog ab", r"cancel (?:the )?dialog"), _standard_dialog_decision("cancel")),
    CommandPattern("retry-standard-dialog", _rx(r"wiederhole (?:den )?dialog", r"retry (?:the )?dialog"), _standard_dialog_decision("retry")),
    CommandPattern("apply-standard-dialog", _rx(r"wende (?:den )?dialog an", r"apply (?:the )?dialog"), _standard_dialog_decision("apply")),
    CommandPattern("read-standard-dialog", _rx(r"lies (?:den )?dialog vor", r"read (?:the )?dialog"), _simple("desktop.standard_dialog.read", Risk.MEDIUM)),
    CommandPattern("dismiss-standard-dialog", _rx(r"schließe (?:den )?dialog", r"close (?:the )?dialog"), _simple("desktop.standard_dialog.dismiss", Risk.HIGH, False)),
    CommandPattern("expand-tree-item", _rx(r"klappe baumelement (?P<target>.+) auf", r"expand tree item (?P<target>.+)"), _target("desktop.tree.expand_named", Risk.MEDIUM)),
    CommandPattern("collapse-tree-item", _rx(r"klappe baumelement (?P<target>.+) zu", r"collapse tree item (?P<target>.+)"), _target("desktop.tree.collapse_named", Risk.MEDIUM)),
    CommandPattern("select-table-row", _rx(r"w\u00e4hle tabellenzeile (?P<target>.+)", r"select table row (?P<target>.+)"), _target("desktop.table.select_row", Risk.MEDIUM)),
    CommandPattern("select-tab", _rx(r"w\u00e4hle registerkarte (?P<target>.+)", r"select tab (?P<target>.+)"), _target("desktop.tabs.select_named", Risk.MEDIUM)),
    CommandPattern("set-slider", _rx(r"setze schieberegler (?P<target>.+?) auf (?P<percent>\d{1,3})(?: prozent)?", r"set slider (?P<target>.+?) to (?P<percent>\d{1,3})(?: percent)?"), _slider),
    CommandPattern("check-checkbox", _rx(r"aktiviere kontrollk\u00e4stchen (?P<target>.+)", r"check (?:the )?checkbox (?P<target>.+)"), _checkbox(True)),
    CommandPattern("uncheck-checkbox", _rx(r"deaktiviere kontrollk\u00e4stchen (?P<target>.+)", r"uncheck (?:the )?checkbox (?P<target>.+)"), _checkbox(False)),
    CommandPattern("enable-switch", _rx(r"schalte schalter (?P<target>.+?) ein", r"turn switch (?P<target>.+?) on"), _switch(True)),
    CommandPattern("disable-switch", _rx(r"schalte schalter (?P<target>.+?) aus", r"turn switch (?P<target>.+?) off"), _switch(False)),
    CommandPattern("select-radio", _rx(r"w\u00e4hle optionsfeld (?P<target>.+)", r"select radio (?:button )?(?P<target>.+)"), _target("desktop.radio.select_named", Risk.MEDIUM)),
    CommandPattern("select-combo-item", _rx(r"w\u00e4hle in auswahlliste (?P<target>.+?) den eintrag (?P<item>.+)", r"select item (?P<item>.+?) in combo box (?P<target>.+)"), _combo),
    CommandPattern("set-spin-button", _rx(r"setze zahlenfeld (?P<target>.+?) auf (?P<value>-?\d{1,9}(?:[.,]\d{1,6})?)", r"set spin button (?P<target>.+?) to (?P<value>-?\d{1,9}(?:[.,]\d{1,6})?)"), _spin),
    CommandPattern("activate-menu-item", _rx(r"aktiviere men\u00fceintrag (?P<target>.+)", r"activate menu item (?P<target>.+)"), _target("desktop.menu.activate_item", Risk.MEDIUM)),
    CommandPattern("select-list-item", _rx(r"w\u00e4hle listeneintrag (?P<target>.+)", r"select list item (?P<target>.+)"), _target("desktop.selection.select_named", Risk.MEDIUM)),
    CommandPattern("activate-named", _rx(r"w\u00e4hle (?P<target>.+)", r"select (?P<target>.+)"), _target("desktop.control.activate_named", Risk.MEDIUM)),
    CommandPattern("next-control", _rx(r"fokus weiter", r"n\u00e4chstes bedienelement", r"next control"), _simple("desktop.focus.next")),
    CommandPattern("previous-control", _rx(r"fokus zur\u00fcck", r"vorheriges bedienelement", r"previous control"), _simple("desktop.focus.previous")),
    CommandPattern("focus-named", _rx(r"fokussiere (?P<target>.+)", r"focus (?P<target>.+)"), _target("desktop.focus.named")),
    CommandPattern("set-text", _rx(r"schreibe (?:in das|ins) textfeld (?P<target>.+)", r"(?:type|enter text) (?:into|in) (?:the )?field (?P<target>.+)"), _target("desktop.text.set", Risk.MEDIUM)),
    CommandPattern("clear-text", _rx(r"textfeld leeren", r"clear (?:the )?(?:text )?field"), _simple("desktop.text.clear", Risk.MEDIUM)),
    CommandPattern("clear-clipboard", _rx(r"zwischenablage leeren", r"clear (?:the )?clipboard"), _simple("desktop.clipboard.clear", Risk.MEDIUM, False)),
    CommandPattern("read-clipboard", _rx(r"lies (?:die )?zwischenablage vor", r"read (?:the )?clipboard"), _simple("desktop.clipboard.read_text", Risk.MEDIUM)),
    CommandPattern("write-clipboard", _rx(r"schreibe in (?:die )?zwischenablage (?P<target>.+)", r"write to (?:the )?clipboard (?P<target>.+)"), _target("desktop.clipboard.write_text", Risk.MEDIUM, False)),
    CommandPattern("repeat", _rx(r"wiederholen", r"wiederhole das", r"repeat"), _simple("voice.repeat")),
    CommandPattern("cancel", _rx(r"abbrechen", r"cancel"), _simple("voice.cancel")),
    CommandPattern("correct", _rx(r"korrigieren", r"correct that"), _simple("voice.correct")),
    CommandPattern("close-window", _rx(r"fenster schließen", r"close (?:the )?window"), _simple("desktop.window.close", Risk.MEDIUM)),
    CommandPattern("move-window-workspace-previous", _rx(r"fenster auf (?:die )?(?:vorherige|linke) arbeitsfläche verschieben", r"move (?:the )?window to (?:the )?(?:previous|left) workspace"), _simple("desktop.window.workspace_previous", Risk.MEDIUM)),
    CommandPattern("move-window-workspace-next", _rx(r"fenster auf (?:die )?(?:nächste|rechte) arbeitsfläche verschieben", r"move (?:the )?window to (?:the )?(?:next|right) workspace"), _simple("desktop.window.workspace_next", Risk.MEDIUM)),
    CommandPattern("launch", _rx(r"(?:öffne|starte) (?P<target>[\w.+@:-]+)", r"(?:open|launch) (?P<target>[\w.+@:-]+)"), _target("app.launch")),
    CommandPattern("close", _rx(r"schließe (?P<target>[\w.+@:-]+)", r"close (?P<target>[\w.+@:-]+)"), _target("app.close", Risk.MEDIUM)),
    CommandPattern("settings", _rx(r"öffne (?:die )?einstellungen", r"open settings"), _simple("desktop.settings.open")),
    CommandPattern("overview", _rx(r"zeige (?:die )?übersicht", r"show overview"), _simple("desktop.overview")),
    CommandPattern("applications", _rx(r"zeige (?:die )?anwendungen", r"show applications"), _simple("desktop.applications")),
    CommandPattern("quick-settings", _rx(r"(?:\u00f6ffne|zeige) (?:die )?schnelleinstellungen", r"(?:open|show) quick settings"), _simple("desktop.quick_settings")),
    CommandPattern("notifications", _rx(r"(?:\u00f6ffne|zeige) (?:die )?benachrichtigungen", r"(?:open|show) notifications"), _simple("desktop.notifications")),
    CommandPattern("read-notifications", _rx(r"lies (?:die )?benachrichtigungen vor", r"read (?:the )?notifications"), _simple("desktop.notifications.read", Risk.MEDIUM)),
    CommandPattern("dismiss-notification", _rx(r"verwirf benachrichtigung (?:nummer )?(?P<number>\d{1,2}|eins|zwei|drei|vier|fünf|sechs|sieben|acht|neun|zehn)", r"dismiss notification (?:number )?(?P<number>\d{1,2}|one|two|three|four|five|six|seven|eight|nine|ten)"), _notification_number),
    CommandPattern("enable-screen-keyboard", _rx(r"bildschirmtastatur einschalten", r"enable (?:the )?(?:on-screen|screen) keyboard"), _simple("accessibility.screen_keyboard.enable", Risk.MEDIUM)),
    CommandPattern("enable-screen-reader", _rx(r"(?:orca|screenreader) einschalten", r"enable (?:orca|the screen reader)"), _simple("accessibility.screen_reader.enable", Risk.MEDIUM)),
    CommandPattern("restart-screen-reader-with-speech", _rx(r"(?:orca|screenreader) neu starten", r"restart (?:orca|the screen reader)"), _simple("accessibility.screen_reader.restart_with_speech", Risk.MEDIUM)),
    CommandPattern("enable-screen-magnifier", _rx(r"(?:bildschirmvergrößerung|lupe) einschalten", r"enable (?:the )?(?:screen magnifier|magnifier)"), _simple("accessibility.screen_magnifier.enable", Risk.MEDIUM)),
    CommandPattern("disable-screen-magnifier", _rx(r"(?:bildschirmvergrößerung|lupe) ausschalten", r"disable (?:the )?(?:screen magnifier|magnifier)"), _simple("accessibility.screen_magnifier.disable", Risk.MEDIUM)),
    CommandPattern("set-screen-magnifier", _rx(r"(?:bildschirmvergrößerung|lupe) (?P<percent>\d{1,4}) prozent", r"(?:screen magnifier|magnifier) (?P<percent>\d{1,4}) percent"), lambda match: ActionRequest("accessibility.screen_magnifier.set_percent", arguments={"percent": int(match.group("percent"))}, risk=Risk.MEDIUM)),
    CommandPattern("enable-magnifier-inversion", _rx(r"(?:farbinvertierung|farben umkehren) einschalten", r"enable (?:magnifier )?(?:color |lightness )?inversion"), _simple("accessibility.screen_magnifier.invert_lightness.enable", Risk.MEDIUM)),
    CommandPattern("disable-magnifier-inversion", _rx(r"(?:farbinvertierung|farben umkehren) ausschalten", r"disable (?:magnifier )?(?:color |lightness )?inversion"), _simple("accessibility.screen_magnifier.invert_lightness.disable", Risk.MEDIUM)),
    CommandPattern("set-magnifier-saturation", _rx(r"(?:farbsättigung|sättigung) (?P<percent>\d{1,3}) prozent", r"(?:magnifier )?(?:color )?saturation (?P<percent>\d{1,3}) percent"), lambda match: ActionRequest("accessibility.screen_magnifier.set_saturation", arguments={"percent": int(match.group("percent"))}, risk=Risk.MEDIUM)),
    CommandPattern("set-magnifier-brightness", _rx(r"(?:lupe )?helligkeit (?:(?P<sign>plus|minus) )?(?P<percent>\d{1,2}) prozent", r"magnifier brightness (?:(?P<sign>plus|minus|positive|negative) )?(?P<percent>\d{1,2}) percent"), _magnifier_filter("accessibility.screen_magnifier.set_brightness")),
    CommandPattern("set-magnifier-contrast", _rx(r"(?:lupe )?kontrast (?:(?P<sign>plus|minus) )?(?P<percent>\d{1,2}) prozent", r"magnifier contrast (?:(?P<sign>plus|minus|positive|negative) )?(?P<percent>\d{1,2}) percent"), _magnifier_filter("accessibility.screen_magnifier.set_contrast")),
    CommandPattern("set-magnifier-screen-position", _rx(r"(?:bildschirmvergrößerung|lupe) (?P<position>vollbild|obere hälfte|untere hälfte|linke hälfte|rechte hälfte)", r"(?:screen magnifier|magnifier) (?P<position>full screen|top half|bottom half|left half|right half)"), _magnifier_screen_position),
    CommandPattern("enable-magnifier-cross-hairs", _rx(r"(?:lupe )?fadenkreuz einschalten", r"enable (?:magnifier )?crosshairs"), _simple("accessibility.screen_magnifier.cross_hairs.enable", Risk.MEDIUM)),
    CommandPattern("disable-magnifier-cross-hairs", _rx(r"(?:lupe )?fadenkreuz ausschalten", r"disable (?:magnifier )?crosshairs"), _simple("accessibility.screen_magnifier.cross_hairs.disable", Risk.MEDIUM)),
    CommandPattern("set-magnifier-cross-hairs-opacity", _rx(r"fadenkreuz deckkraft (?P<percent>\d{1,3}) prozent", r"(?:magnifier )?crosshairs opacity (?P<percent>\d{1,3}) percent"), lambda match: ActionRequest("accessibility.screen_magnifier.cross_hairs.set_opacity", arguments={"percent": int(match.group("percent"))}, risk=Risk.MEDIUM)),
    CommandPattern("enable-magnifier-cross-hairs-clip", _rx(r"fadenkreuz mitte aussparen", r"clip (?:magnifier )?crosshairs at (?:the )?center"), _simple("accessibility.screen_magnifier.cross_hairs.clip.enable", Risk.MEDIUM)),
    CommandPattern("disable-magnifier-cross-hairs-clip", _rx(r"fadenkreuz mitte nicht aussparen", r"do not clip (?:magnifier )?crosshairs at (?:the )?center"), _simple("accessibility.screen_magnifier.cross_hairs.clip.disable", Risk.MEDIUM)),
    CommandPattern("set-magnifier-cross-hairs-length", _rx(r"fadenkreuz länge (?P<pixels>\d{1,4}) pixel", r"(?:magnifier )?crosshairs length (?P<pixels>\d{1,4}) pixels?"), lambda match: ActionRequest("accessibility.screen_magnifier.cross_hairs.set_length", arguments={"pixels": int(match.group("pixels"))}, risk=Risk.MEDIUM)),
    CommandPattern("set-magnifier-cross-hairs-thickness", _rx(r"fadenkreuz dicke (?P<pixels>\d{1,3}) pixel", r"(?:magnifier )?crosshairs thickness (?P<pixels>\d{1,3}) pixels?"), lambda match: ActionRequest("accessibility.screen_magnifier.cross_hairs.set_thickness", arguments={"pixels": int(match.group("pixels"))}, risk=Risk.MEDIUM)),
    CommandPattern("set-magnifier-cross-hairs-named-color", _rx(r"fadenkreuz farbe (?P<color>schwarz|weiß|weiss|rot|grün|gruen|blau|gelb|cyan|magenta)", r"(?:magnifier )?crosshairs color (?P<color>black|white|red|green|blue|yellow|cyan|magenta)"), _magnifier_cross_hairs_named_color),
    CommandPattern("set-magnifier-cross-hairs-rgb-color", _rx(r"fadenkreuz farbe rgb (?P<red>\d{1,3}) (?P<green>\d{1,3}) (?P<blue>\d{1,3})", r"(?:magnifier )?crosshairs color rgb (?P<red>\d{1,3}) (?P<green>\d{1,3}) (?P<blue>\d{1,3})"), _magnifier_cross_hairs_rgb_color),
    CommandPattern("set-magnifier-focus-tracking", _rx(r"(?:lupe )?fokusverfolgung (?P<mode>aus|zentriert|proportional|schiebend)", r"magnifier focus tracking (?P<mode>off|centered|proportional|push)"), _magnifier_focus_tracking),
    CommandPattern("set-magnifier-caret-tracking", _rx(r"(?:lupe )?textcursorverfolgung (?P<mode>aus|zentriert|proportional|schiebend)", r"magnifier caret tracking (?P<mode>off|centered|proportional|push)"), _magnifier_tracking("accessibility.screen_magnifier.set_caret_tracking")),
    CommandPattern("set-magnifier-mouse-tracking", _rx(r"(?:lupe )?mausverfolgung (?P<mode>aus|zentriert|proportional|schiebend)", r"magnifier mouse tracking (?P<mode>off|centered|proportional|push)"), _magnifier_tracking("accessibility.screen_magnifier.set_mouse_tracking")),
    CommandPattern("enable-magnifier-lens-mode", _rx(r"(?:lupe )?linsenmodus einschalten", r"enable (?:magnifier )?lens mode"), _simple("accessibility.screen_magnifier.lens_mode.enable", Risk.MEDIUM)),
    CommandPattern("disable-magnifier-lens-mode", _rx(r"(?:lupe )?linsenmodus ausschalten", r"disable (?:magnifier )?lens mode"), _simple("accessibility.screen_magnifier.lens_mode.disable", Risk.MEDIUM)),
    CommandPattern("enable-magnifier-scroll-at-edges", _rx(r"(?:lupe )?randscrollen einschalten", r"enable (?:magnifier )?scrolling at (?:the )?edges"), _simple("accessibility.screen_magnifier.scroll_at_edges.enable", Risk.MEDIUM)),
    CommandPattern("disable-magnifier-scroll-at-edges", _rx(r"(?:lupe )?randscrollen ausschalten", r"disable (?:magnifier )?scrolling at (?:the )?edges"), _simple("accessibility.screen_magnifier.scroll_at_edges.disable", Risk.MEDIUM)),
    CommandPattern("next-window", _rx(r"nächstes fenster", r"next window"), _simple("desktop.window.next")),
    CommandPattern("previous-window", _rx(r"vorheriges fenster", r"previous window"), _simple("desktop.window.previous")),
    CommandPattern("minimize-window", _rx(r"fenster minimieren", r"minimize (?:the )?window"), _simple("desktop.window.minimize")),
    CommandPattern("maximize-window", _rx(r"fenster maximieren", r"maximize (?:the )?window"), _simple("desktop.window.maximize")),
    CommandPattern("restore-window", _rx(r"fenster wiederherstellen", r"restore (?:the )?window"), _simple("desktop.window.restore")),
    CommandPattern("volume-up", _rx(r"lauter", r"volume up"), _simple("audio.volume.up")),
    CommandPattern("volume-down", _rx(r"leiser", r"volume down"), _simple("audio.volume.down")),
    CommandPattern("mute", _rx(r"ton (?:aus|stumm)", r"mute"), _simple("audio.mute.toggle")),
    CommandPattern("volume-set", _rx(r"lautstärke (?P<percent>\d{1,3})(?: prozent)?", r"volume (?P<percent>\d{1,3})(?: percent)?"), _volume),
    CommandPattern("network-status", _rx(r"netzwerkstatus", r"network status"), _simple("network.status")),
    CommandPattern("wifi-on", _rx(r"wlan an", r"wifi on"), _simple("network.wifi.enable", Risk.MEDIUM)),
    CommandPattern("wifi-off", _rx(r"wlan aus", r"wifi off"), _simple("network.wifi.disable", Risk.MEDIUM)),
    CommandPattern("system-status", _rx(r"systemstatus", r"system status"), _simple("system.status")),
    CommandPattern("lock", _rx(r"bildschirm sperren", r"lock (?:the )?screen"), _simple("system.lock")),
    CommandPattern("logout", _rx(r"abmelden", r"log ?out"), _simple("system.logout", Risk.HIGH)),
    CommandPattern("reboot", _rx(r"(?:computer|rechner) neu starten", r"reboot (?:the )?(?:computer|system)?"), _simple("system.reboot", Risk.CRITICAL, False)),
    CommandPattern("poweroff", _rx(r"(?:computer|rechner) ausschalten", r"(?:power off|shut down)(?: the computer)?"), _simple("system.poweroff", Risk.CRITICAL, False)),
    CommandPattern("file-open", _rx(r"öffne datei (?P<target>/[^\x00]+)", r"open file (?P<target>/[^\x00]+)"), _target("file.open")),
    CommandPattern("file-search", _rx(r"suche datei (?P<target>.+)", r"find file (?P<target>.+)"), _target("file.search")),
    CommandPattern("trash", _rx(r"verschiebe datei (?P<target>/[^\x00]+) in den papierkorb", r"move file (?P<target>/[^\x00]+) to trash"), _target("file.move_to_trash", Risk.HIGH)),
    CommandPattern("update-check", _rx(r"suche nach updates", r"check for updates"), _simple("update.check")),
    CommandPattern("security-updates", _rx(r"installiere sicherheitsupdates", r"install security updates"), _simple("update.install_security", Risk.HIGH)),
)


class OfflineRouter:
    def __init__(self, commands: Sequence[CommandPattern] = COMMANDS) -> None:
        self._commands = commands

    def route(self, transcript: str) -> Optional[ActionRequest]:
        normalized = " ".join(transcript.strip().split())
        if not normalized or len(normalized) > 1024:
            return None
        for command in self._commands:
            for pattern in command.patterns:
                match = pattern.fullmatch(normalized)
                if match:
                    request = command.builder(match)
                    if request.action == "voice.stop":
                        return request
                    return ActionRequest(
                        action=request.action,
                        target=request.target,
                        arguments=request.arguments,
                        origin=Origin.LOCAL_VOICE,
                        risk=request.risk,
                        reversible=request.reversible,
                    )
        return None
