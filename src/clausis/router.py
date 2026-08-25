"""Deterministic offline command router for German and English."""

from __future__ import annotations

from dataclasses import dataclass
import re
from typing import Callable, List, Match, Optional, Pattern, Sequence

from .dictation_modes import apply_mode, contains_control_characters
from .models import ActionRequest, Origin, Risk
from .punctuation import expand_punctuation
from .spelling import normalise_spelling


#: A builder turns a match into a request, or returns ``None`` to decline
#: the utterance (dictation modes do this when their payload is refused);
#: the router then returns ``None`` so the utterance falls to the agent.
Builder = Callable[[Match[str]], Optional[ActionRequest]]


@dataclass(frozen=True)
class CommandPattern:
    name: str
    patterns: Sequence[Pattern[str]]
    builder: Builder


def _simple(action: str, risk: Risk = Risk.LOW, reversible: bool = True) -> Builder:
    return lambda _: ActionRequest(action, risk=risk, reversible=reversible)


def _target(action: str, risk: Risk = Risk.LOW, reversible: bool = True) -> Builder:
    return lambda match: ActionRequest(
        action,
        target=match.group("target").strip(),
        risk=risk,
        reversible=reversible,
    )


def _dictation(match: Match[str]) -> Optional[ActionRequest]:
    """Keep dictated prose exactly as spoken, including case and punctuation.

    Spoken punctuation commands at the end of the utterance are rewritten into
    real characters first (deterministic table, see ``punctuation.py``); mid-
    utterance words always stay exactly as spoken.  A payload with control
    characters riding inside it is refused (builder returns ``None``): the
    request schema would reject it anyway, and a routing crash inside the
    voice loop is the one outcome a blind user cannot afford.
    """

    payload = match.group("target").strip()
    if contains_control_characters(payload):
        return None
    return ActionRequest(
        "text.insert", target=expand_punctuation(payload)
    )


def _dictation_replacement(match: Match[str]) -> Optional[ActionRequest]:
    """Route „nein, ich meinte …" into the field's correction slot.

    The payload follows exactly the dictation contract: spoken punctuation
    at the end is rewritten, control characters riding inside refuse the
    whole utterance before any adapter runs, and the request schema bounds
    stay the same — this is no new injection path, it is dictation with a
    remembered anchor.  Whether a dictation to replace actually exists is
    the adapter's honest decision (it owns the per-field dictation memory),
    never the router's.
    """

    payload = match.group("target").strip()
    if contains_control_characters(payload):
        return None
    return ActionRequest(
        "text.replace_last_dictation", target=expand_punctuation(payload)
    )


def _spelling(match: Match[str]) -> Optional[ActionRequest]:
    """Turn a spelled utterance into the characters it names.

    ``"Buchstabiere A wie Anton, N wie Nordpol"`` becomes the dictation
    ``"AN"``: names, identifiers and digits dictated letter by letter reach
    the field as characters, not as the spoken helper words (deterministic
    table, see ``spelling.py``).  Unknown words stay prose, so nothing the
    user really said is ever mangled.  Control characters inside the
    payload refuse the utterance (same contract as plain dictation).
    """

    payload = match.group("target").strip()
    if contains_control_characters(payload):
        return None
    return ActionRequest(
        "text.insert", target=normalise_spelling(payload)
    )


def _dictation_mode(mode: str) -> Builder:
    """Builder factory for a named dictation mode (e-mail, URL, number).

    The mode parser runs here, before the ``ActionRequest`` is built — the
    same place ``expand_punctuation`` runs for plain dictation.  An
    unparseable payload (REFUSED) must not surface as an exception, so the
    builder returns ``None`` and :meth:`OfflineRouter.route` declines the
    whole utterance (it falls through to the agent); the mode
    transformation only ever fires on its explicit trigger phrase, never
    mid-utterance, consistent with the sentence-end rule in
    ``punctuation.py``.
    """

    def build(match: Match[str]) -> Optional[ActionRequest]:
        rendered = apply_mode(mode, match.group("target").strip())
        if rendered is None:
            return None
        return ActionRequest("text.insert", target=rendered)

    return build


def _number_word(match: Match[str]) -> Optional[int]:
    """Numeric value of a router number group: digits or a spoken word.

    Reuses the dictation-mode number table (now including the German
    hundred/thousand compounds up to 999,999), so „Zeile 12" and „Zeile
    zwölf" both parse and every numbered command shares one number
    vocabulary.  A grammar-over-accepted nonsense token resolves to
    ``None`` — the caller must decline, never raise: a voice loop cannot
    crash on a malformed transcript.
    """

    from .dictation_modes import word_number

    return word_number(match.group("number"))


def _counted_caret_builder(direction: str) -> Builder:
    """Builder for „<n> <Einheit(en)> weiter/zurück" counted caret moves.

    The unit word decides which unit action fires; the adapter loops
    ``count`` times internally (one round trip, one spoken position), so
    the router never fires an action N times.
    """

    unit_actions = {
        "word": f"text.caret.word_{direction}",
        "line": f"text.caret.line_{direction}",
        "sentence": f"text.caret.sentence_{direction}",
        "paragraph": f"text.caret.paragraph_{direction}",
    }

    def build(match: Match[str]) -> Optional[ActionRequest]:
        count = _number_word(match)
        # The shared vocabulary reaches 999,999, but a counted move stays
        # capped at 1–99 steps (the policy validator enforces the same
        # bound); a larger spoken number declines the utterance so the
        # agent can explain instead of a cryptic policy denial.
        if count is None or not 1 <= count <= 99:
            return None
        unit = _COUNTED_UNIT_WORDS[match.group("unit").casefold()]
        return ActionRequest(unit_actions[unit], arguments={"count": count})

    return build


def _line_number_target(match: Match[str]) -> Optional[ActionRequest]:
    number = _number_word(match)
    # The shared vocabulary reaches 999,999, but a line jump stays capped
    # at 1–999 (the policy validator enforces the same bound); a larger
    # spoken number declines the utterance instead of guessing a line.
    if number is None or not 1 <= number <= 999:
        return None
    return ActionRequest("text.caret.line", target=str(number))


def _unit_caret(action: str) -> Builder:
    return lambda _: ActionRequest(action)


def _volume(match: Match[str]) -> ActionRequest:
    return ActionRequest(
        "audio.volume.set",
        arguments={"percent": int(match.group("percent"))},
    )


_SPOKEN_NUMBERS = {
    "eins": 1,
    "one": 1,
    "zwei": 2,
    "two": 2,
    "drei": 3,
    "three": 3,
    "vier": 4,
    "four": 4,
    "fünf": 5,
    "five": 5,
    "sechs": 6,
    "six": 6,
    "sieben": 7,
    "seven": 7,
    "acht": 8,
    "eight": 8,
    "neun": 9,
    "nine": 9,
    "zehn": 10,
    "ten": 10,
}


def _control_number(match: Match[str]) -> ActionRequest:
    value = match.group("number").casefold()
    number = int(value) if value.isdigit() else _SPOKEN_NUMBERS[value]
    return ActionRequest(
        "desktop.control.activate",
        target=str(number),
        risk=Risk.MEDIUM,
    )


def _file_number_command(action: str) -> Builder:
    def build(match: Match[str]) -> ActionRequest:
        value = match.group("number").casefold()
        number = int(value) if value.isdigit() else _SPOKEN_NUMBERS[value]
        return ActionRequest(action, target=str(number))

    return build


_GRANULARITY_WORDS = {
    "zeichen": "character",
    "character": "character",
    "wort": "word",
    "word": "word",
    "zeile": "line",
    "line": "line",
    "satz": "sentence",
    "sentence": "sentence",
    "absatz": "paragraph",
    "paragraph": "paragraph",
}

#: Unit words of the counted navigation patterns (singular and plural,
#: German and English) mapped to their unit name.
_COUNTED_UNIT_WORDS = {
    "wort": "word",
    "worts": "word",
    "wörter": "word",
    "word": "word",
    "words": "word",
    "zeile": "line",
    "zeilen": "line",
    "line": "line",
    "lines": "line",
    "satz": "sentence",
    "sätze": "sentence",
    "sentence": "sentence",
    "sentences": "sentence",
    "absatz": "paragraph",
    "absätze": "paragraph",
    "paragraph": "paragraph",
    "paragraphs": "paragraph",
}


def _read_granular(match: Match[str]) -> ActionRequest:
    granularity = _GRANULARITY_WORDS[match.group("unit").casefold()]
    return ActionRequest(
        "text.read_granular",
        arguments={"granularity": granularity},
    )


_file_select = _file_number_command("dialog.file.select")
_folder_open = _file_number_command("dialog.folder.open")

#: Number vocabulary shared by every counted navigation pattern: digits
#: (up to three) or a German/English number word from the dictation-mode
#: table — atoms plus the generated compounds, now including the hundreds
#: and "tausend" anchors.  Built from the dictation-mode table so the
#: router and the number dictation mode can never drift apart.
from .dictation_modes import _SPOKEN_NUMBERS as _DICTATION_NUMBER_WORDS  # noqa: E402

_NUMBER_ALTERNATION = "|".join(
    sorted(
        (re.escape(word) for word in _DICTATION_NUMBER_WORDS),
        key=len,
        reverse=True,
    )
)

#: German compound numbers up to 999,999 ("zweihundertfünfundzwanzig",
#: "dreihundertfünfundzwanzigtausend") are compositional — a table
#: alternation cannot enumerate them — so the router accepts the closed
#: grammar of spoken German ([…]tausend + hundert + 1–99) and the builders
#: resolve the value with ``word_number``, which shares the dictation-mode
#: parser and its honest 999,999 ceiling.  The grammar may over-accept
#: nonsense ("hunderttausendtausend"); the builder then declines the
#: utterance — never a crash, never a guess.
_COMPOUND_HUNDREDS = (
    r"(?:(?:ein|zwei|drei|vier|fünf|sechs|sieben|acht|neun)hundert"
    r"|hundert|einhundert)"
)
_COMPOUND_ONES = r"(?:ein|eins|zwei|drei|vier|fünf|sechs|sieben|acht|neun)"
_COMPOUND_TEENS = (
    r"(?:zehn|elf|zwölf|dreizehn|vierzehn|fünfzehn|sechzehn"
    r"|siebzehn|achtzehn|neunzehn)"
)
_COMPOUND_TENS = (
    r"(?:und(?:zwanzig|dreißig|dreissig|vierzig|fünfzig"
    r"|sechzig|siebzig|achtzig|neunzig))?"
)
_COMPOUND_ONES_99 = rf"(?:{_COMPOUND_TEENS}|{_COMPOUND_ONES}{_COMPOUND_TENS})"
_COMPOUND_GRAMMAR = (
    rf"(?:{_COMPOUND_HUNDREDS}?{_COMPOUND_ONES_99}?tausend)?"
    rf"(?:{_COMPOUND_HUNDREDS}{_COMPOUND_ONES_99}?"
    rf"|{_COMPOUND_HUNDREDS}?{_COMPOUND_ONES_99}?tausend)"
)
_NUMBER_GRAMMAR = rf"(?:{_NUMBER_ALTERNATION}|{_COMPOUND_GRAMMAR})"
_NUMBER_GROUP = rf"(?:\d{{1,3}}|{_NUMBER_GRAMMAR})"


def _rx(*values: str) -> Sequence[Pattern[str]]:
    return tuple(re.compile(rf"^(?:{value})[.!?]*$", re.IGNORECASE) for value in values)


COMMANDS: Sequence[CommandPattern] = (
    CommandPattern("stop", _rx(r"stopp (?:hermes|clausis)", r"(?:hermes|clausis) stopp", r"stop (?:hermes|clausis)"), _simple("voice.stop")),
    CommandPattern("where-am-i", _rx(r"wo bin ich", r"where am i"), _simple("desktop.context.describe")),
    CommandPattern("read-window", _rx(r"lies (?:das )?fenster vor", r"read (?:the )?window"), _simple("desktop.context.describe")),
    CommandPattern("available-controls", _rx(r"was kann ich hier tun", r"was kann ich tun", r"what can i do here"), _simple("desktop.controls.list")),
    CommandPattern(
        "activate-number",
        _rx(
            r"(?:nummer )?(?P<number>\d{1,2}|eins|zwei|drei|vier|fünf|sechs|sieben|acht|neun|zehn)",
            r"(?:number )?(?P<number>\d{1,2}|one|two|three|four|five|six|seven|eight|nine|ten)",
        ),
        _control_number,
    ),
    CommandPattern("back", _rx(r"zurück", r"go back", r"back"), _simple("desktop.navigate.back")),
    CommandPattern("repeat", _rx(r"wiederholen", r"wiederhole das", r"repeat"), _simple("voice.repeat")),
    CommandPattern("cancel", _rx(r"abbrechen", r"cancel"), _simple("voice.cancel")),
    CommandPattern("correct", _rx(r"korrigieren", r"correct that"), _simple("voice.correct")),
    CommandPattern(
        "describe-dialog",
        _rx(r"was fragt (?:mich )?der dialog", r"dialog vorlesen", r"read (?:the )?dialog"),
        _simple("dialog.describe"),
    ),
    CommandPattern("accept-dialog", _rx(r"dialog bestätigen", r"confirm (?:the )?dialog"), _simple("dialog.accept", Risk.MEDIUM)),
    CommandPattern("cancel-dialog", _rx(r"dialog abbrechen", r"dialog schließen", r"cancel (?:the )?dialog"), _simple("dialog.cancel")),
    CommandPattern("clipboard-read", _rx(r"was (?:ist|steht) in der zwischenablage", r"zwischenablage vorlesen", r"read (?:the )?clipboard"), _simple("clipboard.read")),
    CommandPattern("clipboard-copy", _rx(r"kopieren", r"copy(?: that)?"), _simple("clipboard.copy")),
    CommandPattern("clipboard-paste", _rx(r"einfügen", r"paste"), _simple("clipboard.paste")),
    CommandPattern("keyboard-on", _rx(r"bildschirmtastatur an", r"(?:screen|on-screen) keyboard on"), _simple("a11y.keyboard.enable")),
    CommandPattern("keyboard-off", _rx(r"bildschirmtastatur aus", r"(?:screen|on-screen) keyboard off"), _simple("a11y.keyboard.disable")),
    CommandPattern("magnifier-on", _rx(r"(?:bildschirm)?lupe an", r"magnifier on"), _simple("a11y.magnifier.enable")),
    CommandPattern("magnifier-off", _rx(r"(?:bildschirm)?lupe aus", r"magnifier off"), _simple("a11y.magnifier.disable")),
    CommandPattern("screenreader-on", _rx(r"(?:orca|bildschirmleser|screenreader) an", r"screen reader on"), _simple("a11y.screenreader.enable")),
    CommandPattern("screenreader-off", _rx(r"(?:orca|bildschirmleser|screenreader) aus", r"screen reader off"), _simple("a11y.screenreader.disable")),
    CommandPattern("read-field", _rx(r"lies (?:das )?feld vor", r"was steht im feld", r"read (?:the )?field"), _simple("text.read")),
    CommandPattern("delete-word", _rx(r"(?:letztes )?wort löschen", r"delete (?:the )?(?:last )?word"), _simple("text.delete_word")),
    CommandPattern("clear-field", _rx(r"feld leeren", r"clear (?:the )?field"), _simple("text.clear", Risk.MEDIUM)),
    CommandPattern("caret-start", _rx(r"cursor an den anfang", r"caret to (?:the )?start", r"(?:move )?cursor to (?:the )?beginning"), _simple("text.caret.start")),
    CommandPattern("caret-end", _rx(r"cursor ans ende", r"caret to (?:the )?end", r"(?:move )?cursor to (?:the )?end"), _simple("text.caret.end")),
    # Counted unit navigation must sit BEFORE the plain single-step patterns:
    # "drei wörter zurück" would otherwise fall through to "wort zurück"
    # only after failing the dictation verbs, and "ein wort weiter" must
    # keep working through the single-step pattern as well.
    CommandPattern(
        "caret-counted-next",
        _rx(
            rf"(?P<number>{_NUMBER_GROUP}) (?P<unit>wörter|worts?|zeilen|sätze|absätze) weiter",
            rf"(?P<number>{_NUMBER_GROUP}) (?P<unit>words?|lines|sentences|paragraphs) (?:forward|ahead|next)",
        ),
        _counted_caret_builder("next"),
    ),
    CommandPattern(
        "caret-counted-previous",
        _rx(
            rf"(?P<number>{_NUMBER_GROUP}) (?P<unit>wörter|worts?|zeilen|sätze|absätze) zurück",
            rf"(?P<number>{_NUMBER_GROUP}) (?P<unit>words?|lines|sentences|paragraphs) back",
        ),
        _counted_caret_builder("previous"),
    ),
    CommandPattern(
        "caret-unit-next",
        _rx(
            r"(?:nächstes wort|wort weiter|cursor wort weiter)",
            r"next word",
        ),
        _unit_caret("text.caret.word_next"),
    ),
    CommandPattern(
        "caret-unit-previous",
        _rx(
            r"(?:vorheriges wort|wort zurück|cursor wort zurück)",
            r"previous word",
        ),
        _unit_caret("text.caret.word_previous"),
    ),
    CommandPattern(
        "caret-line-next",
        _rx(r"(?:nächste zeile|zeile weiter|cursor zeile weiter)", r"next line"),
        _unit_caret("text.caret.line_next"),
    ),
    CommandPattern(
        "caret-line-previous",
        _rx(r"(?:vorherige zeile|zeile zurück|cursor zeile zurück)", r"previous line"),
        _unit_caret("text.caret.line_previous"),
    ),
    CommandPattern(
        "caret-sentence-next",
        _rx(r"(?:nächster satz|satz weiter|cursor satz weiter)", r"next sentence"),
        _unit_caret("text.caret.sentence_next"),
    ),
    CommandPattern(
        "caret-sentence-previous",
        _rx(r"(?:vorheriger satz|satz zurück|cursor satz zurück)", r"previous sentence"),
        _unit_caret("text.caret.sentence_previous"),
    ),
    CommandPattern(
        "caret-paragraph-next",
        _rx(r"(?:nächster absatz|absatz weiter|cursor absatz weiter)", r"next paragraph"),
        _unit_caret("text.caret.paragraph_next"),
    ),
    CommandPattern(
        "caret-paragraph-previous",
        _rx(r"(?:vorheriger absatz|absatz zurück|cursor absatz zurück)", r"previous paragraph"),
        _unit_caret("text.caret.paragraph_previous"),
    ),
    CommandPattern(
        "caret-line-number",
        _rx(
            rf"zeile (?P<number>{_NUMBER_GROUP})",
            rf"(?:go to |jump to )?line (?P<number>{_NUMBER_GROUP})",
        ),
        _line_number_target,
    ),
    CommandPattern("caret-next-word", _rx(r"cursor (?:ein )?wort weiter", r"next word"), _simple("text.caret.word_next")),
    CommandPattern("caret-previous-word", _rx(r"cursor (?:ein )?wort zurück", r"previous word"), _simple("text.caret.word_previous")),
    CommandPattern("read-from-caret", _rx(r"lies ab dem cursor(?: vor)?", r"read from (?:the )?caret"), _simple("text.read_from_caret")),
    # Say-all: one command starts the chunked background read; "stopp"
    # (bare, no Hermes/Clausis) cancels it; "lies weiter" resumes.
    CommandPattern(
        "read-all",
        _rx(r"lies (?:alles|das ganze|das dokument)(?: vor)?", r"read (?:everything|it all|the whole (?:field|document))(?: aloud)?", r"say all"),
        _simple("text.read_all"),
    ),
    CommandPattern(
        "read-all-stop",
        _rx(r"stopp", r"stop(?: reading)?", r"halt(?: reading)?"),
        _simple("text.read_all.stop"),
    ),
    CommandPattern(
        "read-all-resume",
        _rx(r"lies weiter", r"(?:keep |continue )?reading", r"resume reading"),
        _simple("text.read_all.resume"),
    ),
    # A line break cannot ride inside a dictated target: the request schema
    # forbids control characters so nothing smuggles one across a trust
    # boundary.  The adapter therefore synthesizes the newline itself and the
    # spoken command becomes its own low-risk action.
    CommandPattern("newline", _rx(r"neue zeile", r"new line"), _simple("text.newline")),
    CommandPattern("paragraph", _rx(r"absatz", r"new paragraph"), _simple("text.paragraph")),
    CommandPattern("select-word", _rx(r"markiere(?: das)? wort", r"select (?:the )?word"), _simple("text.select_word")),
    CommandPattern(
        "select-sentence",
        _rx(r"markiere(?: den)? satz", r"select (?:the )?sentence"),
        _simple("text.select_sentence"),
    ),
    CommandPattern(
        "select-all",
        _rx(r"alles markieren", r"markiere alles", r"select all"),
        _simple("text.select_all"),
    ),
    CommandPattern(
        "replace-selection",
        _rx(r"ersetze (?:die )?auswahl (?:durch|mit) (?P<target>.+)", r"replace (?:the )?selection (?:with|by) (?P<target>.+)"),
        _target("text.replace_selection"),
    ),
    CommandPattern(
        "delete-selection",
        _rx(r"lösche (?:die )?auswahl", r"delete (?:the )?selection"),
        _simple("text.delete_selection"),
    ),
    CommandPattern("undo", _rx(r"rückgängig", r"mach rückgängig", r"undo"), _simple("text.undo")),
    CommandPattern("redo", _rx(r"wiederherstellen", r"mach wiederherstellen", r"redo"), _simple("text.redo")),
    CommandPattern(
        "read-granular",
        _rx(
            r"lies (?:(?:das|den|die|der) )?(?:aktuelle[nr]? )?(?P<unit>zeichen|wort|zeile|satz|absatz)(?: ab dem cursor| am cursor)?(?: vor)?",
            r"read (?:the )?(?:current )?(?P<unit>character|word|line|sentence|paragraph)(?: from (?:the )?caret)?(?: aloud)?",
        ),
        _read_granular,
    ),
    CommandPattern(
        "file-list",
        _rx(
            r"liste dateien auf",
            r"was (?:ist |steht )?im dateidialog",
            r"welche dateien gibt es",
            r"zeige die dateien",
            r"list files",
            r"what(?:'s| is) in the file dialog",
        ),
        _simple("dialog.file.list"),
    ),
    CommandPattern(
        "file-select",
        _rx(r"wähle datei (?P<number>\d{1,2}|eins|zwei|drei|vier|fünf|sechs|sieben|acht|neun|zehn)", r"select file (?P<number>\d{1,2}|one|two|three|four|five|six|seven|eight|nine|ten)"),
        _file_select,
    ),
    CommandPattern(
        "folder-open",
        _rx(r"öffne ordner (?P<number>\d{1,2}|eins|zwei|drei|vier|fünf|sechs|sieben|acht|neun|zehn)", r"open folder (?P<number>\d{1,2}|one|two|three|four|five|six|seven|eight|nine|ten)"),
        _folder_open,
    ),
    # Dictation modes: the user names the mode, and only then do "punkt",
    # "at", "slash" etc. become characters.  The transformation never runs
    # mid-utterance — consistent with the sentence-end rule of plain
    # dictation — and the mode patterns must sit BEFORE the plain
    # "diktiere/tippe …" family so the trigger phrase wins.
    CommandPattern(
        "dictate-email",
        _rx(
            r"diktiere e-?mail (?P<target>.+)",
            r"dictate e-?mail (?P<target>.+)",
        ),
        _dictation_mode("email"),
    ),
    CommandPattern(
        "dictate-url",
        _rx(
            r"diktiere (?:url|adresse) (?P<target>.+)",
            r"dictate (?:url|address) (?P<target>.+)",
        ),
        _dictation_mode("url"),
    ),
    CommandPattern(
        "dictate-number",
        _rx(
            r"diktiere zahl (?P<target>.+)",
            r"diktiere nummer (?P<target>.+)",
            r"dictate (?:number|num) (?P<target>.+)",
        ),
        _dictation_mode("number"),
    ),
    CommandPattern(
        "dictate-date",
        _rx(
            r"diktiere datum (?P<target>.+)",
            r"dictate (?:date|the date) (?P<target>.+)",
        ),
        _dictation_mode("date"),
    ),
    CommandPattern(
        "dictate-time",
        _rx(
            r"diktiere uhrzeit (?P<target>.+)",
            r"dictate (?:time|the time) (?P<target>.+)",
        ),
        _dictation_mode("time"),
    ),
    CommandPattern(
        "dictate-path",
        _rx(
            r"diktiere pfad (?P<target>.+)",
            r"dictate (?:path|file path) (?P<target>.+)",
        ),
        _dictation_mode("path"),
    ),
    # Correction slot: "nein, ich meinte <text>" replaces the last dictation
    # in the focused field instead of appending a new one.  The pattern must
    # sit BEFORE every dictation verb — "nein, ich meinte diktiere foo" would
    # otherwise fall through to plain dictation and append the very text the
    # user is trying to correct.  The adapter owns the memory and refuses
    # honestly when nothing was dictated; the router only carries the payload
    # with the same printable-only dictation contract.
    CommandPattern(
        "dictation-correct",
        _rx(
            r"nein,? ich meinte?:? (?P<target>.+)",
            r"no,? i meant:? (?P<target>.+)",
        ),
        _dictation_replacement,
    ),
    # "Schreibe mir ein Gedicht" is a request to the agent, not dictation, so
    # the dictation verbs stay unambiguous and an ambiguous "schreibe …" keeps
    # falling through to Hermes.
    CommandPattern(
        "dictate",
        _rx(
            r"(?:diktiere|tippe) (?P<target>.+)",
            r"schreib(?:e)? ins feld (?P<target>.+)",
            r"(?:dictate|type) (?P<target>.+)",
        ),
        _dictation,
    ),
    # Spelling mode is its own dictation verb: "buchstabiere …" is never
    # ordinary prose dictation, and its characters reach the field named,
    # not spoken.
    CommandPattern(
        "spell",
        _rx(
            r"buchstabier(?:e|en)? (?P<target>.+)",
            r"spelling (?P<target>.+)",
            r"spell (?P<target>.+)",
        ),
        _spelling,
    ),
    CommandPattern("launch", _rx(r"(?:öffne|starte) (?P<target>[\w.+@:-]+)", r"(?:open|launch) (?P<target>[\w.+@:-]+)"), _target("app.launch")),
    CommandPattern("close", _rx(r"schließe (?P<target>[\w.+@:-]+)", r"close (?P<target>[\w.+@:-]+)"), _target("app.close", Risk.MEDIUM)),
    CommandPattern("settings", _rx(r"öffne (?:die )?einstellungen", r"open settings"), _simple("desktop.settings.open")),
    CommandPattern("overview", _rx(r"zeige (?:die )?übersicht", r"show overview"), _simple("desktop.overview")),
    CommandPattern("applications", _rx(r"zeige (?:die )?anwendungen", r"show applications"), _simple("desktop.applications")),
    CommandPattern("quick-settings", _rx(r"(?:zeige (?:die )?)?schnelleinstellungen", r"(?:show )?quick settings"), _simple("desktop.quick_settings")),
    CommandPattern("notifications", _rx(r"(?:zeige (?:die )?)?benachrichtigungen", r"(?:show )?notifications"), _simple("desktop.notifications")),
    CommandPattern("minimize", _rx(r"fenster minimieren", r"minimize (?:the )?window"), _simple("desktop.window.minimize")),
    CommandPattern("maximize", _rx(r"fenster maximieren", r"maximize (?:the )?window"), _simple("desktop.window.maximize")),
    CommandPattern("unmaximize", _rx(r"fenster wiederherstellen", r"(?:restore|unmaximize) (?:the )?window"), _simple("desktop.window.unmaximize")),
    CommandPattern(
        "window-to-next-workspace",
        _rx(r"fenster (?:auf|zur) nächste[nr]? arbeitsfläche", r"move (?:the )?window to (?:the )?next workspace"),
        _simple("desktop.window.to_next_workspace"),
    ),
    CommandPattern(
        "window-to-previous-workspace",
        _rx(r"fenster (?:auf|zur) vorherige[nr]? arbeitsfläche", r"move (?:the )?window to (?:the )?previous workspace"),
        _simple("desktop.window.to_previous_workspace"),
    ),
    CommandPattern("next-workspace", _rx(r"nächste arbeitsfläche", r"next workspace"), _simple("desktop.workspace.next")),
    CommandPattern("previous-workspace", _rx(r"vorherige arbeitsfläche", r"previous workspace"), _simple("desktop.workspace.previous")),
    CommandPattern("next-window", _rx(r"nächstes fenster", r"next window"), _simple("desktop.window.next")),
    CommandPattern("previous-window", _rx(r"vorheriges fenster", r"previous window"), _simple("desktop.window.previous")),
    CommandPattern("volume-up", _rx(r"lauter", r"volume up"), _simple("audio.volume.up")),
    CommandPattern("volume-down", _rx(r"leiser", r"volume down"), _simple("audio.volume.down")),
    CommandPattern("mute", _rx(r"ton (?:aus|stumm)", r"mute"), _simple("audio.mute.toggle")),
    CommandPattern("volume-set", _rx(r"lautstärke (?P<percent>\d{1,3})(?: prozent)?", r"volume (?P<percent>\d{1,3})(?: percent)?"), _volume),
    CommandPattern("speech-faster", _rx(r"sprich schneller", r"speak faster", r"faster speech"), _simple("speech.rate.faster")),
    CommandPattern("speech-slower", _rx(r"sprich langsamer", r"speak slower", r"slower speech"), _simple("speech.rate.slower")),
    CommandPattern("speech-normal", _rx(r"sprechgeschwindigkeit normal", r"normal speech rate", r"normal speaking rate"), _simple("speech.rate.normal")),
    CommandPattern("speech-german", _rx(r"antworte auf deutsch", r"sprich deutsch", r"speak german"), _simple("speech.language.german")),
    CommandPattern("speech-english", _rx(r"antworte auf englisch", r"sprich englisch", r"speak english"), _simple("speech.language.english")),
    CommandPattern("network-status", _rx(r"netzwerkstatus", r"network status"), _simple("network.status")),
    CommandPattern("wifi-on", _rx(r"wlan an", r"wifi on"), _simple("network.wifi.enable", Risk.MEDIUM)),
    CommandPattern("wifi-off", _rx(r"wlan aus", r"wifi off"), _simple("network.wifi.disable", Risk.MEDIUM)),
    CommandPattern("report", _rx(r"(?:erstelle |mach )?(?:einen )?fehlerbericht", r"diagnosebericht", r"create (?:a )?report"), _simple("system.report")),
    CommandPattern("system-status", _rx(r"systemstatus", r"system status"), _simple("system.status")),
    CommandPattern("lock", _rx(r"bildschirm sperren", r"lock (?:the )?screen"), _simple("system.lock")),
    CommandPattern("logout", _rx(r"abmelden", r"log ?out"), _simple("system.logout", Risk.HIGH)),
    CommandPattern("reboot", _rx(r"(?:computer|rechner) neu starten", r"reboot (?:the )?(?:computer|system)?"), _simple("system.reboot", Risk.CRITICAL, False)),
    CommandPattern("poweroff", _rx(r"(?:computer|rechner) ausschalten", r"(?:power off|shut down)(?: the computer)?"), _simple("system.poweroff", Risk.CRITICAL, False)),
    CommandPattern("file-open", _rx(r"öffne datei (?P<target>/[^\x00]+)", r"open file (?P<target>/[^\x00]+)"), _target("file.open")),
    CommandPattern("file-search", _rx(r"suche datei (?P<target>.+)", r"find file (?P<target>.+)"), _target("file.search")),
    CommandPattern("trash", _rx(r"verschiebe datei (?P<target>/[^\x00]+) in den papierkorb", r"move file (?P<target>/[^\x00]+) to trash"), _target("file.move_to_trash", Risk.HIGH)),
    CommandPattern("update-check", _rx(r"suche nach updates", r"check for updates"), _simple("update.check")),
    CommandPattern("security-updates", _rx(r"installiere sicherheitsupdates", r"install security updates"), _simple("update.install_security", Risk.HIGH)),
)


class OfflineRouter:
    def __init__(self, commands: Sequence[CommandPattern] = COMMANDS) -> None:
        self._commands = commands

    def route(self, transcript: str) -> Optional[ActionRequest]:
        normalized = " ".join(transcript.strip().split())
        if not normalized or len(normalized) > 1024:
            return None
        for command in self._commands:
            for pattern in command.patterns:
                match = pattern.fullmatch(normalized)
                if match:
                    request = command.builder(match)
                    if request is None:
                        # A dictation mode refused its payload (unparsable,
                        # empty or oversized).  Honest refusal: no local
                        # action at all — the utterance falls through to the
                        # agent, which can explain what was not parseable.
                        # (Falling through to the plain dictation pattern
                        # would insert the mode words as prose, which is
                        # exactly what the user did NOT say.)
                        return None
                    if request.action == "voice.stop":
                        return request
                    return ActionRequest(
                        action=request.action,
                        target=request.target,
                        arguments=request.arguments,
                        origin=Origin.LOCAL_VOICE,
                        risk=request.risk,
                        reversible=request.reversible,
                    )
        return None
