import json
import subprocess
import tempfile
import unittest
from pathlib import Path

from clausis.models import ActionRequest
from clausis.policy import ACTION_POLICIES
from clausis.system_actions import (
    APT_SIMULATE_COMMAND,
    LocalQueryExecutor,
    UpgradeSummary,
    check_updates,
    parse_apt_simulation,
    read_system_status,
    search_files,
    spoken_search_result,
)


def _completed(stdout="", returncode=0):
    return subprocess.CompletedProcess(list(APT_SIMULATE_COMMAND), returncode, stdout, "")


class SystemStatusTests(unittest.TestCase):
    def _fake_root(self, directory, *, battery=True):
        root = Path(directory)
        (root / "proc").mkdir()
        (root / "proc/uptime").write_text("7384.12 29000.00\n", encoding="utf-8")
        (root / "proc/loadavg").write_text("0.42 0.31 0.28 1/512 900\n", encoding="utf-8")
        (root / "proc/meminfo").write_text(
            "MemTotal:       16000000 kB\nMemFree:         2000000 kB\nMemAvailable:    8000000 kB\n",
            encoding="utf-8",
        )
        supplies = root / "sys/class/power_supply"
        supplies.mkdir(parents=True)
        if battery:
            battery_dir = supplies / "BAT0"
            battery_dir.mkdir()
            (battery_dir / "capacity").write_text("73\n", encoding="utf-8")
            (battery_dir / "status").write_text("Discharging\n", encoding="utf-8")
        return root

    def test_status_is_read_from_proc_and_sys(self):
        with tempfile.TemporaryDirectory() as directory:
            status = read_system_status(self._fake_root(directory))
        self.assertAlmostEqual(status.uptime_seconds, 7384.12, places=2)
        self.assertAlmostEqual(status.load_1m, 0.42)
        self.assertAlmostEqual(status.memory_available_percent, 50.0)
        self.assertEqual(status.battery_percent, 73)
        self.assertFalse(status.battery_charging)

    def test_status_speaks_german_summary(self):
        with tempfile.TemporaryDirectory() as directory:
            spoken = read_system_status(self._fake_root(directory)).spoken()
        self.assertIn("2 Stunden", spoken)
        self.assertIn("Akku", spoken)
        self.assertIn("73 Prozent", spoken)

    def test_missing_battery_is_omitted(self):
        with tempfile.TemporaryDirectory() as directory:
            spoken = read_system_status(self._fake_root(directory, battery=False)).spoken()
        self.assertNotIn("Akku", spoken)

    def test_unreadable_root_reports_unknown_instead_of_zero(self):
        with tempfile.TemporaryDirectory() as directory:
            status = read_system_status(Path(directory))
        self.assertIsNone(status.uptime_seconds)
        self.assertIsNone(status.load_1m)
        self.assertNotIn("0 Stunden", status.spoken())


class UpdateCheckTests(unittest.TestCase):
    SIMULATION = (
        "NOTE: This is only a simulation!\n"
        "Inst libssl3 [3.1.0] (3.1.1 Debian-Security:12/stable-security [amd64])\n"
        "Inst nano [7.2-1] (7.2-2 Debian:12.5/stable [amd64])\n"
        "Conf libssl3 (3.1.1 Debian-Security:12/stable-security [amd64])\n"
    )

    def test_counts_upgrades_and_security_subset(self):
        total, security = parse_apt_simulation(self.SIMULATION)
        self.assertEqual(total, 2)
        self.assertEqual(security, 1)

    def test_conf_lines_are_not_counted(self):
        total, _ = parse_apt_simulation("Conf nano (7.2-2 Debian:12.5/stable [amd64])\n")
        self.assertEqual(total, 0)

    def test_uses_a_non_locking_simulation_only(self):
        seen = []

        def runner(command):
            seen.append(list(command))
            return _completed(self.SIMULATION)

        check_updates(runner)
        self.assertEqual(seen, [list(APT_SIMULATE_COMMAND)])
        self.assertIn("--simulate", seen[0])

    def test_failed_apt_run_is_reported_as_unavailable(self):
        summary = check_updates(lambda command: _completed("", returncode=100))
        self.assertFalse(summary.available)
        self.assertIn("nicht erreichbar", summary.spoken())

    def test_missing_apt_binary_is_reported_as_unavailable(self):
        def runner(command):
            raise FileNotFoundError("apt-get")

        self.assertFalse(check_updates(runner).available)

    def test_up_to_date_system_is_announced(self):
        self.assertIn("aktuellen Stand", UpgradeSummary(0, 0, True).spoken())


class FileSearchTests(unittest.TestCase):
    def _home(self, directory):
        home = Path(directory)
        documents = home / "Dokumente"
        (documents / "Projekte").mkdir(parents=True)
        (documents / "Steuer 2025.pdf").write_text("x", encoding="utf-8")
        (documents / "Projekte/steuerbescheid.odt").write_text("x", encoding="utf-8")
        (documents / ".versteckt.pdf").write_text("x", encoding="utf-8")
        (home / "Musik").mkdir()
        (home / "Musik/lied.mp3").write_text("x", encoding="utf-8")
        return home

    def test_finds_case_insensitive_matches(self):
        with tempfile.TemporaryDirectory() as directory:
            matches = search_files("steuer", home=self._home(directory))
        names = sorted(path.name for path in matches)
        self.assertEqual(names, ["Steuer 2025.pdf", "steuerbescheid.odt"])

    def test_hidden_files_are_skipped(self):
        with tempfile.TemporaryDirectory() as directory:
            matches = search_files("versteckt", home=self._home(directory))
        self.assertEqual(matches, [])

    def test_directories_outside_the_allowlist_are_ignored(self):
        with tempfile.TemporaryDirectory() as directory:
            home = self._home(directory)
            (home / ".ssh").mkdir()
            (home / ".ssh/id_ed25519").write_text("secret", encoding="utf-8")
            matches = search_files("id_ed25519", home=home)
        self.assertEqual(matches, [])

    def test_empty_query_is_rejected(self):
        with self.assertRaises(ValueError):
            search_files("   ")

    def test_result_is_numbered_for_speech(self):
        spoken = spoken_search_result("steuer", [Path("/home/u/Dokumente/Steuer.pdf")])
        self.assertIn("Nummer 1", spoken)
        self.assertIn("Steuer.pdf", spoken)


class LocalQueryExecutorTests(unittest.TestCase):
    def test_every_local_query_action_is_allowlisted(self):
        from clausis.system_actions import LOCAL_QUERY_ACTIONS

        for action in LOCAL_QUERY_ACTIONS:
            self.assertIn(action, ACTION_POLICIES)

    def test_status_action_completes(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "proc").mkdir()
            (root / "proc/uptime").write_text("60.0 60.0\n", encoding="utf-8")
            (root / "proc/loadavg").write_text("1.00 1.00 1.00 1/1 1\n", encoding="utf-8")
            result = LocalQueryExecutor(root=root).execute(
                ActionRequest("system.status"), ACTION_POLICIES["system.status"]
            )
        self.assertEqual(result.status, "completed")
        self.assertIn("System", result.message)
        self.assertEqual(result.details["uptime_seconds"], 60)

    def test_update_check_reports_counts(self):
        executor = LocalQueryExecutor(runner=lambda command: _completed(UpdateCheckTests.SIMULATION))
        result = executor.execute(
            ActionRequest("update.check"), ACTION_POLICIES["update.check"]
        )
        self.assertEqual(result.status, "completed")
        self.assertEqual(result.details["total"], 2)
        self.assertEqual(result.details["security"], 1)

    def test_unavailable_apt_fails_without_raising(self):
        executor = LocalQueryExecutor(runner=lambda command: _completed("", returncode=1))
        result = executor.execute(
            ActionRequest("update.check"), ACTION_POLICIES["update.check"]
        )
        self.assertEqual(result.status, "failed")

    def test_file_search_action_reports_matches(self):
        with tempfile.TemporaryDirectory() as directory:
            home = Path(directory)
            (home / "Downloads").mkdir()
            (home / "Downloads/rechnung.pdf").write_text("x", encoding="utf-8")
            executor = LocalQueryExecutor(home=home)
            result = executor.execute(
                ActionRequest("file.search", "rechnung"), ACTION_POLICIES["file.search"]
            )
        self.assertEqual(result.status, "completed")
        self.assertIn("rechnung.pdf", result.message)

    def test_unknown_action_fails_closed(self):
        result = LocalQueryExecutor().execute(
            ActionRequest("audio.volume.up"), ACTION_POLICIES["audio.volume.up"]
        )
        self.assertEqual(result.status, "failed")


if __name__ == "__main__":
    unittest.main()


class DiagnosticReportTests(unittest.TestCase):
    """The report a community tester files must be safe to share."""

    def _log(self, directory):
        path = Path(directory) / "actions.jsonl"
        path.write_text(
            '{"request": {"action": "text.insert", "target": "meine geheime Notiz"},'
            ' "result": {"status": "completed", "message": "Notiz: geheim"}}\n'
            '{"request": {"action": "file.search", "target": "/home/u/Steuer.pdf"},'
            ' "result": {"status": "failed"}}\n'
            "kaputte zeile\n",
            encoding="utf-8",
        )
        return path

    def test_audit_summary_keeps_no_content(self):
        from clausis.report import summarise_audit

        with tempfile.TemporaryDirectory() as directory:
            summary = summarise_audit(self._log(directory))
        serialised = json.dumps(summary, ensure_ascii=False)
        self.assertIn("text.insert:completed", summary)
        self.assertIn("file.search:failed", summary)
        for secret in ("geheim", "Steuer.pdf", "/home/u", "Notiz"):
            self.assertNotIn(secret, serialised)

    def test_missing_audit_log_is_not_an_error(self):
        from clausis.report import summarise_audit

        self.assertEqual(summarise_audit(Path("/nonexistent-clausis-audit")), {})

    def test_report_contains_no_transcript_or_path(self):
        from clausis.report import build_report

        with tempfile.TemporaryDirectory() as directory:
            report = build_report(
                health=lambda: {"failures": [], "recovery": ["ignoriere mich"]},
                audit_path=self._log(directory),
                mounts_path=Path("/nonexistent-clausis-mounts"),
                which=lambda name: None,
            )
        text = report.to_json()
        for secret in ("geheim", "Steuer.pdf", "ignoriere mich"):
            self.assertNotIn(secret, text)
        self.assertIn("keine Aufnahmen", report.payload["privacy"])

    def test_spoken_summary_says_what_is_shared(self):
        from clausis.report import build_report

        report = build_report(
            health=lambda: {"failures": ["no_microphone"]},
            audit_path=Path("/nonexistent"),
            mounts_path=Path("/nonexistent"),
            which=lambda name: None,
        )
        spoken = report.spoken()
        self.assertIn("no_microphone", spoken)
        self.assertIn("keine Aufnahmen", spoken)

    def test_a_failing_health_check_does_not_break_the_report(self):
        from clausis.report import build_report

        def exploding():
            raise RuntimeError("health unavailable")

        report = build_report(
            health=exploding,
            audit_path=Path("/nonexistent"),
            mounts_path=Path("/nonexistent"),
            which=lambda name: None,
        )
        self.assertEqual(report.payload["health"], {"error": "RuntimeError"})

    def test_report_is_reachable_by_voice(self):
        from clausis.router import OfflineRouter

        request = OfflineRouter().route("Fehlerbericht")
        self.assertIsNotNone(request)
        self.assertEqual(request.action, "system.report")

    def test_spoken_report_writes_a_private_file(self):
        with tempfile.TemporaryDirectory() as directory:
            home = Path(directory)
            result = LocalQueryExecutor(home=home).execute(
                ActionRequest("system.report"), ACTION_POLICIES["system.report"]
            )
            self.assertEqual(result.status, "completed")
            written = Path(result.details["path"])
            self.assertTrue(written.is_file())
            self.assertEqual(written.stat().st_mode & 0o077, 0)
