"""Unit tests for counted caret navigation and say-all, on a fake tree.

These encode the Stage-2 design decisions from the task card: the counted
navigation loops adapter-side (one round trip, one spoken position, honest
clamping at the edges), line numbers clamp instead of erroring, and the
say-all reader runs chunk by chunk in the background with a character-offset
bookmark that survives pause/resume and dies on navigation.

They complement ``test_caret_navigation.py`` (single steps) and the real
GTK session smoke test (live widgets, real bus).
"""

from __future__ import annotations

import threading
import time
import unittest

from clausis.gnome_adapter import GnomeAdapterError, PyAtSpiDesktop
from clausis.router import OfflineRouter

from tests.test_dictation import (
    STATE_EDITABLE,
    STATE_FOCUSED,
    STATE_SHOWING,
    DesktopHarness,
    FakeNode,
    build_desktop,
)


def field(content="", caret=None, **kwargs):
    return FakeNode(
        "Notiz",
        "text",
        {STATE_SHOWING, STATE_FOCUSED, STATE_EDITABLE},
        content=content,
        caret=caret,
        **kwargs,
    )


MULTILINE = (
    "Erste Zeile des Dokuments.\n"
    "Zweite Zeile folgt.\n"
    "\n"
    "Neuer Absatz beginnt hier.\n"
    "Noch eine Zeile mit Inhalt.\n"
    "\n"
    "Letzter Absatz."
)


class CountedNavigationTests(DesktopHarness):
    def test_three_words_forward_in_one_command(self):
        node = field("eins zwei drei vier", caret=0)
        desktop = self.desktop_for(build_desktop(node))
        spoken = desktop.move_caret("word_next", 3)
        self.assertEqual(node.caret, 15)  # start of "vier": steps land at unit starts
        self.assertIn("Position 15", spoken)

    def test_three_words_back_clamps_at_start_with_honest_report(self):
        node = field("eins zwei drei", caret=10)
        desktop = self.desktop_for(build_desktop(node))
        spoken = desktop.move_caret("word_previous", 3)
        self.assertEqual(node.caret, 0)
        self.assertIn("Anfang erreicht", spoken)

    def test_count_is_validated(self):
        desktop = self.desktop_for(build_desktop(field("Text")))
        for bad in (0, -1, 100, "zwei", True):
            with self.subTest(bad=bad):
                with self.assertRaises(GnomeAdapterError):
                    desktop.move_caret("word_next", bad)

    def test_two_lines_back_in_one_command(self):
        node = field(MULTILINE, caret=52)  # start of "Neuer Absatz"
        desktop = self.desktop_for(build_desktop(node))
        spoken = desktop.move_caret("line_previous", 2)
        self.assertEqual(node.caret, 27)  # start of line 2
        self.assertIn("Position 27", spoken)

    def test_paragraph_next_jumps_over_blank_line(self):
        node = field(MULTILINE, caret=0)
        desktop = self.desktop_for(build_desktop(node))
        desktop.move_caret("paragraph_next")
        self.assertEqual(node.caret, 48)  # start of line 4 "Neuer Absatz"
        desktop.move_caret("paragraph_next")
        self.assertEqual(node.caret, 104)  # start of line 7 "Letzter Absatz."


class LineJumpTests(DesktopHarness):
    def test_line_number_jumps_to_line_start(self):
        node = field(MULTILINE, caret=0)
        desktop = self.desktop_for(build_desktop(node))
        spoken = desktop.move_caret_to_line(4)
        self.assertEqual(node.caret, 48)
        self.assertIn("Zeile 4", spoken)

    def test_line_number_past_the_end_clamps_honestly(self):
        node = field(MULTILINE, caret=0)
        desktop = self.desktop_for(build_desktop(node))
        spoken = desktop.move_caret_to_line(12)
        self.assertEqual(node.caret, 104)  # first character of line 7
        self.assertIn("nur 7", spoken)
        self.assertIn("Zeile 7", spoken)

    def test_line_number_is_validated(self):
        desktop = self.desktop_for(build_desktop(field(MULTILINE)))
        for bad in (0, -3, 1000, "3", None, False):
            with self.subTest(bad=bad):
                with self.assertRaises(GnomeAdapterError):
                    desktop.move_caret_to_line(bad)


class SayAllChunkTests(DesktopHarness):
    def test_every_sentence_is_a_chunk_blank_lines_are_not(self):
        node = field(MULTILINE)
        desktop = self.desktop_for(build_desktop(node))
        spans = desktop._say_all_chunks(node, 0)
        spoken = [MULTILINE[s:e].strip() for s, e in spans]
        self.assertEqual(
            spoken,
            [
                "Erste Zeile des Dokuments.",
                "Zweite Zeile folgt.",
                "Neuer Absatz beginnt hier.",
                "Noch eine Zeile mit Inhalt.",
                "Letzter Absatz.",
            ],
        )

    def test_resume_at_offset_skips_earlier_sentences(self):
        node = field(MULTILINE)
        desktop = self.desktop_for(build_desktop(node))
        spans = desktop._say_all_chunks(node, 46)  # after sentence 2
        first = spans[0]
        self.assertEqual(MULTILINE[first[0]:first[1]].strip(), "Neuer Absatz beginnt hier.")

    def test_empty_field_has_no_chunks(self):
        node = field("")
        desktop = self.desktop_for(build_desktop(node))
        self.assertEqual(desktop._say_all_chunks(node, 0), [])


class _FakeUtterance:
    def __init__(self, gate: threading.Event):
        self._gate = gate

    def wait(self, timeout=None):
        return self._gate.wait(timeout)


class _BlockingSpeaker:
    """Speaker whose chunks block until released — like real playback.

    ``block_from`` makes every chunk from that one-based index onward block
    on a shared gate until ``release()``/``cancel()`` sets it, so a test can
    let the first chunks complete and cancel the run *mid-chunk* exactly
    like a user interrupting playback.
    """

    def __init__(self, block_from: int = 1):
        self.gate = threading.Event()
        self.spoken = []
        self.cancel_calls = 0
        self._calls = 0
        self._block_from = block_from

    def speak_async(self, text, language="de"):
        self._calls += 1
        self.spoken.append(text)
        if self._calls >= self._block_from:
            return _FakeUtterance(self.gate)
        completed = threading.Event()
        completed.set()
        return _FakeUtterance(completed)

    def cancel(self):
        self.cancel_calls += 1
        self.gate.set()

    def release(self):
        self.gate.set()


class SayAllReaderTests(unittest.TestCase):
    def _reader(self, speaker, spans):
        from clausis.say_all import SayAllReader

        progress = []
        reader = SayAllReader(
            chunks=lambda: spans,
            speak_chunk=lambda span: speaker.speak_async("x"),
            cancel_speech=speaker.cancel,
            on_progress=progress.append,
        )
        return reader, progress

    def test_reads_all_chunks_and_reports_field_end(self):
        speaker = _BlockingSpeaker(block_from=1)
        reader, progress = self._reader(speaker, [(0, 5), (5, 10), (10, 15)])
        thread = threading.Thread(target=reader._run)
        thread.start()
        speaker.release()
        reader.wait(timeout=5)
        thread.join(timeout=5)
        self.assertEqual(progress, [5, 10, 15, None])
        self.assertTrue(reader.finished_field)
        self.assertEqual(reader.bookmark, 15)

    def test_stop_mid_chunk_keeps_last_completed_bookmark(self):
        # Chunk 1 completes instantly; chunk 2 blocks like real playback the
        # user interrupts with „stopp".
        speaker = _BlockingSpeaker(block_from=2)
        reader, progress = self._reader(speaker, [(0, 5), (5, 10), (10, 15)])
        thread = threading.Thread(target=reader._run)
        thread.start()
        time.sleep(0.1)  # chunk 1 done, worker blocked inside chunk 2's wait()
        reader.stop()  # the user says „stopp" mid-chunk
        reader.wait(timeout=5)
        thread.join(timeout=5)
        # Chunk (0,5) finished before the cancel; nothing after may count.
        self.assertEqual(reader.bookmark, 5)
        self.assertFalse(reader.finished_field)
        self.assertEqual(speaker.cancel_calls, 1)

    def test_start_runs_in_background_thread(self):
        speaker = _BlockingSpeaker(block_from=1)
        reader, progress = self._reader(speaker, [(0, 5)])
        reader.start()
        speaker.release()
        self.assertTrue(reader.wait(timeout=5))
        self.assertEqual(progress, [5, None])


class SayAllAdapterTests(DesktopHarness):
    """read_all_start/stop/resume through the adapter with a stub speaker."""

    class StubSpeaker:
        def __init__(self):
            self.spoken = []
            self.cancel_calls = 0

        def speak_async(self, text, language="de"):
            self.spoken.append(text)
            # Instant completion: wait() is a no-op via a finished handle.
            class _Done:
                def wait(self, timeout=None):
                    del timeout

            return _Done()

        def cancel(self):
            self.cancel_calls += 1

    def test_start_stop_resume_round_trip(self):
        node = field(MULTILINE)
        desktop = self.desktop_for(build_desktop(node))
        speaker = self.StubSpeaker()

        confirmation = desktop.read_all_start(speaker)
        self.assertIn("Stopp", confirmation)
        # The reader ran to completion instantly (stub speaker): all five
        # sentences were handed to speech.
        self.assertEqual(len(speaker.spoken), 5)

        # After a completed run, stop reports "nothing is running".
        stopped = desktop.read_all_stop(speaker)
        self.assertIn("nicht", stopped)

    def test_stop_without_a_run_is_honest(self):
        desktop = self.desktop_for(build_desktop(field(MULTILINE)))
        spoken = desktop.read_all_stop(self.StubSpeaker())
        self.assertIn("nicht", spoken)

    def test_resume_without_a_bookmark_is_refused(self):
        desktop = self.desktop_for(build_desktop(field(MULTILINE)))
        with self.assertRaisesRegex(GnomeAdapterError, "Fortsetzungsstelle"):
            desktop.read_all_resume(self.StubSpeaker())

    def test_resume_in_a_different_field_is_refused(self):
        node = field(MULTILINE)
        other = FakeNode(
            "Anderes", "text", {STATE_SHOWING, STATE_FOCUSED, STATE_EDITABLE}, content="x"
        )
        # Two fields; the focused one decides which is "current".
        desktop = self.desktop_for(build_desktop(node))
        speaker = self.StubSpeaker()
        desktop.read_all_start(speaker)

        # Simulate the bookmark of another field: resume must refuse.
        desktop._say_all_bookmark = {"key": "other|window|field", "offset": 10}
        with self.assertRaisesRegex(GnomeAdapterError, "anderen Feld"):
            desktop.read_all_resume(speaker)

    def test_navigation_consumes_the_bookmark(self):
        node = field(MULTILINE, caret=0)
        desktop = self.desktop_for(build_desktop(node))
        desktop._say_all_bookmark = {"key": "x", "offset": 10}
        desktop.move_caret("end")
        self.assertIsNone(desktop._say_all_bookmark)


class CountedRoutingTests(unittest.TestCase):
    """Router patterns: digits and spoken numbers, German and English."""

    def test_counted_patterns_route_with_count_argument(self):
        router = OfflineRouter()
        cases = [
            ("drei wörter zurück", "text.caret.word_previous", 3),
            ("zwei zeilen weiter", "text.caret.line_next", 2),
            ("fünf sätze zurück", "text.caret.sentence_previous", 5),
            ("zwei absätze weiter", "text.caret.paragraph_next", 2),
            ("three words back", "text.caret.word_previous", 3),
            ("two lines forward", "text.caret.line_next", 2),
            ("3 wörter zurück", "text.caret.word_previous", 3),
        ]
        for spoken, action, count in cases:
            with self.subTest(spoken=spoken):
                request = router.route(spoken)
                self.assertIsNotNone(request, spoken)
                self.assertEqual(request.action, action, spoken)
                self.assertEqual(request.arguments.get("count"), count, spoken)

    def test_number_words_parse_including_compounds(self):
        router = OfflineRouter()
        for spoken, count in [
            ("ein wort weiter", 1),
            ("zwölf wörter zurück", 12),
            ("dreiundzwanzig zeilen weiter", 23),
        ]:
            with self.subTest(spoken=spoken):
                request = router.route(spoken)
                self.assertIsNotNone(request, spoken)
                self.assertEqual(request.arguments.get("count"), count, spoken)

    def test_counted_steps_over_99_decline(self):
        # The shared vocabulary now reaches 999,999, but a counted move
        # stays capped at 1–99 steps: a larger spoken number declines the
        # utterance (honest refusal before the policy layer) instead of
        # building a request the broker would deny cryptically.
        router = OfflineRouter()
        self.assertIsNone(router.route("hundert wörter weiter"))
        self.assertIsNone(router.route("tausend zeilen zurück"))

    def test_line_number_patterns_digits_and_words(self):
        router = OfflineRouter()
        for spoken, target in [
            ("zeile 12", "12"),
            ("zeile zwölf", "12"),
            ("zeile drei", "3"),
            ("line 12", "12"),
            ("go to line 7", "7"),
            # The shared vocabulary now reaches 999,999, and the spoken
            # compounds work for line numbers too…
            ("zeile hundert", "100"),
            ("zeile zweihundertfünfundzwanzig", "225"),
            ("zeile neunhundertneunundneunzig", "999"),
        ]:
            with self.subTest(spoken=spoken):
                request = router.route(spoken)
                self.assertIsNotNone(request, spoken)
                self.assertEqual(request.action, "text.caret.line", spoken)
                self.assertEqual(request.target, target, spoken)
        # …but the 1–999 validator still refuses anything beyond, so the
        # builder declines the utterance instead of guessing a line.
        self.assertIsNone(router.route("zeile tausend"))
        self.assertIsNone(router.route("zeile 1000"))

    def test_say_all_commands_route(self):
        router = OfflineRouter()
        cases = [
            ("lies alles vor", "text.read_all"),
            ("lies das ganze", "text.read_all"),
            ("lies das dokument", "text.read_all"),
            ("read everything", "text.read_all"),
            ("say all", "text.read_all"),
            ("stopp", "text.read_all.stop"),
            ("stop reading", "text.read_all.stop"),
            ("lies weiter", "text.read_all.resume"),
            ("continue reading", "text.read_all.resume"),
        ]
        for spoken, action in cases:
            with self.subTest(spoken=spoken):
                request = router.route(spoken)
                self.assertIsNotNone(request, spoken)
                self.assertEqual(request.action, action, spoken)

    def test_single_step_patterns_still_work(self):
        router = OfflineRouter()
        cases = [
            ("wort weiter", "text.caret.word_next"),
            ("nächste zeile", "text.caret.line_next"),
            ("vorheriger absatz", "text.caret.paragraph_previous"),
            ("next sentence", "text.caret.sentence_next"),
        ]
        for spoken, action in cases:
            with self.subTest(spoken=spoken):
                request = router.route(spoken)
                self.assertIsNotNone(request, spoken)
                self.assertEqual(request.action, action, spoken)


if __name__ == "__main__":
    unittest.main()
