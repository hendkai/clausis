import unittest

from clausis.models import Risk
from clausis.router import OfflineRouter


class RouterTests(unittest.TestCase):
    def setUp(self):
        self.router = OfflineRouter()

    def test_german_launch(self):
        request = self.router.route("Öffne firefox")
        self.assertEqual((request.action, request.target), ("app.launch", "firefox"))

    def test_english_volume(self):
        request = self.router.route("volume 42 percent")
        self.assertEqual(request.arguments["percent"], 42)

    def test_reboot_is_critical(self):
        request = self.router.route("Rechner neu starten")
        self.assertEqual(request.risk, Risk.CRITICAL)
        self.assertFalse(request.reversible)

    def test_stop_is_local(self):
        self.assertEqual(self.router.route("Stopp Hermes").action, "voice.stop")
        self.assertEqual(self.router.route("Stopp Clausis").action, "voice.stop")

    def test_orientation_commands_are_local_and_semantic(self):
        self.assertEqual(
            self.router.route("Wo bin ich").action, "desktop.context.describe"
        )
        self.assertEqual(
            self.router.route("Was kann ich hier tun").action,
            "desktop.controls.list",
        )
        numbered = self.router.route("Nummer drei")
        self.assertEqual(
            (numbered.action, numbered.target, numbered.risk),
            ("desktop.control.activate", "3", Risk.MEDIUM),
        )

    def test_correction_commands_do_not_need_hermes(self):
        self.assertEqual(self.router.route("Zurück").action, "desktop.navigate.back")
        self.assertEqual(self.router.route("Wiederholen").action, "voice.repeat")
        self.assertEqual(self.router.route("Abbrechen").action, "voice.cancel")
        self.assertEqual(self.router.route("Korrigieren").action, "voice.correct")

    def test_unknown_returns_none(self):
        self.assertIsNone(self.router.route("Schreibe mir ein Gedicht"))

    def test_twenty_or_more_commands_exist(self):
        self.assertGreaterEqual(len(self.router._commands), 20)

    def test_speech_control_commands_route_locally(self):
        # Speech output control must stay deterministic and offline: the
        # phrases are exact fixed vectors, so they can never fall through
        # to Hermes.
        cases = [
            ("sprich schneller", "speech.rate.faster"),
            ("sprich langsamer", "speech.rate.slower"),
            ("sprechgeschwindigkeit normal", "speech.rate.normal"),
            ("antworte auf deutsch", "speech.language.german"),
            ("antworte auf englisch", "speech.language.english"),
            ("speak faster", "speech.rate.faster"),
            ("speak slower", "speech.rate.slower"),
            ("speak german", "speech.language.german"),
            ("speak english", "speech.language.english"),
        ]
        for phrase, action in cases:
            with self.subTest(phrase=phrase):
                request = self.router.route(phrase)
                self.assertIsNotNone(request)
                self.assertEqual(request.action, action)
                self.assertEqual(request.origin.value, "local_voice")

    def test_speech_actions_are_fixed_vectors_without_target(self):
        from clausis.policy import ACTION_POLICIES

        for action in (
            "speech.rate.faster",
            "speech.rate.slower",
            "speech.rate.normal",
            "speech.language.german",
            "speech.language.english",
        ):
            with self.subTest(action=action):
                policy = ACTION_POLICIES[action]
                self.assertIsNotNone(policy.command)
                self.assertEqual(policy.command[0], "spd-say")
                # No caller-supplied value ever reaches the vector.
                with self.assertRaises(ValueError):
                    ACTION_POLICIES[action].validator and ACTION_POLICIES[action].validator(
                        type("R", (), {"target": "400"})()
                    )


if __name__ == "__main__":
    unittest.main()
