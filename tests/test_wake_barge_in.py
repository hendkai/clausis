"""Wake-word gating, barge-in detection and the non-speech earcons.

The property under test throughout is restraint: the cheap stage must reject
silence before any model runs, and full duplex must stay unreachable until
every part of the chain — certified hardware, shared clock, echo cancellation
and a measured interruption detector — is actually present.
"""

from __future__ import annotations

import array
import math
import tempfile
import unittest
import wave
from pathlib import Path

from clausis.audio import AudioCapabilities, AudioMode, choose_audio_mode
from clausis.barge_in import (
    BargeInDetector,
    BargeInUnavailable,
    InterruptibleSpeaker,
    barge_in_supported,
)
from clausis.earcons import TONES, Earcon, EarconPlayer, render, write_wav
from clausis.wake import (
    PLACEHOLDER_MARKER,
    EnergyGate,
    WakeListener,
    WakeWordGate,
    frame_rms,
    wake_model_is_configured,
)


def tone(level: float, samples: int = 1280) -> bytes:
    """Build a mono int16 frame at roughly the requested RMS."""

    data = array.array("h")
    amplitude = level * math.sqrt(2.0) * 32767
    for index in range(samples):
        data.append(int(amplitude * math.sin(2.0 * math.pi * 440.0 * index / 16000.0)))
    return data.tobytes()


SILENCE = bytes(2560)
QUIET = tone(0.004)
SPEECH = tone(0.09)
LOUD = tone(0.30)


class FrameEnergyTests(unittest.TestCase):
    def test_silence_has_no_energy(self):
        self.assertEqual(frame_rms(SILENCE), 0.0)

    def test_empty_and_odd_frames_do_not_crash(self):
        self.assertEqual(frame_rms(b""), 0.0)
        self.assertEqual(frame_rms(b"\x01"), 0.0)

    def test_level_is_measured_roughly_correctly(self):
        self.assertAlmostEqual(frame_rms(tone(0.1)), 0.1, places=2)


class EnergyGateTests(unittest.TestCase):
    def test_silence_never_passes(self):
        gate = EnergyGate()
        for _ in range(10):
            self.assertFalse(gate.accepts(SILENCE))

    def test_speech_passes_only_after_consecutive_frames(self):
        gate = EnergyGate(speech_frames=3)
        self.assertFalse(gate.accepts(SPEECH))
        self.assertFalse(gate.accepts(SPEECH))
        self.assertTrue(gate.accepts(SPEECH))

    def test_a_gap_restarts_the_count(self):
        gate = EnergyGate(speech_frames=3)
        gate.accepts(SPEECH)
        gate.accepts(SPEECH)
        gate.accepts(SILENCE)
        self.assertFalse(gate.accepts(SPEECH))

    def test_invalid_threshold_is_rejected(self):
        for value in (0.0, 1.0, -1.0):
            with self.subTest(value=value):
                with self.assertRaises(ValueError):
                    EnergyGate(threshold=value)


class WakeWordGateTests(unittest.TestCase):
    class CountingDetector:
        def __init__(self, score=0.9):
            self.calls = 0
            self._score = score

        def score(self, frame):
            self.calls += 1
            return self._score

    def test_model_never_runs_on_silence(self):
        # This is the whole point of the energy gate: no inference while the
        # room is quiet.
        detector = self.CountingDetector()
        gate = WakeWordGate(detector)
        for _ in range(20):
            gate.push(SILENCE)
        self.assertEqual(detector.calls, 0)

    def test_wake_word_is_reported_above_the_threshold(self):
        gate = WakeWordGate(self.CountingDetector(0.9), threshold=0.6)
        events = [gate.push(SPEECH) for _ in range(3)]
        self.assertTrue(events[-1].detected)
        self.assertAlmostEqual(events[-1].score, 0.9)

    def test_low_score_is_not_a_wake_word(self):
        gate = WakeWordGate(self.CountingDetector(0.2), threshold=0.6)
        events = [gate.push(SPEECH) for _ in range(4)]
        self.assertFalse(any(event.detected for event in events))

    def test_gate_without_a_model_is_unavailable_and_silent(self):
        gate = WakeWordGate(None)
        self.assertFalse(gate.available())
        self.assertFalse(gate.push(SPEECH).detected)

    def test_a_failing_model_does_not_take_the_session_down(self):
        class Exploding:
            def score(self, frame):
                raise RuntimeError("inference failed")

        gate = WakeWordGate(Exploding())
        for _ in range(4):
            self.assertFalse(gate.push(SPEECH).detected)

    def test_from_model_degrades_when_nothing_is_configured(self):
        with tempfile.TemporaryDirectory() as directory:
            gate = WakeWordGate.from_model(Path(directory))
        self.assertFalse(gate.available())


class WakeModelConfigurationTests(unittest.TestCase):
    def test_placeholder_directory_is_not_configured(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory)
            (path / "model.onnx").write_bytes(b"\x00")
            (path / "README").write_text(PLACEHOLDER_MARKER, encoding="utf-8")
            self.assertFalse(wake_model_is_configured(path))

    def test_model_without_the_placeholder_is_configured(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory)
            (path / "model.onnx").write_bytes(b"\x00")
            self.assertTrue(wake_model_is_configured(path))

    def test_empty_or_missing_directory_is_not_configured(self):
        with tempfile.TemporaryDirectory() as directory:
            self.assertFalse(wake_model_is_configured(Path(directory)))
        self.assertFalse(wake_model_is_configured(Path("/nonexistent-clausis-wake")))

    def test_shipped_directory_is_still_the_placeholder(self):
        shipped = Path(__file__).resolve().parents[1] / "packaging/models/wake"
        self.assertTrue((shipped / "README").is_file())
        self.assertFalse(wake_model_is_configured(shipped))


class BargeInTests(unittest.TestCase):
    FULL = AudioCapabilities(True, True, True, True, True, True)

    def test_barge_in_needs_echo_cancellation(self):
        self.assertFalse(
            barge_in_supported(AudioCapabilities(True, True, True, False, True))
        )
        self.assertTrue(barge_in_supported(self.FULL))

    def test_detector_refuses_to_arm_without_echo_cancellation(self):
        # Otherwise Clausis hears its own speaker and interrupts itself forever.
        with self.assertRaisesRegex(BargeInUnavailable, "Halbduplex"):
            BargeInDetector(AudioCapabilities(True, True, True, False, True))

    def test_speech_over_the_assistant_interrupts(self):
        detector = BargeInDetector(self.FULL, noise_floor=0.005, frames=3)
        self.assertFalse(detector.push(LOUD).interrupted)
        self.assertFalse(detector.push(LOUD).interrupted)
        self.assertTrue(detector.push(LOUD).interrupted)

    def test_quiet_room_never_interrupts(self):
        detector = BargeInDetector(self.FULL, noise_floor=0.005, frames=3)
        for _ in range(20):
            self.assertFalse(detector.push(QUIET).interrupted)

    def test_a_single_loud_frame_is_not_an_interruption(self):
        detector = BargeInDetector(self.FULL, noise_floor=0.005, frames=3)
        detector.push(LOUD)
        detector.push(SILENCE)
        self.assertFalse(detector.push(LOUD).interrupted)

    def test_threshold_follows_the_room(self):
        detector = BargeInDetector(self.FULL, noise_floor=0.005)
        before = detector.level
        for _ in range(30):
            detector.observe_noise(SPEECH)
        self.assertGreater(detector.level, before)


class InterruptibleSpeakerTests(unittest.TestCase):
    class Speaker:
        def __init__(self):
            self.spoken = []

        def speak(self, text, language="de"):
            self.spoken.append(text)

    def test_without_a_detector_it_is_a_plain_speaker(self):
        speaker = self.Speaker()
        self.assertTrue(InterruptibleSpeaker(speaker).speak("Guten Tag"))
        self.assertEqual(speaker.spoken, ["Guten Tag"])

    def test_interruption_stops_playback(self):
        speaker = self.Speaker()
        stopped = []
        frames = [LOUD, LOUD, LOUD, SILENCE]
        interruptible = InterruptibleSpeaker(
            speaker,
            detector=BargeInDetector(BargeInTests.FULL, noise_floor=0.005, frames=3),
            read_frame=lambda: frames.pop(0) if frames else b"",
            stop=lambda: stopped.append(True),
        )
        self.assertFalse(interruptible.speak("Ein langer Satz"))
        self.assertTrue(interruptible.interrupted)
        self.assertEqual(stopped, [True])

    def test_quiet_playback_completes(self):
        speaker = self.Speaker()
        frames = [QUIET, QUIET, b""]
        interruptible = InterruptibleSpeaker(
            speaker,
            detector=BargeInDetector(BargeInTests.FULL, noise_floor=0.005, frames=3),
            read_frame=lambda: frames.pop(0),
        )
        self.assertTrue(interruptible.speak("Kurz"))
        self.assertFalse(interruptible.interrupted)


class AudioModeTests(unittest.TestCase):
    def test_full_duplex_is_reachable_when_the_whole_chain_is_present(self):
        decision = choose_audio_mode(
            AudioCapabilities(True, True, True, True, True, True)
        )
        self.assertEqual(decision.mode, AudioMode.FULL_DUPLEX)
        self.assertTrue(decision.barge_in)
        self.assertIn("unterbrechen", decision.announcement)

    def test_missing_interrupt_detector_keeps_half_duplex(self):
        decision = choose_audio_mode(AudioCapabilities(True, True, True, True, True))
        self.assertEqual(decision.mode, AudioMode.HALF_DUPLEX)
        self.assertFalse(decision.barge_in)

    def test_interrupt_detector_alone_does_not_unlock_full_duplex(self):
        # Without echo cancellation the detector would fire on Clausis itself.
        decision = choose_audio_mode(
            AudioCapabilities(True, True, False, False, False, True)
        )
        self.assertEqual(decision.mode, AudioMode.HALF_DUPLEX)
        self.assertFalse(decision.barge_in)


class EarconTests(unittest.TestCase):
    def test_every_earcon_has_a_distinct_tone_sequence(self):
        sequences = {earcon: TONES[earcon] for earcon in Earcon}
        self.assertEqual(len(sequences), len(Earcon))
        self.assertEqual(len({tuple(v) for v in sequences.values()}), len(Earcon))

    def test_rendered_audio_is_non_empty_and_bounded(self):
        for earcon in Earcon:
            with self.subTest(earcon=earcon):
                pcm = render(earcon)
                self.assertGreater(len(pcm), 0)
                samples = array.array("h")
                samples.frombytes(pcm)
                self.assertLessEqual(max(abs(s) for s in samples), 32767)

    def test_tones_start_and_end_quietly(self):
        # A hard edge clicks, and a click is what a hearing aid amplifies worst.
        samples = array.array("h")
        samples.frombytes(render(Earcon.WAKE))
        self.assertLess(abs(samples[0]), 2000)
        self.assertLess(abs(samples[-1]), 2000)

    def test_written_file_is_a_valid_mono_wav(self):
        with tempfile.TemporaryDirectory() as directory:
            path = write_wav(Earcon.CONFIRM, Path(directory) / "confirm.wav")
            with wave.open(str(path), "rb") as handle:
                self.assertEqual(handle.getnchannels(), 1)
                self.assertEqual(handle.getsampwidth(), 2)
                self.assertGreater(handle.getnframes(), 0)

    def test_missing_player_stays_silent_instead_of_failing(self):
        player = EarconPlayer(which=lambda name: None)
        self.assertFalse(player.available)
        self.assertFalse(player.play(Earcon.WAKE))

    def test_player_uses_a_fixed_argument_vector(self):
        calls = []
        with EarconPlayer(
            which=lambda name: "/usr/bin/paplay" if name == "paplay" else None,
            runner=calls.append,
        ) as player:
            self.assertTrue(player.play(Earcon.ERROR))
        self.assertEqual(calls[0][0], "paplay")
        self.assertTrue(calls[0][-1].endswith("error.wav"))

    def test_rendering_is_cached_per_earcon(self):
        calls = []
        with EarconPlayer(which=lambda name: "/usr/bin/paplay", runner=calls.append) as player:
            player.play(Earcon.WAKE)
            player.play(Earcon.WAKE)
        self.assertEqual(calls[0][-1], calls[1][-1])

    def test_closing_removes_the_rendered_tones(self):
        player = EarconPlayer(which=lambda name: "/usr/bin/paplay", runner=lambda c: None)
        player.play(Earcon.WAKE)
        directory = player._directory
        self.assertTrue(directory.is_dir())
        player.close()
        self.assertFalse(directory.exists())
        player.close()


class WakeListenerTests(unittest.TestCase):
    class Detector:
        def __init__(self, fire_after):
            self.calls = 0
            self.fire_after = fire_after

        def score(self, frame):
            self.calls += 1
            return 0.95 if self.calls >= self.fire_after else 0.1

    def _listener(self, frames, gate, **kwargs):
        remaining = list(frames)
        return WakeListener(
            gate, lambda: remaining.pop(0) if remaining else b"", **kwargs
        )

    def test_wake_word_in_the_stream_is_detected(self):
        fired = []
        gate = WakeWordGate(self.Detector(fire_after=2), threshold=0.6)
        listener = self._listener([SPEECH] * 8, gate, on_detect=lambda: fired.append(True))
        self.assertTrue(listener.wait(timeout=None))
        self.assertEqual(fired, [True])

    def test_a_quiet_stream_never_fires(self):
        detector = self.Detector(fire_after=1)
        gate = WakeWordGate(detector, threshold=0.6)
        listener = self._listener([SILENCE] * 30, gate)
        self.assertFalse(listener.wait(timeout=None))
        self.assertEqual(detector.calls, 0)

    def test_exhausted_stream_returns_control_to_the_caller(self):
        gate = WakeWordGate(self.Detector(fire_after=99), threshold=0.6)
        self.assertFalse(self._listener([SPEECH] * 3, gate).wait(timeout=None))

    def test_unavailable_gate_never_blocks(self):
        listener = WakeListener(WakeWordGate(None), lambda: SPEECH)
        self.assertFalse(listener.wait(timeout=None))

    def test_a_failing_frame_source_is_survivable(self):
        def exploding():
            raise RuntimeError("microphone vanished")

        listener = WakeListener(WakeWordGate(self.Detector(1)), exploding)
        self.assertFalse(listener.wait(timeout=None))

    def test_timeout_is_honoured(self):
        now = [0.0]

        def clock():
            now[0] += 0.5
            return now[0]

        gate = WakeWordGate(self.Detector(fire_after=99), threshold=0.6)
        listener = WakeListener(gate, lambda: SPEECH, clock=clock)
        self.assertFalse(listener.wait(timeout=2.0))


if __name__ == "__main__":
    unittest.main()
