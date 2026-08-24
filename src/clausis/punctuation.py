"""Deterministic expansion of spoken punctuation commands in dictation.

A voice-only user cannot type a period, so dictation needs spoken commands for
punctuation.  The transformation is a plain table plus three rules:

1. Only the **last** token of the utterance is treated as a command word.  A
   spoken "punkt" inside a file name, identifier or URL ("daten punkt csv")
   stays byte for byte, because AT-SPI recognisers emit mid-sentence command
   words as ordinary prose far more often than as commands.
2. The word before the command can protect it: an article before a German
   noun ("der Punkt") or a number before a decimal or section number
   ("drei Komma vier") marks the command word as dictated prose.  Missing a
   comma is visible and correctable; silently mangling what the user actually
   said is not, so protection errs towards prose.
3. "wörtlich" / "literal" drops itself and protects the next word, so any
   command word can still be dictated as prose.

A line break cannot ride inside a dictated target: the request schema forbids
control characters on every trust boundary, and that stays unchanged.  "Neue
Zeile" and "Absatz" are therefore first-class spoken commands that the adapter
carries out itself (``text.newline`` / ``text.paragraph``); see the router.

The output of :func:`expand_punctuation` is still validated by the same schema
rules as before: no control characters, no empty dictation, bounded length.
Nothing here relaxes them.
"""

from __future__ import annotations

from typing import Dict, List, Tuple

#: Spoken punctuation commands, German and English.  Keys are compared
#: case-insensitively after whitespace normalisation; values are the
#: characters actually written into the field.  Every value is printable.
SPOKEN_PUNCTUATION: Dict[str, str] = {
    "punkt": ".",
    "point": ".",
    "full stop": ".",
    "period": ".",
    "komma": ",",
    "comma": ",",
    "semikolon": ";",
    "strichpunkt": ";",
    "semicolon": ";",
    "doppelpunkt": ":",
    "colon": ":",
    "ausrufezeichen": "!",
    "exclamation mark": "!",
    "exclamation point": "!",
    "fragezeichen": "?",
    "question mark": "?",
    "bindestrich": "-",
    "hyphen": "-",
    "gedankenstrich": "—",
    "em dash": "—",
    "klammern auf": "(",
    "klammer auf": "(",
    "open paren": "(",
    "open parenthesis": "(",
    "klammer zu": ")",
    "close paren": ")",
    "close parenthesis": ")",
    "öffnendes anführungszeichen": "„",
    "anführungszeichen öffnen": "„",
    "anführungszeichen auf": "„",
    "open quote": "„",
    "anführungszeichen schließen": "“",
    "schließendes anführungszeichen": "“",
    "anführungszeichen zu": "“",
    "close quote": "“",
    "klammeraffe": "@",
    "at sign": "@",
}

#: Punctuation that attaches to the previous word without a space.
_CLOSING = frozenset({".", ",", ";", ":", "!", "?", "”", ")", "@"})

#: Words that protect a trailing command word from being rewritten: spoken
#: directly before it, they mark the command word as dictated prose (the
#: article of a German noun, or the integer part of a decimal or section
#: number).
_ARTICLES = frozenset(
    {"der", "die", "das", "den", "dem", "ein", "eine", "einen", "kein", "keine", "the", "a", "an", "no"}
)
_NUMBER_WORDS = frozenset(
    {
        "eins", "zwei", "drei", "vier", "fünf", "sechs", "sieben", "acht", "neun", "null",
        "one", "two", "three", "four", "five", "six", "seven", "eight", "nine", "zero",
    }
)
_DIGITS = frozenset({str(digit) for digit in range(10)})

#: Escape words: they drop themselves and protect the next word.
_ESCAPES = frozenset({"wörtlich", "literal"})

#: Longest command first, so multi-word commands ("full stop") are matched
#: before their single-word prefixes could fire.
_COMMAND_KEYS_BY_LENGTH: Tuple[str, ...] = tuple(
    sorted(SPOKEN_PUNCTUATION, key=lambda key: -len(key.split()))
)


def _protected_context(previous: str) -> bool:
    """True when the previous word marks the next word as plain prose."""

    folded = previous.casefold()
    return folded in _ARTICLES or folded in _NUMBER_WORDS or folded in _DIGITS


def expand_punctuation(text: str) -> str:
    """Rewrite a spoken punctuation command into its character.

    Whitespace-normalised input; byte-for-byte output for everything that is
    not a command word in command position — which is the last token of the
    utterance, matched longest-first.  Articles and numbers protect their
    successor, and the escape words drop themselves while protecting the next
    word.  The function is pure: no state, no I/O, same input always yields
    the same output.
    """

    words = text.split()
    if not words:
        return text
    for key in _COMMAND_KEYS_BY_LENGTH:
        parts = key.split()
        count = len(parts)
        if count > len(words):
            continue
        tail = [word.casefold() for word in words[-count:]]
        if tail != parts:
            continue
        before = words[:-count]
        previous = before[-1] if before else ""
        if previous.casefold() in _ESCAPES:
            # "wörtlich Punkt": drop the escape, keep the words as prose.
            return " ".join(before[:-1] + words[-count:])
        if _protected_context(previous):
            return text
        out: List[str] = list(before)
        character = SPOKEN_PUNCTUATION[key]
        if out and character in _CLOSING:
            out[-1] = out[-1] + character
        else:
            out.append(character)
        return " ".join(out)
    return " ".join(words)
