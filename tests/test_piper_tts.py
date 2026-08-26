from __future__ import annotations

import unittest

from pathlib import Path

from clausis import piper_tts


ROOT = Path(__file__).resolve().parents[1]
HOOK = (
    ROOT
    / "packaging/live-build/config/hooks/normal/021-clausis-piper.hook.chroot"
)
PACKAGES = (
    ROOT / "packaging/live-build/config/package-lists/clausis.list.chroot"
)


class PiperArtifactTests(unittest.TestCase):
    def test_artifacts_are_checksum_pinned_and_official(self) -> None:
        arts = piper_tts.artifacts()
        self.assertEqual(len(arts), 3)
        for art in arts:
            self.assertEqual(len(art.sha256), 64)
            self.assertTrue(art.url.startswith("https://"))
            self.assertNotEqual(art.license_ref, "")
        urls = [a.url for a in arts]
        self.assertTrue(any("github.com/rhasspy/piper/releases" in u for u in urls))
        self.assertTrue(
            all("huggingface.co/rhasspy/piper-voices" in u for u in urls[1:])
        )

    def test_model_license_is_documented_as_cc0(self) -> None:
        self.assertEqual(piper_tts.PIPER_LICENSE, "MIT")
        self.assertEqual(piper_tts.MODEL_LICENSE, "CC0")


class PiperModuleConfigTests(unittest.TestCase):
    def test_config_targets_generic_module_with_piper_command(self) -> None:
        conf = piper_tts.module_config()
        # Registered through sd_generic (no native piper module exists).
        self.assertIn("GenericExecuteSynth", conf)
        self.assertNotIn("GenericExecuteString", conf)
        self.assertIn("/opt/piper/piper --model", conf)
        self.assertIn("--output-raw", conf)
        # Text reaches piper through stdin only ($DATA), never as arguments.
        self.assertIn("printf %s '$DATA'", conf)
        # Playback through the speechd audio backend player, not a second
        # audio stack of our own.
        self.assertIn("| $PLAY_COMMAND", conf)

    def test_config_declares_model_dependency_before_addvoice(self) -> None:
        conf = piper_tts.module_config()
        self.assertIn(
            'VoiceFileDependency "%s/de_DE-thorsten-medium.onnx"'
            % piper_tts.MODEL_DIR.as_posix(),
            conf,
        )
        self.assertIn(
            'AddVoice "de" "MALE1" "de_DE-thorsten-medium"', conf
        )
        # dotconf is sequential: the dependency must be declared first so a
        # missing model drops the voice instead of silently speaking anyway.
        self.assertLess(
            conf.index("VoiceFileDependency"),
            conf.index("AddVoice"),
        )

    def test_config_dependencies_cover_piper_and_playback(self) -> None:
        conf = piper_tts.module_config()
        self.assertIn('GenericCmdDependency "piper"', conf)
        self.assertIn('GenericCmdDependency "paplay"', conf)

    def test_rate_mapping_keeps_zero_at_model_default(self) -> None:
        # speechd $RATE = rate * multiply/100 + add  →  length-scale
        # 1 - 0.01 * rate:  0 → 1.0 (model default), +50 → 0.5, -50 → 1.5.
        # The ends of the SSIP range are clamped in the command line.
        for speechd_rate, expected in ((0, 1.0), (50, 0.5), (-50, 1.5)):
            length = (
                speechd_rate * (piper_tts.RATE_MULTIPLY / 100)
                + piper_tts.RATE_ADD
            )
            self.assertAlmostEqual(length, expected)
        self.assertEqual(piper_tts.RATE_FORCE_INTEGER, 0)

    def test_config_mentions_licenses_for_provenance(self) -> None:
        conf = piper_tts.module_config()
        self.assertIn("MIT", conf)
        self.assertIn("CC0", conf)


class SpeechdDefaultsTests(unittest.TestCase):
    def test_german_prefers_piper_without_global_default_module(self) -> None:
        lines = piper_tts.speechd_conf_lines()
        self.assertIn('LanguageDefaultModule "de" "piper-generic"', lines)
        # No global DefaultModule: speechd 0.12 does not fall back from a
        # dead DefaultModule for connected clients; the language default plus
        # server-side fallback keeps espeak-ng honest.
        self.assertEqual(piper_tts.speechd_conf_removals(), ["DefaultModule piper-generic"])

    def test_fallback_module_is_espeak_ng(self) -> None:
        self.assertEqual(piper_tts.FALLBACK_MODULE, "espeak-ng")
        self.assertNotEqual(piper_tts.MODULE_NAME, piper_tts.FALLBACK_MODULE)


class BuildHookTests(unittest.TestCase):
    def test_hook_fetches_pinned_artifacts_with_checksums(self) -> None:
        hook = HOOK.read_text(encoding="utf-8")
        for art in piper_tts.artifacts():
            self.assertIn(art.sha256, hook)
        self.assertIn(piper_tts.PIPER_TARBALL_SHA256, hook)
        self.assertIn("verify_sha256", hook)
        # Fail the build when the checksum does not match.
        self.assertIn('fail "checksum mismatch', hook)

    def test_hook_generates_module_config_from_pinned_source(self) -> None:
        hook = HOOK.read_text(encoding="utf-8")
        self.assertIn("piper-generic.conf", hook)
        self.assertIn("clausis.piper_tts", hook)
        # speechd defaults are set in the hook, matching piper_tts.
        self.assertIn('LanguageDefaultModule "de" "piper-generic"', hook)

    def test_hook_pins_are_identical_to_module_constants(self) -> None:
        hook = HOOK.read_text(encoding="utf-8")
        self.assertIn(f"piper_release='{piper_tts.PIPER_RELEASE}'", hook)
        self.assertIn(f"piper_tarball_sha256='{piper_tts.PIPER_TARBALL_SHA256}'", hook)
        self.assertIn(f"model_sha256='{piper_tts.MODEL_SHA256}'", hook)
        self.assertIn(
            f"model_config_sha256='{piper_tts.MODEL_CONFIG_SHA256}'", hook
        )
        self.assertIn(f"model_name='{piper_tts.MODEL_NAME}'", hook)

    def test_hook_requires_paplay(self) -> None:
        hook = HOOK.read_text(encoding="utf-8")
        self.assertIn("paplay missing", hook)


class PackageListTests(unittest.TestCase):
    def test_espeak_fallback_and_paplay_are_explicit_packages(self) -> None:
        packages = PACKAGES.read_text(encoding="utf-8").splitlines()
        # speech-dispatcher-espeak-ng is only a Recommends of
        # speech-dispatcher; the espeak fallback must be explicit.
        self.assertIn("speech-dispatcher-espeak-ng", packages)
        # paplay ($PLAY_COMMAND under PipeWire/PulseAudio) for sd_generic.
        self.assertIn("pulseaudio-utils", packages)
        self.assertIn("speech-dispatcher", packages)
        self.assertIn("espeak-ng", packages)


class LicenseDocumentationTests(unittest.TestCase):
    def test_piper_license_doc_exists_and_names_both_licenses(self) -> None:
        doc = (ROOT / "docs/licenses/piper.md").read_text(encoding="utf-8")
        self.assertIn("MIT", doc)
        self.assertIn("CC0", doc)
        self.assertIn("Thorsten-Voice", doc)
        self.assertIn(piper_tts.PIPER_RELEASE, doc)
        self.assertIn(piper_tts.MODEL_SHA256, doc)
        self.assertIn(piper_tts.PIPER_TARBALL_SHA256, doc)


class GeneratorEntryPointTests(unittest.TestCase):
    def test_main_writes_module_config(self) -> None:
        import contextlib
        import io

        buffer = io.StringIO()
        with contextlib.redirect_stdout(buffer):
            code = piper_tts.main(["--write-module-config"])
        self.assertEqual(code, 0)
        self.assertIn("GenericExecuteSynth", buffer.getvalue())


if __name__ == "__main__":
    unittest.main()
