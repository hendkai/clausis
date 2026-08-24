"""Deterministic offline command router for German and English."""

from __future__ import annotations

from dataclasses import dataclass
import re
from typing import Callable, List, Match, Optional, Pattern, Sequence

from .models import ActionRequest, Origin, Risk
from .punctuation import expand_punctuation
from .spelling import normalise_spelling


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


def _dictation(match: Match[str]) -> ActionRequest:
    """Keep dictated prose exactly as spoken, including case and punctuation.

    Spoken punctuation commands at the end of the utterance are rewritten into
    real characters first (deterministic table, see ``punctuation.py``); mid-
    utterance words always stay exactly as spoken.
    """

    return ActionRequest(
        "text.insert", target=expand_punctuation(match.group("target").strip())
    )


def _spelling(match: Match[str]) -> ActionRequest:
    """Turn a spelled utterance into the characters it names.

    ``"Buchstabiere A wie Anton, N wie Nordpol"`` becomes the dictation
    ``"AN"``: names, identifiers and digits dictated letter by letter reach
    the field as characters, not as the spoken helper words (deterministic
    table, see ``spelling.py``).  Unknown words stay prose, so nothing the
    user really said is ever mangled.
    """

    return ActionRequest(
        "text.insert", target=normalise_spelling(match.group("target").strip())
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


def _file_number_command(action: str) -> Builder:
    def build(match: Match[str]) -> ActionRequest:
        value = match.group("number").casefold()
        number = int(value) if value.isdigit() else _SPOKEN_NUMBERS[value]
        return ActionRequest(action, target=str(number))

    return build


_GRANULARITY_WORDS = {
    "zeichen": "character",
    "character": "character",
    "wort": "word",
    "word": "word",
    "zeile": "line",
    "line": "line",
    "satz": "sentence",
    "sentence": "sentence",
    "absatz": "paragraph",
    "paragraph": "paragraph",
}


def _read_granular(match: Match[str]) -> ActionRequest:
    granularity = _GRANULARITY_WORDS[match.group("unit").casefold()]
    return ActionRequest(
        "text.read_granular",
        arguments={"granularity": granularity},
    )


_file_select = _file_number_command("dialog.file.select")
_folder_open = _file_number_command("dialog.folder.open")


def _rx(*values: str) -> Sequence[Pattern[str]]:
    return tuple(re.compile(rf"^(?:{value})[.!?]*$", re.IGNORECASE) for value in values)


COMMANDS: Sequence[CommandPattern] = (
    CommandPattern("stop", _rx(r"stopp (?:hermes|clausis)", r"(?:hermes|clausis) stopp", r"stop (?:hermes|clausis)"), _simple("voice.stop")),
    CommandPattern("where-am-i", _rx(r"wo bin ich", r"where am i"), _simple("desktop.context.describe")),
    CommandPattern("read-window", _rx(r"lies (?:das )?fenster vor", r"read (?:the )?window"), _simple("desktop.context.describe")),
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
    CommandPattern("repeat", _rx(r"wiederholen", r"wiederhole das", r"repeat"), _simple("voice.repeat")),
    CommandPattern("cancel", _rx(r"abbrechen", r"cancel"), _simple("voice.cancel")),
    CommandPattern("correct", _rx(r"korrigieren", r"correct that"), _simple("voice.correct")),
    CommandPattern(
        "describe-dialog",
        _rx(r"was fragt (?:mich )?der dialog", r"dialog vorlesen", r"read (?:the )?dialog"),
        _simple("dialog.describe"),
    ),
    CommandPattern("accept-dialog", _rx(r"dialog bestätigen", r"confirm (?:the )?dialog"), _simple("dialog.accept", Risk.MEDIUM)),
    CommandPattern("cancel-dialog", _rx(r"dialog abbrechen", r"dialog schließen", r"cancel (?:the )?dialog"), _simple("dialog.cancel")),
    CommandPattern("clipboard-read", _rx(r"was (?:ist|steht) in der zwischenablage", r"zwischenablage vorlesen", r"read (?:the )?clipboard"), _simple("clipboard.read")),
    CommandPattern("clipboard-copy", _rx(r"kopieren", r"copy(?: that)?"), _simple("clipboard.copy")),
    CommandPattern("clipboard-paste", _rx(r"einfügen", r"paste"), _simple("clipboard.paste")),
    CommandPattern("keyboard-on", _rx(r"bildschirmtastatur an", r"(?:screen|on-screen) keyboard on"), _simple("a11y.keyboard.enable")),
    CommandPattern("keyboard-off", _rx(r"bildschirmtastatur aus", r"(?:screen|on-screen) keyboard off"), _simple("a11y.keyboard.disable")),
    CommandPattern("magnifier-on", _rx(r"(?:bildschirm)?lupe an", r"magnifier on"), _simple("a11y.magnifier.enable")),
    CommandPattern("magnifier-off", _rx(r"(?:bildschirm)?lupe aus", r"magnifier off"), _simple("a11y.magnifier.disable")),
    CommandPattern("screenreader-on", _rx(r"(?:orca|bildschirmleser|screenreader) an", r"screen reader on"), _simple("a11y.screenreader.enable")),
    CommandPattern("screenreader-off", _rx(r"(?:orca|bildschirmleser|screenreader) aus", r"screen reader off"), _simple("a11y.screenreader.disable")),
    CommandPattern("read-field", _rx(r"lies (?:das )?feld vor", r"was steht im feld", r"read (?:the )?field"), _simple("text.read")),
    CommandPattern("delete-word", _rx(r"(?:letztes )?wort löschen", r"delete (?:the )?(?:last )?word"), _simple("text.delete_word")),
    CommandPattern("clear-field", _rx(r"feld leeren", r"clear (?:the )?field"), _simple("text.clear", Risk.MEDIUM)),
    CommandPattern("caret-start", _rx(r"cursor an den anfang", r"caret to (?:the )?start", r"(?:move )?cursor to (?:the )?beginning"), _simple("text.caret.start")),
    CommandPattern("caret-end", _rx(r"cursor ans ende", r"caret to (?:the )?end", r"(?:move )?cursor to (?:the )?end"), _simple("text.caret.end")),
    CommandPattern("caret-next-word", _rx(r"cursor (?:ein )?wort weiter", r"next word"), _simple("text.caret.word_next")),
    CommandPattern("caret-previous-word", _rx(r"cursor (?:ein )?wort zurück", r"previous word"), _simple("text.caret.word_previous")),
    CommandPattern("read-from-caret", _rx(r"lies ab dem cursor(?: vor)?", r"read from (?:the )?caret"), _simple("text.read_from_caret")),
    # A line break cannot ride inside a dictated target: the request schema
    # forbids control characters so nothing smuggles one across a trust
    # boundary.  The adapter therefore synthesizes the newline itself and the
    # spoken command becomes its own low-risk action.
    CommandPattern("newline", _rx(r"neue zeile", r"new line"), _simple("text.newline")),
    CommandPattern("paragraph", _rx(r"absatz", r"new paragraph"), _simple("text.paragraph")),
    CommandPattern("select-word", _rx(r"markiere(?: das)? wort", r"select (?:the )?word"), _simple("text.select_word")),
    CommandPattern(
        "select-sentence",
        _rx(r"markiere(?: den)? satz", r"select (?:the )?sentence"),
        _simple("text.select_sentence"),
    ),
    CommandPattern(
        "select-all",
        _rx(r"alles markieren", r"markiere alles", r"select all"),
        _simple("text.select_all"),
    ),
    CommandPattern(
        "replace-selection",
        _rx(r"ersetze (?:die )?auswahl (?:durch|mit) (?P<target>.+)", r"replace (?:the )?selection (?:with|by) (?P<target>.+)"),
        _target("text.replace_selection"),
    ),
    CommandPattern(
        "delete-selection",
        _rx(r"lösche (?:die )?auswahl", r"delete (?:the )?selection"),
        _simple("text.delete_selection"),
    ),
    CommandPattern("undo", _rx(r"rückgängig", r"mach rückgängig", r"undo"), _simple("text.undo")),
    CommandPattern("redo", _rx(r"wiederherstellen", r"mach wiederherstellen", r"redo"), _simple("text.redo")),
    CommandPattern(
        "read-granular",
        _rx(
            r"lies (?:(?:das|den|die|der) )?(?:aktuelle[nr]? )?(?P<unit>zeichen|wort|zeile|satz|absatz)(?: ab dem cursor| am cursor)?(?: vor)?",
            r"read (?:the )?(?:current )?(?P<unit>character|word|line|sentence|paragraph)(?: from (?:the )?caret)?(?: aloud)?",
        ),
        _read_granular,
    ),
    CommandPattern(
        "file-list",
        _rx(
            r"liste dateien auf",
            r"was (?:ist |steht )?im dateidialog",
            r"welche dateien gibt es",
            r"zeige die dateien",
            r"list files",
            r"what(?:'s| is) in the file dialog",
        ),
        _simple("dialog.file.list"),
    ),
    CommandPattern(
        "file-select",
        _rx(r"wähle datei (?P<number>\d{1,2}|eins|zwei|drei|vier|fünf|sechs|sieben|acht|neun|zehn)", r"select file (?P<number>\d{1,2}|one|two|three|four|five|six|seven|eight|nine|ten)"),
        _file_select,
    ),
    CommandPattern(
        "folder-open",
        _rx(r"öffne ordner (?P<number>\d{1,2}|eins|zwei|drei|vier|fünf|sechs|sieben|acht|neun|zehn)", r"open folder (?P<number>\d{1,2}|one|two|three|four|five|six|seven|eight|nine|ten)"),
        _folder_open,
    ),
    # "Schreibe mir ein Gedicht" is a request to the agent, not dictation, so
    # the dictation verbs stay unambiguous and an ambiguous "schreibe …" keeps
    # falling through to Hermes.
    CommandPattern(
        "dictate",
        _rx(
            r"(?:diktiere|tippe) (?P<target>.+)",
            r"schreib(?:e)? ins feld (?P<target>.+)",
            r"(?:dictate|type) (?P<target>.+)",
        ),
        _dictation,
    ),
    # Spelling mode is its own dictation verb: "buchstabiere …" is never
    # ordinary prose dictation, and its characters reach the field named,
    # not spoken.
    CommandPattern(
        "spell",
        _rx(
            r"buchstabier(?:e|en)? (?P<target>.+)",
            r"spelling (?P<target>.+)",
            r"spell (?P<target>.+)",
        ),
        _spelling,
    ),
    CommandPattern("launch", _rx(r"(?:öffne|starte) (?P<target>[\w.+@:-]+)", r"(?:open|launch) (?P<target>[\w.+@:-]+)"), _target("app.launch")),
    CommandPattern("close", _rx(r"schließe (?P<target>[\w.+@:-]+)", r"close (?P<target>[\w.+@:-]+)"), _target("app.close", Risk.MEDIUM)),
    CommandPattern("settings", _rx(r"öffne (?:die )?einstellungen", r"open settings"), _simple("desktop.settings.open")),
    CommandPattern("overview", _rx(r"zeige (?:die )?übersicht", r"show overview"), _simple("desktop.overview")),
    CommandPattern("applications", _rx(r"zeige (?:die )?anwendungen", r"show applications"), _simple("desktop.applications")),
    CommandPattern("quick-settings", _rx(r"(?:zeige (?:die )?)?schnelleinstellungen", r"(?:show )?quick settings"), _simple("desktop.quick_settings")),
    CommandPattern("notifications", _rx(r"(?:zeige (?:die )?)?benachrichtigungen", r"(?:show )?notifications"), _simple("desktop.notifications")),
    CommandPattern("minimize", _rx(r"fenster minimieren", r"minimize (?:the )?window"), _simple("desktop.window.minimize")),
    CommandPattern("maximize", _rx(r"fenster maximieren", r"maximize (?:the )?window"), _simple("desktop.window.maximize")),
    CommandPattern("unmaximize", _rx(r"fenster wiederherstellen", r"(?:restore|unmaximize) (?:the )?window"), _simple("desktop.window.unmaximize")),
    CommandPattern(
        "window-to-next-workspace",
        _rx(r"fenster (?:auf|zur) nächste[nr]? arbeitsfläche", r"move (?:the )?window to (?:the )?next workspace"),
        _simple("desktop.window.to_next_workspace"),
    ),
    CommandPattern(
        "window-to-previous-workspace",
        _rx(r"fenster (?:auf|zur) vorherige[nr]? arbeitsfläche", r"move (?:the )?window to (?:the )?previous workspace"),
        _simple("desktop.window.to_previous_workspace"),
    ),
    CommandPattern("next-workspace", _rx(r"nächste arbeitsfläche", r"next workspace"), _simple("desktop.workspace.next")),
    CommandPattern("previous-workspace", _rx(r"vorherige arbeitsfläche", r"previous workspace"), _simple("desktop.workspace.previous")),
    CommandPattern("next-window", _rx(r"nächstes fenster", r"next window"), _simple("desktop.window.next")),
    CommandPattern("previous-window", _rx(r"vorheriges fenster", r"previous window"), _simple("desktop.window.previous")),
    CommandPattern("volume-up", _rx(r"lauter", r"volume up"), _simple("audio.volume.up")),
    CommandPattern("volume-down", _rx(r"leiser", r"volume down"), _simple("audio.volume.down")),
    CommandPattern("mute", _rx(r"ton (?:aus|stumm)", r"mute"), _simple("audio.mute.toggle")),
    CommandPattern("volume-set", _rx(r"lautstärke (?P<percent>\d{1,3})(?: prozent)?", r"volume (?P<percent>\d{1,3})(?: percent)?"), _volume),
    CommandPattern("network-status", _rx(r"netzwerkstatus", r"network status"), _simple("network.status")),
    CommandPattern("wifi-on", _rx(r"wlan an", r"wifi on"), _simple("network.wifi.enable", Risk.MEDIUM)),
    CommandPattern("wifi-off", _rx(r"wlan aus", r"wifi off"), _simple("network.wifi.disable", Risk.MEDIUM)),
    CommandPattern("report", _rx(r"(?:erstelle |mach )?(?:einen )?fehlerbericht", r"diagnosebericht", r"create (?:a )?report"), _simple("system.report")),
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
