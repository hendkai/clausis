import unittest

from clausis.confirmation import ConfirmationResponse
from clausis.speech import SpeechError
from clausis.trusted_audio import DirectAudioConfirmation, normalize_spoken_pin


class TrustedAudioTests(unittest.TestCase):
    def test_numeric_pin_is_normalized_locally(self):
        self.assertEqual(normalize_spoken_pin("12 34 56."), "123456")

    def test_german_spoken_digits_are_normalized(self):
        self.assertEqual(
            normalize_spoken_pin("eins zwei drei vier fünf sechs"), "123456"
        )

    def test_english_spoken_digits_are_normalized(self):
        self.assertEqual(
            normalize_spoken_pin("one two three four five six"), "123456"
        )

    def test_non_digit_words_fail_closed(self):
        with self.assertRaises(SpeechError):
            normalize_spoken_pin("bitte genehmigen")

    def test_direct_frontend_deletes_both_recordings_and_never_speaks_pin(self):
        class Recorder:
            paths = []

            def record(self, destination):
                self.paths.append(destination)
                destination.write_bytes(b"audio")
                return destination

        class Transcriber:
            values = iter(("anker birke mond", "eins zwei drei vier fünf sechs"))

            def transcribe(self, _path):
                return next(self.values)

        class Speaker:
            messages = []

            def speak(self, text, *, language):
                self.messages.append((text, language))

        recorder = Recorder()
        speaker = Speaker()
        frontend = DirectAudioConfirmation(
            language="de",
            recorder=recorder,
            transcriber=Transcriber(),
            speaker=speaker,
        )
        response = frontend.collect(
            "Sichere Zusammenfassung: anker birke mond", "anker birke mond"
        )
        self.assertEqual(
            response, ConfirmationResponse("anker birke mond", "123456")
        )
        self.assertTrue(all(not path.exists() for path in recorder.paths))
        spoken = " ".join(text for text, _ in speaker.messages)
        self.assertNotIn("123456", spoken)


if __name__ == "__main__":
    unittest.main()
