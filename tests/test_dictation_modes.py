"""Unit tests for the deterministic dictation modes.

E-Mail, URL/path and number payloads are transformed only inside their
explicit mode; the tests pin the German and English trigger vocabularies,
the escape word, refusal behaviour and the schema bounds the modes must
never widen.
"""

from __future__ import annotations

import unittest

from clausis.dictation_modes import MAX_MODE_CHARS, apply_mode, word_number
from clausis.models import ActionRequest


class EmailModeTests(unittest.TestCase):
    def test_german_at_variants(self):
        for spoken in ("at", "ät", "affe", "klammeraffe", "ätzeichen"):
            with self.subTest(spoken=spoken):
                self.assertEqual(
                    apply_mode("email", f"hendrik {spoken} example punkt de"),
                    "hendrik@example.de",
                )

    def test_english_dot_and_underscore(self):
        self.assertEqual(
            apply_mode("email", "john dot smith at example dot com"),
            "john.smith@example.com",
        )
        self.assertEqual(
            apply_mode("email", "vor underscore name at example dot org"),
            "vor_name@example.org",
        )

    def test_hyphen_and_unknown_words_stay_literal(self):
        self.assertEqual(
            apply_mode("email", "max minus mustermann at beispiel punkt de"),
            "max-mustermann@beispiel.de",
        )
        # "kaiser" is not a command token — it stays byte for byte.
        self.assertEqual(
            apply_mode("email", "hendrik at kaiser-mail punkt de"),
            "hendrik@kaiser-mail.de",
        )

    def test_escape_word_keeps_the_next_token_verbatim(self):
        self.assertEqual(
            apply_mode("email", "wörtlich at punkt de"),
            "at.de",
        )
        self.assertEqual(
            apply_mode("email", "literal dot at example dot com"),
            "dot@example.com",
        )

    def test_mode_result_is_schema_valid(self):
        rendered = apply_mode("email", "a at b punkt co")
        self.assertIsNotNone(rendered)
        # The request constructor enforces TARGET_RE; it must not raise.
        request = ActionRequest("text.insert", target=rendered)
        self.assertEqual(request.target, "a@b.co")


class UrlModeTests(unittest.TestCase):
    def test_scheme_colon_only_after_scheme(self):
        self.assertEqual(
            apply_mode("url", "https doppelpunkt schrägstrich schrägstrich example punkt de"),
            "https://example.de",
        )
        self.assertEqual(
            apply_mode("url", "http doppelpunkt slash slash localhost slash"),
            "http://localhost/",
        )

    def test_english_trigger_vocabulary(self):
        self.assertEqual(
            apply_mode("url", "https colon slash slash example dot org slash path"),
            "https://example.org/path",
        )

    def test_host_without_scheme_keeps_prose_colon(self):
        # A colon not in scheme position is prose and stays literal.
        self.assertEqual(
            apply_mode("url", "localhost doppelpunkt 8080"),
            "localhostdoppelpunkt8080",
        )

    def test_leading_slash_is_a_path(self):
        self.assertEqual(
            apply_mode("url", "schrägstrich home hendrik dokumente punkt txt"),
            "/homehendrikdokumente.txt",
        )

    def test_first_token_without_colon_is_prose(self):
        # "www" looks scheme-like but no colon follows: it stays a word.
        self.assertEqual(
            apply_mode("url", "www punkt example punkt de"),
            "www.example.de",
        )

    def test_escape_word(self):
        self.assertEqual(
            apply_mode("url", "wörtlich localhost doppelpunkt x"),
            "localhostdoppelpunktx",
        )


class NumberModeTests(unittest.TestCase):
    def test_digit_chain_with_decimal(self):
        self.assertEqual(apply_mode("number", "drei Komma eins vier"), "3,14")
        self.assertEqual(apply_mode("number", "null Komma fünf"), "0,5")

    def test_compound_german_numbers(self):
        self.assertEqual(apply_mode("number", "zweiundzwanzig"), "22")
        self.assertEqual(apply_mode("number", "dreiundzwanzig"), "23")
        self.assertEqual(apply_mode("number", "einundzwanzig"), "21")
        self.assertEqual(apply_mode("number", "einsundzwanzig"), "21")
        self.assertEqual(apply_mode("number", "neunundneunzig"), "99")
        self.assertEqual(word_number("sechsundsechzig"), 66)

    def test_mixed_digits_and_words(self):
        self.assertEqual(apply_mode("number", "4 2"), "42")
        self.assertEqual(apply_mode("number", "vier zwei"), "42")
        self.assertEqual(apply_mode("number", "12 Komma 5"), "12,5")

    def test_english_number_words(self):
        self.assertEqual(apply_mode("number", "three point one four"), "3,14")
        self.assertEqual(apply_mode("number", "twelve"), "12")
        self.assertEqual(apply_mode("number", "twenty"), "20")

    def test_unparsable_words_refuse_the_whole_payload(self):
        self.assertIsNone(apply_mode("number", "drei Bananen"))
        self.assertIsNone(apply_mode("number", "hundert"))

    def test_leading_decimal_and_empty_refuse(self):
        self.assertIsNone(apply_mode("number", "Komma fünf"))
        self.assertIsNone(apply_mode("number", "   "))
        self.assertIsNone(apply_mode("number", "wörtlich"))

    def test_whitespace_is_normalised(self):
        self.assertEqual(apply_mode("number", "  zwölf  "), "12")


class ModeBoundTests(unittest.TestCase):
    def test_overlong_payload_is_refused_not_truncated(self):
        spoken = " ".join(["neun"] * 600)
        self.assertIsNone(apply_mode("number", spoken))
        self.assertGreater(len(spoken), MAX_MODE_CHARS)

    def test_unknown_mode_raises(self):
        with self.assertRaises(ValueError):
            apply_mode("date", "dreiundzwanzigster mai")


if __name__ == "__main__":
    unittest.main()
