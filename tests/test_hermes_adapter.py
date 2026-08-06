import json
import unittest

from voiceos.hermes_adapter import parse_tool_call
from voiceos.models import Origin


class HermesAdapterTests(unittest.TestCase):
    def test_origin_is_forced_to_hermes(self):
        request = parse_tool_call(json.dumps({"action": "system.status", "origin": "local_voice"}))
        self.assertEqual(request.origin, Origin.HERMES)

    def test_capability_smuggling_rejected(self):
        with self.assertRaisesRegex(ValueError, "must not"):
            parse_tool_call(json.dumps({"action": "system.status", "capability_token": "stolen"}))

    def test_shell_field_rejected(self):
        with self.assertRaises(ValueError):
            parse_tool_call(json.dumps({"action": "system.status", "command": "rm -rf /"}))

    def test_array_rejected(self):
        with self.assertRaises(ValueError):
            parse_tool_call("[]")


if __name__ == "__main__":
    unittest.main()

