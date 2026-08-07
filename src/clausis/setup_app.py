"""Accessible GTK and local-voice setup surface for the Clausis live system."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import re
import sys
import threading
from typing import Sequence

from .hermes_setup import (
    HermesSetupPlan,
    PROVIDERS,
    configure_hermes,
    stage_installer_configuration,
)
from .speech import LocalWhisper, MicrophoneRecorder, SpeechError, SystemSpeaker, record_temporary


WELCOME = (
    "Willkommen bei Clausis. Hermes Agent ist bereits installiert. Während der Installation "
    "sucht Clausis nach der neuesten offiziellen stabilen Version. Ohne Internet bleibt die "
    "geprüfte mitgelieferte Version erhalten. "
    "Dieser Dialog kann mit Orca, Tastatur oder Sprache bedient werden. "
    "Cloud API-Schlüssel werden geschützt per Tastatur eingegeben und niemals vorgelesen."
)


def save_setup_configuration(
    home: Path,
    plan: HermesSetupPlan,
    *,
    secret: str = "",
    realtime_secret: str = "",
    stage_for_installer: bool,
) -> None:
    """Save once in an installed system or stage an additional Calamares copy."""
    if stage_for_installer:
        stage_installer_configuration(
            home, plan, secret=secret, realtime_secret=realtime_secret
        )
    else:
        configure_hermes(
            home, plan, secret=secret, realtime_secret=realtime_secret
        )


def provider_from_speech(transcript: str) -> str:
    normalized = transcript.casefold()
    aliases = (
        ("zai", ("glm", "z ai", "z.ai", "zhipu")),
        ("anthropic", ("anthropic", "claude")),
        ("openrouter", ("open router", "openrouter")),
        ("nous", ("nous", "nous api")),
        ("local", ("lokal", "local", "ollama")),
        ("custom", ("kompatibel", "compatible", "eigener anbieter")),
        ("offline", ("offline", "später", "skip", "überspringen")),
    )
    for identifier, words in aliases:
        if any(word in normalized for word in words):
            return identifier
    raise ValueError("Der Anbieter wurde nicht eindeutig erkannt.")


def affirmative_from_speech(transcript: str) -> bool:
    normalized = transcript.casefold().strip()
    if re.search(r"\b(nein|no|abbrechen|nicht zustimmen)\b", normalized):
        return False
    if re.search(r"\b(ja|yes|zustimmen|einverstanden)\b", normalized):
        return True
    raise ValueError("Bitte antworten Sie eindeutig mit Ja oder Nein.")


class SetupWindow:
    def __init__(self, live_home: Path, *, stage_for_installer: bool = True) -> None:
        import gi

        gi.require_version("Gtk", "3.0")
        from gi.repository import GLib, Gtk

        self.GLib = GLib
        self.Gtk = Gtk
        self.live_home = live_home
        self.stage_for_installer = stage_for_installer
        self.speaker = SystemSpeaker()
        self.window = Gtk.Window(title="Clausis – Hermes und Installation")
        self.window.get_accessible().set_name("Clausis Hermes und Installation")
        self.window.set_default_size(780, 760)
        self.window.set_border_width(24)
        self.window.connect("destroy", Gtk.main_quit)

        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=14)
        self.window.add(box)
        heading = Gtk.Label()
        heading.set_markup("<span size='xx-large' weight='bold'>Clausis einrichten</span>")
        heading.set_xalign(0)
        box.pack_start(heading, False, False, 0)
        intro = Gtk.Label(label=WELCOME)
        intro.set_line_wrap(True)
        intro.set_xalign(0)
        box.pack_start(intro, False, False, 0)

        grid = Gtk.Grid(column_spacing=16, row_spacing=12)
        box.pack_start(grid, True, True, 0)
        self.provider = Gtk.ComboBoxText()
        for identifier, option in PROVIDERS.items():
            self.provider.append(identifier, option.label_de)
        self.provider.set_active_id("offline")
        self._row(grid, 0, "_Hermes-Anbieter", self.provider)
        self.model = Gtk.Entry()
        self.model.set_placeholder_text("Wird passend zum Anbieter vorgeschlagen")
        self._row(grid, 1, "_Modell", self.model)
        self.base_url = Gtk.Entry()
        self.base_url.set_placeholder_text("https://… oder lokaler Server")
        self._row(grid, 2, "_Basis-URL", self.base_url)
        self.secret = Gtk.Entry()
        self.secret.set_visibility(False)
        self.secret.set_input_purpose(Gtk.InputPurpose.PASSWORD)
        self.secret.set_placeholder_text("Wird nicht angezeigt oder vorgelesen")
        self._row(grid, 3, "API-_Schlüssel", self.secret)
        self.consent = Gtk.CheckButton(
            label="Ich stimme der Übertragung meiner Hermes-Anfragen an den gewählten Cloud-Anbieter zu."
        )
        self.consent.get_accessible().set_name("Cloud-Übertragung erlauben")
        grid.attach(self.consent, 0, 4, 2, 1)

        self.realtime = Gtk.CheckButton(
            label="Freiwillig: _GPT Live für flüssige Online-Sprache und Systemsteuerung verwenden"
        )
        self.realtime.set_use_underline(True)
        self.realtime.get_accessible().set_name("GPT Live freiwillig aktivieren")
        grid.attach(self.realtime, 0, 5, 2, 1)
        live_notice = Gtk.Label(
            label=(
                "Dabei wird Mikrofon-Audio an OpenAI übertragen. Die OpenAI API wird separat "
                "abgerechnet; ein ChatGPT-Abonnement enthält nicht automatisch API-Guthaben."
            )
        )
        live_notice.set_line_wrap(True)
        live_notice.set_xalign(0)
        live_notice.get_accessible().set_name("GPT Live Kosten- und Datenschutzhinweis")
        grid.attach(live_notice, 0, 6, 2, 1)
        self.realtime_consent = Gtk.CheckButton(
            label="Ich stimme der laufenden Übertragung meiner Sprache an OpenAI zu."
        )
        self.realtime_consent.get_accessible().set_name(
            "GPT Live Audioübertragung erlauben"
        )
        grid.attach(self.realtime_consent, 0, 7, 2, 1)
        self.realtime_secret = Gtk.Entry()
        self.realtime_secret.set_visibility(False)
        self.realtime_secret.set_input_purpose(Gtk.InputPurpose.PASSWORD)
        self.realtime_secret.set_placeholder_text(
            "OpenAI API-Schlüssel – wird nie vorgelesen"
        )
        self._row(grid, 8, "OpenAI API-_Schlüssel", self.realtime_secret)

        self.status = Gtk.Label(label="Noch nicht eingerichtet.")
        self.status.get_accessible().set_name("Status der Einrichtung")
        self.status.set_xalign(0)
        self.status.set_line_wrap(True)
        box.pack_start(self.status, False, False, 0)
        buttons = Gtk.ButtonBox(orientation=Gtk.Orientation.HORIZONTAL)
        buttons.set_layout(Gtk.ButtonBoxStyle.END)
        box.pack_start(buttons, False, False, 0)
        self.voice_button = Gtk.Button.new_with_mnemonic("Mit _Sprache auswählen")
        self.voice_button.set_tooltip_text("Nennt den Anbieter per lokaler Spracherkennung")
        self.voice_button.connect("clicked", self._voice_clicked)
        buttons.add(self.voice_button)
        self.save_button = Gtk.Button.new_with_mnemonic(
            "_Speichern und Installation fortsetzen"
        )
        self.save_button.get_style_context().add_class("suggested-action")
        self.save_button.connect("clicked", self._save_clicked)
        buttons.add(self.save_button)
        self.provider.connect("changed", self._provider_changed)
        self.realtime.connect("toggled", self._realtime_changed)
        self._provider_changed(self.provider)
        self._realtime_changed(self.realtime)

    def _row(self, grid, row: int, text: str, widget) -> None:
        label = self.Gtk.Label.new_with_mnemonic(text)
        label.set_xalign(0)
        label.set_mnemonic_widget(widget)
        widget.get_accessible().set_name(text.replace("_", ""))
        grid.attach(label, 0, row, 1, 1)
        grid.attach(widget, 1, row, 1, 1)

    def _provider_changed(self, _widget) -> None:
        option = PROVIDERS[self.provider.get_active_id() or "offline"]
        if not self.model.get_text().strip() or self.model.get_text() in {
            item.default_model for item in PROVIDERS.values()
        }:
            self.model.set_text(option.default_model)
        self.base_url.set_text(option.base_url)
        self.secret.set_sensitive(option.secret_environment is not None)
        self.consent.set_sensitive(option.cloud)
        if not option.cloud:
            self.consent.set_active(False)

    def _realtime_changed(self, _widget) -> None:
        enabled = self.realtime.get_active()
        self.realtime_consent.set_sensitive(enabled)
        self.realtime_secret.set_sensitive(enabled)
        if not enabled:
            self.realtime_consent.set_active(False)

    def _plan(self) -> HermesSetupPlan:
        return HermesSetupPlan(
            provider_id=self.provider.get_active_id() or "offline",
            model=self.model.get_text(),
            base_url=self.base_url.get_text(),
            cloud_consent=self.consent.get_active(),
            realtime_enabled=self.realtime.get_active(),
            realtime_cloud_consent=self.realtime_consent.get_active(),
        )

    def _save_clicked(self, _button) -> None:
        try:
            plan = self._plan()
            save_setup_configuration(
                self.live_home,
                plan,
                secret=self.secret.get_text(),
                realtime_secret=self.realtime_secret.get_text(),
                stage_for_installer=self.stage_for_installer,
            )
        except (OSError, ValueError) as exc:
            self.status.set_text(f"Nicht gespeichert: {exc}")
            self._speak_async(f"Nicht gespeichert. {exc}")
            return
        self.secret.set_text("")
        self.realtime_secret.set_text("")
        self.status.set_text(plan.public_summary() + " Der Debian-Installer wird geöffnet.")
        self._speak_async(self.status.get_text())
        self.GLib.timeout_add(1200, self._close_after_save)

    def _close_after_save(self):
        self.window.destroy()
        return False

    def _voice_clicked(self, button) -> None:
        button.set_sensitive(False)
        self.status.set_text("Lokale Spracherkennung hört auf den Anbieternamen.")
        threading.Thread(target=self._voice_worker, args=(button,), daemon=True).start()

    def _voice_worker(self, button) -> None:
        audio_paths = []
        try:
            self.speaker.speak(
                "Nennen Sie einen Anbieter: Nous, Open Router, Anthropic, GLM, lokal, kompatibel oder später.",
                language="de",
            )
            audio_path = record_temporary(MicrophoneRecorder())
            audio_paths.append(audio_path)
            transcript = LocalWhisper(
                "/usr/share/clausis/models/faster-whisper-base", language="de"
            ).transcribe(audio_path)
            provider_id = provider_from_speech(transcript)
            consent = None
            if PROVIDERS[provider_id].cloud:
                self.speaker.speak(
                    "Dieser Anbieter erhält Ihre Hermes-Anfragen über das Internet. "
                    "Stimmen Sie zu? Sagen Sie eindeutig Ja oder Nein.",
                    language="de",
                )
                consent_path = record_temporary(MicrophoneRecorder())
                audio_paths.append(consent_path)
                consent_text = LocalWhisper(
                    "/usr/share/clausis/models/faster-whisper-base", language="de"
                ).transcribe(consent_path)
                consent = affirmative_from_speech(consent_text)
            self.speaker.speak(
                "Möchten Sie freiwillig GPT Live verwenden? Dabei wird Ihre Sprache laufend "
                "an OpenAI übertragen und die OpenAI API separat berechnet. Sagen Sie Ja oder Nein.",
                language="de",
            )
            realtime_path = record_temporary(MicrophoneRecorder())
            audio_paths.append(realtime_path)
            realtime_text = LocalWhisper(
                "/usr/share/clausis/models/faster-whisper-base", language="de"
            ).transcribe(realtime_path)
            realtime_consent = affirmative_from_speech(realtime_text)
            self.GLib.idle_add(
                self._apply_spoken_provider,
                provider_id,
                transcript,
                consent,
                realtime_consent,
            )
        except (SpeechError, ValueError) as exc:
            self.GLib.idle_add(self.status.set_text, f"Spracheingabe nicht übernommen: {exc}")
            self._speak_async(str(exc))
        finally:
            for audio_path in audio_paths:
                audio_path.unlink(missing_ok=True)
            self.GLib.idle_add(button.set_sensitive, True)

    def _apply_spoken_provider(
        self,
        provider_id: str,
        transcript: str,
        consent: bool | None,
        realtime_consent: bool,
    ):
        self.provider.set_active_id(provider_id)
        option = PROVIDERS[provider_id]
        if option.cloud:
            self.consent.set_active(consent is True)
            if consent:
                self.status.set_text(
                    f"Erkannt: {transcript}. Cloud-Übertragung wurde erlaubt. "
                    "Bitte den API-Schlüssel geschützt über die Tastatur eingeben."
                )
                self.secret.grab_focus()
            else:
                self.status.set_text(
                    f"Erkannt: {transcript}. Cloud-Übertragung wurde nicht erlaubt. "
                    "Es wurde noch nichts gespeichert."
                )
                self.consent.grab_focus()
        else:
            self.status.set_text(f"Erkannt: {transcript}. {option.label_de} ausgewählt.")
        self.realtime.set_active(realtime_consent)
        self.realtime_consent.set_active(realtime_consent)
        if realtime_consent:
            self.status.set_text(
                self.status.get_text()
                + " GPT Live wurde erlaubt. Bitte den OpenAI API-Schlüssel geschützt eingeben."
            )
            self.realtime_secret.grab_focus()
        return False

    def _speak_async(self, text: str) -> None:
        def worker() -> None:
            try:
                self.speaker.speak(text, language="de")
            except SpeechError:
                pass

        threading.Thread(target=worker, daemon=True).start()

    def run(self) -> int:
        self.window.show_all()
        self.secret.set_sensitive(
            PROVIDERS[self.provider.get_active_id() or "offline"].secret_environment
            is not None
        )
        self._realtime_changed(self.realtime)
        self._speak_async(WELCOME)
        self.Gtk.main()
        return 0

    def accessibility_report(self) -> dict:
        """Return a deterministic smoke report for the ISO build gate."""
        widgets = {
            "window": self.window,
            "provider": self.provider,
            "model": self.model,
            "base_url": self.base_url,
            "secret": self.secret,
            "consent": self.consent,
            "realtime": self.realtime,
            "realtime_consent": self.realtime_consent,
            "realtime_secret": self.realtime_secret,
            "status": self.status,
            "voice": self.voice_button,
            "save": self.save_button,
        }
        names = {
            key: (widget.get_accessible().get_name() or "").strip()
            for key, widget in widgets.items()
        }
        return {
            "ok": all(names.values())
            and not self.secret.get_visibility()
            and not self.realtime_secret.get_visibility(),
            "names": names,
            "secret_hidden": not self.secret.get_visibility(),
            "realtime_secret_hidden": not self.realtime_secret.get_visibility(),
        }


def main(argv: Sequence[str] = ()) -> int:
    parser = argparse.ArgumentParser(description="Barrierefreie Clausis-Einrichtung")
    parser.add_argument("--home", type=Path, default=Path.home())
    parser.add_argument(
        "--installed",
        action="store_true",
        help="direkt für das installierte Konto speichern, ohne Calamares-Kopie",
    )
    parser.add_argument("--provider-from-text", help="Sprachtext ohne Mikrofon auswerten")
    parser.add_argument(
        "--accessibility-check",
        action="store_true",
        help="Beschriftungen und verdeckte Schlüsseleingabe prüfen",
    )
    args = parser.parse_args(list(argv) or None)
    if args.provider_from_text is not None:
        print(provider_from_speech(args.provider_from_text))
        return 0
    try:
        window = SetupWindow(args.home, stage_for_installer=not args.installed)
        if args.accessibility_check:
            report = window.accessibility_report()
            print(json.dumps(report, ensure_ascii=False, sort_keys=True))
            window.window.hide()
            return 0 if report["ok"] else 1
        return window.run()
    except ImportError as exc:
        print(f"GTK-Einrichtung nicht verfügbar: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
