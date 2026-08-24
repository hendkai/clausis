"""Pure text-unit boundary helpers for voice-only editing.

Everything here is deterministic string arithmetic: no I/O, no state, no
AT-SPI access.  The adapter layer uses these helpers to find word, sentence,
line and paragraph boundaries around a caret offset so selection and granular
reading do not depend on heuristic guesses inside the adapter.

Sentence boundaries are deliberately simple — ``". "``, ``"! "``, ``"? "`` and
newlines — because the goal is a predictable, spoken-friendly unit, not a
linguistic parse.  Offsets are always inside ``[0, len(content)]``.
"""

from __future__ import annotations

from typing import Optional, Tuple


def word_bounds(content: str, offset: int) -> Tuple[int, int]:
    """Start and end of the word at ``offset``.

    A caret right after a word (the usual position after dictating) selects
    that word; a caret inside a separator run selects the word that follows;
    trailing separators select the last word.  Empty input yields ``(0, 0)``.
    """

    if not content:
        return 0, 0
    offset = max(0, min(offset, len(content)))
    if offset > 0 and not content[offset - 1].isspace():
        # Caret at the end of (or inside) a word: use that word.
        pass
    elif offset < len(content) and not content[offset].isspace():
        # Caret at the start of a word: use it.
        pass
    else:
        # Caret inside a separator run: skip forward, else fall back to the
        # last word before the trailing separators.
        while offset < len(content) and content[offset].isspace():
            offset += 1
        if offset >= len(content):
            offset = len(content.rstrip())
    start = offset
    while start > 0 and not content[start - 1].isspace():
        start -= 1
    end = offset
    while end < len(content) and not content[end].isspace():
        end += 1
    if start == end:
        # A separator-only stretch: no word to select.
        return end, end
    return start, end


def _sentence_end(content: str, from_index: int) -> int:
    """End offset (exclusive) of the sentence starting at ``from_index``.

    A sentence ends after ``.``, ``!``, ``?`` or a newline — with no trailing
    space, so replacing a sentence keeps the separating space intact.
    """

    index = from_index
    while index < len(content):
        character = content[index]
        if character == "\n" or character in ".!?":
            return index + 1
        index += 1
    return len(content)


def _sentence_start(content: str, before: int) -> int:
    """Start offset of the sentence that contains offset ``before``."""

    index = min(before, len(content))
    while index > 0:
        index -= 1
        character = content[index]
        if character == "\n":
            return index + 1
        if character in ".!?":
            probe = index + 1
            while probe < len(content) and content[probe].isspace() and content[probe] != "\n":
                probe += 1
            if probe >= index + 2 or probe >= len(content):
                return min(probe, len(content))
    return 0


def sentence_bounds(content: str, offset: int) -> Tuple[int, int]:
    """Start and end of the sentence containing ``offset``.

    The span includes the closing punctuation but never the following space,
    so a selection boundary matches what a replacement should cover.
    """

    if not content:
        return 0, 0
    offset = max(0, min(offset, len(content)))
    start = _sentence_start(content, offset)
    end = _sentence_end(content, start)
    if end <= offset and offset < len(content):
        # The offset points at the boundary itself: use the next sentence.
        start = offset
        while start < len(content) and content[start].isspace() and content[start] != "\n":
            start += 1
        end = _sentence_end(content, start)
    if end < offset:
        end = offset
    return start, max(end, start)


def line_bounds(content: str, offset: int) -> Tuple[int, int]:
    """Start and end (excluding the newline) of the line containing ``offset``."""

    if not content:
        return 0, 0
    offset = max(0, min(offset, len(content)))
    start = content.rfind("\n", 0, offset) + 1
    end = content.find("\n", offset)
    if end == -1:
        end = len(content)
    return start, end


def paragraph_bounds(content: str, offset: int) -> Tuple[int, int]:
    """Start and end of the paragraph (blank-line separated) around ``offset``.

    The blank line itself belongs to neither paragraph, so the spans contain
    only the paragraphs' own text (single newlines inside stay included).
    """

    if not content:
        return 0, 0
    offset = max(0, min(offset, len(content)))
    start = 0
    index = 0
    while True:
        boundary = content.find("\n\n", index)
        if boundary == -1 or boundary + 2 > offset:
            break
        start = boundary + 2
        index = boundary + 2
    end = content.find("\n\n", offset)
    if end == -1:
        end = len(content)
    return min(start, offset), max(end, start)


#: Granularity names accepted by ``text.read_granular``.
GRANULARITIES = ("character", "word", "line", "sentence", "paragraph")


def granular_chunk(
    content: str, granularity: str, offset: Optional[int] = None
) -> Tuple[str, int]:
    """Return ``(text, new_offset)`` for the unit at ``offset``.

    For ``character`` the single character at the offset is spoken and the
    offset advances by one; for the other granularities the whole unit is
    spoken and the offset moves to its end.  The returned offset is always
    within ``[0, len(content)]``.
    """

    if granularity not in GRANULARITIES:
        raise ValueError(f"unbekannte Granularität: {granularity}")
    if not content:
        return "", 0
    if offset is None:
        offset = 0
    offset = max(0, min(offset, len(content)))
    if granularity == "character":
        if offset >= len(content):
            return "", offset
        return content[offset], offset + 1
    if granularity == "word":
        start, end = word_bounds(content, offset)
    elif granularity == "line":
        start, end = line_bounds(content, offset)
    elif granularity == "sentence":
        start, end = sentence_bounds(content, offset)
    else:
        start, end = paragraph_bounds(content, offset)
    if start >= end:
        return "", min(max(end, offset), len(content))
    return content[start:end], min(end, len(content))
