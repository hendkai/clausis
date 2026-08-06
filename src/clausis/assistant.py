"""Interactive, offline-first Clausis assistant for the live system."""

from __future__ import annotations

import argparse
import os
from pathlib import Path
import sys
from typing import Sequence

from .broker import ActionBroker, SafeExecutor
from .capabilities import CapabilityAuthority
from .router import OfflineRouter
from .runtime import RuntimeState, VoiceRuntime
from .speech import LocalWhisper, MicrophoneRecorder, SpeechError, SystemSpeaker, record_temporary


AI_NOTICE_DE = (
    "Hinweis: Clausis verwendet für Spracherkennung und optionale Antworten ein KI-System. "
    "Offline-Kernbefehle werden lokal verarbeitet. Drücken Sie jederzeit Steuerung C zum Beenden."
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
    args = parser.parse_args(list(argv) or None)

    speaker = SystemSpeaker()
    print(AI_NOTICE_DE, flush=True)
    try:
        speaker.speak(AI_NOTICE_DE, language=args.language)
    except SpeechError as exc:
        print(f"Sprachausgabe eingeschränkt: {exc}", file=sys.stderr)

    runtime = VoiceRuntime(
        OfflineRouter(),
        ActionBroker(CapabilityAuthority.generate(), SafeExecutor(dry_run=not args.execute)),
    )
    recorder = MicrophoneRecorder()
    transcriber = LocalWhisper(_model_path(args.model), language=args.language)
    pending_text = args.text

    while runtime.state is not RuntimeState.STOPPED:
        audio_path = None
        try:
            if pending_text is not None:
                transcript = pending_text
                pending_text = None
            else:
                prompt = "Ich höre zu."
                print(prompt, flush=True)
                speaker.speak(prompt, language=args.language)
                audio_path = record_temporary(recorder)
                transcript = transcriber.transcribe(audio_path)
            if not transcript:
                raise SpeechError("Ich habe nichts verstanden.")
            print(f"Erkannt: {transcript}", flush=True)
            result = runtime.handle_transcript(transcript)
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
        return "Diesen Befehl kenne ich offline noch nicht."
    return message


if __name__ == "__main__":
    raise SystemExit(main())
