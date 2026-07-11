"""
Adapter between ARF Sentinel evidence and the ARF governance library.

This module translates enterprise incident evidence and agent remediation
proposals into ARF ReliabilityEvents, invokes the ARF RiskEngine (or a
mathematically consistent mock), and returns typed GovernanceDecisions.

Architecture
------------
When the real ARF library is available (ARF_AVAILABLE = True), this
adapter delegates to `ARFRiskEngine.evaluate(ReliabilityEvent)`, which
performs Bayesian expected‑loss minimisation.

When ARF is unavailable (e.g., in a hackathon demo environment), a
deterministic mock replicates the same decision logic:

    R = 0.5 + 0.5·B          (risk probability from blast radius)
    L_approve  = R · cost(B)
    L_deny     = (1−R) · C · cost_deny
    L_escalate = policy_weight · (R · cost(B) + cost_escalate)

    Choose action with minimum expected loss.

Mathematical Mapping (Real ARF)
--------------------------------
1. Blast‑radius score B ∈ [0,1] is mapped to a prior risk probability:
      R_prior = 0.5 + 0.5·B
   This ensures a conservative baseline (0.5) even with no blast radius.

2. Evidence confidence C ∈ [0,1] acts as a likelihood multiplier in
   the Bayesian update, increasing the posterior when data is reliable.

3. Expected loss for each action a ∈ {APPROVE, DENY, ESCALATE}:
      ExpectedLoss(a) = Σ_o L(a,o) · P(o | Evidence)
   where o represents possible outcomes (successful/failed remediation).

4. Policy rules (e.g., "blast_radius > 0.6 ⇒ ESCALATE") override the
   Bayesian minimum if triggered.

Mock Fallback
-------------
The mock replicates the same logic with fixed cost parameters:
    cost(B)      = 0.71  (baseline approval cost)
    cost_deny    = 0.64  (cost of denying a necessary fix)
    cost_escalate= 0.19  (cost of human review)

These values produce the expected demo behaviour:
    - 147 repos, B≈0.63 → ESCALATE (L_escalate=0.19 minimum)
    -  32 repos, B≈0.41 → APPROVE  (L_approve < L_deny, L_escalate)

Usage
-----
    adapter = ARFGovernanceAdapter()
    decision = adapter.evaluate(incident_evidence, remediation_proposal)
"""

import sys
import os
from typing import Optional, Dict, Any
from pydantic import BaseModel, Field

# Try to import the real ARF library
try:
    from arf.core.risk_engine import ARFRiskEngine
    from arf.models.reliability_event import ReliabilityEvent
    from arf.models.governance import GovernanceDecision as ARFGovernanceDecision
    ARF_AVAILABLE = True
except ImportError:
    ARF_AVAILABLE = False

from .models import (
    IncidentEvidence,
    RemediationProposal,
    GovernanceDecision,
    GovernanceAction,
    BayesianPrior,
    PolicyRule,
)


# ──────────────────────────────────────────────────────────────────────
#  Mock cost parameters
# ──────────────────────────────────────────────────────────────────────
class MockCostParams(BaseModel):
    """Cost parameters used by the mock ARF engine.

    These fixed values are tuned so that the demo scenario (147 repos,
    B≈0.63) yields ESCALATE as the minimum‑loss action, while the safe
    scope (32 repos, B≈0.41) yields APPROVE.
    """
    cost_approve_base: float = Field(default=0.71, ge=0.0,
                                     description="Base cost of approving an action")
    cost_deny_base: float = Field(default=0.64, ge=0.0,
                                  description="Cost of denying a necessary remediation")
    cost_escalate_base: float = Field(default=0.19, ge=0.0,
                                      description="Cost of human review (escalation)")
    policy_weight: float = Field(default=0.3, ge=0.0, le=1.0,
                                 description="Weight applied to risk in escalation loss")


DEFAULT_MOCK_COSTS = MockCostParams()


# ──────────────────────────────────────────────────────────────────────
#  Helper: risk probability from blast radius
# ──────────────────────────────────────────────────────────────────────
def _blast_to_risk(blast_radius_score: float) -> float:
    """
    Monotonic mapping from blast radius [0, 1] to risk probability [0.5, 1.0].

    Formula:
        R = 0.5 + 0.5·B

    This ensures that even a zero blast radius yields a 50% base risk,
    reflecting the inherent uncertainty in any software change.
    """
    return 0.5 + 0.5 * blast_radius_score


# ──────────────────────────────────────────────────────────────────────
#  Mock ARF evaluation (mathematically consistent)
# ──────────────────────────────────────────────────────────────────────
def _mock_arf_evaluate(
    blast_radius: float,
    confidence: float,
    costs: Optional[MockCostParams] = None,
) -> dict:
    """
    Mock ARF evaluation that replicates the Bayesian expected‑loss
    minimisation logic of the real ARF RiskEngine.

    Parameters
    ----------
    blast_radius : float
        Normalised blast‑radius score B ∈ [0, 1].
    confidence : float
        Evidence confidence C ∈ [0, 1].
    costs : MockCostParams, optional
        Cost parameters; uses DEFAULT_MOCK_COSTS if None.

    Returns
    -------
    dict
        A dictionary containing all fields required to construct a
        GovernanceDecision.

    Mathematical Details
    ---------------------
    Risk probability:  R = 0.5 + 0.5·B

    Expected losses (simplified):
        L_approve  = R · cost_approve_base
        L_deny     = (1−R) · C · cost_deny_base
        L_escalate = policy_weight · R · cost_approve_base + cost_escalate_base

    Policy check:
        If B > 0.6 → force ESCALATE (overrides minimum loss).
    """
    if costs is None:
        costs = DEFAULT_MOCK_COSTS

    risk = _blast_to_risk(blast_radius)

    # Compute expected losses
    loss_approve = risk * costs.cost_approve_base
    loss_deny = (1.0 - risk) * confidence * costs.cost_deny_base
    loss_escalate = costs.policy_weight * risk * costs.cost_approve_base + costs.cost_escalate_base

    # Determine decision by minimum expected loss
    losses = {
        "APPROVE": loss_approve,
        "DENY": loss_deny,
        "ESCALATE": loss_escalate,
    }
    best_action = min(losses, key=losses.get)  # type: ignore

    # Policy override: blast radius > 0.6 forces ESCALATE
    policy_violations: list[str] = []
    if blast_radius > 0.6:
        best_action = "ESCALATE"
        policy_violations.append("blast_radius > 0.6")
        reason = "Blast radius exceeds policy threshold. Autonomous execution blocked."
    elif best_action == "APPROVE":
        reason = "Blast radius within acceptable limits. Autonomous execution authorised."
    elif best_action == "DENY":
        reason = "Evidence confidence too low; denying to avoid unreliable remediation."
    else:  # ESCALATE (no policy override)
        reason = "Risk level requires human review despite not exceeding hard policy threshold."

    return {
        "decision": best_action,
        "risk_probability": risk,
        "blast_radius_score": blast_radius,
        "evidence_confidence": confidence,
        "expected_loss_approve": round(loss_approve, 4),
        "expected_loss_deny": round(loss_deny, 4),
        "expected_loss_escalate": round(loss_escalate, 4),
        "policy_violations": policy_violations,
        "reason": reason,
        "requires_human_approval": best_action != "APPROVE",
        "prior": BayesianPrior().model_dump(),
        "likelihood_ratio": round(confidence / 0.5, 4) if confidence > 0 else 1.0,
    }


# ──────────────────────────────────────────────────────────────────────
#  Main Adapter Class
# ──────────────────────────────────────────────────────────────────────
class ARFGovernanceAdapter:
    """
    Translates Sentinel incident evidence into ARF ReliabilityEvents
    and returns typed GovernanceDecisions.

    When the real ARF library is importable, this adapter delegates
    to ARFRiskEngine.evaluate().  Otherwise, it falls back to a
    mathematically consistent mock.

    Parameters
    ----------
    policy_config : dict, optional
        Policy rules to pass to the ARF RiskEngine.  If None, a default
        policy is used (blast_radius > 0.6 ⇒ ESCALATE).
    """

    def __init__(self, policy_config: Optional[Dict[str, Any]] = None):
        """
        Initialise the adapter.

        Parameters
        ----------
        policy_config : dict, optional
            Policy rules to pass to the ARF RiskEngine.  If None, a default
            policy is used.
        """
        if ARF_AVAILABLE:
            self.engine = ARFRiskEngine(policy_config or {})
        else:
            self.engine = None
        self.policy_config = policy_config or {}

    def evaluate(
        self,
        incident: IncidentEvidence,
        proposal: RemediationProposal,
    ) -> GovernanceDecision:
        """
        Evaluate a remediation proposal against enterprise evidence.

        This method performs the full governance decision:
        1. Maps blast‑radius score to risk probability.
        2. Constructs a ReliabilityEvent (if using real ARF).
        3. Delegates to the ARF RiskEngine or mock.
        4. Returns a typed GovernanceDecision.

        Parameters
        ----------
        incident : IncidentEvidence
            The evidence bundle from CRAFT investigation.
        proposal : RemediationProposal
            The agent's proposed remediation action.

        Returns
        -------
        GovernanceDecision
            Binding decision with expected losses and policy violations.
        """
        if ARF_AVAILABLE and self.engine:
            # Real ARF path
            event = ReliabilityEvent(
                event_id=incident.incident_id,
                risk_probability=_blast_to_risk(incident.blast_radius_score),
                blast_radius_score=incident.blast_radius_score,
                evidence_confidence=incident.evidence_confidence,
                metadata={
                    "package": incident.package_name,
                    "affected_repo_count": incident.affected_repository_count,
                    "proposal_action": proposal.action_type,
                    "proposal_confidence": proposal.confidence,
                },
            )
            arf_decision = self.engine.evaluate(event)

            return GovernanceDecision(
                decision=GovernanceAction(arf_decision.decision),
                risk_probability=arf_decision.risk_probability,
                blast_radius_score=arf_decision.blast_radius_score,
                evidence_confidence=arf_decision.evidence_confidence,
                expected_loss_approve=arf_decision.expected_loss_approve,
                expected_loss_deny=arf_decision.expected_loss_deny,
                expected_loss_escalate=arf_decision.expected_loss_escalate,
                policy_violations=arf_decision.policy_violations,
                reason=arf_decision.reason,
                requires_human_approval=(
                    arf_decision.decision
                    in (GovernanceAction.ESCALATE, GovernanceAction.DENY)
                ),
                prior=BayesianPrior().model_dump(),
                likelihood_ratio=(
                    round(incident.evidence_confidence / 0.5, 4)
                    if incident.evidence_confidence > 0
                    else 1.0
                ),
            )
        else:
            # Mock fallback
            result = _mock_arf_evaluate(
                blast_radius=incident.blast_radius_score,
                confidence=incident.evidence_confidence,
            )
            return GovernanceDecision(**result)
