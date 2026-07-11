from apps.arf_sentinel.execution_boundary import ExecutionBoundary
from apps.arf_sentinel.models import RemediationProposal, GovernanceDecision

def test_escalate_cannot_execute():
    boundary = ExecutionBoundary()
    proposal = RemediationProposal(action_type="upgrade", target_package="pkg", affected_repository_count=10, rationale="", confidence=0.9, execution_scope="")
    decision = GovernanceDecision(decision="ESCALATE", risk_probability=0.8, blast_radius_score=0.8, evidence_confidence=0.9, expected_loss_approve=0.5, expected_loss_deny=0.4, expected_loss_escalate=0.1, reason="", requires_human_approval=True)
    result = boundary.execute(proposal, decision)
    assert result.status == "BLOCKED_PENDING_HUMAN_APPROVAL"

def test_deny_cannot_execute():
    boundary = ExecutionBoundary()
    proposal = RemediationProposal(action_type="upgrade", target_package="pkg", affected_repository_count=10, rationale="", confidence=0.9, execution_scope="")
    decision = GovernanceDecision(decision="DENY", risk_probability=0.9, blast_radius_score=0.9, evidence_confidence=0.5, expected_loss_approve=0.9, expected_loss_deny=0.1, expected_loss_escalate=0.3, reason="", requires_human_approval=True)
    result = boundary.execute(proposal, decision)
    assert result.status == "BLOCKED_POLICY"

def test_approve_simulates():
    boundary = ExecutionBoundary()
    proposal = RemediationProposal(action_type="upgrade", target_package="pkg", affected_repository_count=10, rationale="", confidence=0.9, execution_scope="")
    decision = GovernanceDecision(decision="APPROVE", risk_probability=0.1, blast_radius_score=0.1, evidence_confidence=0.9, expected_loss_approve=0.0, expected_loss_deny=0.5, expected_loss_escalate=0.3, reason="", requires_human_approval=False)
    result = boundary.execute(proposal, decision)
    assert result.status == "AUTHORIZED_SIMULATION"
