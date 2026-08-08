"""Maintainer-signature verification for the online Hermes release.

The point of these tests is the absence of an "unsigned is fine" path: an
unconfigured trust anchor, a missing signature, a lightweight tag and an
unknown key must all end the update and leave the bundled release active.
"""

from __future__ import annotations

import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from clausis.hermes_update import (
    HermesUpdateError,
    StableRelease,
    install_latest_stable,
)
from clausis.signing import (
    PLACEHOLDER_MARKER,
    PUBLIC_KEY_HEADER,
    TRUST_STORE,
    SignatureError,
    trust_store_is_configured,
    verify_release,
)


GOOD_KEY = "A" * 40
OTHER_KEY = "B" * 40


def _completed(returncode=0, stdout="", stderr=""):
    return subprocess.CompletedProcess(["fake"], returncode, stdout, stderr)


class FakeGpg:
    """Answer the gpg and git calls the verifier makes."""

    def __init__(self, *, keys=(GOOD_KEY,), signed_by=GOOD_KEY, signs="tag"):
        self.keys = list(keys)
        self.signed_by = signed_by
        self.signs = signs
        self.calls = []
        self.homes = []

    def __call__(self, command, env=None):
        self.calls.append(list(command))
        if env and "GNUPGHOME" in env:
            self.homes.append(env["GNUPGHOME"])
        if command[0] == "gpg" and "--import" in command:
            return _completed(0)
        if command[0] == "gpg" and "--fingerprint" in command:
            rows = "".join(f"fpr:::::::::{key}:\n" for key in self.keys)
            return _completed(0, rows)
        if command[0] == "git":
            wants_tag = "verify-tag" in command
            kind = "tag" if wants_tag else "commit"
            if self.signs != kind or self.signed_by is None:
                return _completed(1, "", "error: no signature found\n")
            return _completed(0, "", f"[GNUPG:] VALIDSIG {self.signed_by} 2026-01-01\n")
        return _completed(0)


class TrustStoreTests(unittest.TestCase):
    def _store(self, directory, content):
        path = Path(directory) / "keys.asc"
        path.write_text(content, encoding="utf-8")
        return path

    def test_placeholder_is_not_a_trust_anchor(self):
        with tempfile.TemporaryDirectory() as directory:
            store = self._store(directory, f"text\n{PLACEHOLDER_MARKER}\n{PUBLIC_KEY_HEADER}\n")
            self.assertFalse(trust_store_is_configured(store))

    def test_real_key_block_is_accepted(self):
        with tempfile.TemporaryDirectory() as directory:
            store = self._store(directory, f"{PUBLIC_KEY_HEADER}\nmQ...\n")
            self.assertTrue(trust_store_is_configured(store))

    def test_missing_file_is_not_configured(self):
        self.assertFalse(trust_store_is_configured(Path("/nonexistent-clausis-trust.asc")))

    def test_shipped_store_is_still_the_placeholder(self):
        # The repository must not pretend to have a trust anchor it never had.
        shipped = Path(__file__).resolve().parents[1] / "packaging/trust/hermes-maintainers.asc"
        self.assertTrue(shipped.is_file())
        self.assertFalse(trust_store_is_configured(shipped))
        self.assertTrue(str(TRUST_STORE).startswith("/usr/share/clausis/trust/"))


class VerifyReleaseTests(unittest.TestCase):
    def _store(self, directory):
        path = Path(directory) / "keys.asc"
        path.write_text(f"{PUBLIC_KEY_HEADER}\nmQ...\n", encoding="utf-8")
        return path

    def test_signed_tag_from_a_trusted_key_is_accepted(self):
        gpg = FakeGpg()
        with tempfile.TemporaryDirectory() as directory:
            result = verify_release(
                Path(directory), "v1.2.3", trust_store=self._store(directory), runner=gpg
            )
        self.assertEqual(result.kind, "tag")
        self.assertEqual(result.fingerprint, GOOD_KEY)

    def test_signed_commit_is_accepted_when_the_tag_is_lightweight(self):
        gpg = FakeGpg(signs="commit")
        with tempfile.TemporaryDirectory() as directory:
            result = verify_release(
                Path(directory), "v1.2.3", trust_store=self._store(directory), runner=gpg
            )
        self.assertEqual(result.kind, "commit")

    def test_unsigned_release_is_rejected(self):
        gpg = FakeGpg(signed_by=None)
        with tempfile.TemporaryDirectory() as directory:
            with self.assertRaisesRegex(SignatureError, "no verifiable"):
                verify_release(
                    Path(directory), "v1.2.3", trust_store=self._store(directory), runner=gpg
                )

    def test_signature_from_an_untrusted_key_is_rejected(self):
        gpg = FakeGpg(keys=(GOOD_KEY,), signed_by=OTHER_KEY)
        with tempfile.TemporaryDirectory() as directory:
            with self.assertRaisesRegex(SignatureError, "does not trust"):
                verify_release(
                    Path(directory), "v1.2.3", trust_store=self._store(directory), runner=gpg
                )

    def test_unconfigured_trust_anchor_refuses_every_release(self):
        with tempfile.TemporaryDirectory() as directory:
            store = Path(directory) / "keys.asc"
            store.write_text(PLACEHOLDER_MARKER, encoding="utf-8")
            with self.assertRaisesRegex(SignatureError, "trust anchor"):
                verify_release(Path(directory), "v1.2.3", trust_store=store, runner=FakeGpg())

    def test_empty_trust_store_is_rejected(self):
        gpg = FakeGpg(keys=())
        with tempfile.TemporaryDirectory() as directory:
            with self.assertRaisesRegex(SignatureError, "no usable key"):
                verify_release(
                    Path(directory), "v1.2.3", trust_store=self._store(directory), runner=gpg
                )

    def test_verification_uses_an_isolated_keyring(self):
        gpg = FakeGpg()
        with tempfile.TemporaryDirectory() as directory:
            verify_release(
                Path(directory), "v1.2.3", trust_store=self._store(directory), runner=gpg
            )
        # Never the caller's ~/.gnupg, and torn down with the temporary home.
        self.assertTrue(gpg.homes)
        for home in gpg.homes:
            self.assertIn("clausis-trust-", home)
            self.assertFalse(Path(home).exists())

    def test_no_call_ever_uses_a_shell(self):
        gpg = FakeGpg()
        with tempfile.TemporaryDirectory() as directory:
            verify_release(
                Path(directory), "v1.2.3", trust_store=self._store(directory), runner=gpg
            )
        for call in gpg.calls:
            self.assertIn(call[0], {"gpg", "git"})
            self.assertNotIn(";", " ".join(call))


class UpdaterFailsClosedTests(unittest.TestCase):
    def test_default_updater_refuses_without_a_trust_anchor(self):
        # install_latest_stable defaults to the real verifier; on a machine
        # without the maintainer keys it must not install anything.
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "etc").mkdir()
            (root / "etc/os-release").write_text("ID=debian\n", encoding="utf-8")
            (root / "opt").mkdir()
            release = StableRelease("v1.2.3", "2026-01-01T00:00:00Z")
            with patch(
                "clausis.hermes_update.latest_stable_release", return_value=release
            ), self.assertRaises(HermesUpdateError):
                install_latest_stable(root)
            self.assertFalse((root / "usr/local/bin/hermes").exists())


if __name__ == "__main__":
    unittest.main()
