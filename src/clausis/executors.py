"""Composition of the session-side action adapters.

Every allowlisted action must reach exactly one adapter.  The router is a plain
table lookup so a missing adapter is a visible, testable condition instead of a
generic ``action requires a platform adapter`` failure at runtime:

``desktop.*`` and ``app.close``
    semantic GNOME control over AT-SPI and the Clausis shell extension
``system.status``, ``update.check``, ``file.search``
    read-only local queries
privileged policies
    the Polkit-gated root helper
everything else
    a fixed argument vector run without a shell
"""

from __future__ import annotations

from typing import Any, Optional

from .gnome_adapter import (
    SEMANTIC_ACTIONS,
    SEMANTIC_MUTATIONS,
    GnomeSemanticExecutor,
)
from .models import ActionRequest, ActionResult
from .policy import ACTION_POLICIES, ActionPolicy
from .privileged import PRIVILEGED_ACTIONS, PrivilegedExecutor
from .system_actions import LOCAL_QUERY_ACTIONS, LocalQueryExecutor


class SessionExecutor:
    """Route each action to its adapter and honour the session dry-run flag."""

    def __init__(
        self,
        command_executor: Any,
        semantic_executor: Optional[Any] = None,
        *,
        local_executor: Optional[Any] = None,
        privileged_executor: Optional[Any] = None,
    ) -> None:
        self.command_executor = command_executor
        self.semantic_executor = semantic_executor or GnomeSemanticExecutor()
        self.local_executor = local_executor or LocalQueryExecutor()
        dry_run = bool(getattr(command_executor, "dry_run", False))
        self.privileged_executor = privileged_executor or PrivilegedExecutor(dry_run=dry_run)

    @property
    def dry_run(self) -> bool:
        return bool(getattr(self.command_executor, "dry_run", False))

    def execute(self, request: ActionRequest, policy: ActionPolicy) -> ActionResult:
        if request.action in SEMANTIC_ACTIONS:
            if request.action in SEMANTIC_MUTATIONS and self.dry_run:
                return ActionResult(
                    "dry_run",
                    "validated semantic action; execution disabled",
                    request.action,
                )
            return self.semantic_executor.execute(request, policy)
        if request.action in LOCAL_QUERY_ACTIONS:
            # Read-only queries answer in dry-run mode as well, exactly like the
            # read-only semantic actions above.
            return self.local_executor.execute(request, policy)
        if policy.privileged:
            return self.privileged_executor.execute(request, policy)
        return self.command_executor.execute(request, policy)


def adapted_actions() -> frozenset:
    """Allowlisted actions that some adapter can actually execute.

    This is the single source of truth for what a voice frontend may offer.
    Deriving it from the presence of an argument vector was wrong twice over:
    it hid the privileged actions, whose vector lives on the root side, and it
    hid every action answered by a session adapter instead of a command.
    """

    covered = set(SEMANTIC_ACTIONS) | set(LOCAL_QUERY_ACTIONS) | set(PRIVILEGED_ACTIONS)
    return frozenset(
        name
        for name, policy in ACTION_POLICIES.items()
        if name in covered or policy.command is not None
    )


def unadapted_actions() -> frozenset:
    """Allowlisted actions that no adapter can execute.

    A non-empty result means the router or Hermes can reach an action that will
    always fail; the test suite asserts that this set stays empty.
    """

    covered = set(SEMANTIC_ACTIONS) | set(LOCAL_QUERY_ACTIONS) | set(PRIVILEGED_ACTIONS)
    return frozenset(
        name
        for name, policy in ACTION_POLICIES.items()
        if name not in covered and policy.command is None
    )
