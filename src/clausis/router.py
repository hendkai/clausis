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
    CommandPattern("launch", _rx(r"(?:öffne|starte) (?P<target>[\w.+@:-]+)", r"(?:open|launch) (?P<target>[\w.+@:-]+)"), _target("app.launch")),
    CommandPattern("close", _rx(r"schließe (?P<target>[\w.+@:-]+)", r"close (?P<target>[\w.+@:-]+)"), _target("app.close", Risk.MEDIUM)),
    CommandPattern("settings", _rx(r"öffne (?:die )?einstellungen", r"open settings"), _simple("desktop.settings.open")),
    CommandPattern("overview", _rx(r"zeige (?:die )?übersicht", r"show overview"), _simple("desktop.overview")),
    CommandPattern("next-window", _rx(r"nächstes fenster", r"next window"), _simple("desktop.window.next")),
    CommandPattern("previous-window", _rx(r"vorheriges fenster", r"previous window"), _simple("desktop.window.previous")),
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
