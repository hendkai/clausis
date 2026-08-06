import unittest

from voiceos.models import Risk
from voiceos.router import OfflineRouter


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

    def test_unknown_returns_none(self):
        self.assertIsNone(self.router.route("Schreibe mir ein Gedicht"))

    def test_twenty_or_more_commands_exist(self):
        self.assertGreaterEqual(len(self.router._commands), 20)


if __name__ == "__main__":
    unittest.main()

