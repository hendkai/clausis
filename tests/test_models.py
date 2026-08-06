import unittest

from voiceos.models import ActionRequest, Origin, Risk


class ActionRequestTests(unittest.TestCase):
    def test_round_trip(self):
        original = ActionRequest(
            "file.open", "/tmp/example.txt", {"mode": "read"}, Origin.HERMES, Risk.MEDIUM
        )
        self.assertEqual(ActionRequest.from_dict(original.to_dict()), original)

    def test_unknown_fields_rejected(self):
        with self.assertRaisesRegex(ValueError, "unknown"):
            ActionRequest.from_dict({"action": "system.status", "shell": "rm -rf /"})

    def test_control_character_rejected(self):
        with self.assertRaises(ValueError):
            ActionRequest("file.open", "/tmp/a\ncommand")

    def test_non_json_argument_rejected(self):
        with self.assertRaises(ValueError):
            ActionRequest("system.status", arguments={"bad": object()})

    def test_oversized_arguments_rejected(self):
        with self.assertRaisesRegex(ValueError, "16 KiB"):
            ActionRequest("system.status", arguments={"data": "x" * 20_000})

    def test_malformed_action_rejected(self):
        with self.assertRaises(ValueError):
            ActionRequest("rm -rf /")

    def test_string_boolean_rejected(self):
        with self.assertRaisesRegex(ValueError, "boolean"):
            ActionRequest.from_dict({"action": "system.reboot", "reversible": "false"})

    def test_non_string_target_rejected(self):
        with self.assertRaisesRegex(ValueError, "target"):
            ActionRequest.from_dict({"action": "file.open", "target": None})


if __name__ == "__main__":
    unittest.main()
