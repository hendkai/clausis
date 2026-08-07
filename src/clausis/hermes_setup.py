"""Secret-safe Hermes provider setup shared by GUI, voice and installer code."""

from __future__ import annotations

from dataclasses import dataclass, field
import json
import os
from pathlib import Path
import re
import secrets
import tempfile
from typing import Mapping, Optional
from urllib.parse import urlparse


HERMES_UPSTREAM_VERSION = "0.20.0"
HERMES_UPSTREAM_COMMIT = "0957277f2f468bac22bbfcfa7c43029858c9597e"
GPT_LIVE_MODEL = "gpt-realtime-2.1"

DANGEROUS_TOOLSETS = (
    "terminal",
    "file",
    "skills",
    "browser",
    "cronjob",
    "code_execution",
    "delegation",
    "computer_use",
    "project",
    "homeassistant",
)


@dataclass(frozen=True)
class ProviderOption:
    identifier: str
    label_de: str
    provider: str
    default_model: str
    secret_environment: Optional[str]
    cloud: bool
    base_url: str = ""


PROVIDERS: Mapping[str, ProviderOption] = {
    "offline": ProviderOption(
        "offline", "Später oder nur Offline-Befehle", "auto", "", None, False
    ),
    "nous": ProviderOption(
        "nous",
        "Nous API-Schlüssel (keine Abo-Anmeldung)",
        "nous",
        "z-ai/glm-5.2",
        "NOUS_API_KEY",
        True,
    ),
    "openrouter": ProviderOption(
        "openrouter",
        "OpenRouter",
        "openrouter",
        "anthropic/claude-sonnet-4.6",
        "OPENROUTER_API_KEY",
        True,
        "https://openrouter.ai/api/v1",
    ),
    "anthropic": ProviderOption(
        "anthropic",
        "Anthropic",
        "anthropic",
        "claude-sonnet-4.6",
        "ANTHROPIC_API_KEY",
        True,
    ),
    "zai": ProviderOption(
        "zai",
        "Z.ai oder GLM Coding Plan",
        "zai",
        "glm-5.2",
        "GLM_API_KEY",
        True,
        "https://api.z.ai/api/coding/paas/v4",
    ),
    "custom": ProviderOption(
        "custom",
        "OpenAI-kompatibler Anbieter",
        "custom",
        "",
        "OPENAI_API_KEY",
        True,
    ),
    "local": ProviderOption(
        "local",
        "Lokaler OpenAI-kompatibler Server",
        "custom",
        "local-model",
        None,
        False,
        "http://127.0.0.1:11434/v1",
    ),
}


_MODEL_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:/+-]{0,159}$")


@dataclass(frozen=True)
class HermesSetupPlan:
    provider_id: str = "offline"
    model: str = ""
    base_url: str = ""
    cloud_consent: bool = False
    realtime_enabled: bool = False
    realtime_cloud_consent: bool = False
    safety_identifier: str = field(default_factory=lambda: secrets.token_hex(16))

    @property
    def option(self) -> ProviderOption:
        try:
            return PROVIDERS[self.provider_id]
        except KeyError as exc:
            raise ValueError("Unbekannter Hermes-Anbieter.") from exc

    def validate(self, *, secret: str = "", realtime_secret: str = "") -> None:
        option = self.option
        model = self.model.strip() or option.default_model
        if model and not _MODEL_RE.fullmatch(model):
            raise ValueError("Der Modellname enthält nicht erlaubte Zeichen.")
        if option.cloud and not self.cloud_consent:
            raise ValueError("Ein Cloud-Anbieter benötigt eine ausdrückliche Einwilligung.")
        if option.secret_environment and not secret.strip():
            raise ValueError("Für diesen Anbieter fehlt der API-Schlüssel.")
        if any(character in secret for character in "\r\n\x00"):
            raise ValueError("Der API-Schlüssel enthält nicht erlaubte Steuerzeichen.")
        base_url = self.base_url.strip() or option.base_url
        if option.provider == "custom" and not base_url:
            raise ValueError("Für einen kompatiblen Anbieter wird eine Basis-URL benötigt.")
        if base_url:
            _validate_base_url(base_url, allow_local=not option.cloud)
        if self.realtime_enabled:
            if not self.realtime_cloud_consent:
                raise ValueError(
                    "GPT Live benötigt eine ausdrückliche Einwilligung zur Audio-Übertragung."
                )
            if not realtime_secret.strip():
                raise ValueError("Für GPT Live fehlt der OpenAI API-Schlüssel.")
        if any(character in realtime_secret for character in "\r\n\x00"):
            raise ValueError("Der OpenAI API-Schlüssel enthält nicht erlaubte Steuerzeichen.")
        if not re.fullmatch(r"[0-9a-f]{32}", self.safety_identifier):
            raise ValueError("Die lokale GPT-Live-Kennung ist ungültig.")

    def public_summary(self) -> str:
        option = self.option
        if option.identifier == "offline":
            summary = "Hermes bleibt vorinstalliert. Die Anbieter-Einrichtung wird übersprungen."
        else:
            location = "Cloud" if option.cloud else "diesem Gerät"
            summary = f"Hermes wird für {option.label_de} auf {location} eingerichtet."
        if self.realtime_enabled:
            summary += " GPT Live wird freiwillig für flüssige Online-Sprache aktiviert."
        return summary

    def config_payload(self) -> dict:
        option = self.option
        model = self.model.strip() or option.default_model
        base_url = self.base_url.strip() or option.base_url
        model_config = {"provider": option.provider}
        if model:
            model_config["default"] = model
        if base_url:
            model_config["base_url"] = base_url
        return {
            "model": model_config,
            "agent": {
                "disabled_toolsets": list(DANGEROUS_TOOLSETS),
                "coding_context": "off",
            },
            "auxiliary": {"free_only": True},
            "terminal": {
                "backend": "local",
                "cwd": ".",
                "docker_mount_cwd_to_workspace": False,
                "docker_network": False,
            },
            "clausis": {
                "managed": True,
                "setup_complete": option.identifier != "offline",
                "upstream_version": HERMES_UPSTREAM_VERSION,
                "upstream_commit": HERMES_UPSTREAM_COMMIT,
                "realtime_enabled": self.realtime_enabled,
                "realtime_cloud_consent": self.realtime_cloud_consent,
                "realtime_model": GPT_LIVE_MODEL,
                "safety_identifier": self.safety_identifier,
            },
        }


def _validate_base_url(value: str, *, allow_local: bool) -> None:
    parsed = urlparse(value)
    if parsed.scheme == "https" and parsed.netloc and not parsed.username:
        return
    local_hosts = {"127.0.0.1", "localhost", "::1"}
    if (
        allow_local
        and parsed.scheme == "http"
        and parsed.hostname in local_hosts
        and not parsed.username
    ):
        return
    raise ValueError("Die Anbieter-URL muss HTTPS verwenden; HTTP ist nur lokal erlaubt.")


def configure_hermes(
    home: Path,
    plan: HermesSetupPlan,
    *,
    secret: str = "",
    realtime_secret: str = "",
) -> None:
    """Write one user's Hermes configuration without exposing its secret."""
    plan.validate(secret=secret, realtime_secret=realtime_secret)
    hermes_home = home / ".hermes"
    hermes_home.mkdir(mode=0o700, parents=True, exist_ok=True)
    try:
        hermes_home.chmod(0o700)
    except OSError:
        pass
    _atomic_private_write(
        hermes_home / "config.yaml",
        json.dumps(plan.config_payload(), ensure_ascii=False, indent=2) + "\n",
    )
    option = plan.option
    env_lines = []
    if option.secret_environment:
        env_lines.append(f"{option.secret_environment}={secret.strip()}")
    _atomic_private_write(hermes_home / ".env", "\n".join(env_lines) + ("\n" if env_lines else ""))
    realtime_lines = (
        [f"CLAUSIS_OPENAI_API_KEY={realtime_secret.strip()}"]
        if plan.realtime_enabled
        else []
    )
    _atomic_private_write(
        hermes_home / ".gpt-live.env",
        "\n".join(realtime_lines) + ("\n" if realtime_lines else ""),
    )


def stage_installer_configuration(
    live_home: Path,
    plan: HermesSetupPlan,
    *,
    secret: str = "",
    realtime_secret: str = "",
) -> Path:
    """Stage a private copy that Calamares can move into the target account."""
    stage_home = live_home / ".config" / "clausis-installer" / "target-home"
    configure_hermes(
        stage_home, plan, secret=secret, realtime_secret=realtime_secret
    )
    configure_hermes(
        live_home, plan, secret=secret, realtime_secret=realtime_secret
    )
    marker = stage_home.parent / "ready.json"
    _atomic_private_write(
        marker,
        json.dumps(
            {
                "provider": plan.provider_id,
                "cloud_consent": plan.cloud_consent,
                "realtime_enabled": plan.realtime_enabled,
            }
        )
        + "\n",
    )
    return stage_home


def _atomic_private_write(path: Path, content: str) -> None:
    path.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
    descriptor, temporary = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent)
    try:
        os.fchmod(descriptor, 0o600)
        with os.fdopen(descriptor, "w", encoding="utf-8", closefd=True) as handle:
            handle.write(content)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
        path.chmod(0o600)
    except Exception:
        try:
            os.close(descriptor)
        except OSError:
            pass
        Path(temporary).unlink(missing_ok=True)
        raise
