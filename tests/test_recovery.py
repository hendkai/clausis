"""Failure handling: every failure must leave a usable way forward.

The rule these tests encode is the project's own: "nur mit Sprache" may never
mean that keyboard and Orca stop being equal paths, so no failure is allowed to
end in silence or in an exception that drops the user.
"""

from __future__ import annotations

import io
import unittest
from pathlib import Path

from clausis.broker import ActionBroker, SafeExecutor
from clausis.capabilities import CapabilityAuthority
from clausis.healthcheck import collect
from clausis.recovery import (
    NOTIFY_COMMAND,
    RECOVERIES,
    Announcer,
    Failure,
    recovery_for,
)
from clausis.router import OfflineRouter
from clausis.runtime import RuntimeState, VoiceRuntime


class BrokenSpeaker:
    def speak(self, text, language="de"):
        raise RuntimeError("speech-dispatcher is not running")


class RecordingSpeaker:
    def __init__(self):
        self.spoken = []

    def speak(self, text, language="de"):
        self.spoken.append(text)


class RecoveryTableTests(unittest.TestCase):
    def test_every_failure_has_a_recovery(self):
        for failure in Failure:
            with self.subTest(failure=failure):
                self.assertIn(failure, RECOVERIES)

    def test_every_recovery_names_a_keyboard_or_orca_path(self):
        for failure, recovery in RECOVERIES.items():
            with self.subTest(failure=failure):
                self.assertTrue(recovery.keyboard.strip())
                self.assertRegex(recovery.keyboard, r"Tastatur|Orca|Tabulator|Super")

    def test_every_recovery_is_spoken_in_full_sentences(self):
        for failure, recovery in RECOVERIES.items():
            with self.subTest(failure=failure):
                self.assertTrue(recovery.spoken.strip().endswith("."))
                self.assertIn(recovery.spoken, recovery.message())
                self.assertIn(recovery.keyboard, recovery.message())

    def test_recovery_lookup_is_keyed_by_its_own_failure(self):
        for failure in Failure:
            self.assertIs(recovery_for(failure).failure, failure)

    def test_failures_that_stop_voice_control_are_the_input_failures(self):
        stopped = {failure for failure, r in RECOVERIES.items() if not r.can_continue}
        self.assertEqual(
            stopped,
            {Failure.NO_MICROPHONE, Failure.NO_AUDIO, Failure.STT_UNAVAILABLE},
        )


class AnnouncerTests(unittest.TestCase):
    def test_speech_is_used_when_it_works(self):
        speaker = RecordingSpeaker()
        announcer = Announcer(speaker, notifier=lambda text: True)
        self.assertEqual(announcer.announce("Guten Tag"), "speech")
        self.assertEqual(speaker.spoken, ["Guten Tag"])

    def test_dead_speech_falls_back_to_a_notification(self):
        seen = []

        def notifier(text):
            seen.append(text)
            return True

        announcer = Announcer(BrokenSpeaker(), notifier=notifier)
        self.assertEqual(announcer.announce("Guten Tag"), "notification")
        self.assertEqual(seen, ["Guten Tag"])
        self.assertTrue(announcer.speech_failed)

    def test_dead_speech_and_notification_still_reach_the_terminal(self):
        stream = io.StringIO()
        announcer = Announcer(BrokenSpeaker(), notifier=lambda text: False, stream=stream)
        self.assertEqual(announcer.announce("Guten Tag"), "text")
        self.assertIn("Guten Tag", stream.getvalue())

    def test_broken_speech_is_not_retried_on_every_message(self):
        class CountingSpeaker(BrokenSpeaker):
            def __init__(self):
                self.attempts = 0

            def speak(self, text, language="de"):
                self.attempts += 1
                raise RuntimeError("dead")

        speaker = CountingSpeaker()
        announcer = Announcer(speaker, notifier=lambda text: True)
        for _ in range(5):
            announcer.announce("Hinweis")
        self.assertEqual(speaker.attempts, 1)

    def test_missing_speaker_goes_straight_to_the_other_channels(self):
        stream = io.StringIO()
        announcer = Announcer(None, notifier=lambda text: False, stream=stream)
        self.assertEqual(announcer.announce("Hinweis"), "text")

    def test_recovery_message_is_announced_in_full(self):
        speaker = RecordingSpeaker()
        Announcer(speaker).announce_recovery(Failure.NO_SPEECH_OUTPUT)
        self.assertIn("Orca", speaker.spoken[0])

    def test_notification_uses_a_fixed_argument_vector(self):
        self.assertEqual(NOTIFY_COMMAND[0], "notify-send")
        self.assertIn("--app-name=Clausis", NOTIFY_COMMAND)


class BrokerFailureTests(unittest.TestCase):
    def test_a_crashing_broker_becomes_a_spoken_recovery(self):
        from clausis.assistant import _submit

        class ExplodingBroker:
            def submit(self, request):
                raise RuntimeError("system bus is gone")

        runtime = VoiceRuntime(OfflineRouter(), ExplodingBroker())
        result = _submit(runtime, "Netzwerkstatus")
        self.assertEqual(result.status, "failed")
        self.assertIn("Tastatur", result.message)
        self.assertIs(runtime.state, RuntimeState.IDLE)

    def test_a_working_broker_is_untouched(self):
        from clausis.assistant import _submit

        runtime = VoiceRuntime(
            OfflineRouter(),
            ActionBroker(CapabilityAuthority.generate(), SafeExecutor(dry_run=True)),
        )
        result = _submit(runtime, "Netzwerkstatus")
        self.assertEqual(result.status, "dry_run")

    def test_unavailable_confirmation_is_reported_with_its_recovery(self):
        from clausis.assistant import _localized_result

        message = _localized_result(
            "denied", "Die geschützte lokale Bestätigung ist nicht verfügbar."
        )
        self.assertIn("Tastatur", message)
        self.assertIn("gleichwertige", message)

    def test_stop_still_stops_after_a_broker_failure(self):
        from clausis.assistant import _submit

        class ExplodingBroker:
            def submit(self, request):
                raise RuntimeError("gone")

        runtime = VoiceRuntime(OfflineRouter(), ExplodingBroker())
        _submit(runtime, "Netzwerkstatus")
        self.assertEqual(_submit(runtime, "Stopp Hermes").status, "stopped")
        self.assertIs(runtime.state, RuntimeState.STOPPED)


class HealthcheckTests(unittest.TestCase):
    def _collect(self, *, present=(), model=True, microphone=True):
        class Capabilities:
            def __init__(self, value):
                self.microphone = value

        return collect(
            model_path=Path("/") if model else Path("/nonexistent-clausis-model"),
            probe=lambda: Capabilities(microphone),
            which=lambda name: f"/usr/bin/{name}" if name in present else None,
        )

    ALL = ("wpctl", "systemctl", "loginctl", "gio", "spd-say")

    def test_complete_system_is_healthy(self):
        report = self._collect(present=self.ALL)
        self.assertTrue(report["healthy"])
        self.assertFalse(report["rollback_recommended"])
        self.assertEqual(report["failures"], [])

    def test_missing_microphone_is_degraded_but_not_a_rollback_reason(self):
        report = self._collect(present=self.ALL, microphone=False)
        self.assertFalse(report["healthy"])
        self.assertFalse(report["rollback_recommended"])
        self.assertIn(Failure.NO_MICROPHONE.value, report["failures"])

    def test_missing_speech_output_recommends_rollback(self):
        report = self._collect(present=("wpctl", "systemctl", "loginctl", "gio"))
        self.assertTrue(report["rollback_recommended"])
        self.assertIn(Failure.NO_SPEECH_OUTPUT.value, report["failures"])

    def test_missing_stt_model_recommends_rollback(self):
        report = self._collect(present=self.ALL, model=False)
        self.assertTrue(report["rollback_recommended"])
        self.assertIn(Failure.STT_UNAVAILABLE.value, report["failures"])

    def test_report_always_carries_a_spoken_recovery_for_each_failure(self):
        report = self._collect(present=(), model=False, microphone=False)
        self.assertEqual(len(report["recovery"]), len(report["failures"]))
        for line in report["recovery"]:
            self.assertRegex(line, r"Tastatur|Orca")

    def test_probe_failure_does_not_crash_the_check(self):
        def exploding():
            raise RuntimeError("no audio stack")

        report = collect(
            model_path=Path("/"),
            probe=exploding,
            which=lambda name: f"/usr/bin/{name}",
        )
        self.assertFalse(report["microphone"])
        self.assertFalse(report["rollback_recommended"])


if __name__ == "__main__":
    unittest.main()
