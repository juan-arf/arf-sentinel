""" Hard execution boundary that enforces ARF governance decisions.

The boundary independently validates the decision and cannot be bypassed by the UI. """

from .models import RemediationProposal, GovernanceDecision, ExecutionResult

class ExecutionBoundary:
    """ Enforces ARF decisions.  APPROVE -> simulated execution DENY -> blocked
    (policy) ESCALATE -> blocked (pending human approval)"""
    """Independently enforces ARF governance decisions."""

    def execute(
        self,
        proposal: RemediationProposal,
        governance: GovernanceDecision
    ) -> ExecutionResult:
        decision = governance.decision
        if decision == "APPROVE":
            return ExecutionResult(
                status="AUTHORIZED_SIMULATION",
                governance_decision=governance
            )
        elif decision == "DENY":
            return ExecutionResult(
                status="BLOCKED_POLICY",
                governance_decision=governance
            )
        elif decision == "ESCALATE":
            return ExecutionResult(
                status="BLOCKED_PENDING_HUMAN_APPROVAL",
                governance_decision=governance
            )
        else:
            raise ValueError(f"Unknown governance decision: {decision}")
