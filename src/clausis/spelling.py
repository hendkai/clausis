"""Deterministic spelling normalisation for dictated names and identifiers.

A voice-only user dictates names, passwords (where the field allows it), file
names and identifiers by spelling them out: ``"A wie Anton, N wie Nordpol"``
must reach the field as ``AN`` — not as the spoken words.  This module turns
such an utterance into the characters it names, letter by letter:

* ``"A wie Anton"`` → ``A`` — the anchor letter counts, the helper word only
  confirms it (and protects against recogniser errors: if the anchor and the
  helper disagree, the helper wins because it is unambiguous prose).
* ``"A"``, ``"a"`` → the letter itself.
* ``"F wie Fahrenheit"`` → ``F`` — a wrong but harmless helper still yields
  the correct letter.
* ``"drei"`` → ``3`` — spoken digits become digits.
* An unknown word passes through unchanged, space-separated: spelling mode
  never mangles what it cannot prove ("Müller" stays "Müller").

Everything is a plain table plus one rule; the function is pure and the
output keeps the same guarantees the dictation schema already enforces (no
control characters, bounded length).
"""

from __future__ import annotations

from typing import Dict, List

#: German and English spelling-alphabet helper words, lowercase.  Keys are
#: compared case-insensitively; values are the characters they name.
SPOKEN_LETTERS: Dict[str, str] = {
    "anton": "A",
    "berta": "B",
    "caesar": "C",
    "dora": "D",
    "emil": "E",
    "friedrich": "F",
    "gustav": "G",
    "heinrich": "H",
    "ida": "I",
    "julius": "J",
    "kaufmann": "K",
    "ludwig": "L",
    "martha": "M",
    "nordpol": "N",
    "otto": "O",
    "paula": "P",
    "quelle": "Q",
    "richard": "R",
    "samuel": "S",
    "theodor": "T",
    "ulrich": "U",
    "viktor": "V",
    "wilhelm": "W",
    "xanthippe": "X",
    "ypsilon": "Y",
    "zeppelin": "Z",
    "alfa": "A",
    "bravo": "B",
    "charlie": "C",
    "delta": "D",
    "echo": "E",
    "foxtrot": "F",
    "golf": "G",
    "hotel": "H",
    "india": "I",
    "juliett": "J",
    "kilo": "K",
    "lima": "L",
    "mike": "M",
    "november": "N",
    "oscar": "O",
    "papa": "P",
    "quebec": "Q",
    "romeo": "R",
    "sierra": "S",
    "tango": "T",
    "uniform": "U",
    "victor": "V",
    "whiskey": "W",
    "x-ray": "X",
    "xray": "X",
    "yankee": "Y",
    "zulu": "Z",
    "ä": "Ä",
    "ö": "Ö",
    "ü": "Ü",
    "schäfer": "Ä",
    "öl": "Ö",
    "übermut": "Ü",
    "ae": "Ä",
    "oe": "Ö",
    "ue": "Ü",
    "eszett": "ß",
    "scharfes s": "ß",
}

#: Spoken digits, German and English.
SPOKEN_DIGITS: Dict[str, str] = {
    "null": "0",
    "eins": "1",
    "zwei": "2",
    "zwei": "2",
    "drei": "3",
    "vier": "4",
    "fünf": "5",
    "sechs": "6",
    "sieben": "7",
    "acht": "8",
    "neun": "9",
    "zero": "0",
    "one": "1",
    "two": "2",
    "three": "3",
    "four": "4",
    "five": "5",
    "six": "6",
    "seven": "7",
    "eight": "8",
    "nine": "9",
}

#: The connectives: ``"A wie Anton"`` / ``"A as in Anton"``.
_LIKE = frozenset({"wie", "as", "in"})

#: Separators the recogniser attaches to spoken spelling items.  They carry
#: no meaning inside a spelled utterance and are stripped for the lookup
#: only — an unknown word keeps its original bytes.
_SEPARATORS = ",;:"


def _strip_separators(word: str) -> str:
    return word.strip(_SEPARATORS)


def _lookup(word: str) -> str | None:
    """The character a spoken word names, or ``None`` for prose.

    A lone letter names itself (its spoken case is kept); a lone separator
    token names nothing but is not prose either.
    """

    stripped = _strip_separators(word)
    folded = stripped.casefold()
    if not folded:
        return ""
    named = SPOKEN_LETTERS.get(folded) or SPOKEN_DIGITS.get(folded)
    if named is not None:
        return named
    if len(stripped) == 1 and stripped.isalpha():
        return stripped
    return None


def _single_letter(word: str) -> bool:
    return len(word) == 1 and word.isalpha()


def normalise_spelling(text: str) -> str:
    """Rewrite a spelled utterance into the characters it names.

    Whitespace-normalised input; every word is looked up case-insensitively
    as a spelling-alphabet letter, a spoken digit, a single letter or a
    helper word after ``wie``/``as``/``in``.  Named characters concatenate
    directly (``"A wie Anton, N wie Nordpol"`` → ``"AN"``); unknown words
    stay byte for byte and separate the runs around them with spaces, so an
    ordinary dictated word can never be silently mangled.  ``"wie"`` /
    ``"as"`` / ``"in"`` without a known helper also stays prose.
    """

    words = text.split()
    if not words:
        return text
    tokens: List[str] = []
    run = ""

    def flush() -> None:
        nonlocal run
        if run:
            tokens.append(run)
            run = ""

    def emit(character: str) -> None:
        nonlocal run
        run += character

    index = 0
    while index < len(words):
        word = words[index]
        folded = _strip_separators(word).casefold()
        if folded in _LIKE and index + 1 < len(words):
            helper = words[index + 1]
            # "a as in alfa": a second connective directly after the first
            # means the helper word follows it, so skip ahead.
            if _strip_separators(helper).casefold() in _LIKE and index + 2 < len(words):
                helper = words[index + 2]
                index += 1
            character = _lookup(helper)
            if character:
                # "A wie Anton": the previous anchor letter is already in
                # the run; the helper confirms it (or corrects a
                # misrecognised anchor — the helper is unambiguous prose).
                if run and len(run[-1]) == 1 and run[-1].isalpha():
                    run = run[:-1] + character
                else:
                    emit(character)
                index += 2
                continue
        named = _lookup(word)
        if named:
            emit(named)
        elif named is not None and not named:
            # A lone separator token (","): nothing to name.
            pass
        else:
            flush()
            tokens.append(word)
        index += 1
    flush()
    return " ".join(tokens)
