from .models import RemediationProposal, GovernanceDecision, ExecutionResult

class ExecutionBoundary:
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
