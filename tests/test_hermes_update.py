from __future__ import annotations

import io
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from clausis.signing import Verification
from clausis.hermes_update import (
    HermesUpdateError,
    StableRelease,
    install_latest_stable,
    latest_stable_release,
    record_fallback,
)


def _accepting_verifier(repository, tag):
    return Verification(reference=tag, kind="tag", fingerprint="A" * 40)


class FakeResponse(io.BytesIO):
    def __enter__(self):
        return self

    def __exit__(self, _type, _value, _traceback):
        self.close()


class HermesUpdateTests(unittest.TestCase):
    def target_root(self, base: Path) -> Path:
        root = base / "target"
        (root / "etc").mkdir(parents=True)
        (root / "etc/os-release").write_text("ID=debian\n", encoding="utf-8")
        (root / "opt").mkdir()
        return root

    def test_latest_official_stable_release_is_accepted(self) -> None:
        payload = {
            "tag_name": "v2026.8.3",
            "published_at": "2026-08-03T16:57:52Z",
            "draft": False,
            "prerelease": False,
        }
        opener = lambda _request, timeout: FakeResponse(json.dumps(payload).encode())

        self.assertEqual(
            latest_stable_release(opener),
            StableRelease("v2026.8.3", "2026-08-03T16:57:52Z"),
        )

    def test_prerelease_and_unexpected_tag_are_rejected(self) -> None:
        for payload in (
            {
                "tag_name": "v2026.8.3",
                "published_at": "now",
                "draft": False,
                "prerelease": True,
            },
            {
                "tag_name": "main; touch /tmp/unsafe",
                "published_at": "now",
                "draft": False,
                "prerelease": False,
            },
        ):
            opener = lambda _request, timeout, value=payload: FakeResponse(
                json.dumps(value).encode()
            )
            with self.assertRaises(HermesUpdateError):
                latest_stable_release(opener)

    def test_fallback_record_contains_no_exception_details(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            record_fallback(root, "online-update-unavailable")
            payload = json.loads(
                (root / "var/lib/clausis/hermes-install.json").read_text()
            )
            self.assertEqual(payload["status"], "bundled-fallback")
            self.assertEqual(payload["reason"], "online-update-unavailable")

    def test_success_switches_launcher_only_after_frozen_sync(self) -> None:
        release = StableRelease("v2026.8.3", "2026-08-03T16:57:52Z")
        calls: list[list[str]] = []
        with tempfile.TemporaryDirectory() as directory:
            root = self.target_root(Path(directory))

            def fake_run(command: list[str], *, timeout: int = 120) -> str:
                calls.append(command)
                if command[0] == "chroot":
                    executable = Path(command[1]) / "opt/hermes-agent-releases/v2026.8.3/venv/bin/hermes"
                    executable.parent.mkdir(parents=True)
                    executable.write_text("#!/bin/sh\n", encoding="utf-8")
                    executable.chmod(0o755)
                elif "checkout" in command:
                    repository = Path(command[2])
                    (repository / "uv.lock").write_text("version = 1\n", encoding="utf-8")
                    (repository / "LICENSE").write_text("MIT\n", encoding="utf-8")
                elif "rev-parse" in command:
                    return "3c27eb6234bf91b8ceee9e9071591b31e9b148cb"
                return ""

            with patch(
                "clausis.hermes_update.latest_stable_release", return_value=release
            ), patch("clausis.hermes_update._run", side_effect=fake_run):
                result = install_latest_stable(root, verifier=_accepting_verifier)

            launcher = root / "usr/local/bin/hermes"
            self.assertTrue(launcher.is_symlink())
            self.assertEqual(
                launcher.readlink(),
                Path("/opt/hermes-agent-releases/v2026.8.3/venv/bin/hermes"),
            )
            self.assertTrue(result.changed)
            sync = next(command for command in calls if command[0] == "chroot")
            self.assertIn("--frozen", sync)
            self.assertNotIn("sh", sync)
            record = json.loads((root / "var/lib/clausis/hermes-install.json").read_text())
            self.assertEqual(record["release"], "v2026.8.3")
            self.assertEqual(record["status"], "updated")
            self.assertEqual(record["signature"]["fingerprint"], "A" * 40)
            fetch = next(c for c in calls if "fetch" in c)
            # Without a local refs/tags entry there would be no object to verify.
            self.assertIn("refs/tags/v2026.8.3:refs/tags/v2026.8.3", fetch)

    def test_failed_update_keeps_existing_bundled_launcher(self) -> None:
        release = StableRelease("v2026.8.3", "2026-08-03T16:57:52Z")
        with tempfile.TemporaryDirectory() as directory:
            root = self.target_root(Path(directory))
            launcher = root / "usr/local/bin/hermes"
            launcher.parent.mkdir(parents=True)
            launcher.symlink_to("/opt/hermes-agent/venv/bin/hermes")
            with patch(
                "clausis.hermes_update.latest_stable_release", return_value=release
            ), patch(
                "clausis.hermes_update._run",
                side_effect=HermesUpdateError("network failed"),
            ):
                with self.assertRaises(HermesUpdateError):
                    install_latest_stable(root)
            self.assertEqual(launcher.readlink(), Path("/opt/hermes-agent/venv/bin/hermes"))

if __name__ == "__main__":
    unittest.main()
