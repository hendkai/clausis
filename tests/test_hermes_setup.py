from __future__ import annotations

import json
from pathlib import Path
import stat
import tempfile
import unittest

from clausis.hermes_setup import (
    DANGEROUS_TOOLSETS,
    HERMES_UPSTREAM_COMMIT,
    HermesSetupPlan,
    configure_hermes,
    stage_installer_configuration,
)
from clausis.setup_app import (
    affirmative_from_speech,
    provider_from_speech,
    save_setup_configuration,
)


class HermesSetupTests(unittest.TestCase):
    def test_cloud_provider_requires_consent_and_secret(self) -> None:
        plan = HermesSetupPlan(provider_id="zai", model="glm-5.2")
        with self.assertRaisesRegex(ValueError, "Einwilligung"):
            plan.validate(secret="secret")
        with self.assertRaisesRegex(ValueError, "API-Schlüssel"):
            HermesSetupPlan(
                provider_id="zai", model="glm-5.2", cloud_consent=True
            ).validate()

    def test_custom_http_endpoint_is_rejected_but_local_http_is_allowed(self) -> None:
        with self.assertRaisesRegex(ValueError, "HTTPS"):
            HermesSetupPlan(
                provider_id="custom",
                model="example/model",
                base_url="http://provider.example/v1",
                cloud_consent=True,
            ).validate(secret="secret")
        HermesSetupPlan(provider_id="local").validate()

    def test_secret_is_only_written_to_private_env_file(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            home = Path(directory)
            plan = HermesSetupPlan(
                provider_id="zai", model="glm-5.2", cloud_consent=True
            )
            configure_hermes(home, plan, secret="top-secret")

            config = (home / ".hermes/config.yaml").read_text(encoding="utf-8")
            env = home / ".hermes/.env"
            self.assertNotIn("top-secret", config)
            self.assertEqual(env.read_text(encoding="utf-8"), "GLM_API_KEY=top-secret\n")
            self.assertEqual(stat.S_IMODE(env.stat().st_mode), 0o600)
            payload = json.loads(config)
            self.assertEqual(payload["model"]["provider"], "zai")
            self.assertEqual(
                payload["clausis"]["upstream_commit"], HERMES_UPSTREAM_COMMIT
            )
            self.assertTrue(set(DANGEROUS_TOOLSETS).issubset(payload["agent"]["disabled_toolsets"]))

    def test_installer_staging_contains_no_secret_in_marker(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            home = Path(directory)
            plan = HermesSetupPlan(
                provider_id="openrouter", cloud_consent=True
            )
            stage = stage_installer_configuration(home, plan, secret="private-value")
            marker = (stage.parent / "ready.json").read_text(encoding="utf-8")
            self.assertNotIn("private-value", marker)
            self.assertIn("OPENROUTER_API_KEY=private-value", (stage / ".hermes/.env").read_text())

    def test_installed_setup_does_not_duplicate_secret_in_installer_stage(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            home = Path(directory)
            plan = HermesSetupPlan(provider_id="zai", cloud_consent=True)
            save_setup_configuration(
                home,
                plan,
                secret="private-value",
                stage_for_installer=False,
            )
            self.assertIn(
                "GLM_API_KEY=private-value",
                (home / ".hermes/.env").read_text(encoding="utf-8"),
            )
            self.assertFalse((home / ".config/clausis-installer").exists())

    def test_installer_setup_stages_only_a_derived_confirmation_pin(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            home = Path(directory)
            save_setup_configuration(
                home,
                HermesSetupPlan(),
                confirmation_pin="123456",
                stage_for_installer=True,
            )
            verifier_path = (
                home / ".config/clausis-installer/system/voice-pin.json"
            )
            text = verifier_path.read_text(encoding="utf-8")
            self.assertNotIn("123456", text)
            self.assertEqual(stat.S_IMODE(verifier_path.stat().st_mode), 0o600)

    def test_german_voice_provider_aliases(self) -> None:
        self.assertEqual(provider_from_speech("Ich möchte GLM nutzen"), "zai")
        self.assertEqual(provider_from_speech("später nur offline"), "offline")
        self.assertEqual(provider_from_speech("Claude von Anthropic"), "anthropic")

    def test_voice_cloud_consent_requires_clear_yes_or_no(self) -> None:
        self.assertTrue(affirmative_from_speech("Ja, ich stimme zu"))
        self.assertFalse(affirmative_from_speech("Nein"))
        with self.assertRaisesRegex(ValueError, "eindeutig"):
            affirmative_from_speech("vielleicht")


if __name__ == "__main__":
    unittest.main()
