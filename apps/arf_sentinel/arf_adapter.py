import sys
import os
from typing import Optional

try:
    from arf.core.risk_engine import ARFRiskEngine
    from arf.models.reliability_event import ReliabilityEvent
    from arf.models.governance import GovernanceDecision as ARFGovernanceDecision
    ARF_AVAILABLE = True
except ImportError:
    ARF_AVAILABLE = False

from .models import IncidentEvidence, RemediationProposal, GovernanceDecision

def _mock_arf_evaluate(blast_radius: float, confidence: float) -> dict:
    if blast_radius > 0.6:
        decision = "ESCALATE"
        reason = "Blast radius exceeds policy threshold. Autonomous execution blocked."
    else:
        decision = "APPROVE"
        reason = "Blast radius within acceptable limits."
    return {
        "decision": decision,
        "risk_probability": 0.5 + 0.5 * blast_radius,
        "blast_radius_score": blast_radius,
        "evidence_confidence": confidence,
        "expected_loss_approve": 0.71,
        "expected_loss_deny": 0.64,
        "expected_loss_escalate": 0.19,
        "policy_violations": ["blast_radius > 0.6"] if blast_radius > 0.6 else [],
        "reason": reason,
        "requires_human_approval": decision != "APPROVE"
    }

class ARFGovernanceAdapter:
    def __init__(self, policy_config: Optional[dict] = None):
        if ARF_AVAILABLE:
            self.engine = ARFRiskEngine(policy_config or {})
        else:
            self.engine = None

    def evaluate(
        self,
        incident: IncidentEvidence,
        proposal: RemediationProposal
    ) -> GovernanceDecision:
        if ARF_AVAILABLE and self.engine:
            event = ReliabilityEvent(
                event_id=incident.incident_id,
                risk_probability=0.5 + 0.5 * incident.blast_radius_score,
                blast_radius_score=incident.blast_radius_score,
                evidence_confidence=incident.evidence_confidence,
                metadata={
                    "package": incident.package_name,
                    "affected_repo_count": incident.affected_repository_count,
                    "proposal_action": proposal.action_type
                }
            )
            arf_decision = self.engine.evaluate(event)
            return GovernanceDecision(
                decision=arf_decision.decision,
                risk_probability=arf_decision.risk_probability,
                blast_radius_score=arf_decision.blast_radius_score,
                evidence_confidence=arf_decision.evidence_confidence,
                expected_loss_approve=arf_decision.expected_loss_approve,
                expected_loss_deny=arf_decision.expected_loss_deny,
                expected_loss_escalate=arf_decision.expected_loss_escalate,
                policy_violations=arf_decision.policy_violations,
                reason=arf_decision.reason,
                requires_human_approval=(arf_decision.decision == "ESCALATE" or arf_decision.decision == "DENY")
            )
        else:
            result = _mock_arf_evaluate(incident.blast_radius_score, incident.evidence_confidence)
            return GovernanceDecision(**result)
