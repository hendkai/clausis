from __future__ import annotations

import json
import os
from pathlib import Path
import subprocess
import sys
import unittest


ROOT = Path(__file__).resolve().parents[1]
BRIDGE = ROOT / "scripts/calamares_clausis.py"


class InstallerBridgeTests(unittest.TestCase):
    def run_bridge(self, payload: dict) -> subprocess.CompletedProcess[str]:
        environment = os.environ.copy()
        environment["PYTHONPATH"] = str(ROOT / "src")
        return subprocess.run(
            [sys.executable, str(BRIDGE), "--fixture-no-device-check"],
            input=json.dumps(payload),
            text=True,
            capture_output=True,
            env=environment,
            check=False,
        )

    def valid_payload(self) -> dict:
        return {
            "locale": "de_DE.UTF-8",
            "timezone": "Europe/Berlin",
            "username": "anna",
            "disk_id": "/dev/disk/by-id/ata-VBOX_HARDDISK_VB123456",
            "disk_bytes": 64 * 1024**3,
            "disk_model": "VBOX HARDDISK",
            "disk_serial_suffix": "123456",
            "erase_disk": True,
            "encryption": True,
            "recovery_key_exported": True,
        }

    def test_valid_plan_requires_protected_confirmation(self):
        result = self.run_bridge(self.valid_payload())
        self.assertEqual(result.returncode, 0, result.stderr)
        response = json.loads(result.stdout)
        self.assertEqual(response["status"], "confirmation_required")
        self.assertIn("VBOX HARDDISK", response["summary"])
        self.assertIn("dauerhaft gelöscht", response["summary"])

    def test_secret_or_non_whole_disk_plan_is_denied(self):
        payload = self.valid_payload()
        payload["metadata"] = {"passphrase": "must-not-enter-plan"}
        result = self.run_bridge(payload)
        self.assertEqual(result.returncode, 2)
        self.assertEqual(json.loads(result.stdout)["status"], "denied")

        payload = self.valid_payload()
        payload["erase_disk"] = False
        result = self.run_bridge(payload)
        self.assertEqual(result.returncode, 2)
        self.assertEqual(json.loads(result.stdout)["status"], "denied")


if __name__ == "__main__":
    unittest.main()
