import json
import tempfile
import unittest
from pathlib import Path

from clausis.audit import AuditLog
from clausis.models import ActionRequest, ActionResult


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


if __name__ == "__main__":
    unittest.main()
