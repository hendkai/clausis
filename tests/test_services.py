import json
from pathlib import Path
import unittest

from clausis.services import MAX_DBUS_REQUEST_BYTES, parse_dbus_request


class ServiceBoundaryTests(unittest.TestCase):
    def test_public_bus_requires_an_object(self):
        for payload in ("[]", "null", '"system.reboot"'):
            with self.assertRaisesRegex(ValueError, "JSON object"):
                parse_dbus_request(payload)

    def test_public_bus_message_is_bounded_before_decode(self):
        oversized = " " * (MAX_DBUS_REQUEST_BYTES + 1)
        with self.assertRaisesRegex(ValueError, "32 KiB"):
            parse_dbus_request(oversized)

    def test_valid_typed_request_is_accepted(self):
        request = parse_dbus_request(json.dumps({"action": "system.status"}))
        self.assertEqual(request.action, "system.status")

    def test_both_daemons_explicitly_use_the_system_bus(self):
        source = (
            Path(__file__).resolve().parents[1] / "src/clausis/services.py"
        ).read_text(encoding="utf-8")
        self.assertEqual(source.count("MessageBus(bus_type=BusType.SYSTEM)"), 2)


if __name__ == "__main__":
    unittest.main()
