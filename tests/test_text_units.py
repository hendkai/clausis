"""Unit tests for the pure text-unit boundary helpers."""

from __future__ import annotations

import unittest

from clausis.text_units import (
    granular_chunk,
    line_bounds,
    paragraph_bounds,
    sentence_bounds,
    word_bounds,
)


TEXT = (
    "Erster Satz. Zweiter Satz danebena! Dritter Satz?\n"
    "Neue Zeile hier.\n\n"
    "Neuer Absatz. Noch ein Satz."
)


class WordBoundsTests(unittest.TestCase):
    def test_word_inside_and_at_edges(self):
        content = "hallo welt hier"
        self.assertEqual(word_bounds(content, 0), (0, 5))
        self.assertEqual(word_bounds(content, 3), (0, 5))
        self.assertEqual(word_bounds(content, 5), (0, 5))
        self.assertEqual(word_bounds(content, 6), (6, 10))
        self.assertEqual(word_bounds(content, 15), (11, 15))

    def test_offset_in_separator_run_uses_following_word(self):
        content = "eins  zwei"
        self.assertEqual(word_bounds(content, 5), (6, 10))
        self.assertEqual(word_bounds(content, 4), (0, 4))

    def test_offset_at_trailing_separator_uses_last_word(self):
        content = "eins "
        self.assertEqual(word_bounds(content, 4), (0, 4))

    def test_empty_content(self):
        self.assertEqual(word_bounds("", 0), (0, 0))


class SentenceBoundsTests(unittest.TestCase):
    def test_sentences_are_found_in_order(self):
        content = "Erster Satz. Zweiter Satz! Dritter?"
        first_end = content.index(".") + 1
        second_end = content.index("!") + 1
        self.assertEqual(sentence_bounds(content, 0), (0, first_end))
        self.assertEqual(sentence_bounds(content, first_end + 1), (first_end + 1, second_end))
        self.assertEqual(
            sentence_bounds(content, second_end + 1), (second_end + 1, len(content))
        )

    def test_offset_on_the_boundary_moves_to_next_sentence(self):
        content = "Eins. Zwei."
        start, end = sentence_bounds(content, 5)
        self.assertEqual(content[start:end], "Zwei.")

    def test_newline_ends_a_sentence(self):
        content = "Zeile eins\nZeile zwei"
        start, end = sentence_bounds(content, 0)
        self.assertEqual(content[start:end], "Zeile eins\n")

    def test_empty_content(self):
        self.assertEqual(sentence_bounds("", 0), (0, 0))


class LineBoundsTests(unittest.TestCase):
    def test_lines_are_found(self):
        content = "eins\nzwei\ndrei"
        self.assertEqual(line_bounds(content, 2), (0, 4))
        self.assertEqual(line_bounds(content, 5), (5, 9))
        self.assertEqual(line_bounds(content, 11), (10, 14))


class ParagraphBoundsTests(unittest.TestCase):
    def test_paragraphs_are_blank_line_separated(self):
        content = "Absatz eins.\n\nAbsatz zwei."
        self.assertEqual(paragraph_bounds(content, 3), (0, 12))
        start, end = paragraph_bounds(content, 14)
        self.assertEqual(content[start:end], "Absatz zwei.")


class GranularChunkTests(unittest.TestCase):
    def test_character_advances_by_one(self):
        self.assertEqual(granular_chunk("abc", "character", 0), ("a", 1))
        self.assertEqual(granular_chunk("abc", "character", 2), ("c", 3))
        self.assertEqual(granular_chunk("abc", "character", 3), ("", 3))

    def test_word_and_line_and_sentence(self):
        content = "hallo welt. neue"
        text, offset = granular_chunk(content, "word", 0)
        self.assertEqual((text, offset), ("hallo", 5))
        text, offset = granular_chunk(content, "line", 0)
        self.assertEqual(text, content)
        text, offset = granular_chunk(content, "sentence", 0)
        self.assertEqual((text, offset), ("hallo welt.", 11))

    def test_paragraph(self):
        content = "eins.\n\nzwei."
        text, offset = granular_chunk(content, "paragraph", 0)
        self.assertEqual((text, offset), ("eins.", 5))

    def test_unknown_granularity_is_rejected(self):
        with self.assertRaises(ValueError):
            granular_chunk("x", "page", 0)

    def test_full_document_sample(self):
        text, _ = granular_chunk(TEXT, "sentence", 0)
        self.assertEqual(text, "Erster Satz.")
        text, _ = granular_chunk(TEXT, "paragraph", 0)
        self.assertTrue(text.startswith("Erster Satz."))
        self.assertNotIn("\n\n", text)


if __name__ == "__main__":
    unittest.main()
