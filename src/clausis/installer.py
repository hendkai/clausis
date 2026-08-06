"""Voice installer plan validation and secret-safe summaries."""

from __future__ import annotations

from dataclasses import dataclass, field
import re
from typing import Dict, Mapping, Optional


LOCALES = {"de_DE.UTF-8", "en_GB.UTF-8", "en_US.UTF-8"}
TIMEZONE_RE = re.compile(r"^[A-Za-z_+-]+(?:/[A-Za-z0-9_+.-]+)+$")
USERNAME_RE = re.compile(r"^[a-z_][a-z0-9_-]{0,31}$")
PROVIDERS = {"none", "nous", "openai-compatible", "local"}


@dataclass(frozen=True)
class InstallerPlan:
    locale: str
    timezone: str
    username: str
    disk_id: str
    erase_disk: bool
    encryption: bool = True
    tpm_enroll: bool = True
    hermes_provider: str = "none"
    cloud_consent: bool = False
    recovery_key_exported: bool = False
    metadata: Mapping[str, str] = field(default_factory=dict)

    def validate(self) -> None:
        if self.locale not in LOCALES:
            raise ValueError("unsupported locale")
        if not TIMEZONE_RE.fullmatch(self.timezone):
            raise ValueError("invalid timezone")
        if not USERNAME_RE.fullmatch(self.username):
            raise ValueError("invalid username")
        if not self.disk_id or any(character in self.disk_id for character in "\x00\n\r"):
            raise ValueError("invalid disk identifier")
        if self.hermes_provider not in PROVIDERS:
            raise ValueError("unsupported Hermes provider")
        if self.hermes_provider in {"nous", "openai-compatible"} and not self.cloud_consent:
            raise ValueError("cloud provider requires explicit consent")
        if self.encryption and not self.recovery_key_exported:
            raise ValueError("encrypted installation requires an exported recovery key")
        forbidden = {"password", "passphrase", "pin", "api_key", "token", "voiceprint"}
        if any(key.casefold() in forbidden for key in self.metadata):
            raise ValueError("installer plan must not contain secrets or biometric templates")

    def spoken_summary(self) -> str:
        self.validate()
        destructive = "wird vollständig gelöscht" if self.erase_disk else "wird ohne vollständiges Löschen verwendet"
        cloud = "mit freigegebenem Cloud-Zugang" if self.cloud_consent else "ohne Cloud-Zugang"
        encryption = "verschlüsselt" if self.encryption else "nicht verschlüsselt"
        return (
            f"Installation auf {self.disk_id}. Der Datenträger {destructive}. "
            f"Das System wird {encryption}. Benutzer {self.username}. "
            f"Sprache {self.locale}. Zeitzone {self.timezone}. Hermes {cloud}."
        )

