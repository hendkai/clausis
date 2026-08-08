"""Pre-rendered boot prompts and the initramfs wiring.

The disk-unlock prompt is the one moment where none of Clausis is running yet,
so it cannot be synthesised on demand and it cannot be recovered from. These
tests cover the two properties that matter: the files exist before the boot,
and nothing here is allowed to fail a boot or a package configuration.
"""

from __future__ import annotations

import subprocess
import tempfile
import unittest
import wave
from pathlib import Path

from clausis.boot_audio import (
    PROMPT_DIR,
    PROMPT_EARCONS,
    PROMPTS,
    render_prompts,
)


ROOT = Path(__file__).resolve().parents[1]


def _completed(returncode=0):
    return subprocess.CompletedProcess(["fake"], returncode, "", "")


class PromptTextTests(unittest.TestCase):
    def test_every_prompt_has_an_earcon(self):
        self.assertEqual(set(PROMPTS), set(PROMPT_EARCONS))

    def test_the_unlock_prompt_names_the_keyboard(self):
        # Voice cannot unlock the disk, so the prompt must not imply it can.
        self.assertIn("Tastatur", PROMPTS["unlock"])
        self.assertIn("nicht vorgelesen", PROMPTS["unlock"])

    def test_the_retry_prompt_mentions_the_recovery_key(self):
        self.assertIn("Wiederherstellungsschlüssel", PROMPTS["unlock-retry"])

    def test_no_prompt_would_read_a_secret_aloud(self):
        for name, text in PROMPTS.items():
            with self.subTest(name=name):
                lowered = text.casefold()
                self.assertNotIn("ihr passwort lautet", lowered)
                self.assertNotIn("pin lautet", lowered)


class RenderTests(unittest.TestCase):
    def _fake_synth(self, calls, *, returncode=0, write=True):
        def runner(command):
            calls.append(list(command))
            if write and returncode == 0:
                Path(command[-2]).write_bytes(b"RIFF----WAVEfmt ")
            return _completed(returncode)

        return runner

    def test_speech_is_rendered_for_every_prompt(self):
        calls = []
        with tempfile.TemporaryDirectory() as directory:
            result = render_prompts(
                Path(directory),
                which=lambda name: "/usr/bin/espeak-ng" if name == "espeak-ng" else None,
                runner=self._fake_synth(calls),
            )
            self.assertEqual(set(result.spoken), set(PROMPTS))
            self.assertEqual(result.synthesiser, "espeak-ng")
            for name in PROMPTS:
                self.assertTrue((Path(directory) / f"{name}.wav").is_file())

    def test_earcons_are_written_even_without_a_synthesiser(self):
        with tempfile.TemporaryDirectory() as directory:
            result = render_prompts(Path(directory), which=lambda name: None)
            self.assertFalse(result.has_speech)
            self.assertIsNone(result.synthesiser)
            self.assertEqual(set(result.earcons), set(PROMPT_EARCONS))
            for name in PROMPT_EARCONS:
                path = Path(directory) / f"{name}-tone.wav"
                with wave.open(str(path), "rb") as handle:
                    self.assertEqual(handle.getnchannels(), 1)
                    self.assertGreater(handle.getnframes(), 0)

    def test_a_failing_synthesiser_does_not_raise(self):
        calls = []
        with tempfile.TemporaryDirectory() as directory:
            result = render_prompts(
                Path(directory),
                which=lambda name: "/usr/bin/espeak-ng",
                runner=self._fake_synth(calls, returncode=1, write=False),
            )
        # Package configuration must not fail because speech is unavailable.
        self.assertFalse(result.has_speech)
        self.assertTrue(result.earcons)

    def test_a_crashing_synthesiser_does_not_raise(self):
        def exploding(command):
            raise OSError("espeak-ng vanished")

        with tempfile.TemporaryDirectory() as directory:
            result = render_prompts(
                Path(directory),
                which=lambda name: "/usr/bin/espeak-ng",
                runner=exploding,
            )
        self.assertFalse(result.has_speech)

    def test_synthesiser_is_invoked_without_a_shell(self):
        calls = []
        with tempfile.TemporaryDirectory() as directory:
            render_prompts(
                Path(directory),
                which=lambda name: "/usr/bin/espeak-ng",
                runner=self._fake_synth(calls),
            )
        for call in calls:
            self.assertEqual(call[0], "espeak-ng")
            self.assertIn("-w", call)


class InitramfsPackagingTests(unittest.TestCase):
    def setUp(self):
        self.hook = ROOT / "packaging/initramfs/hooks/clausis-audio"
        self.script = ROOT / "packaging/initramfs/scripts/init-premount/clausis-audio"

    def test_hook_and_script_exist_and_are_executable(self):
        for path in (self.hook, self.script):
            with self.subTest(path=path.name):
                self.assertTrue(path.is_file())
                self.assertTrue(path.stat().st_mode & 0o111)

    def test_hook_copies_the_player_prompts_and_sound_modules(self):
        source = self.hook.read_text(encoding="utf-8")
        self.assertIn("copy_exec /usr/bin/aplay", source)
        self.assertIn("copy_modules_dir kernel/sound", source)
        self.assertIn(str(PROMPT_DIR), source)

    def test_boot_script_runs_before_the_disk_is_unlocked(self):
        # init-premount runs ahead of local-top, where cryptroot lives.
        self.assertEqual(self.script.parent.name, "init-premount")

    def test_boot_script_never_fails_the_boot(self):
        source = self.script.read_text(encoding="utf-8")
        # Every playback path swallows its own failure; a missing card must not
        # leave a machine stuck before the passphrase prompt.
        self.assertIn("|| true", source)
        self.assertIn("exit 0", source)

    def test_boot_script_prefers_speech_and_falls_back_to_a_tone(self):
        source = self.script.read_text(encoding="utf-8")
        self.assertIn("$name.wav", source)
        self.assertIn("$name-tone.wav", source)

    def test_debian_package_installs_both(self):
        install = (ROOT / "debian/clausis-core.install").read_text(encoding="utf-8")
        self.assertIn(
            "packaging/initramfs/hooks/clausis-audio usr/share/initramfs-tools/hooks/",
            install,
        )
        self.assertIn(
            "packaging/initramfs/scripts/init-premount/clausis-audio "
            "usr/share/initramfs-tools/scripts/init-premount/",
            install,
        )

    def test_postinst_renders_prompts_and_refreshes_the_initramfs(self):
        postinst = (ROOT / "debian/clausis-core.postinst").read_text(encoding="utf-8")
        self.assertIn("render_prompts", postinst)
        self.assertIn("update-initramfs -u", postinst)

    def test_player_is_a_declared_dependency(self):
        control = (ROOT / "debian/control").read_text(encoding="utf-8")
        self.assertIn("alsa-utils", control)


class LoginScreenTests(unittest.TestCase):
    def test_orca_speaks_at_the_login_screen(self):
        # Nothing of Clausis runs at the greeter, so Orca is the only voice
        # available there.
        dconf = (
            ROOT
            / "packaging/live-build/config/includes.chroot/etc/dconf/db/gdm.d/00-clausis"
        ).read_text(encoding="utf-8")
        self.assertIn("[org/gnome/desktop/a11y/applications]", dconf)
        self.assertIn("screen-reader-enabled=true", dconf)


if __name__ == "__main__":
    unittest.main()
