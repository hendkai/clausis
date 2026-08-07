from __future__ import annotations

import json
from pathlib import Path
import stat
import tempfile
import unittest
from unittest.mock import patch

from clausis.confirmation import PinVerifier
from clausis.enrollment import install_staged_voice_pin, stage_voice_pin


class EnrollmentTests(unittest.TestCase):
    def test_staging_persists_only_a_private_verifier(self):
        with tempfile.TemporaryDirectory() as directory:
            path = stage_voice_pin(Path(directory), "123456")
            text = path.read_text(encoding="utf-8")
            self.assertNotIn("123456", text)
            self.assertEqual(stat.S_IMODE(path.stat().st_mode), 0o600)
            verifier = PinVerifier.from_export(json.loads(text))
            self.assertTrue(verifier.verify("123456"))

    def test_calamares_install_validates_and_copies_verifier(self):
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory)
            source = stage_voice_pin(base / "live", "123456")
            root = base / "target"
            (root / "etc").mkdir(parents=True)
            (root / "etc/passwd").write_text("root:x:0:0:root:/root:/bin/bash\n")
            with patch("clausis.enrollment.os.chown"):
                self.assertTrue(install_staged_voice_pin(root, source))
            installed = root / "etc/clausis/voice-pin.json"
            self.assertEqual(stat.S_IMODE(installed.stat().st_mode), 0o600)
            self.assertTrue(
                PinVerifier.from_export(json.loads(installed.read_text())).verify(
                    "123456"
                )
            )

    def test_symlinked_staging_file_is_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory)
            real = stage_voice_pin(base / "live", "123456")
            link = base / "pin-link"
            link.symlink_to(real)
            root = base / "target"
            (root / "etc").mkdir(parents=True)
            (root / "etc/passwd").write_text("root:x:0:0:root:/root:/bin/bash\n")
            with self.assertRaisesRegex(ValueError, "unsafe"):
                install_staged_voice_pin(root, link)

    def test_modified_work_factor_is_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory)
            source = stage_voice_pin(base / "live", "123456")
            payload = json.loads(source.read_text())
            payload["iterations"] = "1"
            source.write_text(json.dumps(payload), encoding="utf-8")
            root = base / "target"
            (root / "etc").mkdir(parents=True)
            (root / "etc/passwd").write_text("root:x:0:0:root:/root:/bin/bash\n")
            with self.assertRaisesRegex(ValueError, "work factor"):
                install_staged_voice_pin(root, source)


if __name__ == "__main__":
    unittest.main()
