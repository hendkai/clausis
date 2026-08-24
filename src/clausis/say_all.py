"""Say-all: continuous reading of a field with pause and resume.

Design (see the task card and the orchestrator's verified speech mechanics):

* The field is read chunk by chunk (sentence-sized) through a *cancelable*
  speech handle (``SystemSpeaker.speak_async`` + ``spd-say -C``); the loop
  runs in its own background thread so the command loop stays free for
  „stopp" and „lies weiter".
* The bookmark is a character offset — the offset after the last chunk that
  finished speaking completely.  It is deliberately NOT the caret: moving the
  real caret along would flood AT-SPI events and visibly flicker, so the
  bookmark lives only here until „lies weiter" or a navigation command uses
  it.  After the whole field was read, the caret is set to the field end
  exactly once so subsequent navigation continues from the end.
* Honest limits, documented in BLIND_USE_GAP_ANALYSIS: no speed change
  mid-read, no highlighting, the bookmark is per field and dropped on focus
  change, and „stopp" is reliably recognised at the earliest chunk boundary
  (half-duplex microphone).
"""

from __future__ import annotations

import threading
from typing import Callable, List, Optional, Sequence, Tuple


class SayAllError(RuntimeError):
    """A recoverable say-all failure (no speech output, unreadable field)."""


class WaitableUtterance:
    """Structural type of a cancelable speech handle (see SystemSpeaker)."""

    def wait(self, timeout: Optional[float] = None) -> None:
        del timeout


#: Maximum number of chunks spoken in one say-all run.  A field is capped at
#: MAX_FIELD_CHARS (2048) characters, so sentence chunks stay far below this;
#: the bound exists so a pathological splitter can never loop forever.
MAX_CHUNKS = 4096

#: Spans of the text to speak: ``(start, end)`` character offsets.
SpanSource = Callable[[], Sequence[Tuple[int, int]]]
#: Speaks the text of one span; returns a waitable, cancelable handle
#: (``wait()`` blocks until the chunk finished or was cancelled).
ChunkSpeaker = Callable[[Tuple[int, int]], "WaitableUtterance"]
#: Cancels the current speech output (speech-dispatcher cancel).
SpeechCanceller = Callable[[], None]
#: Called with the end offset of each completed chunk, ``None`` at field end.
ProgressReporter = Callable[[Optional[int]], None]


class SayAllReader:
    """One background reader per ``text.read_all`` command.

    ``stop()`` sets the cancel flag and (through ``cancel_speech``) cancels
    the speech-dispatcher output, which makes the blocking ``wait()`` of the
    current chunk return; the loop then ends with the bookmark on the last
    chunk boundary that fully finished.
    """

    def __init__(
        self,
        *,
        chunks: SpanSource,
        speak_chunk: ChunkSpeaker,
        cancel_speech: SpeechCanceller,
        on_progress: Optional[ProgressReporter] = None,
    ) -> None:
        self._chunks = chunks
        self._speak_chunk = speak_chunk
        self._cancel_speech = cancel_speech
        self._on_progress = on_progress
        self._stop_flag = threading.Event()
        self._done = threading.Event()
        self.thread: Optional[threading.Thread] = None
        #: Bookmark of the last completed chunk: its end offset.
        self.bookmark: Optional[int] = None
        #: ``True`` when the field was read to its very end.
        self.finished_field = False

    # -- control side -----------------------------------------------------

    def start(self) -> None:
        if self.thread is not None:
            raise SayAllError("Dieser Vorlese-Lauf ist bereits aktiv.")
        self.thread = threading.Thread(target=self._run, daemon=True, name="clausis-say-all")
        self.thread.start()

    def stop(self) -> None:
        self._stop_flag.set()
        try:
            self._cancel_speech()
        except Exception:
            pass

    def wait(self, timeout: Optional[float] = None) -> bool:
        return self._done.wait(timeout=timeout)

    # -- worker side ------------------------------------------------------

    def _run(self) -> None:
        try:
            spans = self._chunks()
            for start, end in spans[:MAX_CHUNKS]:
                if self._stop_flag.is_set():
                    return
                handle = self._speak_chunk((start, end))
                if handle is not None:
                    # Block until the chunk finished or was cancelled; the
                    # cancel path makes wait() return via process exit.
                    handle.wait()
                if self._stop_flag.is_set():
                    return
                self.bookmark = end
                if self._on_progress is not None:
                    self._on_progress(end)
            self.finished_field = True
            if self._on_progress is not None:
                self._on_progress(None)
        finally:
            self._done.set()
