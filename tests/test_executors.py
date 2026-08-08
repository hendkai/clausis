import unittest
from dataclasses import replace

from clausis.broker import ActionBroker, SafeExecutor
from clausis.capabilities import CapabilityAuthority
from clausis.executors import SessionExecutor, unadapted_actions
from clausis.models import ActionRequest, Risk
from clausis.policy import ACTION_POLICIES
from clausis.privileged import PrivilegedExecutor
from clausis.router import OfflineRouter
from clausis.system_actions import LocalQueryExecutor


class RecordingExecutor:
    def __init__(self, name, dry_run=False):
        self.name = name
        self.dry_run = dry_run
        self.seen = []

    def execute(self, request, policy):
        self.seen.append(request.action)
        from clausis.models import ActionResult

        return ActionResult("completed", self.name, request.action)


class AdapterCoverageTests(unittest.TestCase):
    def test_no_allowlisted_action_is_left_without_an_adapter(self):
        self.assertEqual(unadapted_actions(), frozenset())

    def test_every_routable_voice_command_reaches_an_adapter(self):
        router = OfflineRouter()
        transcripts = [
            "schließe firefox",
            "zeige die übersicht",
            "systemstatus",
            "suche datei bericht",
            "suche nach updates",
            "installiere sicherheitsupdates",
            "computer neu starten",
            "netzwerkstatus",
            "lautstärke 30 prozent",
        ]
        semantic = RecordingExecutor("semantic")
        local = RecordingExecutor("local")
        privileged = RecordingExecutor("privileged")
        command = RecordingExecutor("command")
        executor = SessionExecutor(
            command,
            semantic,
            local_executor=local,
            privileged_executor=privileged,
        )
        for transcript in transcripts:
            request = router.route(transcript)
            self.assertIsNotNone(request, transcript)
            policy = ACTION_POLICIES[request.action]
            result = executor.execute(request, policy)
            self.assertEqual(result.status, "completed", transcript)

    def test_actions_are_routed_to_the_expected_adapter(self):
        semantic = RecordingExecutor("semantic")
        local = RecordingExecutor("local")
        privileged = RecordingExecutor("privileged")
        command = RecordingExecutor("command")
        executor = SessionExecutor(
            command, semantic, local_executor=local, privileged_executor=privileged
        )
        for action in ("app.close", "desktop.overview", "desktop.context.describe"):
            executor.execute(ActionRequest(action, "firefox"), ACTION_POLICIES[action])
        for action in ("system.status", "update.check"):
            executor.execute(ActionRequest(action), ACTION_POLICIES[action])
        executor.execute(
            ActionRequest("system.reboot", risk=Risk.CRITICAL, reversible=False),
            ACTION_POLICIES["system.reboot"],
        )
        executor.execute(ActionRequest("network.status"), ACTION_POLICIES["network.status"])

        self.assertEqual(
            semantic.seen, ["app.close", "desktop.overview", "desktop.context.describe"]
        )
        self.assertEqual(local.seen, ["system.status", "update.check"])
        self.assertEqual(privileged.seen, ["system.reboot"])
        self.assertEqual(command.seen, ["network.status"])

    def test_deleted_file_action_is_no_longer_allowlisted(self):
        self.assertNotIn("file.delete", ACTION_POLICIES)


class DryRunTests(unittest.TestCase):
    def setUp(self):
        self.semantic = RecordingExecutor("semantic")
        self.local = RecordingExecutor("local")
        self.privileged = RecordingExecutor("privileged")
        self.executor = SessionExecutor(
            SafeExecutor(dry_run=True),
            self.semantic,
            local_executor=self.local,
            privileged_executor=self.privileged,
        )

    def test_semantic_mutation_is_withheld(self):
        result = self.executor.execute(
            ActionRequest("app.close", "firefox", risk=Risk.MEDIUM), ACTION_POLICIES["app.close"]
        )
        self.assertEqual(result.status, "dry_run")
        self.assertEqual(self.semantic.seen, [])

    def test_read_only_semantic_action_still_answers(self):
        self.executor.execute(
            ActionRequest("desktop.context.describe"), ACTION_POLICIES["desktop.context.describe"]
        )
        self.assertEqual(self.semantic.seen, ["desktop.context.describe"])

    def test_read_only_local_query_still_answers(self):
        self.executor.execute(ActionRequest("system.status"), ACTION_POLICIES["system.status"])
        self.assertEqual(self.local.seen, ["system.status"])

    def test_privileged_executor_inherits_the_dry_run_flag(self):
        executor = SessionExecutor(SafeExecutor(dry_run=True))
        self.assertIsInstance(executor.privileged_executor, PrivilegedExecutor)
        self.assertTrue(executor.privileged_executor.dry_run)
        self.assertIsInstance(executor.local_executor, LocalQueryExecutor)


class BrokerIntegrationTests(unittest.TestCase):
    def setUp(self):
        self.authority = CapabilityAuthority(b"s" * 32)
        self.local = RecordingExecutor("local")
        self.privileged = RecordingExecutor("privileged")
        self.broker = ActionBroker(
            self.authority,
            SessionExecutor(
                SafeExecutor(dry_run=False),
                RecordingExecutor("semantic"),
                local_executor=self.local,
                privileged_executor=self.privileged,
            ),
        )

    def test_low_risk_query_needs_no_confirmation(self):
        result = self.broker.submit(ActionRequest("system.status"))
        self.assertEqual(result.status, "completed")

    def test_privileged_action_still_requires_confirmation_first(self):
        request = ActionRequest("system.reboot", risk=Risk.CRITICAL, reversible=False)
        self.assertEqual(self.broker.submit(request).status, "confirmation_required")
        self.assertEqual(self.privileged.seen, [])

    def test_confirmed_privileged_action_reaches_the_helper_client(self):
        request = ActionRequest("system.reboot", risk=Risk.CRITICAL, reversible=False)
        approved = replace(request, capability_token=self.authority.issue(request))
        self.assertEqual(self.broker.submit(approved).status, "completed")
        self.assertEqual(self.privileged.seen, ["system.reboot"])


if __name__ == "__main__":
    unittest.main()
