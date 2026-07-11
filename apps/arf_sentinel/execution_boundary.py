"""
Execution Boundary — the hard authorisation gate.

This module implements the final enforcement point for ARF governance
decisions.  It is structurally incapable of being bypassed by the agent
or the UI:

    - The agent proposes (RemediationProposal).
    - ARF evaluates and decides (GovernanceDecision).
    - The ExecutionBoundary independently inspects the decision and
      determines whether execution may proceed.

The boundary enforces three outcomes:

    APPROVE  → AUTHORIZED_SIMULATION
        The action is safe within ARF's policy.  In this prototype,
        execution is simulated (no actual repository changes).

    DENY     → BLOCKED_POLICY
        The action violates a hard policy rule.  Execution is forbidden
        regardless of the agent's confidence.

    ESCALATE → BLOCKED_PENDING_HUMAN_APPROVAL
        The action exceeds the autonomous risk threshold.  A human must
        explicitly authorise it before the boundary will permit execution.

Architectural Invariant
-----------------------
There is no code path from the agent's proposal to execution that
bypasses this boundary.  The LangGraph state machine enforces that
the `arf_governance` node is mandatory and its output is consumed
by the boundary before any `prepare_execution` node.

The boundary does not perform its own risk assessment; it trusts
the GovernanceDecision as the source of truth and simply enforces
the prescribed outcome.
"""

from .models import (
    RemediationProposal,
    GovernanceDecision,
    ExecutionResult,
    GovernanceAction,
    ExecutionStatus,
)


class ExecutionBoundary:
    """
    Hard enforcement point for ARF governance decisions.

    This class is intentionally simple: it contains no business logic,
    no risk calculations, and no policy evaluation.  Its sole purpose is
    to inspect a GovernanceDecision and produce the appropriate
    ExecutionResult.  Any attempt to subvert this gate must be prevented
    at the architecture level (LangGraph, deployment controls).

    Usage
    -----
    boundary = ExecutionBoundary()
    result = boundary.execute(proposal, governance_decision)
    if result.status == ExecutionStatus.AUTHORIZED_SIMULATION:
        # proceed (simulated)
    else:
        # blocked – log, alert, or escalate
    """

    def execute(
        self,
        proposal: RemediationProposal,
        governance: GovernanceDecision,
    ) -> ExecutionResult:
        """
        Enforce the ARF governance decision on a remediation proposal.

        Parameters
        ----------
        proposal : RemediationProposal
            The agent's proposed action.  The boundary does not evaluate
            this proposal; it is included for audit trail purposes only.
        governance : GovernanceDecision
            The binding governance decision produced by ARF.  Must contain
            a valid GovernanceAction.

        Returns
        -------
        ExecutionResult
            The outcome of the enforcement check, with status, message,
            and the original governance decision embedded for audit.

        Raises
        ------
        ValueError
            If the governance decision's action is not recognised.
        """
        decision = governance.decision

        if decision == GovernanceAction.APPROVE:
            return ExecutionResult(
                status=ExecutionStatus.AUTHORIZED_SIMULATION,
                governance_decision=governance,
                message=(
                    f"Action '{proposal.action_type}' on "
                    f"'{proposal.target_package}' approved for simulated execution."
                ),
            )

        elif decision == GovernanceAction.DENY:
            return ExecutionResult(
                status=ExecutionStatus.BLOCKED_POLICY,
                governance_decision=governance,
                message=(
                    f"Action '{proposal.action_type}' on "
                    f"'{proposal.target_package}' blocked by ARF policy: "
                    f"{governance.reason}"
                ),
            )

        elif decision == GovernanceAction.ESCALATE:
            return ExecutionResult(
                status=ExecutionStatus.BLOCKED_PENDING_HUMAN_APPROVAL,
                governance_decision=governance,
                message=(
                    f"Action '{proposal.action_type}' on "
                    f"'{proposal.target_package}' requires human approval: "
                    f"{governance.reason}"
                ),
            )

        else:
            raise ValueError(
                f"Unknown governance action: {decision}. "
                f"Must be one of {list(GovernanceAction)}."
            )
