import json
import unittest

from clausis.models import ActionRequest, ActionResult, Risk
from clausis.system_client import ConfirmationAwareBroker, _parse_result


class StubBroker:
    def __init__(self, result):
        self.result = result

    def submit(self, request):
        return self.result


class StubConfirmer:
    def __init__(self, result=None, error=None):
        self.result = result
        self.error = error
        self.calls = []

    def confirm_and_submit(self, request):
        self.calls.append(request)
        if self.error:
            raise self.error
        return self.result


class SystemClientTests(unittest.TestCase):
    def test_only_broker_declared_confirmation_invokes_system_service(self):
        request = ActionRequest("network.wifi.disable", risk=Risk.MEDIUM)
        confirmer = StubConfirmer(ActionResult("dry_run", "ok", request.action))
        broker = ConfirmationAwareBroker(
            StubBroker(ActionResult("confirmation_required", "confirm", request.action)),
            confirmer,
        )
        self.assertEqual(broker.submit(request).status, "dry_run")
        self.assertEqual(confirmer.calls, [request])

    def test_low_risk_result_never_opens_confirmation(self):
        request = ActionRequest("audio.volume.up")
        confirmer = StubConfirmer(ActionResult("denied", "unexpected", request.action))
        result = ActionResult("completed", "done", request.action)
        self.assertIs(
            ConfirmationAwareBroker(StubBroker(result), confirmer).submit(request),
            result,
        )
        self.assertEqual(confirmer.calls, [])

    def test_confirmation_failure_fails_closed(self):
        request = ActionRequest("system.reboot", risk=Risk.CRITICAL, reversible=False)
        broker = ConfirmationAwareBroker(
            StubBroker(ActionResult("confirmation_required", "confirm", request.action)),
            StubConfirmer(error=OSError("private detail")),
        )
        result = broker.submit(request)
        self.assertEqual(result.status, "denied")
        self.assertNotIn("private detail", result.message)

    def test_response_parser_rejects_action_swap_and_unknown_fields(self):
        with self.assertRaisesRegex(ValueError, "mismatch"):
            _parse_result(
                json.dumps({"status": "completed", "message": "x", "action": "system.poweroff"}),
                expected_action="system.reboot",
            )
        with self.assertRaisesRegex(ValueError, "unknown"):
            _parse_result(
                json.dumps({"status": "completed", "message": "x", "action": "system.reboot", "capability_token": "secret"}),
                expected_action="system.reboot",
            )


if __name__ == "__main__":
    unittest.main()
