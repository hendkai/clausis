"""Deterministic spoken-punctuation expansion for dictation.

The transformation runs in the router, before policy validation, and is pure
table work: same input, same output, no state, no I/O.  These tests pin the
behaviour a voice-only user depends on — and the cases where a naive rewrite
would silently mangle what was actually said.
"""

from __future__ import annotations

import unittest

from clausis.punctuation import SPOKEN_PUNCTUATION, expand_punctuation
from clausis.router import OfflineRouter


class ExpansionTests(unittest.TestCase):
    def test_basic_commands_become_characters(self):
        cases = {
            "Hallo Welt Punkt": "Hallo Welt.",
            "Hallo Welt Komma": "Hallo Welt,",
            "ist das richtig Fragezeichen": "ist das richtig?",
            "sehr gut Ausrufezeichen": "sehr gut!",
            "erstens Doppelpunkt": "erstens:",
            "hallo Semikolon": "hallo;",
            "hello world full stop": "hello world.",
            "really question mark": "really?",
            "great exclamation mark": "great!",
        }
        for spoken, expected in cases.items():
            with self.subTest(spoken=spoken):
                self.assertEqual(expand_punctuation(spoken), expected)

    def test_trailing_command_glues_to_the_previous_word(self):
        self.assertEqual(expand_punctuation("Guten Tag Komma"), "Guten Tag,")
        self.assertEqual(expand_punctuation("danke Punkt"), "danke.")

    def test_multiword_commands_win_over_their_parts(self):
        self.assertEqual(expand_punctuation("wait full stop"), "wait.")

    def test_mid_utterance_command_words_stay_prose(self):
        # A recogniser emits mid-sentence command words as ordinary prose far
        # more often than as commands (file names, URLs, dictation of the
        # word itself), so only the last token is ever rewritten.
        for prose in (
            "Milch und Brot kaufen",
            "Der Treffpunkt ist um drei",
            "version 2 point 4 ist veraltet",
            "lies daten punkt csv vor",
            "hello comma world",
        ):
            with self.subTest(prose=prose):
                self.assertEqual(expand_punctuation(prose), prose)

    def test_article_protects_a_trailing_command_word(self):
        self.assertEqual(expand_punctuation("der Punkt"), "der Punkt")
        self.assertEqual(expand_punctuation("das Fragezeichen"), "das Fragezeichen")

    def test_number_protects_a_trailing_command_word(self):
        self.assertEqual(expand_punctuation("drei Komma vier"), "drei Komma vier")
        self.assertEqual(expand_punctuation("3 Komma 4"), "3 Komma 4")

    def test_escape_word_drops_itself_and_protects_the_next_word(self):
        self.assertEqual(expand_punctuation("wörtlich Punkt"), "Punkt")
        self.assertEqual(expand_punctuation("literal point"), "point")
        self.assertEqual(expand_punctuation("note wörtlich Punkt"), "note Punkt")

    def test_a_trailing_escape_word_stays_prose(self):
        # Dropping a word the user actually said is never right; the escape
        # only drops itself when it protects a command word.
        self.assertEqual(expand_punctuation("Ende wörtlich"), "Ende wörtlich")

    def test_empty_and_whitespace_input_pass_through(self):
        self.assertEqual(expand_punctuation(""), "")
        self.assertEqual(expand_punctuation("   "), "   ")

    def test_pure_punctuation_utterance_becomes_the_character(self):
        self.assertEqual(expand_punctuation("Punkt"), ".")
        self.assertEqual(expand_punctuation("Komma"), ",")


class DeterminismTests(unittest.TestCase):
    def test_same_input_yields_same_output(self):
        for _ in range(3):
            self.assertEqual(expand_punctuation("Guten Tag Punkt"), "Guten Tag.")

    def test_every_table_value_is_printable_and_single(self):
        for value in SPOKEN_PUNCTUATION.values():
            with self.subTest(value=value):
                self.assertEqual(len(value), 1)
                self.assertFalse(value.isspace())

    def test_no_command_value_contains_whitespace(self):
        for key, value in SPOKEN_PUNCTUATION.items():
            with self.subTest(key=key):
                self.assertEqual(value, value.strip())


class RouterIntegrationTests(unittest.TestCase):
    def test_router_expands_trailing_punctuation_command(self):
        request = OfflineRouter().route("diktiere Guten Tag Punkt")
        self.assertEqual(request.action, "text.insert")
        self.assertEqual(request.target, "Guten Tag.")

    def test_router_keeps_protected_prose_verbatim(self):
        request = OfflineRouter().route("diktiere der Punkt ist der Treffpunkt")
        self.assertEqual(request.target, "der Punkt ist der Treffpunkt")

    def test_router_escape_word_reaches_the_field_as_prose(self):
        request = OfflineRouter().route("tippe wörtlich Punkt")
        self.assertEqual(request.target, "Punkt")

    def test_newline_and_paragraph_are_actions_not_dictation(self):
        router = OfflineRouter()
        for spoken, action in (
            ("neue zeile", "text.newline"),
            ("absatz", "text.paragraph"),
            ("new line", "text.newline"),
            ("new paragraph", "text.paragraph"),
        ):
            with self.subTest(spoken=spoken):
                request = router.route(spoken)
                self.assertTrue(request is not None and request.action == action, spoken)

    def test_schema_still_forbids_control_characters_in_the_target(self):
        # The expansion only produces printable characters; the schema keeps
        # forbidding control characters regardless of where a target came from.
        from clausis.models import ActionRequest

        with self.assertRaises(ValueError):
            ActionRequest("text.insert", "zeile\numbruch")


if __name__ == "__main__":
    unittest.main()
