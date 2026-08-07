from __future__ import annotations

import os
from pathlib import Path
import stat
import tempfile
import unittest

from clausis.finalize_install import copy_configuration, target_account


class FinalizeInstallTests(unittest.TestCase):
    def test_staged_config_is_copied_to_target_user_privately(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory)
            root = base / "target"
            (root / "etc").mkdir(parents=True)
            (root / "home/anna").mkdir(parents=True)
            (root / "etc/passwd").write_text(
                f"anna:x:{os.getuid()}:{os.getgid()}:Anna:/home/anna:/bin/bash\n",
                encoding="utf-8",
            )
            source = base / "source"
            source.mkdir()
            (source / "config.yaml").write_text('{"model": {"provider": "zai"}}\n')
            (source / ".env").write_text("GLM_API_KEY=private\n")
            (source / ".gpt-live.env").write_text(
                "CLAUSIS_OPENAI_API_KEY=live-private\n"
            )

            self.assertTrue(copy_configuration(root, "anna", source))
            env = root / "home/anna/.hermes/.env"
            self.assertEqual(env.read_text(), "GLM_API_KEY=private\n")
            self.assertEqual(stat.S_IMODE(env.stat().st_mode), 0o600)
            live_env = root / "home/anna/.hermes/.gpt-live.env"
            self.assertEqual(
                live_env.read_text(), "CLAUSIS_OPENAI_API_KEY=live-private\n"
            )
            self.assertEqual(stat.S_IMODE(live_env.stat().st_mode), 0o600)

    def test_root_and_username_are_validated(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "etc").mkdir()
            (root / "etc/passwd").write_text("", encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "username"):
                target_account(root, "../../root")

    def test_staged_symlink_is_rejected_without_touching_its_target(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory)
            root = base / "target"
            (root / "etc").mkdir(parents=True)
            (root / "home/anna").mkdir(parents=True)
            (root / "etc/passwd").write_text(
                f"anna:x:{os.getuid()}:{os.getgid()}:Anna:/home/anna:/bin/bash\n",
                encoding="utf-8",
            )
            protected = base / "protected"
            protected.write_text("must-stay-private\n", encoding="utf-8")
            source = base / "source"
            source.mkdir()
            (source / "config.yaml").symlink_to(protected)

            with self.assertRaisesRegex(ValueError, "regular file"):
                copy_configuration(root, "anna", source)
            self.assertEqual(protected.read_text(), "must-stay-private\n")
            self.assertFalse((root / "home/anna/.hermes/config.yaml").exists())

    def test_existing_target_symlink_is_replaced_not_followed(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory)
            root = base / "target"
            target_home = root / "home/anna"
            (root / "etc").mkdir(parents=True)
            target_home.mkdir(parents=True)
            (root / "etc/passwd").write_text(
                f"anna:x:{os.getuid()}:{os.getgid()}:Anna:/home/anna:/bin/bash\n",
                encoding="utf-8",
            )
            protected = base / "protected"
            protected.write_text("unchanged\n", encoding="utf-8")
            destination = target_home / ".hermes"
            destination.mkdir()
            (destination / "config.yaml").symlink_to(protected)
            source = base / "source"
            source.mkdir()
            (source / "config.yaml").write_text("safe: true\n", encoding="utf-8")

            self.assertTrue(copy_configuration(root, "anna", source))
            self.assertEqual(protected.read_text(), "unchanged\n")
            target = destination / "config.yaml"
            self.assertFalse(target.is_symlink())
            self.assertEqual(target.read_text(), "safe: true\n")


if __name__ == "__main__":
    unittest.main()
