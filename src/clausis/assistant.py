"""Interactive, offline-first Clausis assistant for the live system."""

from __future__ import annotations

import argparse
import os
from pathlib import Path
import sys
import time
from typing import Sequence

from .broker import ActionBroker, SafeExecutor
from .audio import (
    AudioMode,
    LocalActivationController,
    choose_audio_mode,
    probe_audio_capabilities,
)
from .capabilities import CapabilityAuthority
from .hermes_client import HermesOneShot, hermes_is_configured
from .gpt_live import GptLiveSession, load_gpt_live_config, request_local_stop
from .gnome_adapter import SessionExecutor
from .router import OfflineRouter
from .runtime import RuntimeState, VoiceRuntime
from .speech import LocalWhisper, MicrophoneRecorder, SpeechError, SystemSpeaker, record_temporary
from .system_client import ConfirmationAwareBroker, SystemTrustedConfirmation


AI_NOTICE_DE = (
    "Hinweis: Clausis verwendet für Spracherkennung und optionale Antworten ein KI-System. "
    "Offline-Kernbefehle werden lokal verarbeitet. Sagen Sie jederzeit Stopp Hermes "
    "oder drücken Sie in einem geöffneten Terminal Steuerung C zum Beenden."
)


def _model_path(requested: str) -> str:
    bundled = Path("/usr/share/clausis/models/faster-whisper-base")
    return str(bundled) if requested == "base" and bundled.is_dir() else requested


def main(argv: Sequence[str] = ()) -> int:
    parser = argparse.ArgumentParser(description="Lokale Clausis-Sprachsteuerung")
    parser.add_argument("--language", choices=("de", "en"), default="de")
    parser.add_argument("--model", default="base")
    parser.add_argument("--execute", action="store_true", help="validierte, risikoarme Aktionen ausführen")
    parser.add_argument("--once", action="store_true", help="nach einer Äußerung beenden")
    parser.add_argument("--text", help="Text statt Mikrofon verwenden (Test und Barrierefreiheits-Fallback)")
    parser.add_argument(
        "--local",
        action="store_true",
        help="freiwillig konfiguriertes GPT Live für diesen Start überspringen",
    )
    parser.add_argument(
        "--stop-live",
        action="store_true",
        help="eine laufende GPT-Live-Sitzung lokal und ohne Cloud beenden",
    )
    args = parser.parse_args(list(argv) or None)

    if args.stop_live:
        request_local_stop()
        print("Lokaler Stopp für GPT Live wurde angefordert.", flush=True)
        return 0

    speaker = SystemSpeaker()
    print(AI_NOTICE_DE, flush=True)
    try:
        speaker.speak(AI_NOTICE_DE, language=args.language)
    except SpeechError as exc:
        print(f"Sprachausgabe eingeschränkt: {exc}", file=sys.stderr)

    local_broker = ActionBroker(
        CapabilityAuthority.generate(),
        SessionExecutor(SafeExecutor(dry_run=not args.execute)),
    )
    confirmer = (
        SystemTrustedConfirmation()
        if args.execute and Path("/etc/clausis/voice-pin.json").is_file()
        else None
    )
    broker = ConfirmationAwareBroker(local_broker, confirmer)
    live_config = None if args.local or args.text is not None else load_gpt_live_config(Path.home())
    if live_config is not None:
        live_notice = (
            "GPT Live ist aktiv. Mikrofon-Audio wird jetzt an OpenAI übertragen. "
            "Sagen Sie Stopp Clausis oder drücken Sie Steuerung C zum Beenden."
        )
        print(live_notice, flush=True)
        try:
            speaker.speak(live_notice, language=args.language)
            while True:
                started = time.monotonic()
                try:
                    return GptLiveSession(
                        live_config, broker, language=args.language
                    ).run()
                except RuntimeError:
                    if time.monotonic() - started < 50 * 60:
                        raise
                    reconnect_notice = (
                        "Die GPT Live Sitzung wird nach der Zeitgrenze sicher neu verbunden."
                    )
                    print(reconnect_notice, flush=True)
                    try:
                        speaker.speak(reconnect_notice, language=args.language)
                    except SpeechError:
                        pass
        except KeyboardInterrupt:
            print("Clausis beendet.", flush=True)
            return 130
        except (OSError, RuntimeError) as exc:
            print(f"GPT Live nicht verfügbar: {exc}", file=sys.stderr, flush=True)
            fallback_notice = (
                "GPT Live ist nicht erreichbar. Clausis verwendet jetzt automatisch "
                "die lokale Sprachsteuerung."
            )
            try:
                speaker.speak(fallback_notice, language=args.language)
            except SpeechError:
                pass

    hermes_fallback = HermesOneShot(home=Path.home()) if hermes_is_configured(Path.home()) else None
    runtime = VoiceRuntime(
        OfflineRouter(),
        broker,
        hermes_fallback=hermes_fallback,
    )
    recorder = MicrophoneRecorder()
    transcriber = LocalWhisper(_model_path(args.model), language=args.language)
    activation = LocalActivationController()
    pending_text = args.text

    audio_decision = choose_audio_mode(probe_audio_capabilities())
    print(audio_decision.announcement, flush=True)
    try:
        speaker.speak(audio_decision.announcement, language=args.language)
    except SpeechError:
        pass
    if pending_text is None and audio_decision.mode in {
        AudioMode.OUTPUT_ONLY,
        AudioMode.UNAVAILABLE,
    }:
        return 2
    wake_notice = "Die lokale Steuerung ist bereit. Sagen Sie Hallo Clausis."
    print(wake_notice, flush=True)
    try:
        speaker.speak(wake_notice, language=args.language)
    except SpeechError:
        pass

    while runtime.state is not RuntimeState.STOPPED:
        audio_path = None
        try:
            if pending_text is not None:
                transcript = pending_text
                pending_text = None
            else:
                audio_path = record_temporary(recorder)
                transcript = transcriber.transcribe(audio_path)
            if not transcript:
                raise SpeechError("Ich habe nichts verstanden.")
            gated = activation.ingest(transcript, bypass_wake=args.text is not None)
            if gated.announcement:
                print(gated.announcement, flush=True)
                speaker.speak(gated.announcement, language=args.language)
            if gated.command is None:
                if args.once and activation.state.value != "awake":
                    break
                continue
            print(f"Erkannt: {gated.command}", flush=True)
            result = runtime.handle_transcript(gated.command)
            response = _localized_result(result.status, result.message)
            print(response, flush=True)
            speaker.speak(response, language=args.language)
        except SpeechError as exc:
            print(str(exc), file=sys.stderr, flush=True)
            try:
                speaker.speak(str(exc), language=args.language)
            except SpeechError:
                pass
        except KeyboardInterrupt:
            print("Clausis beendet.", flush=True)
            return 130
        finally:
            if audio_path is not None:
                audio_path.unlink(missing_ok=True)
        if args.once or args.text is not None:
            break
    return 0


def _localized_result(status: str, message: str) -> str:
    if status == "completed":
        return "Aktion ausgeführt."
    if status == "dry_run":
        return "Aktion erkannt. Die Ausführung ist im sicheren Testmodus ausgeschaltet."
    if status == "confirmation_required":
        return "Diese Aktion benötigt eine vertrauenswürdige Bestätigung und wurde nicht ausgeführt."
    if status == "offline_unmatched":
        return message if message else "Diesen Befehl kenne ich offline noch nicht."
    if status == "hermes_response":
        return message
    return message


if __name__ == "__main__":
    raise SystemExit(main())
