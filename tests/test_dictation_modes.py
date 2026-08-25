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
        # Big-number vocabulary: a single compound word parses; separate
        # words keep the digit-chain concatenation ("hundert eins" →
        # "1001"), while an unknown scale and a digit token over the
        # 999,999 ceiling refuse — never a half-guess.
        self.assertEqual(apply_mode("number", "hundert eins"), "1001")
        # Separate big words keep the digit-chain contract ("tausend
        # tausend" → "10001000"): each word is rendered honestly; the
        # 999,999 ceiling refuses only single words/compounds and digit
        # TOKENS, which is where a misheard magnitude could hide.
        self.assertEqual(apply_mode("number", "tausend tausend"), "10001000")
        self.assertIsNone(apply_mode("number", "eine million"))
        self.assertIsNone(apply_mode("number", "1000000"))

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
            apply_mode("color", "dreiundzwanzigster mai")


class BigNumberTests(unittest.TestCase):
    def test_hundreds_and_thousands_compounds(self):
        self.assertEqual(apply_mode("number", "hundert"), "100")
        self.assertEqual(apply_mode("number", "einhundert"), "100")
        self.assertEqual(apply_mode("number", "dreihundertfünfundzwanzig"), "325")
        self.assertEqual(apply_mode("number", "sechshundert"), "600")
        self.assertEqual(apply_mode("number", "zweitausendvierhundert"), "2400")
        self.assertEqual(apply_mode("number", "einundzwanzigtausend"), "21000")
        self.assertEqual(apply_mode("number", "hunderttausend"), "100000")
        self.assertEqual(apply_mode("number", "fünfzehnhundert"), "1500")
        self.assertEqual(apply_mode("number", "tausend"), "1000")

    def test_full_range_and_ceiling(self):
        self.assertEqual(
            apply_mode("number", "neunhundertneunundneunzigtausendneunhundertneunundneunzig"),
            "999999",
        )
        self.assertEqual(apply_mode("number", "zweihundertfünfzigtausend"), "250000")
        # The ceiling is honest: a million in one word or digit token
        # refuses instead of half-parsing.
        self.assertIsNone(apply_mode("number", "eine million"))
        self.assertIsNone(word_number("1000000"))
        self.assertEqual(word_number("999999"), 999999)

    def test_german_morphology_edges(self):
        # "sechzehn" vs "sechzig", ß/ss twins, and the "einund…" compound.
        self.assertEqual(apply_mode("number", "sechzehn"), "16")
        self.assertEqual(apply_mode("number", "sechzig"), "60")
        self.assertEqual(apply_mode("number", "dreißig"), "30")
        self.assertEqual(apply_mode("number", "dreissig"), "30")
        self.assertEqual(word_number("einunddreißig"), 31)
        self.assertEqual(word_number("einsunddreißig"), 31)
        self.assertEqual(word_number("zweiunddreißigtausendhundertfünfzig"), 32150)
        self.assertEqual(word_number("hundertfünfundzwanzigtausenddreihundertvier"), 125304)
        # Beyond the 999,999 ceiling the compositional parser refuses.
        self.assertIsNone(word_number("million"))
        # "tausend" appears at most once in a valid German number; a
        # second one is grammar-over-accepted nonsense and refuses.
        self.assertIsNone(word_number("tausendtausend"))
        self.assertIsNone(word_number("hunderttausendtausend"))

    def test_navigation_cap_stays_999(self):
        # The shared vocabulary grows, but the line-number validator keeps
        # the 1–999 cap and the counted-step cap stays 99: a spoken
        # "Zeile tausend" routes nowhere (builder refuses via policy).
        from clausis.policy import ACTION_POLICIES
        from clausis.models import ActionRequest

        validator = ACTION_POLICIES["text.caret.line"].validator
        self.assertIsNotNone(validator)
        request = ActionRequest("text.caret.line", target="1000")
        with self.assertRaises(ValueError):
            validator(request)  # type: ignore[misc]


class DateModeTests(unittest.TestCase):
    def test_digits_cardinals_and_ordinals(self):
        self.assertEqual(apply_mode("date", "12 august 2026"), "12.08.2026")
        self.assertEqual(apply_mode("date", "12. august 2026"), "12.08.2026")
        self.assertEqual(apply_mode("date", "12. 8. 2026"), "12.08.2026")
        self.assertEqual(apply_mode("date", "zwölf august 2026"), "12.08.2026")
        self.assertEqual(apply_mode("date", "zwölfter august 2026"), "12.08.2026")
        self.assertEqual(apply_mode("date", "zwölften august 2026"), "12.08.2026")
        self.assertEqual(apply_mode("date", "12 punkt 8 2026"), "12.08.2026")
        self.assertEqual(
            apply_mode("date", "den ersten mai zweitausendsechsundzwanzig"), "01.05.2026"
        )

    def test_year_as_word_and_boundaries(self):
        self.assertEqual(apply_mode("date", "1 1 1900"), "01.01.1900")
        self.assertEqual(apply_mode("date", "12 august 2099"), "12.08.2099")
        # Years outside 1900–2099 refuse, whether digits or words.
        self.assertIsNone(apply_mode("date", "12 august 1899"))
        self.assertIsNone(apply_mode("date", "12 august 2100"))
        self.assertIsNone(apply_mode("date", "12 august tausend"))

    def test_calendar_decides(self):
        self.assertEqual(apply_mode("date", "29 februar 2024"), "29.02.2024")
        self.assertIsNone(apply_mode("date", "29 februar 2025"))
        self.assertIsNone(apply_mode("date", "31 april 2026"))
        self.assertIsNone(apply_mode("date", "31 juni 2026"))
        self.assertIsNone(apply_mode("date", "32 januar 2026"))
        self.assertIsNone(apply_mode("date", "null januar 2026"))
        self.assertIsNone(apply_mode("date", "dreiunddreißigster januar 2026"))

    def test_english_months_and_missing_parts_refuse(self):
        self.assertEqual(apply_mode("date", "12 january 2026"), "12.01.2026")
        self.assertIsNone(apply_mode("date", "zwölf august"))
        self.assertIsNone(apply_mode("date", "august 2026"))
        self.assertIsNone(apply_mode("date", "montag zwölfter august"))
        self.assertIsNone(apply_mode("date", "12 13 2026"))

    def test_mode_result_is_schema_valid(self):
        rendered = apply_mode("date", "erster januar 2026")
        self.assertIsNotNone(rendered)
        request = ActionRequest("text.insert", target=rendered)
        self.assertEqual(request.target, "01.01.2026")


class TimeModeTests(unittest.TestCase):
    def test_hour_and_hour_minute(self):
        self.assertEqual(apply_mode("time", "vierzehn uhr"), "14:00")
        self.assertEqual(apply_mode("time", "vierzehn uhr dreißig"), "14:30")
        self.assertEqual(apply_mode("time", "8 uhr 5"), "08:05")
        self.assertEqual(apply_mode("time", "neun uhr sechsundvierzig"), "09:46")
        self.assertEqual(apply_mode("time", "null uhr"), "00:00")
        self.assertEqual(apply_mode("time", "12 uhr null"), "12:00")

    def test_minutes_as_word_or_digits(self):
        self.assertEqual(apply_mode("time", "14 uhr 30"), "14:30")
        self.assertEqual(apply_mode("time", "14 uhr dreißig"), "14:30")
        self.assertEqual(apply_mode("time", "23 uhr neunundfünfzig"), "23:59")

    def test_colloquial_forms_refuse(self):
        # V1 limit, honestly refused: the 14:30/15:30 ambiguity must never
        # be guessed.
        self.assertIsNone(apply_mode("time", "halb drei"))
        self.assertIsNone(apply_mode("time", "viertel nach fünf"))
        self.assertIsNone(apply_mode("time", "viertel vor acht"))
        self.assertIsNone(apply_mode("time", "fünf nach halb drei"))

    def test_out_of_range_and_malformed_refuse(self):
        self.assertIsNone(apply_mode("time", "24 uhr"))
        self.assertIsNone(apply_mode("time", "14 uhr 60"))
        self.assertIsNone(apply_mode("time", "14 uhr 15 30"))
        self.assertIsNone(apply_mode("time", "uhr"))
        self.assertIsNone(apply_mode("time", "vierzehn uhr banane"))

    def test_mode_result_is_schema_valid(self):
        rendered = apply_mode("time", "neunzehn uhr sechsundvierzig")
        self.assertIsNotNone(rendered)
        request = ActionRequest("text.insert", target=rendered)
        self.assertEqual(request.target, "19:46")


class PathModeTests(unittest.TestCase):
    def test_slash_starts_a_new_segment(self):
        # The documented run-together bug ("schrägstrich home hendrik" →
        # "/homehendrik") is fixed: every word is its own segment.
        self.assertEqual(apply_mode("path", "schrägstrich home hendrik"), "/home/hendrik")
        self.assertEqual(apply_mode("path", "slash home hendrik"), "/home/hendrik")
        self.assertEqual(
            apply_mode("path", "schrägstrich usr share doc"), "/usr/share/doc"
        )

    def test_dot_files_and_extensions(self):
        self.assertEqual(apply_mode("path", "home hendrik punkt bashrc"), "home/hendrik/.bashrc")
        self.assertEqual(
            apply_mode("path", "schrägstrich home hendrik punkt bashrc"), "/home/hendrik/.bashrc"
        )
        self.assertEqual(apply_mode("path", "punkt bashrc"), ".bashrc")

    def test_number_words_render_as_digits(self):
        self.assertEqual(
            apply_mode("path", "usr share doc paket 2 readme"), "usr/share/doc/paket/2/readme"
        )
        self.assertEqual(
            apply_mode("path", "home hendrik version zwei"), "home/hendrik/version/2"
        )

    def test_trailing_slash_and_double_slash_collapse(self):
        self.assertEqual(apply_mode("path", "schrägstrich home hendrik schrägstrich"), "/home/hendrik/")
        # Repeated separators collapse to one boundary, so a misheard
        # "schrägstrich schrägstrich" cannot produce a double slash.
        self.assertEqual(apply_mode("path", "schrägstrich schrägstrich home"), "/home")

    def test_refusals(self):
        # A trailing "punkt" names no segment; whitespace-only refuses.
        self.assertIsNone(apply_mode("path", "home hendrik punkt"))
        self.assertIsNone(apply_mode("path", "   "))

    def test_escape_word_keeps_the_next_token_verbatim(self):
        self.assertEqual(apply_mode("path", "wörtlich punkt"), "punkt")
        self.assertEqual(apply_mode("path", "home wörtlich slash doc"), "home/slash/doc")

    def test_mode_result_is_schema_valid(self):
        rendered = apply_mode("path", "schrägstrich home hendrik punkt bashrc")
        self.assertIsNotNone(rendered)
        request = ActionRequest("text.insert", target=rendered)
        self.assertEqual(request.target, "/home/hendrik/.bashrc")


if __name__ == "__main__":
    unittest.main()
