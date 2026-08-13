import json
import tempfile
import unittest
from pathlib import Path

from clausis.audit import AuditLog
from clausis.models import ActionRequest, ActionResult, Risk


class AuditTests(unittest.TestCase):
    def test_sensitive_values_are_redacted(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "audit.jsonl"
            log = AuditLog(path, b"e" * 32)
            request = ActionRequest("system.status", arguments={"pin": "123456", "safe": "yes"})
            log.append(request, ActionResult("completed", "ok", request.action))
            entry = json.loads(path.read_text())
            self.assertEqual(entry["request"]["arguments"]["pin"], "[REDACTED]")
            self.assertNotIn("123456", path.read_text())

    def test_tampering_is_detected(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "audit.jsonl"
            log = AuditLog(path, b"f" * 32)
            request = ActionRequest("system.status")
            log.append(request, ActionResult("completed", "ok", request.action))
            path.write_text(path.read_text().replace('"completed"', '"failed"'))
            self.assertFalse(log.verify())

    def test_capability_token_is_redacted(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "audit.jsonl"
            log = AuditLog(path, b"g" * 32)
            request = ActionRequest("system.status", capability_token="secret-capability")
            log.append(request, ActionResult("completed", "ok", request.action))
            self.assertNotIn("secret-capability", path.read_text())

    def test_focused_text_result_is_never_persisted(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "audit.jsonl"
            log = AuditLog(path, b"h" * 32)
            request = ActionRequest("desktop.text.read_focused")
            log.append(request, ActionResult("completed", "Text in Notes: private words", request.action))
            contents = path.read_text()
            self.assertNotIn("private words", contents)
            self.assertIn("[REDACTED: focused text]", contents)
            self.assertTrue(log.verify())

    def test_clipboard_text_result_is_never_persisted(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "audit.jsonl"
            log = AuditLog(path, b"c" * 32)
            request = ActionRequest("desktop.clipboard.read_text")
            log.append(
                request,
                ActionResult("completed", "private clipboard content", request.action),
            )
            contents = path.read_text()
            self.assertNotIn("private clipboard content", contents)
            self.assertIn("[REDACTED: clipboard text]", contents)
            self.assertTrue(log.verify())

    def test_selected_text_result_is_never_persisted(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "audit.jsonl"
            log = AuditLog(path, b"s" * 32)
            request = ActionRequest("desktop.text.read_selection", risk=Risk.MEDIUM)
            log.append(
                request,
                ActionResult("completed", "Textauswahl: private selected words", request.action),
            )
            contents = path.read_text()
            self.assertNotIn("private selected words", contents)
            self.assertIn("[REDACTED: selected text]", contents)
            self.assertTrue(log.verify())

    def test_standard_dialog_text_is_never_persisted(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "audit.jsonl"
            log = AuditLog(path, b"j" * 32)
            request = ActionRequest("desktop.standard_dialog.read", risk=Risk.MEDIUM)
            log.append(
                request,
                ActionResult("completed", "Dialog Warning. private failure detail.", request.action),
            )
            contents = path.read_text()
            self.assertNotIn("private failure detail", contents)
            self.assertIn("[REDACTED: standard dialog text]", contents)
            self.assertTrue(log.verify())

    def test_notification_text_is_never_persisted(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "audit.jsonl"
            log = AuditLog(path, b"n" * 32)
            request = ActionRequest("desktop.notifications.read", risk=Risk.MEDIUM)
            log.append(
                request,
                ActionResult("completed", "private notification text", request.action),
            )
            contents = path.read_text()
            self.assertNotIn("private notification text", contents)
            self.assertIn("[REDACTED: notification text]", contents)
            self.assertTrue(log.verify())

    def test_single_character_results_are_never_persisted(self):
        for action, marker in (
            ("desktop.text.read_previous_character", "[REDACTED: previous character]"),
            ("desktop.text.read_next_character", "[REDACTED: next character]"),
        ):
            with self.subTest(action=action), tempfile.TemporaryDirectory() as directory:
                path = Path(directory) / "audit.jsonl"
                log = AuditLog(path, b"r" * 32)
                request = ActionRequest(action, risk=Risk.MEDIUM)
                log.append(request, ActionResult("completed", "private character: 🙂", action))
                contents = path.read_text()
                self.assertNotIn("🙂", contents)
                self.assertIn(marker, contents)
                self.assertTrue(log.verify())

    def test_single_word_results_are_never_persisted(self):
        for action, marker in (
            ("desktop.text.read_previous_word", "[REDACTED: previous word]"),
            ("desktop.text.read_next_word", "[REDACTED: next word]"),
        ):
            with self.subTest(action=action), tempfile.TemporaryDirectory() as directory:
                path = Path(directory) / "audit.jsonl"
                log = AuditLog(path, b"w" * 32)
                request = ActionRequest(action, risk=Risk.MEDIUM)
                log.append(request, ActionResult("completed", "private word: Geheimnis", action))
                contents = path.read_text()
                self.assertNotIn("Geheimnis", contents)
                self.assertIn(marker, contents)
                self.assertTrue(log.verify())

    def test_dictated_targets_are_never_persisted(self):
        for action, marker in (
            ("desktop.text.set", "[REDACTED: dictated text]"),
            ("desktop.text.insert_at_caret", "[REDACTED: inserted text]"),
            ("desktop.text.replace_selection", "[REDACTED: selection replacement text]"),
            ("desktop.text.replace_previous_word", "[REDACTED: previous word replacement text]"),
            ("desktop.text.replace_next_word", "[REDACTED: next word replacement text]"),
            ("desktop.text.replace_current_line", "[REDACTED: current line replacement text]"),
            ("desktop.text.insert_line_above", "[REDACTED: inserted line above text]"),
            ("desktop.text.insert_line_below", "[REDACTED: inserted line below text]"),
            ("desktop.clipboard.write_text", "[REDACTED: clipboard write text]"),
        ):
            with self.subTest(action=action), tempfile.TemporaryDirectory() as directory:
                path = Path(directory) / "audit.jsonl"
                log = AuditLog(path, b"d" * 32)
                request = ActionRequest(action, "private dictated words")
                log.append(request, ActionResult("completed", "ok", request.action))
                contents = path.read_text()
                self.assertNotIn("private dictated words", contents)
                self.assertIn(marker, contents)
                self.assertTrue(log.verify())


if __name__ == "__main__":
    unittest.main()
