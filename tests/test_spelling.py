"""Tests for the spelling mode: spoken letter names become characters.

Covers the pure normalisation, the router integration and the end-to-end
path router → broker → fake editable field.
"""

from dataclasses import replace
import sys
import types
import unittest

from clausis.broker import ActionBroker, SafeExecutor
from clausis.capabilities import CapabilityAuthority
from clausis.executors import SessionExecutor
from clausis.gnome_adapter import GnomeSemanticExecutor
from clausis.policy import ACTION_POLICIES
from clausis.spelling import normalise_spelling


class NormalisationTests(unittest.TestCase):
    def test_spelled_utterance_becomes_characters(self):
        for spoken, expected in [
            ("A wie Anton, N wie Nordpol", "AN"),
            ("A wie Anton N wie Nordpol", "AN"),
            ("Anton Berta Caesar Dora", "ABCD"),
            ("a as in alfa", "A"),
            ("x wie x-ray", "X"),
            ("K wie Kaufmann drei", "K3"),
            ("null null sieben", "007"),
        ]:
            with self.subTest(spoken=spoken):
                self.assertEqual(normalise_spelling(spoken), expected)

    def test_helper_word_corrects_a_misrecognised_anchor(self):
        # The helper is unambiguous prose; a wrong anchor letter yields.
        self.assertEqual(normalise_spelling("I wie Ida, D wie Dora"), "ID")

    def test_case_of_a_spoken_lone_letter_is_kept(self):
        self.assertEqual(normalise_spelling("A b C"), "AbC")

    def test_german_umlauts_and_sz(self):
        self.assertEqual(normalise_spelling("Ä wie Schäfer"), "Ä")
        self.assertEqual(normalise_spelling("ß wie eszett"), "ß")

    def test_unknown_words_stay_prose(self):
        self.assertEqual(normalise_spelling("Müller"), "Müller")
        # An unknown helper keeps the whole "wie" construction as prose.
        self.assertEqual(normalise_spelling("F wie Fahrenheit"), "F wie Fahrenheit")

    def test_prose_around_character_runs_stays_separated(self):
        # "Hendrik" cannot be proven to be a spelling item, so it stays
        # whole and the runs around it keep their spaces.
        self.assertEqual(normalise_spelling("Anton Berta Müller Caesar Dora"), "AB Müller CD")

    def test_connective_without_helper_stays_prose(self):
        self.assertEqual(normalise_spelling("wie bitte"), "wie bitte")

    def test_empty_input_is_returned_unchanged(self):
        self.assertEqual(normalise_spelling("  "), "  ")


class RoutingTests(unittest.TestCase):
    def setUp(self):
        from clausis.router import OfflineRouter

        self.router = OfflineRouter()

    def test_spelling_command_routes_to_dictation_action(self):
        request = self.router.route("buchstabiere A wie Anton, N wie Nordpol")
        self.assertIsNotNone(request)
        self.assertEqual(request.action, "text.insert")
        self.assertEqual(request.target, "AN")
        self.assertEqual(request.risk, ACTION_POLICIES["text.insert"].minimum_risk)

    def test_german_inflected_verb_and_english_match_too(self):
        for transcript, target in [
            ("buchstabieren Anton Berta", "AB"),
            ("spell alfa bravo", "AB"),
            ("spelling A as in alfa", "A"),
        ]:
            with self.subTest(transcript=transcript):
                request = self.router.route(transcript)
                self.assertIsNotNone(request)
                self.assertEqual(request.action, "text.insert")
                self.assertEqual(request.target, target)

    def test_ordinary_dictation_is_untouched(self):
        request = self.router.route("diktiere Milch und Brot kaufen")
        self.assertEqual(request.target, "Milch und Brot kaufen")

    def test_ambiguous_writing_still_falls_through(self):
        self.assertIsNone(self.router.route("Schreibe mir ein Gedicht"))


# ---------------------------------------------------------------------------
# End-to-end: router → broker → fake AT-SPI editable field.
# ---------------------------------------------------------------------------

STATE_FOCUSED = "focused"
STATE_SHOWING = "showing"
STATE_ACTIVE = "active"
STATE_EDITABLE = "editable"
STATE_PROTECTED = "protected"


def fake_pyatspi(desktop):
    module = types.SimpleNamespace(
        STATE_FOCUSED=STATE_FOCUSED,
        STATE_SHOWING=STATE_SHOWING,
        STATE_ACTIVE=STATE_ACTIVE,
        STATE_EDITABLE=STATE_EDITABLE,
        STATE_PROTECTED=STATE_PROTECTED,
        Registry=types.SimpleNamespace(getDesktop=lambda index: desktop),
    )
    return module


class FakeState:
    def __init__(self, states):
        self._states = set(states)

    def contains(self, state):
        return state in self._states


class FakeEditableText:
    def __init__(self, node):
        self.node = node

    def insertText(self, offset, text, length):
        content = self.node.content
        self.node.content = content[:offset] + text + content[offset:]
        return True


class FakeText:
    def __init__(self, node):
        self.node = node

    @property
    def characterCount(self):
        return len(self.node.content)

    @property
    def caretOffset(self):
        return len(self.node.content)

    def getText(self, start, end):
        return self.node.content[start:end]


class FakeComponent:
    def __init__(self, node):
        self.node = node

    def grabFocus(self):
        self.node.focused = True
        return True


class FakeNode:
    def __init__(self, name="", role="", states=(), children=(), content=""):
        self.name = name
        self.role = role
        self.states = set(states)
        self.children = list(children)
        self.content = content
        self.focused = False
        self.parent = None
        for child in self.children:
            child.parent = self

    def getRoleName(self):
        return self.role

    def getState(self):
        return FakeState(self.states)

    @property
    def childCount(self):
        return len(self.children)

    def getChildAtIndex(self, index):
        return self.children[index]

    def queryText(self):
        return FakeText(self)

    def queryComponent(self):
        return FakeComponent(self)

    def queryEditableText(self):
        return FakeEditableText(self)

    def queryAction(self):
        raise RuntimeError("no action interface")


class SpellingEndToEndTests(unittest.TestCase):
    def setUp(self):
        from clausis.router import OfflineRouter

        self.router = OfflineRouter()
        self.authority = CapabilityAuthority(b"s" * 32)

    def _desktop(self, root):
        import clausis.gnome_adapter as adapter

        original = sys.modules.get("pyatspi")
        sys.modules["pyatspi"] = fake_pyatspi(root)
        self.addCleanup(
            lambda: sys.modules.__setitem__("pyatspi", original)
            if original is not None
            else sys.modules.pop("pyatspi", None)
        )
        return adapter.PyAtSpiDesktop()

    def _broker(self, root):
        return ActionBroker(
            self.authority,
            SessionExecutor(SafeExecutor(dry_run=False), GnomeSemanticExecutor(self._desktop(root))),
        )

    @staticmethod
    def _root(field):
        window = FakeNode("Notizen", "frame", {STATE_SHOWING, STATE_ACTIVE}, [field])
        application = FakeNode("Texteditor", "application", set(), [window])
        return FakeNode("desktop", "desktop frame", set(), [application])

    def test_spelled_name_reaches_the_field_as_characters(self):
        field = FakeNode(
            "Name",
            "entry",
            {STATE_FOCUSED, STATE_SHOWING, STATE_EDITABLE},
            content="",
        )
        broker = self._broker(self._root(field))
        request = self.router.route("buchstabiere A wie Anton, N wie Nordpol")
        self.assertEqual(request.action, "text.insert")
        result = broker.submit(request)
        self.assertEqual(result.status, "completed", result.message)
        self.assertEqual(field.content, "AN")
        self.assertIn("AN", result.message)

    def test_spelled_digits_reach_the_field(self):
        field = FakeNode(
            "PIN",
            "entry",
            {STATE_FOCUSED, STATE_SHOWING, STATE_EDITABLE},
            content="",
        )
        broker = self._broker(self._root(field))
        request = self.router.route("buchstabiere null null sieben")
        result = broker.submit(request)
        self.assertEqual(result.status, "completed", result.message)
        self.assertEqual(field.content, "007")


if __name__ == "__main__":
    unittest.main()
