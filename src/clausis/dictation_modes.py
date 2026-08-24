"""Deterministic dictation modes for e-mail addresses, URLs, paths, numbers.

A voice-only user cannot type ``@`` or ``.`` — but plain dictation must never
rewrite them, because a spoken "punkt" inside ordinary prose is nearly always
prose, not a command (see ``punctuation.py``: only the *last* token of an
utterance can be a punctuation command).  Dictation modes resolve that
ambiguity the honest way: the user names the mode, and only then does the
transformation run.

Every mode is triggered by an explicit verb phrase ("diktiere e-mail …" /
"dictate number …"), parsed by the router before an ``ActionRequest`` is
built.  Inside the mode:

* recognised command tokens ("punkt" → ``.``, "at" → ``@``, "slash" → ``/``,
  "minus" → ``-``, spoken digits and German number words 0–99) become their
  character;
* "wörtlich" / "literal" protects the next word verbatim, exactly as in
  ``punctuation.py``;
* anything else stays byte for byte — an unknown word is never mangled.

Everything is a plain table plus rules; the functions are pure and the output
keeps the guarantees the dictation schema already enforces (no control
characters, length ≤ 512 — the request constructor rejects anything else).

Number-word parsing is deliberately V1: digit chains and German compound
words zero to ninety-nine ("zweiundzwanzig" → 22, "drei Komma eins vier" →
"3,14").  Larger numbers, dates and times are documented as missing, not
approximated.
"""

from __future__ import annotations

from typing import Callable, Dict, List, Optional

#: German number words 0–99, plus the English words the dictation triggers
#: accept.  ``word_number`` resolves compounds ("dreiundzwanzig" → 23) via
#: the generated table below, so the atoms here stay irreducible.
_NUMBER_WORDS: Dict[str, int] = {
    "null": 0, "zero": 0,
    "eins": 1, "ein": 1, "eine": 1, "one": 1,
    "zwei": 2, "two": 2,
    "drei": 3, "three": 3,
    "vier": 4, "four": 4,
    "fünf": 5, "five": 5,
    "sechs": 6, "six": 6,
    "sieben": 7, "seven": 7,
    "acht": 8, "eight": 8,
    "neun": 9, "nine": 9,
    "zehn": 10, "ten": 10,
    "elf": 11, "eleven": 11,
    "zwölf": 12, "twelve": 12,
    "dreizehn": 13, "vierzehn": 14, "fünfzehn": 15, "sechzehn": 16,
    "siebzehn": 17, "achtzehn": 18, "neunzehn": 19,
    "thirteen": 13, "fourteen": 14, "fifteen": 15, "sixteen": 16,
    "seventeen": 17, "eighteen": 18, "nineteen": 19,
    "zwanzig": 20, "twenty": 20,
    "dreißig": 30, "thirty": 30,
    "vierzig": 40, "forty": 40,
    "fünfzig": 50, "fifty": 50,
    "sechzig": 60, "sixty": 60,
    "siebzig": 70, "seventy": 70,
    "achtzig": 80, "eighty": 80,
    "neunzig": 90, "ninety": 90,
}

#: Fast compound lookup for 13–99 ("dreiundzwanzig" … "neunundneunzig"),
#: built once from the atoms.  Standard German uses "einund…" for the ones
#: digit 1; dictation also produces "einsund…", so both map to the value.
_ONES_WORDS = ["null", "eins", "zwei", "drei", "vier", "fünf", "sechs", "sieben", "acht", "neun"]
_TENS_WORDS = ["", "", "zwanzig", "dreißig", "vierzig", "fünfzig", "sechzig", "siebzig", "achtzig", "neunzig"]
_COMPOUND_WORDS: Dict[str, int] = {}
for _tens in range(2, 10):
    for _ones in range(1, 10):
        _value = _tens * 10 + _ones
        _COMPOUND_WORDS[f"{_ONES_WORDS[_ones]}und{_TENS_WORDS[_tens]}"] = _value
        if _ones == 1:
            _COMPOUND_WORDS[f"einund{_TENS_WORDS[_tens]}"] = _value

#: Union lookup actually used by the parsers.
_SPOKEN_NUMBERS: Dict[str, int] = {**_NUMBER_WORDS, **_COMPOUND_WORDS}

#: Escape words: they drop themselves and keep the next word verbatim,
#: the same contract as in ``punctuation.py``.
_ESCAPES = frozenset({"wörtlich", "literal"})

#: Output cap: TARGET_RE allows 512 characters, and mode output never
#: widens that (the ``ActionRequest`` constructor rejects longer targets).
MAX_MODE_CHARS = 512


def contains_control_characters(text: str) -> bool:
    """True when a control character rides anywhere in the payload.

    C0 controls (``\\x00``-``\\x1f``), DEL (``\\x7f``) and the C1 range
    (``\\x80``-``\\x9f``) have no place in spoken prose.  Whitespace-class
    controls never reach this check: the router normalises the transcript
    with ``str.split()`` first, which drops them.  What survives mid-word is
    exactly the injection surface, so every dictation payload shaper —
    plain dictation, spelling and the modes — refuses a payload that
    contains one instead of letting the request constructor raise later
    (a voice loop must never crash on a malformed transcript).  The
    refused set matches ``models.TARGET_RE`` exactly; NBSP (``\\xa0``) and
    all other printable Unicode stay allowed on both layers.
    """

    return any(ch < "\x20" or "\x7f" <= ch <= "\x9f" for ch in text)


def word_number(word: str) -> Optional[int]:
    """Value of a single spoken number word (0–99), else ``None``.

    Pure table lookup on the case-folded word; digits pass through as
    integers so digit chains and spoken words mix freely.
    """

    folded = word.casefold()
    if folded.isdigit():
        return int(folded)
    return _SPOKEN_NUMBERS.get(folded)


def _tokens(text: str) -> List[str]:
    return text.split()


def _render_email(words: List[str]) -> Optional[str]:
    """Token rules for e-mail addresses; unknown words stay literal."""

    #: Single-token command words.  "klammeraffe" is the common German
    #: name for ``@`` (also in ``punctuation.py``); "affe" and "ät" are
    #: what recognisers often emit for the English "at".
    named_map = {
        "at": "@", "ät": "@", "affe": "@", "klammeraffe": "@",
        "ätzeichen": "@", "ät-zeichen": "@", "at-zeichen": "@", "at-sign": "@",
        "punkt": ".", "point": ".", "dot": ".",
        "unterstrich": "_", "underscore": "_",
        "bindestrich": "-", "hyphen": "-", "minus": "-",
    }
    out: List[str] = []
    escape_next = False
    for word in words:
        folded = word.casefold()
        if not escape_next and folded in _ESCAPES:
            escape_next = True
            continue
        named = named_map.get(folded)
        if escape_next or named is None:
            out.append(word)
        else:
            out.append(named)
        escape_next = False
    return "".join(out)


#: Schemes whose spoken colon may become ``:``.  Anything alphanumeric of
#: bounded length qualifies, so ``http2`` or a future scheme works without
#: touching this table; the renderer still only converts the colon that
#: directly follows the first token.
def _is_scheme_word(word: str) -> bool:
    return word.isalnum() and 2 <= len(word) <= 8


def _render_url(words: List[str]) -> Optional[str]:
    """Token rules for URLs and file paths.

    "doppelpunkt"/"colon" becomes ``:`` only directly after a first
    scheme-like token (http, https, ftp …), which is held back until the
    colon proves it; a colon anywhere else stays prose.  "punkt"/"dot"
    → ``.``, "schrägstrich"/"slash" → ``/`` (also leading, for paths).
    """

    out: List[str] = []
    escape_next = False
    pending_scheme: Optional[str] = None
    for word in words:
        folded = word.casefold()
        if not escape_next and folded in _ESCAPES:
            if pending_scheme is not None:
                out.append(pending_scheme)
                pending_scheme = None
            escape_next = True
            continue
        if pending_scheme is not None:
            if folded in {"doppelpunkt", "colon"}:
                out.append(pending_scheme + ":")
                pending_scheme = None
                continue
            # No colon follows: the held-back word was ordinary prose.
            out.append(pending_scheme)
            pending_scheme = None
        if escape_next:
            out.append(word)
            escape_next = False
            continue
        if folded in {"punkt", "dot"}:
            out.append(".")
        elif folded in {"schrägstrich", "slash"}:
            out.append("/")
        elif folded in {"doppelpunkt", "colon"}:
            # A colon outside scheme position stays literal prose.
            out.append(word)
        elif not out and _is_scheme_word(folded):
            # First token: it may be a scheme, so hold it back until the
            # next token decides.
            pending_scheme = folded
        else:
            out.append(word)
    if pending_scheme is not None:
        out.append(pending_scheme)
    return "".join(out)


def _render_number(words: List[str]) -> Optional[str]:
    """Digit chains, German number words 0–99 and "Komma" as decimal point.

    A run of digit words concatenates ("drei eins vier" → "314", each word
    its digit, so "zwei zwei" stays "22" with both twos kept); one compound
    word renders as its value ("zweiundzwanzig" → 22, single word).  The
    decimal separator may be "komma", "decimal" or "point" but only after
    something — a leading one is refused with the rest.  Anything
    unparsable makes the whole utterance REFUSED: a half-guessed number is
    worse than none.
    """

    out: List[str] = []
    seen_number = False

    for word in words:
        folded = word.casefold()
        if folded in _ESCAPES:
            # Nothing to protect inside a pure number mode: the escape
            # drops itself and the next word is parsed like any other
            # (a refused payload is the honest outcome for prose escapes).
            continue
        if folded in {"komma", "decimal", "point"}:
            if not seen_number:
                return None
            out.append(",")
            continue
        value = word_number(folded)
        if value is None:
            return None
        out.append(str(value))
        seen_number = True
    if not seen_number:
        return None
    return "".join(out)


#: Registry used by the router: mode name → renderer.
MODE_RENDERERS: Dict[str, Callable[[List[str]], Optional[str]]] = {
    "email": _render_email,
    "url": _render_url,
    "number": _render_number,
}


def apply_mode(mode: str, text: str) -> Optional[str]:
    """Apply a dictation mode to the payload; ``None`` means REFUSED.

    Whitespace-normalised input; the mode never widens the schema (control
    characters cannot appear because none is ever emitted, and a result
    longer than 512 characters is refused rather than truncated).
    """

    renderer = MODE_RENDERERS.get(mode)
    if renderer is None:
        raise ValueError(f"unknown dictation mode: {mode}")
    if contains_control_characters(text):
        return None
    result = renderer(_tokens(text))
    if result is None or not result.strip() or len(result) > MAX_MODE_CHARS:
        return None
    return result
