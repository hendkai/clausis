from __future__ import annotations

import json
import os
from pathlib import Path
import tempfile
import unittest

from clausis.broker import ActionBroker, SafeExecutor
from clausis.capabilities import CapabilityAuthority
from clausis.executors import SessionExecutor, adapted_actions
from clausis.gpt_live import (
    SUPPORTED_ACTIONS,
    GptLiveConfig,
    GptLiveSession,
    action_tool_definition,
    load_gpt_live_config,
    local_stop_path,
    parse_gpt_live_action,
    request_local_stop,
    session_update_event,
)
from clausis.policy import ACTION_POLICIES
from clausis.hermes_setup import HermesSetupPlan, configure_hermes
from clausis.models import Origin, Risk


class GptLiveTests(unittest.TestCase):
    def test_realtime_requires_separate_consent_and_key(self) -> None:
        plan = HermesSetupPlan(provider_id="offline", realtime_enabled=True)
        with self.assertRaisesRegex(ValueError, "Einwilligung"):
            plan.validate(realtime_secret="sk-test-value")
        plan = HermesSetupPlan(
            provider_id="offline",
            realtime_enabled=True,
            realtime_cloud_consent=True,
        )
        with self.assertRaisesRegex(ValueError, "OpenAI API-Schlüssel"):
            plan.validate()

    def test_key_is_private_and_never_placed_in_public_config(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            home = Path(directory)
            plan = HermesSetupPlan(
                provider_id="offline",
                realtime_enabled=True,
                realtime_cloud_consent=True,
            )
            configure_hermes(home, plan, realtime_secret="sk-private-test")
            config_text = (home / ".hermes/config.yaml").read_text()
            self.assertNotIn("sk-private-test", config_text)
            self.assertIn(
                "CLAUSIS_OPENAI_API_KEY=sk-private-test",
                (home / ".hermes/.gpt-live.env").read_text(),
            )
            loaded = load_gpt_live_config(home)
            self.assertIsNotNone(loaded)
            self.assertEqual(loaded.api_key, "sk-private-test")

    def test_model_session_never_receives_key_or_general_computer_tool(self) -> None:
        config = GptLiveConfig("gpt-realtime-2.1", "sk-secret", "a" * 32)
        payload = session_update_event(config, "de")
        encoded = json.dumps(payload)
        self.assertNotIn("sk-secret", encoded)
        self.assertNotIn("shell", encoded)
        self.assertNotIn("computer_use", encoded)
        self.assertEqual(payload["session"]["audio"]["input"]["format"]["rate"], 24000)
        action_enum = payload["session"]["tools"][0]["parameters"]["properties"]["action"]["enum"]
        self.assertIn("desktop.context.describe", action_enum)
        self.assertIn("desktop.controls.list", action_enum)

    def test_hermes_openai_key_and_live_key_do_not_overwrite_each_other(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            home = Path(directory)
            plan = HermesSetupPlan(
                provider_id="custom",
                model="custom-model",
                base_url="https://example.invalid/v1",
                cloud_consent=True,
                realtime_enabled=True,
                realtime_cloud_consent=True,
            )
            configure_hermes(
                home,
                plan,
                secret="sk-hermes",
                realtime_secret="sk-live",
            )
            env_text = (home / ".hermes/.env").read_text(encoding="utf-8")
            live_env_text = (home / ".hermes/.gpt-live.env").read_text(
                encoding="utf-8"
            )
            self.assertIn("OPENAI_API_KEY=sk-hermes\n", env_text)
            self.assertNotIn("sk-live", env_text)
            self.assertIn("CLAUSIS_OPENAI_API_KEY=sk-live\n", live_env_text)
            self.assertEqual(load_gpt_live_config(home).api_key, "sk-live")

    def test_action_is_canonicalized_locally(self) -> None:
        request = parse_gpt_live_action(
            json.dumps({"action": "network.wifi.disable"})
        )
        self.assertEqual(request.origin, Origin.GPT_LIVE)
        self.assertEqual(request.risk, Risk.MEDIUM)
        self.assertTrue(request.reversible)

    def test_unknown_fields_and_shell_are_denied(self) -> None:
        with self.assertRaises(ValueError):
            parse_gpt_live_action(
                json.dumps({"action": "audio.volume.up", "command": "rm -rf /"})
            )
        with self.assertRaises(ValueError):
            parse_gpt_live_action(json.dumps({"action": "shell.execute"}))

    def test_broker_executes_low_risk_but_blocks_risky_live_action(self) -> None:
        broker = ActionBroker(
            CapabilityAuthority.generate(), SafeExecutor(dry_run=True)
        )
        low = broker.submit(parse_gpt_live_action('{"action":"audio.volume.up"}'))
        risky = broker.submit(
            parse_gpt_live_action('{"action":"network.wifi.disable"}')
        )
        self.assertEqual(low.status, "dry_run")
        self.assertEqual(risky.status, "confirmation_required")

    def test_every_adapted_action_is_offered_to_the_model(self) -> None:
        # The offered set must follow adapter coverage, not the presence of an
        # argument vector: the privileged actions keep theirs on the root side
        # and were silently dropped when that vector moved.
        self.assertEqual(set(SUPPORTED_ACTIONS), set(adapted_actions()))
        self.assertEqual(set(SUPPORTED_ACTIONS), set(ACTION_POLICIES))
        for action in ("system.reboot", "system.poweroff", "system.status", "app.close"):
            self.assertIn(action, SUPPORTED_ACTIONS)
        self.assertEqual(
            set(action_tool_definition()["parameters"]["properties"]["action"]["enum"]),
            set(SUPPORTED_ACTIONS),
        )

    def test_privileged_action_from_the_model_is_never_executed_directly(self) -> None:
        broker = ActionBroker(
            CapabilityAuthority.generate(),
            SessionExecutor(SafeExecutor(dry_run=False)),
        )
        for action in ("system.reboot", "system.poweroff", "package.install", "app.close"):
            with self.subTest(action=action):
                payload = {"action": action}
                if action == "package.install":
                    payload["target"] = "nano"
                if action == "app.close":
                    payload["target"] = "firefox"
                result = broker.submit(parse_gpt_live_action(json.dumps(payload)))
                self.assertEqual(result.status, "confirmation_required")

    def test_model_cannot_understate_the_risk_of_a_new_action(self) -> None:
        request = parse_gpt_live_action('{"action":"system.reboot"}')
        self.assertEqual(request.risk, Risk.CRITICAL)
        self.assertFalse(request.reversible)
        self.assertEqual(request.origin, Origin.GPT_LIVE)

    def test_read_only_query_answers_the_model_without_confirmation(self) -> None:
        broker = ActionBroker(
            CapabilityAuthority.generate(),
            SessionExecutor(SafeExecutor(dry_run=False)),
        )
        result = broker.submit(parse_gpt_live_action('{"action":"system.status"}'))
        self.assertEqual(result.status, "completed")

    def test_model_still_cannot_pass_a_command_or_extra_argument(self) -> None:
        for payload in (
            {"action": "package.install", "target": "nano", "arguments": {"percent": 5}},
            {"action": "system.reboot", "command": "rm -rf /"},
            {"action": "file.search", "arguments": {"depth": 99}},
        ):
            with self.subTest(payload=payload):
                with self.assertRaises(ValueError):
                    parse_gpt_live_action(json.dumps(payload))

    def test_stop_tool_never_reaches_broker(self) -> None:
        broker = ActionBroker(
            CapabilityAuthority.generate(), SafeExecutor(dry_run=True)
        )
        session = GptLiveSession(
            GptLiveConfig("gpt-realtime-2.1", "sk-secret", "b" * 32), broker
        )
        call_id, result = session._tool_result(
            {"name": "stop_clausis_live", "call_id": "call-1", "arguments": "{}"}
        )
        self.assertEqual(call_id, "call-1")
        self.assertEqual(result["status"], "stopped")

    def test_local_stop_uses_private_per_user_marker(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            old_runtime = os.environ.get("XDG_RUNTIME_DIR")
            os.environ["XDG_RUNTIME_DIR"] = directory
            try:
                request_local_stop()
                marker = local_stop_path()
                self.assertEqual(marker.read_text(encoding="ascii"), "stop\n")
                self.assertEqual(marker.stat().st_mode & 0o777, 0o600)
                broker = ActionBroker(
                    CapabilityAuthority.generate(), SafeExecutor(dry_run=True)
                )
                session = GptLiveSession(
                    GptLiveConfig("gpt-realtime-2.1", "sk-secret", "c" * 32), broker
                )
                self.assertTrue(session._local_stop_requested())
                self.assertFalse(marker.exists())
            finally:
                if old_runtime is None:
                    os.environ.pop("XDG_RUNTIME_DIR", None)
                else:
                    os.environ["XDG_RUNTIME_DIR"] = old_runtime


if __name__ == "__main__":
    unittest.main()
