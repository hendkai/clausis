"""Trusted confirmation state machine.

This service must run outside the desktop accessibility tree in production.
It generates the challenge itself, speaks the canonical action summary, and
issues a capability only after an exact, time-bounded response and PIN check.
"""

from __future__ import annotations

from dataclasses import dataclass, replace
from datetime import timedelta
import hashlib
import hmac
import re
import secrets
from typing import Dict, Mapping, Optional, Protocol, Sequence

from .capabilities import CapabilityAuthority
from .models import ActionRequest, Origin, utc_now
from .policy import evaluate


DEFAULT_WORDS = (
    "anker", "birke", "dachs", "eule", "feder", "garten", "hafen", "insel",
    "kerze", "lampe", "mond", "nuss", "quelle", "regen", "sonne", "wolke",
)


@dataclass
class PendingConfirmation:
    confirmation_id: str
    request: ActionRequest
    phrase: str
    expires_at: object
    attempts: int = 0


@dataclass(frozen=True)
class ConfirmationResponse:
    """Secrets captured inside the trusted service process only."""

    phrase: str
    pin: str


class TrustedInput(Protocol):
    """Direct input path that is not exposed through desktop automation."""

    def collect(self, summary: str, challenge: str) -> ConfirmationResponse:
        ...


class PinVerifier:
    """PBKDF2 PIN verifier; plaintext PINs are never persisted.

    PBKDF2-HMAC-SHA-256 is available in every supported Python/OpenSSL build,
    including the minimal installer environment.  The format is deliberately
    versioned so a future Argon2 migration can happen without guessing.
    """

    ALGORITHM = "pbkdf2-sha256-v1"
    ITERATIONS = 600_000

    def __init__(self, salt: bytes, digest: bytes) -> None:
        self._salt = salt
        self._digest = digest

    @classmethod
    def enroll(cls, pin: str) -> "PinVerifier":
        cls.validate_pin(pin)
        salt = secrets.token_bytes(16)
        return cls(salt, cls._derive(pin, salt))

    @classmethod
    def from_hex(cls, salt: str, digest: str) -> "PinVerifier":
        decoded_salt = bytes.fromhex(salt)
        decoded_digest = bytes.fromhex(digest)
        if len(decoded_salt) != 16 or len(decoded_digest) != 32:
            raise ValueError("invalid PIN verifier size")
        return cls(decoded_salt, decoded_digest)

    @classmethod
    def from_export(cls, data: Mapping[str, object]) -> "PinVerifier":
        allowed = {"algorithm", "iterations", "salt", "digest"}
        if set(data) != allowed:
            raise ValueError("invalid PIN verifier fields")
        if data["algorithm"] != cls.ALGORITHM:
            raise ValueError("unsupported PIN verifier algorithm")
        if data["iterations"] != str(cls.ITERATIONS):
            raise ValueError("unexpected PIN verifier work factor")
        return cls.from_hex(str(data["salt"]), str(data["digest"]))

    def export(self) -> Dict[str, str]:
        return {
            "algorithm": self.ALGORITHM,
            "iterations": str(self.ITERATIONS),
            "salt": self._salt.hex(),
            "digest": self._digest.hex(),
        }

    def verify(self, pin: str) -> bool:
        try:
            candidate = self._derive(pin, self._salt)
        except (TypeError, ValueError):
            return False
        return hmac.compare_digest(candidate, self._digest)

    @classmethod
    def _derive(cls, pin: str, salt: bytes) -> bytes:
        return hashlib.pbkdf2_hmac(
            "sha256", pin.encode("utf-8"), salt, cls.ITERATIONS, dklen=32
        )

    @staticmethod
    def validate_pin(pin: str) -> None:
        if not isinstance(pin, str) or not pin.isdigit() or not 6 <= len(pin) <= 12:
            raise ValueError("PIN must contain 6 to 12 digits")


class TrustedConfirmer:
    def __init__(
        self,
        authority: CapabilityAuthority,
        pin_verifier: PinVerifier,
        *,
        words: Sequence[str] = DEFAULT_WORDS,
        ttl_seconds: int = 90,
        capability_ttl_seconds: int = 30,
    ) -> None:
        if len(words) < 8:
            raise ValueError("challenge vocabulary is too small")
        self._authority = authority
        self._pin = pin_verifier
        self._words = tuple(words)
        self._ttl_seconds = ttl_seconds
        self._capability_ttl_seconds = capability_ttl_seconds
        self._pending: Dict[str, PendingConfirmation] = {}

    def begin(self, request: ActionRequest) -> PendingConfirmation:
        confirmation_id = secrets.token_urlsafe(18)
        phrase = " ".join(secrets.choice(self._words) for _ in range(3))
        pending = PendingConfirmation(
            confirmation_id=confirmation_id,
            request=request,
            phrase=phrase,
            expires_at=utc_now() + timedelta(seconds=self._ttl_seconds),
        )
        self._pending[confirmation_id] = pending
        return pending

    def canonical_summary(self, pending: PendingConfirmation) -> str:
        request = pending.request
        irreversible = "nicht rückgängig" if not request.reversible else "rückgängig machbar"
        fixed_targets = {
            "desktop.text.set": "das aktuell fokussierte Textfeld; der Inhalt wird nicht wiederholt",
            "desktop.text.copy_focused": "den vollständigen Inhalt des aktuell fokussierten, nicht geschützten Textfelds in die Wayland-Zwischenablage kopieren; der Inhalt wird nicht wiederholt und der bisherige Zwischenablageinhalt wird überschrieben",
            "desktop.text.copy_selection": "die aktuell eindeutig ausgewählte Textspanne aus dem fokussierten, nicht geschützten Textfeld in die Wayland-Zwischenablage kopieren; der Inhalt wird nicht wiederholt und der bisherige Zwischenablageinhalt wird überschrieben",
            "desktop.text.read_selection": "die aktuell eindeutig ausgewählte Textspanne aus dem fokussierten, nicht geschützten Textfeld laut vorlesen; der Inhalt selbst wird weder in dieser Bestätigung noch im Audit gespeichert",
            "desktop.text.delete_selection": "die aktuell eindeutig ausgewählte Textspanne aus dem fokussierten, nicht geschützten Textfeld löschen; der Inhalt wird nicht wiederholt und bei einer Abweichung wird der vorherige Feldzustand wiederhergestellt",
            "desktop.text.delete_current_line": "die aktuelle begrenzte Zeile am Textcursor einschließlich genau eines zugehörigen Zeilenumbruchs aus dem fokussierten, nicht geschützten Textfeld löschen; der Inhalt wird nicht wiederholt und bei einer Abweichung werden Text und Cursor wiederhergestellt",
            "desktop.text.replace_current_line": "die aktuelle begrenzte Zeile am Textcursor im fokussierten, nicht geschützten Textfeld durch den diktierten Text ersetzen; alter und neuer Inhalt werden nicht wiederholt, der vorhandene Zeilenumbruch bleibt erhalten und bei einer Abweichung werden Text und Cursor wiederhergestellt",
            "desktop.text.insert_line_above": "eine neue einzeilige Textzeile direkt oberhalb der aktuellen begrenzten Zeile im fokussierten, nicht geschützten Textfeld einfügen; der diktierte Inhalt wird nicht wiederholt und bei einer Abweichung werden Text und Cursor wiederhergestellt",
            "desktop.text.insert_line_below": "eine neue einzeilige Textzeile direkt unterhalb der aktuellen begrenzten Zeile im fokussierten, nicht geschützten Textfeld einfügen; der diktierte Inhalt wird nicht wiederholt und bei einer Abweichung werden Text und Cursor wiederhergestellt",
            "desktop.text.duplicate_line_above": "die aktuelle begrenzte nicht leere Zeile im fokussierten, nicht geschützten Textfeld direkt oberhalb duplizieren; der Zeileninhalt wird weder wiederholt noch auditiert und bei einer Abweichung werden Text und Cursor wiederhergestellt",
            "desktop.text.duplicate_line_below": "die aktuelle begrenzte nicht leere Zeile im fokussierten, nicht geschützten Textfeld direkt unterhalb duplizieren; der Zeileninhalt wird weder wiederholt noch auditiert und bei einer Abweichung werden Text und Cursor wiederhergestellt",
            "desktop.text.move_line_up": "die aktuelle begrenzte Zeile im fokussierten, nicht geschützten Textfeld exakt mit der Zeile darüber vertauschen; beide Inhalte werden weder wiederholt noch auditiert, die relative Cursorposition bleibt erhalten und bei einer Abweichung werden Text und Cursor wiederhergestellt",
            "desktop.text.move_line_down": "die aktuelle begrenzte Zeile im fokussierten, nicht geschützten Textfeld exakt mit der Zeile darunter vertauschen; beide Inhalte werden weder wiederholt noch auditiert, die relative Cursorposition bleibt erhalten und bei einer Abweichung werden Text und Cursor wiederhergestellt",
            "desktop.text.join_previous_line": "genau den Zeilenumbruch zwischen der aktuellen begrenzten Zeile und der begrenzten Zeile davor im fokussierten, nicht geschützten Textfeld entfernen; beide Inhalte werden weder wiederholt noch auditiert und bei einer Abweichung werden Text und Cursor wiederhergestellt",
            "desktop.text.join_next_line": "genau den Zeilenumbruch zwischen der aktuellen begrenzten Zeile und der begrenzten Zeile danach im fokussierten, nicht geschützten Textfeld entfernen; beide Inhalte werden weder wiederholt noch auditiert und bei einer Abweichung werden Text und Cursor wiederhergestellt",
            "desktop.text.split_line_at_caret": "genau einen Zeilenumbruch an der aktuellen Textcursorposition in der begrenzten aktuellen Zeile des fokussierten, nicht geschützten Textfelds einfügen; der Zeileninhalt wird weder wiederholt noch auditiert und bei einer Abweichung werden Text und Cursor wiederhergestellt",
            "desktop.text.indent_current_line": "genau vier Leerzeichen vor der aktuellen begrenzten Zeile im fokussierten, nicht geschützten Textfeld einfügen; der Zeileninhalt wird weder wiederholt noch auditiert und bei einer Abweichung werden Text und Cursor wiederhergestellt",
            "desktop.text.outdent_current_line": "genau einen führenden Tabulator oder bis zu vier führende Leerzeichen aus der aktuellen begrenzten Zeile im fokussierten, nicht geschützten Textfeld entfernen; der Zeileninhalt wird weder wiederholt noch auditiert und bei einer Abweichung werden Text und Cursor wiederhergestellt",
            "desktop.text.insert_at_caret": "den diktierten Text an der aktuellen Textcursorposition im fokussierten, nicht geschützten Textfeld einfügen; der Inhalt wird nicht wiederholt und bei einer Abweichung wird der vorherige Feldzustand wiederhergestellt",
            "desktop.text.delete_previous_character": "genau ein vorhandenes Zeichen unmittelbar vor dem Textcursor im fokussierten, nicht geschützten Textfeld löschen; der Inhalt wird nicht wiederholt und bei einer Abweichung wird der vorherige Feldzustand wiederhergestellt",
            "desktop.text.delete_next_character": "genau ein vorhandenes Zeichen unmittelbar nach dem Textcursor im fokussierten, nicht geschützten Textfeld löschen; der Inhalt wird nicht wiederholt und bei einer Abweichung wird der vorherige Feldzustand wiederhergestellt",
            "desktop.text.delete_previous_word": "genau ein vorhandenes Wort vor dem Textcursor im fokussierten, nicht geschützten Textfeld löschen; der Inhalt wird nicht wiederholt und bei einer Abweichung wird der vorherige Feldzustand wiederhergestellt",
            "desktop.text.delete_next_word": "genau ein vorhandenes Wort nach dem Textcursor im fokussierten, nicht geschützten Textfeld löschen; der Inhalt wird nicht wiederholt und bei einer Abweichung wird der vorherige Feldzustand wiederhergestellt",
            "desktop.text.replace_previous_word": "genau ein vorhandenes Wort vor dem Textcursor im fokussierten, nicht geschützten Textfeld durch den diktierten Text ersetzen; alter und neuer Inhalt werden nicht wiederholt und bei einer Abweichung wird der vorherige Feldzustand wiederhergestellt",
            "desktop.text.replace_next_word": "genau ein vorhandenes Wort nach dem Textcursor im fokussierten, nicht geschützten Textfeld durch den diktierten Text ersetzen; alter und neuer Inhalt werden nicht wiederholt und bei einer Abweichung wird der vorherige Feldzustand wiederhergestellt",
            "desktop.text.replace_selection": "die aktuell eindeutig ausgewählte Textspanne im fokussierten, nicht geschützten Textfeld durch den diktierten Text ersetzen; Auswahl- und Ersatzinhalt werden nicht wiederholt und bei einer Abweichung wird der vorherige Feldzustand wiederhergestellt",
            "desktop.text.read_previous_character": "genau ein vorhandenes Zeichen unmittelbar vor dem Textcursor im fokussierten, nicht geschützten Textfeld laut vorlesen; das Zeichen selbst wird weder in dieser Bestätigung noch im Audit gespeichert",
            "desktop.text.read_next_character": "genau ein vorhandenes Zeichen unmittelbar nach dem Textcursor im fokussierten, nicht geschützten Textfeld laut vorlesen; das Zeichen selbst wird weder in dieser Bestätigung noch im Audit gespeichert",
            "desktop.text.read_previous_word": "genau ein vorhandenes Wort vor dem Textcursor im fokussierten, nicht geschützten Textfeld innerhalb einer begrenzten Suche laut vorlesen; das Wort selbst wird weder in dieser Bestätigung noch im Audit gespeichert",
            "desktop.text.read_next_word": "genau ein vorhandenes Wort nach dem Textcursor im fokussierten, nicht geschützten Textfeld innerhalb einer begrenzten Suche laut vorlesen; das Wort selbst wird weder in dieser Bestätigung noch im Audit gespeichert",
            "desktop.text.read_current_line": "die aktuelle, auf höchstens 1.000 Zeichen begrenzte Zeile am Textcursor im fokussierten, nicht geschützten Textfeld laut vorlesen; der Zeileninhalt selbst wird weder in dieser Bestätigung noch im Audit gespeichert",
            "desktop.text.paste_focused": "den begrenzten Textinhalt der Wayland-Zwischenablage in das aktuell fokussierte, nicht geschützte und editierbare Textfeld einfügen; der Inhalt wird nicht wiederholt und der bisherige Feldinhalt wird überschrieben",
            "desktop.window.workspace_previous": "das aktive Fenster auf die vorherige Arbeitsfläche",
            "desktop.window.workspace_next": "das aktive Fenster auf die nächste Arbeitsfläche",
            "desktop.clipboard.clear": "den aktuellen Inhalt der Wayland-Zwischenablage dauerhaft löschen; die primäre Auswahl bleibt unverändert",
            "desktop.clipboard.read_text": "den Textinhalt der Wayland-Zwischenablage nach der Bestätigung laut vorlesen; der Inhalt selbst wird weder in dieser Bestätigung noch im Audit gespeichert",
            "desktop.clipboard.write_text": "den diktierten Text dauerhaft in die Wayland-Zwischenablage schreiben und deren bisherigen Inhalt überschreiben; der diktierte Inhalt wird weder wiederholt noch im Audit gespeichert",
            "accessibility.screen_keyboard.enable": "die GNOME-Bildschirmtastatur dauerhaft einschalten",
            "accessibility.screen_reader.enable": "den Orca-Screenreader dauerhaft einschalten",
            "accessibility.screen_reader.restart_with_speech": "den Orca-Screenreader mit erzwungener Sprachausgabe neu starten",
            "accessibility.screen_magnifier.enable": "die GNOME-Bildschirmvergrößerung dauerhaft einschalten",
            "accessibility.screen_magnifier.disable": "die GNOME-Bildschirmvergrößerung ausschalten; Orca und Bildschirmtastatur bleiben eingeschaltet",
            "accessibility.screen_magnifier.invert_lightness.enable": "die Farbinvertierung der GNOME-Bildschirmvergrößerung einschalten",
            "accessibility.screen_magnifier.invert_lightness.disable": "die Farbinvertierung der GNOME-Bildschirmvergrößerung ausschalten",
            "accessibility.screen_magnifier.cross_hairs.enable": "das Fadenkreuz der GNOME-Bildschirmvergrößerung einschalten",
            "accessibility.screen_magnifier.cross_hairs.disable": "das Fadenkreuz der GNOME-Bildschirmvergrößerung ausschalten",
            "accessibility.screen_magnifier.cross_hairs.clip.enable": "die Mitte des Lupen-Fadenkreuzes um den Zeiger aussparen",
            "accessibility.screen_magnifier.cross_hairs.clip.disable": "die Aussparung in der Mitte des Lupen-Fadenkreuzes aufheben",
            "accessibility.screen_magnifier.lens_mode.enable": "den Linsenmodus der GNOME-Bildschirmvergrößerung einschalten",
            "accessibility.screen_magnifier.lens_mode.disable": "den Linsenmodus der GNOME-Bildschirmvergrößerung ausschalten",
            "accessibility.screen_magnifier.scroll_at_edges.enable": "das Scrollen am Bildschirmrand für die GNOME-Bildschirmvergrößerung einschalten",
            "accessibility.screen_magnifier.scroll_at_edges.disable": "das Scrollen am Bildschirmrand für die GNOME-Bildschirmvergrößerung ausschalten",
        }
        target = fixed_targets.get(request.action, request.target or "das System")
        if request.action == "accessibility.screen_magnifier.set_percent":
            target = f"die GNOME-Bildschirmvergrößerung auf {request.arguments['percent']} Prozent"
        elif request.action == "accessibility.screen_magnifier.set_saturation":
            target = f"die Farbsättigung der GNOME-Bildschirmvergrößerung auf {request.arguments['percent']} Prozent"
        elif request.action in {
            "accessibility.screen_magnifier.set_brightness",
            "accessibility.screen_magnifier.set_contrast",
        }:
            feature = "Helligkeit" if request.action.endswith("brightness") else "Kontrast"
            percent = request.arguments["percent"]
            target = f"{feature} der GNOME-Bildschirmvergrößerung auf {percent:+d} Prozent setzen"
        elif request.action == "accessibility.screen_magnifier.set_screen_position":
            positions = {
                "full-screen": "Vollbild",
                "top-half": "die obere Bildschirmhälfte",
                "bottom-half": "die untere Bildschirmhälfte",
                "left-half": "die linke Bildschirmhälfte",
                "right-half": "die rechte Bildschirmhälfte",
            }
            target = f"die GNOME-Bildschirmvergrößerung auf {positions[request.arguments['position']]} begrenzen"
        elif request.action == "accessibility.screen_magnifier.cross_hairs.set_opacity":
            target = f"die Deckkraft des Lupen-Fadenkreuzes auf {request.arguments['percent']} Prozent"
        elif request.action == "accessibility.screen_magnifier.cross_hairs.set_length":
            target = f"die Länge des Lupen-Fadenkreuzes auf {request.arguments['pixels']} Pixel"
        elif request.action == "accessibility.screen_magnifier.cross_hairs.set_thickness":
            target = f"die Dicke des Lupen-Fadenkreuzes auf {request.arguments['pixels']} Pixel"
        elif request.action == "accessibility.screen_magnifier.cross_hairs.set_color":
            red = request.arguments["red"]
            green = request.arguments["green"]
            blue = request.arguments["blue"]
            target = f"die Farbe des Lupen-Fadenkreuzes auf RGB {red}, {green}, {blue} setzen"
        elif request.action == "accessibility.screen_magnifier.set_focus_tracking":
            modes = {
                "none": "aus",
                "centered": "zentriert",
                "proportional": "proportional",
                "push": "schiebend",
            }
            target = f"die Fokusverfolgung der GNOME-Bildschirmvergrößerung auf {modes[request.arguments['mode']]} setzen"
        elif request.action in {
            "accessibility.screen_magnifier.set_caret_tracking",
            "accessibility.screen_magnifier.set_mouse_tracking",
        }:
            modes = {
                "none": "aus",
                "centered": "zentriert",
                "proportional": "proportional",
                "push": "schiebend",
            }
            kind = "Textcursorverfolgung" if request.action.endswith("caret_tracking") else "Mausverfolgung"
            target = f"die {kind} der GNOME-Bildschirmvergrößerung auf {modes[request.arguments['mode']]} setzen"
        return (
            f"Geplante Aktion: {request.action}. Ziel: {target}. "
            f"Risiko: {request.risk.value}. Die Aktion ist {irreversible}. "
            f"Zum Bestätigen sagen Sie: {pending.phrase}."
        )

    def approve(self, confirmation_id: str, phrase: str, pin: str) -> str:
        pending = self._pending.get(confirmation_id)
        if pending is None:
            raise ValueError("unknown confirmation")
        if pending.expires_at <= utc_now():
            self._pending.pop(confirmation_id, None)
            raise ValueError("confirmation expired")
        pending.attempts += 1
        if pending.attempts > 3:
            self._pending.pop(confirmation_id, None)
            raise ValueError("too many confirmation attempts")
        normalized = " ".join(re.findall(r"[\wäöüß]+", phrase.casefold()))
        expected = " ".join(re.findall(r"[\wäöüß]+", pending.phrase.casefold()))
        if not hmac.compare_digest(normalized, expected):
            raise ValueError("challenge phrase did not match")
        if not self._pin.verify(pin):
            raise ValueError("PIN verification failed")
        self._pending.pop(confirmation_id, None)
        return self._authority.issue(
            pending.request, ttl_seconds=self._capability_ttl_seconds
        )

    def deny(self, confirmation_id: str) -> None:
        self._pending.pop(confirmation_id, None)

    def approve_from_trusted_input(
        self,
        request: ActionRequest,
        trusted_input: TrustedInput,
    ) -> ActionRequest:
        """Collect approval locally and return a single action-bound request.

        This is the only production approval path.  The challenge and PIN are
        deliberately passed only to an in-process input implementation; they
        must never be parameters or return values of the public D-Bus API.
        """

        if request.capability_token is not None:
            raise ValueError("caller-supplied capabilities are forbidden")
        decision = evaluate(request)
        if not decision.confirmation_required:
            raise ValueError("action does not require trusted confirmation")
        pending = self.begin(request)
        try:
            response = trusted_input.collect(
                self.canonical_summary(pending), pending.phrase
            )
            capability = self.approve(
                pending.confirmation_id, response.phrase, response.pin
            )
            return replace(request, capability_token=capability)
        except Exception:
            self.deny(pending.confirmation_id)
            raise


def canonicalize_untrusted_request(request: ActionRequest) -> ActionRequest:
    """Remove authority claims made by a normal system-bus client.

    Requests that cross the public bus are never treated as local voice/UI
    input.  Keeping ``external_content`` preserves the stronger audit label;
    every other caller is conservatively treated as Hermes-originated.
    """

    if request.capability_token is not None:
        raise ValueError("caller-supplied capabilities are forbidden")
    origin = (
        Origin.EXTERNAL_CONTENT
        if request.origin is Origin.EXTERNAL_CONTENT
        else Origin.HERMES
    )
    return replace(request, origin=origin, capability_token=None)
