"""Optional low-latency OpenAI Realtime voice frontend for Clausis.

GPT Live never receives a shell or a capability token.  It can only request
typed actions that are canonicalized locally and submitted to ActionBroker.
"""

from __future__ import annotations

import base64
import binascii
from dataclasses import dataclass
import json
import os
from pathlib import Path
import queue
import re
import tempfile
import threading
import time
from typing import Mapping, Optional
from urllib.parse import quote

from .broker import ActionBroker
from .models import ActionRequest, ActionResult, Origin
from .policy import ACTION_POLICIES


REALTIME_ENDPOINT = "wss://api.openai.com/v1/realtime?model={model}"
MAX_CONFIG_BYTES = 1024 * 1024
MAX_EVENT_BYTES = 4 * 1024 * 1024
MAX_AUDIO_DELTA_BYTES = 1024 * 1024
MODEL_RE = re.compile(r"^gpt-realtime-[A-Za-z0-9.]+$")
SAFETY_ID_RE = re.compile(r"^[0-9a-f]{32}$")
SUPPORTED_ACTIONS = tuple(
    action for action, policy in ACTION_POLICIES.items() if policy.command is not None
)


@dataclass(frozen=True)
class GptLiveConfig:
    model: str
    api_key: str
    safety_identifier: str


def local_stop_path() -> Path:
    """Return the per-user, local-only GPT Live stop marker."""

    runtime_dir = Path(os.environ.get("XDG_RUNTIME_DIR", f"/run/user/{os.getuid()}"))
    return runtime_dir / "clausis-gpt-live.stop"


def request_local_stop() -> None:
    """Request that the running GPT Live session stops without using the network."""

    path = local_stop_path()
    path.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
    descriptor, temporary = tempfile.mkstemp(prefix=".clausis-stop.", dir=path.parent)
    try:
        os.fchmod(descriptor, 0o600)
        with os.fdopen(descriptor, "w", encoding="ascii", closefd=True) as handle:
            handle.write("stop\n")
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
    except Exception:
        try:
            os.close(descriptor)
        except OSError:
            pass
        Path(temporary).unlink(missing_ok=True)
        raise


def load_gpt_live_config(home: Path) -> Optional[GptLiveConfig]:
    config_path = home / ".hermes/config.yaml"
    env_path = home / ".hermes/.gpt-live.env"
    try:
        if config_path.stat().st_size > MAX_CONFIG_BYTES:
            return None
        payload = json.loads(config_path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError):
        return None
    clausis = payload.get("clausis") if isinstance(payload, dict) else None
    if not isinstance(clausis, dict):
        return None
    if clausis.get("managed") is not True or clausis.get("realtime_enabled") is not True:
        return None
    if clausis.get("realtime_cloud_consent") is not True:
        return None
    model = clausis.get("realtime_model")
    safety_identifier = clausis.get("safety_identifier")
    if not isinstance(model, str) or not MODEL_RE.fullmatch(model):
        return None
    if not isinstance(safety_identifier, str) or not SAFETY_ID_RE.fullmatch(
        safety_identifier
    ):
        return None
    try:
        if env_path.stat().st_size > MAX_CONFIG_BYTES:
            return None
        env_text = env_path.read_text(encoding="utf-8")
    except (OSError, UnicodeError):
        return None
    api_key = ""
    for line in env_text.splitlines():
        if line.startswith("CLAUSIS_OPENAI_API_KEY="):
            api_key = line.partition("=")[2].strip()
    if not api_key or len(api_key) > 512 or any(c in api_key for c in "\r\n\x00"):
        return None
    return GptLiveConfig(model, api_key, safety_identifier)


def action_tool_definition() -> dict:
    return {
        "type": "function",
        "name": "clausis_action",
        "description": (
            "Request one typed Clausis system action. Clausis validates it locally. "
            "Risky, privileged, or irreversible actions are not executed without a "
            "separate trusted confirmation. Never claim success before reading the result."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "action": {"type": "string", "enum": list(SUPPORTED_ACTIONS)},
                "target": {"type": "string", "maxLength": 512},
                "arguments": {
                    "type": "object",
                    "properties": {
                        "percent": {"type": "number", "minimum": 0, "maximum": 150}
                    },
                    "additionalProperties": False,
                },
            },
            "required": ["action"],
            "additionalProperties": False,
        },
    }


def parse_gpt_live_action(raw_arguments: str) -> ActionRequest:
    if len(raw_arguments.encode("utf-8")) > 32 * 1024:
        raise ValueError("GPT Live action is too large")
    try:
        payload = json.loads(raw_arguments)
    except json.JSONDecodeError as exc:
        raise ValueError("GPT Live action is invalid JSON") from exc
    if not isinstance(payload, dict) or set(payload) - {"action", "target", "arguments"}:
        raise ValueError("GPT Live action has unknown fields")
    action = payload.get("action")
    target = payload.get("target", "")
    arguments = payload.get("arguments", {})
    if action not in SUPPORTED_ACTIONS:
        raise ValueError("GPT Live action is not supported")
    if not isinstance(target, str) or not isinstance(arguments, dict):
        raise ValueError("GPT Live action fields have invalid types")
    if set(arguments) - {"percent"}:
        raise ValueError("GPT Live action arguments have unknown fields")
    if action != "audio.volume.set" and arguments:
        raise ValueError("this GPT Live action accepts no arguments")
    policy = ACTION_POLICIES[action]
    return ActionRequest(
        action=action,
        target=target,
        arguments=arguments,
        origin=Origin.GPT_LIVE,
        risk=policy.minimum_risk,
        reversible=policy.reversible,
    )


def session_update_event(config: GptLiveConfig, language: str) -> dict:
    return {
        "type": "session.update",
        "session": {
            "type": "realtime",
            "model": config.model,
            "output_modalities": ["audio"],
            "instructions": (
                "Du bist GPT Live in Clausis, einem barrierefreien Debian-System. "
                f"Antworte knapp und freundlich auf {language}. Sage klar, dass du KI bist. "
                "Nutze clausis_action nur nach einem eindeutigen Nutzerwunsch. "
                "Systemaktionen werden ausschließlich von Clausis geprüft und ausgeführt. "
                "Behaupte nie, eine Aktion sei ausgeführt, bevor das Werkzeug Erfolg meldet. "
                "Bei Bestätigungspflicht erkläre, dass die Aktion nicht ausgeführt wurde."
            ),
            "audio": {
                "input": {
                    "format": {"type": "audio/pcm", "rate": 24000},
                    "turn_detection": {"type": "semantic_vad"},
                },
                "output": {
                    "format": {"type": "audio/pcm"},
                    "voice": "cedar",
                },
            },
            "tools": [
                action_tool_definition(),
                {
                    "type": "function",
                    "name": "stop_clausis_live",
                    "description": "Stop GPT Live when the user clearly says Stopp Hermes or Stopp Clausis.",
                    "parameters": {"type": "object", "properties": {}, "additionalProperties": False},
                },
            ],
            "tool_choice": "auto",
        },
    }


class GptLiveSession:
    def __init__(self, config: GptLiveConfig, broker: ActionBroker, *, language: str = "de"):
        self.config = config
        self.broker = broker
        self.language = language
        self._stopped = threading.Event()
        self._transport_failed = threading.Event()
        self._audio_input: queue.Queue[bytes] = queue.Queue(maxsize=80)

    def stop(self) -> None:
        self._stopped.set()

    def _local_stop_requested(self) -> bool:
        path = local_stop_path()
        try:
            if not path.is_file():
                return False
            recent = time.time() - path.stat().st_mtime <= 120
            path.unlink(missing_ok=True)
            if recent:
                self.stop()
                return True
            return False
        except OSError:
            return False

    def _tool_result(self, item: Mapping[str, object]) -> tuple[str, ActionResult | dict]:
        name = item.get("name")
        call_id = item.get("call_id")
        if not isinstance(call_id, str) or len(call_id) > 256:
            raise ValueError("invalid GPT Live call id")
        if name == "stop_clausis_live":
            self.stop()
            return call_id, {"status": "stopped", "message": "GPT Live wurde beendet."}
        if name != "clausis_action":
            raise ValueError("unknown GPT Live tool")
        arguments = item.get("arguments")
        if not isinstance(arguments, str):
            raise ValueError("missing GPT Live arguments")
        return call_id, self.broker.submit(parse_gpt_live_action(arguments))

    def _send_tool_output(self, ws, item: Mapping[str, object]) -> None:
        try:
            call_id, result = self._tool_result(item)
            output = result.to_dict() if isinstance(result, ActionResult) else result
        except ValueError as exc:
            call_id = item.get("call_id") if isinstance(item.get("call_id"), str) else "invalid"
            output = {"status": "denied", "message": str(exc)}
        ws.send(
            json.dumps(
                {
                    "type": "conversation.item.create",
                    "item": {
                        "type": "function_call_output",
                        "call_id": call_id,
                        "output": json.dumps(output, ensure_ascii=False),
                    },
                }
            )
        )
        if not self._stopped.is_set():
            ws.send(json.dumps({"type": "response.create"}))

    def run(self) -> int:
        try:
            import sounddevice as sd
            import websocket
        except ImportError as exc:
            raise RuntimeError("GPT-Live-Audiopakete fehlen") from exc

        url = REALTIME_ENDPOINT.format(model=quote(self.config.model, safe=""))
        headers = [
            "Authorization: Bearer " + self.config.api_key,
            "OpenAI-Safety-Identifier: " + self.config.safety_identifier,
        ]
        try:
            ws = websocket.create_connection(url, header=headers, timeout=15)
            ws.settimeout(1)
            ws.send(json.dumps(session_update_event(self.config, self.language)))
        except (OSError, websocket.WebSocketException) as exc:
            raise RuntimeError("GPT Live konnte keine sichere Verbindung aufbauen") from exc

        def capture(indata, _frames, _time, status) -> None:
            if status or self._stopped.is_set():
                return
            try:
                self._audio_input.put_nowait(bytes(indata))
            except queue.Full:
                pass

        def send_audio() -> None:
            while not self._stopped.is_set():
                try:
                    chunk = self._audio_input.get(timeout=0.2)
                except queue.Empty:
                    continue
                try:
                    ws.send(
                        json.dumps(
                            {
                                "type": "input_audio_buffer.append",
                                "audio": base64.b64encode(chunk).decode("ascii"),
                            }
                        )
                    )
                except (OSError, websocket.WebSocketException):
                    self._transport_failed.set()
                    self._stopped.set()
                    return

        sender = threading.Thread(target=send_audio, daemon=True)
        sender.start()
        try:
            with sd.RawInputStream(
                samplerate=24000,
                channels=1,
                dtype="int16",
                blocksize=2400,
                callback=capture,
            ), sd.RawOutputStream(
                samplerate=24000,
                channels=1,
                dtype="int16",
                blocksize=0,
            ) as output:
                while not self._stopped.is_set():
                    if self._local_stop_requested():
                        break
                    try:
                        raw = ws.recv()
                    except websocket.WebSocketTimeoutException:
                        continue
                    if raw == "":
                        raise RuntimeError("GPT Live hat die Verbindung beendet")
                    if not isinstance(raw, str) or len(raw.encode("utf-8")) > MAX_EVENT_BYTES:
                        continue
                    try:
                        event = json.loads(raw)
                    except json.JSONDecodeError:
                        continue
                    if not isinstance(event, dict):
                        continue
                    event_type = event.get("type")
                    if event_type == "response.output_audio.delta":
                        encoded = event.get("delta")
                        if not isinstance(encoded, str) or len(encoded) > MAX_AUDIO_DELTA_BYTES * 2:
                            continue
                        try:
                            audio = base64.b64decode(encoded, validate=True)
                        except (binascii.Error, ValueError):
                            continue
                        if len(audio) <= MAX_AUDIO_DELTA_BYTES:
                            output.write(audio)
                    elif event_type == "response.output_item.done":
                        item = event.get("item")
                        if isinstance(item, dict) and item.get("type") == "function_call":
                            self._send_tool_output(ws, item)
                    elif event_type == "error":
                        raise RuntimeError("GPT Live meldet einen Verbindungsfehler")
        except (OSError, websocket.WebSocketException, sd.PortAudioError) as exc:
            raise RuntimeError("GPT Live wurde durch einen Audio- oder Verbindungsfehler beendet") from exc
        finally:
            self._stopped.set()
            try:
                ws.close()
            except Exception:
                pass
            sender.join(timeout=2)
        if self._transport_failed.is_set():
            raise RuntimeError("GPT Live hat die Audioverbindung verloren")
        return 0
