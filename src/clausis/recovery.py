"""Spoken and keyboard recovery paths for every supported failure.

“Nur mit Sprache” must never mean that a failure leaves the user with nothing.
Every entry below therefore carries two things: what Clausis says, and the
equal keyboard/Orca path that works even when speech itself is the thing that
broke.  A test asserts that no failure is left without either.

:class:`Announcer` is the other half: a message must reach the user even when
speech output is dead, so it falls back from speech to a desktop notification
and finally to the terminal, and reports which channel actually worked.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
import shutil
import subprocess
import sys
from typing import Callable, Mapping, Optional


class Failure(str, Enum):
    NO_MICROPHONE = "no_microphone"
    NO_SPEECH_OUTPUT = "no_speech_output"
    NO_AUDIO = "no_audio"
    STT_UNAVAILABLE = "stt_unavailable"
    NO_NETWORK = "no_network"
    AGENT_UNAVAILABLE = "agent_unavailable"
    BROKER_UNAVAILABLE = "broker_unavailable"
    CONFIRMATION_UNAVAILABLE = "confirmation_unavailable"
    SHELL_BRIDGE_MISSING = "shell_bridge_missing"
    DIALOG_BLOCKED = "dialog_blocked"
    UPDATE_FAILED = "update_failed"


@dataclass(frozen=True)
class Recovery:
    failure: Failure
    spoken: str
    #: The keyboard/Orca path.  Never empty: it is the route that has to work
    #: when voice control itself is unavailable.
    keyboard: str
    #: Whether voice control can keep running after this failure.
    can_continue: bool

    def message(self) -> str:
        return f"{self.spoken} {self.keyboard}"


RECOVERIES: Mapping[Failure, Recovery] = {
    Failure.NO_MICROPHONE: Recovery(
        Failure.NO_MICROPHONE,
        "Ich finde kein Mikrofon. Spracheingabe ist ausgeschaltet.",
        "Bedienen Sie den Rechner mit Tastatur und Orca. Orca schalten Sie mit "
        "Super plus Alt plus S ein. Prüfen Sie danach die Toneinstellungen.",
        can_continue=False,
    ),
    Failure.NO_SPEECH_OUTPUT: Recovery(
        Failure.NO_SPEECH_OUTPUT,
        "Die Sprachausgabe antwortet nicht. Ich zeige Antworten als Benachrichtigung an.",
        "Orca liest Benachrichtigungen vor. Mit Tastatur und Orca bleibt das "
        "System vollständig bedienbar.",
        can_continue=True,
    ),
    Failure.NO_AUDIO: Recovery(
        Failure.NO_AUDIO,
        "Es ist kein Audiogerät verfügbar.",
        "Tastatur und Orca bleiben aktiv. Melden Sie sich ab und wieder an, "
        "wenn Sie das Audiogerät angeschlossen haben.",
        can_continue=False,
    ),
    Failure.STT_UNAVAILABLE: Recovery(
        Failure.STT_UNAVAILABLE,
        "Die Spracherkennung ist nicht verfügbar.",
        "Bedienen Sie den Rechner mit Tastatur und Orca. Sie können Clausis im "
        "Terminal mit clausis-runtime --stdin auch getippt steuern.",
        can_continue=False,
    ),
    Failure.NO_NETWORK: Recovery(
        Failure.NO_NETWORK,
        "Es besteht keine Netzwerkverbindung. Die Offline-Befehle funktionieren weiter.",
        "Für das Netzwerk sagen Sie Schnelleinstellungen oder öffnen die "
        "Einstellungen mit Tastatur und Orca.",
        can_continue=True,
    ),
    Failure.AGENT_UNAVAILABLE: Recovery(
        Failure.AGENT_UNAVAILABLE,
        "Der Assistent antwortet nicht. Die Offline-Befehle funktionieren weiter.",
        "Sagen Sie Was kann ich hier tun, oder verwenden Sie Tastatur und Orca.",
        can_continue=True,
    ),
    Failure.BROKER_UNAVAILABLE: Recovery(
        Failure.BROKER_UNAVAILABLE,
        "Die Aktionsprüfung ist nicht erreichbar. Ich führe deshalb nichts aus.",
        "Bedienen Sie den Rechner mit Tastatur und Orca. Ein Neustart der "
        "Sitzung stellt die Aktionsprüfung wieder her.",
        can_continue=True,
    ),
    Failure.CONFIRMATION_UNAVAILABLE: Recovery(
        Failure.CONFIRMATION_UNAVAILABLE,
        "Die geschützte Bestätigung ist nicht verfügbar. Die Aktion wurde nicht ausgeführt.",
        "Führen Sie die Aktion mit Tastatur und Orca aus. Das ist der "
        "gleichwertige Weg und keine Notlösung.",
        can_continue=True,
    ),
    Failure.SHELL_BRIDGE_MISSING: Recovery(
        Failure.SHELL_BRIDGE_MISSING,
        "Die Erweiterung für die GNOME-Shell ist nicht aktiv.",
        "Fensterwechsel und Übersicht erreichen Sie mit Super und Alt plus Tab "
        "über die Tastatur.",
        can_continue=True,
    ),
    Failure.DIALOG_BLOCKED: Recovery(
        Failure.DIALOG_BLOCKED,
        "Dieser Dialog lässt sich nicht per Sprache beantworten.",
        "Wechseln Sie mit Tabulator zwischen den Schaltflächen und bestätigen "
        "Sie mit der Eingabetaste. Orca liest dabei jede Schaltfläche vor.",
        can_continue=True,
    ),
    Failure.UPDATE_FAILED: Recovery(
        Failure.UPDATE_FAILED,
        "Die Aktualisierung ist fehlgeschlagen. Das System wurde nicht verändert.",
        "Sagen Sie Systemstatus für den Zustand. Über Tastatur und Orca können "
        "Sie die Aktualisierung in den Einstellungen erneut starten.",
        can_continue=True,
    ),
}


def recovery_for(failure: Failure) -> Recovery:
    return RECOVERIES[failure]


NOTIFY_COMMAND = ("notify-send", "--urgency=critical", "--app-name=Clausis", "Clausis")


def _notify(text: str) -> bool:
    """Show a desktop notification with a fixed argument vector."""

    if not shutil.which(NOTIFY_COMMAND[0]):
        return False
    try:
        completed = subprocess.run(
            [*NOTIFY_COMMAND, text],
            shell=False,
            check=False,
            capture_output=True,
            text=True,
            timeout=10.0,
        )
    except (OSError, subprocess.SubprocessError):
        return False
    return completed.returncode == 0


class Announcer:
    """Deliver a message through the first channel that still works.

    Speech is preferred, then a desktop notification — which Orca reads aloud —
    and finally the terminal.  The caller learns which channel was used so a
    dead speech path can itself be reported and recovered from.
    """

    def __init__(
        self,
        speaker: Optional[object] = None,
        *,
        language: str = "de",
        notifier: Callable[[str], bool] = _notify,
        stream=None,
    ) -> None:
        self.speaker = speaker
        self.language = language
        self.notifier = notifier
        self.stream = stream if stream is not None else sys.stderr
        self.speech_failed = False

    def announce(self, text: str) -> str:
        if self.speaker is not None and not self.speech_failed:
            try:
                self.speaker.speak(text, language=self.language)
                return "speech"
            except Exception:
                # Remember the failure so every later message goes straight to
                # a channel that works instead of stalling on the same error.
                self.speech_failed = True
        if self.notifier(text):
            return "notification"
        print(text, file=self.stream, flush=True)
        return "text"

    def announce_recovery(self, failure: Failure) -> str:
        return self.announce(recovery_for(failure).message())
