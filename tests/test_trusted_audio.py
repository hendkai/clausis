import unittest

from clausis.confirmation import ConfirmationResponse
from clausis.speech import SpeechError
from clausis.trusted_audio import (
    ConfirmationAborted,
    DirectAudioConfirmation,
    DirectInstallConfirmation,
    format_recovery_key_for_speech,
    is_spoken_abort,
    normalize_spoken_pin,
    normalize_spoken_recovery_key,
)


class TrustedAudioTests(unittest.TestCase):
    def test_recovery_key_is_spoken_as_individual_digits_in_twelve_groups(self):
        key = "0123-4567-8901-2345-6789-0123-4567-8901-2345-6789-0123-4567"
        spoken = format_recovery_key_for_speech(key)
        self.assertEqual(len(spoken.split("; ")), 12)
        self.assertEqual(spoken.split("; ")[0], "0 1 2 3")
        self.assertEqual(spoken.split("; ")[-1], "4 5 6 7")
        self.assertNotIn("0123", spoken)

    def test_invalid_recovery_key_cannot_be_formatted_for_speech(self):
        with self.assertRaises(ValueError):
            format_recovery_key_for_speech("1234-5678")

    def test_installer_recovery_recorder_allows_full_key_readback(self):
        frontend = DirectInstallConfirmation(
            transcriber=object(), speaker=object()
        )
        self.assertEqual(frontend.recorder.options.max_seconds, 90.0)
        self.assertEqual(frontend.recorder.options.silence_seconds, 1.8)

        regular = DirectAudioConfirmation(transcriber=object(), speaker=object())
        self.assertEqual(regular.recorder.options.max_seconds, 25.0)

    def test_only_complete_explicit_abort_phrases_are_recognized(self):
        for phrase in (
            "Abbrechen!", "Abbruch", "cancel", "Stopp Clausis", "Stop Hermes."
        ):
            self.assertTrue(is_spoken_abort(phrase), phrase)
        for phrase in ("stopp", "bitte abbrechen", "Abbrechen der Datei", "weiter"):
            self.assertFalse(is_spoken_abort(phrase), phrase)

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

    def test_spoken_recovery_key_is_normalized(self):
        spoken = " ".join(f"{value:04d}" for value in range(1, 13))
        self.assertEqual(
            normalize_spoken_recovery_key(spoken),
            "0001-0002-0003-0004-0005-0006-0007-0008-0009-0010-0011-0012",
        )

    def test_invalid_spoken_recovery_key_fails_closed(self):
        with self.assertRaises(SpeechError):
            normalize_spoken_recovery_key("0001 0002 zu kurz")

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
        self.assertIn("Abbrechen oder Stopp Clausis", spoken)

    def test_direct_frontend_aborts_locally_before_pin(self):
        class Recorder:
            paths = []

            def record(self, destination):
                self.paths.append(destination)
                destination.write_bytes(b"audio")
                return destination

        class Transcriber:
            def transcribe(self, _path):
                return "Stopp Clausis"

        class Speaker:
            messages = []

            def speak(self, text, *, language):
                self.messages.append((text, language))

        recorder = Recorder()
        speaker = Speaker()
        frontend = DirectAudioConfirmation(
            recorder=recorder, transcriber=Transcriber(), speaker=speaker
        )
        with self.assertRaises(ConfirmationAborted):
            frontend.collect("Sichere Zusammenfassung", "anker mond")
        self.assertEqual(len(recorder.paths), 1)
        self.assertTrue(all(not path.exists() for path in recorder.paths))
        self.assertIn("lokal abgebrochen", " ".join(x for x, _ in speaker.messages))

    def test_installer_phrase_stays_in_direct_audio_path_and_recording_is_deleted(self):
        class Challenge:
            confirmed = []

            def issue(self):
                return "anker mond 123"

            def confirm(self, response):
                self.confirmed.append(response)
                return response == "anker mond 123"

        class Recorder:
            paths = []

            def record(self, destination):
                self.paths.append(destination)
                destination.write_bytes(b"audio")
                return destination

        class Transcriber:
            values = iter((
                "0001 0002 0003 0004 0005 0006 0007 0008 0009 0010 0011 0012",
                "anker mond 123",
            ))

            def transcribe(self, _path):
                return next(self.values)

        class Speaker:
            messages = []

            def speak(self, text, *, language):
                self.messages.append((text, language))

        challenge = Challenge()
        recorder = Recorder()
        speaker = Speaker()
        frontend = DirectInstallConfirmation(
            recorder=recorder,
            transcriber=Transcriber(),
            speaker=speaker,
            challenge=challenge,
        )
        self.assertTrue(
            frontend.authorize(
                "Datenträgerwarnung",
                "0001-0002-0003-0004-0005-0006-0007-0008-0009-0010-0011-0012",
            )
        )
        self.assertEqual(challenge.confirmed, ["anker mond 123"])
        self.assertEqual(len(recorder.paths), 2)
        self.assertTrue(all(not path.exists() for path in recorder.paths))
        spoken = " ".join(text for text, _ in speaker.messages)
        self.assertIn("Datenträgerwarnung", spoken)
        self.assertIn("anker mond 123", spoken)
        self.assertIn("0 0 0 1; 0 0 0 2", spoken)
        self.assertEqual(
            sum("0 0 0 1; 0 0 0 2" in text for text, _ in speaker.messages),
            2,
        )
        self.assertIn("Abbrechen oder Stopp Clausis", spoken)

    def test_installer_mismatch_fails_closed_without_second_attempt(self):
        class Challenge:
            calls = 0

            def issue(self):
                return "anker mond 123"

            def confirm(self, _response):
                self.calls += 1
                return False

        class Recorder:
            def record(self, destination):
                destination.write_bytes(b"audio")
                return destination

        class Transcriber:
            values = iter((
                "0001 0002 0003 0004 0005 0006 0007 0008 0009 0010 0011 0012",
                "ja",
            ))

            def transcribe(self, _path):
                return next(self.values)

        class Speaker:
            messages = []

            def speak(self, text, *, language):
                self.messages.append((text, language))

        challenge = Challenge()
        frontend = DirectInstallConfirmation(
            recorder=Recorder(),
            transcriber=Transcriber(),
            speaker=Speaker(),
            challenge=challenge,
        )
        self.assertFalse(
            frontend.authorize(
                "Datenträgerwarnung",
                "0001-0002-0003-0004-0005-0006-0007-0008-0009-0010-0011-0012",
            )
        )
        self.assertEqual(challenge.calls, 1)

    def test_installer_recovery_key_mismatch_aborts_before_phrase(self):
        class Challenge:
            def issue(self):
                raise AssertionError("challenge must not be issued")

        class Recorder:
            def record(self, destination):
                destination.write_bytes(b"audio")
                return destination

        class Transcriber:
            def transcribe(self, _path):
                return "9999 " * 12

        class Speaker:
            messages = []

            def speak(self, text, *, language):
                self.messages.append((text, language))

        speaker = Speaker()
        frontend = DirectInstallConfirmation(
            recorder=Recorder(), transcriber=Transcriber(), speaker=speaker,
            challenge=Challenge(),
        )
        self.assertFalse(frontend.authorize(
            "Datenträgerwarnung",
            "0001-0002-0003-0004-0005-0006-0007-0008-0009-0010-0011-0012",
        ))
        self.assertIn("stimmt nicht überein", " ".join(text for text, _ in speaker.messages))

    def test_installer_abort_during_recovery_readback_is_fail_closed(self):
        class Challenge:
            def issue(self):
                raise AssertionError("challenge must not be issued")

        class Recorder:
            def record(self, destination):
                destination.write_bytes(b"audio")
                return destination

        class Transcriber:
            def transcribe(self, _path):
                return "Abbrechen"

        class Speaker:
            messages = []

            def speak(self, text, *, language):
                self.messages.append((text, language))

        speaker = Speaker()
        frontend = DirectInstallConfirmation(
            recorder=Recorder(), transcriber=Transcriber(), speaker=speaker,
            challenge=Challenge(),
        )
        self.assertFalse(frontend.authorize(
            "Datenträgerwarnung",
            "0001-0002-0003-0004-0005-0006-0007-0008-0009-0010-0011-0012",
        ))
        self.assertIn("lokal abgebrochen", " ".join(x for x, _ in speaker.messages))

    def test_installer_abort_during_final_phrase_is_fail_closed(self):
        class Challenge:
            confirmed = False

            def issue(self):
                return "anker mond 123"

            def confirm(self, _response):
                self.confirmed = True
                return True

        class Recorder:
            def record(self, destination):
                destination.write_bytes(b"audio")
                return destination

        class Transcriber:
            values = iter((
                "0001 0002 0003 0004 0005 0006 0007 0008 0009 0010 0011 0012",
                "cancel",
            ))

            def transcribe(self, _path):
                return next(self.values)

        class Speaker:
            messages = []

            def speak(self, text, *, language):
                self.messages.append((text, language))

        challenge = Challenge()
        speaker = Speaker()
        frontend = DirectInstallConfirmation(
            recorder=Recorder(), transcriber=Transcriber(), speaker=speaker,
            challenge=challenge,
        )
        self.assertFalse(frontend.authorize(
            "Datenträgerwarnung",
            "0001-0002-0003-0004-0005-0006-0007-0008-0009-0010-0011-0012",
        ))
        self.assertFalse(challenge.confirmed)
        self.assertIn("lokal abgebrochen", " ".join(x for x, _ in speaker.messages))


if __name__ == "__main__":
    unittest.main()
