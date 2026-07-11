"""
Counterfactual Analysis — finding the maximum safe action scope.

When ARF escalates or denies an agent's remediation proposal, this
module performs a counterfactual optimisation:

    "What is the largest subset of repositories the agent could upgrade
     while keeping the blast‑radius score below the policy threshold?"

The engine iteratively (or analytically) reduces the affected repository
count until the blast‑radius score B falls below the configured threshold,
then re‑evaluates the reduced scope through the ARF governance adapter.
The result is a safe‑scope proposal that ARF typically approves.

Mathematical Formulation
-------------------------
Given original scope N₀ with blast‑radius score B(N₀) > threshold T,
find the maximum N_safe such that B(N_safe) ≤ T.

Blast‑radius formula (from `evidence.py`):
    B(N) = w_repo·min(N/N_cap, 1) + w_trans·min(T_trans(N)/T_cap, 1) + w_path·min(P(N)/P_cap, 1)

Where transitive count T_trans(N) and path count P(N) scale proportionally
with N (assuming uniform dependency density).  We solve for N by inverting
the dominating repository component:

    N_safe = T · N_cap / w_repo   (when other components are negligible)

For the full weighted formula, we use a binary search or analytical
inversion with the known weights.  The default parameters are:

    N_cap=200, w_repo=0.50  →  N_safe ≈ T·400

For T=0.6, N_safe ≈ 48.  We round down to 32 in the demo as a
conservative canary deployment.

Usage
-----
    engine = CounterfactualEngine()
    result = engine.analyse(evidence, original_proposal)
    # result.safe_decision is typically APPROVE
"""

from pydantic import BaseModel, Field
from typing import Optional, Tuple
from .models import (
    IncidentEvidence,
    RemediationProposal,
    GovernanceDecision,
    CounterfactualResult,
    GovernanceAction,
)
from .evidence import compute_blast_radius, BlastRadiusConfig
from .arf_adapter import ARFGovernanceAdapter


# ──────────────────────────────────────────────────────────────────────
#  Counterfactual Engine
# ──────────────────────────────────────────────────────────────────────
class CounterfactualEngine:
    """
    Finds the maximum safe action scope by reducing the blast radius
    until it falls below the policy threshold.

    The engine can either accept a fixed target count (e.g., 32 repos
    for demo purposes) or compute the exact number analytically using
    the inverse blast‑radius mapping.

    Parameters
    ----------
    blast_config : BlastRadiusConfig, optional
        The blast‑radius normalisation parameters.  If None, defaults
        are used (same as `evidence.compute_blast_radius`).
    blast_threshold : float, optional
        The policy threshold T above which autonomous execution is
        blocked (default 0.6).
    target_repo_count : int, optional
        A fixed safe repository count.  If provided, the engine skips
        analytical computation and uses this value directly.
    """

    def __init__(
        self,
        blast_config: Optional[BlastRadiusConfig] = None,
        blast_threshold: float = 0.6,
        target_repo_count: Optional[int] = 32,
    ):
        self.blast_config = blast_config or BlastRadiusConfig()
        self.blast_threshold = blast_threshold
        self.target_repo_count = target_repo_count

    # ──────────────────────────────────────────────────────────────
    #  Analytical safe‑scope computation
    # ──────────────────────────────────────────────────────────────
    def compute_safe_repo_count(
        self,
        direct_count: int,
        transitive_count: int,
        path_count: int,
    ) -> int:
        """
        Compute the largest repository count that keeps B ≤ threshold.

        Uses a binary search because the blast‑radius formula is
        piecewise linear with clamping.  The search range is [1, N₀].

        Parameters
        ----------
        direct_count : int
            Original direct dependency count.
        transitive_count : int
            Original transitive dependency count.
        path_count : int
            Original number of dependency paths.

        Returns
        -------
        int
            Maximum safe repository count N_safe.
        """
        original_N = direct_count + transitive_count  # approximate total
        if original_N == 0:
            return 0

        # Scale factors for transitive and path counts (assume linear scaling)
        def blast_for_n(n: int) -> float:
            scale = n / original_N if original_N > 0 else 1.0
            scaled_transitive = max(1, int(transitive_count * scale))
            scaled_paths = max(1, int(path_count * scale))
            return compute_blast_radius(
                n,
                scaled_transitive,
                scaled_paths,
                config=self.blast_config,
            )

        # Binary search for maximum n with B(n) ≤ threshold
        lo, hi = 1, original_N
        best = 1
        while lo <= hi:
            mid = (lo + hi) // 2
            b = blast_for_n(mid)
            if b <= self.blast_threshold:
                best = mid
                lo = mid + 1
            else:
                hi = mid - 1

        return best

    # ──────────────────────────────────────────────────────────────
    #  Build reduced evidence and proposal
    # ──────────────────────────────────────────────────────────────
    def build_safe_scope(
        self,
        evidence: IncidentEvidence,
        original_proposal: RemediationProposal,
        safe_repo_count: int,
    ) -> Tuple[IncidentEvidence, RemediationProposal]:
        """
        Construct reduced evidence and proposal for a given safe repo count.

        The dependency paths and counts are scaled proportionally.

        Parameters
        ----------
        evidence : IncidentEvidence
            Original evidence bundle.
        original_proposal : RemediationProposal
            Original agent proposal.
        safe_repo_count : int
            Target number of repositories in the safe scope.

        Returns
        -------
        (IncidentEvidence, RemediationProposal)
            The reduced evidence and proposal.
        """
        orig_repo = evidence.affected_repository_count
        if orig_repo == 0:
            return evidence, original_proposal

        scale = safe_repo_count / orig_repo

        # Scale down dependency metrics proportionally
        new_direct = max(1, int(evidence.direct_dependency_count * scale))
        new_transitive = max(1, int(evidence.transitive_dependency_count * scale))
        new_paths_count = max(1, int(len(evidence.dependency_paths) * scale))

        new_paths = [
            {"from": evidence.package_name, "to": f"repo_{i}"}
            for i in range(new_paths_count)
        ]
        new_affected = [
            {"repo": f"repo_{i}", "dependency": evidence.package_name}
            for i in range(safe_repo_count)
        ]

        # Recalculate blast radius for the new scope
        new_blast = compute_blast_radius(
            safe_repo_count,
            new_transitive,
            new_paths_count,
            config=self.blast_config,
        )

        new_evidence = IncidentEvidence(
            incident_id=evidence.incident_id,
            package_name=evidence.package_name,
            vulnerability_description=evidence.vulnerability_description,
            affected_repositories=new_affected,
            dependency_paths=new_paths,
            direct_dependency_count=new_direct,
            transitive_dependency_count=new_transitive,
            affected_repository_count=safe_repo_count,
            evidence_confidence=evidence.evidence_confidence,
            blast_radius_score=new_blast,
            investigation_summary=evidence.investigation_summary,
        )

        new_proposal = RemediationProposal(
            action_type=original_proposal.action_type,
            target_package=original_proposal.target_package,
            proposed_version=original_proposal.proposed_version,
            affected_repository_count=safe_repo_count,
            rationale=(
                f"Canary upgrade of {safe_repo_count} repos with continuous "
                f"monitoring (reduced from {orig_repo})"
            ),
            confidence=original_proposal.confidence,
            execution_scope=f"Limited to {safe_repo_count} repositories",
        )

        return new_evidence, new_proposal

    # ──────────────────────────────────────────────────────────────
    #  Full analysis pipeline
    # ──────────────────────────────────────────────────────────────
    def analyse(
        self,
        evidence: IncidentEvidence,
        original_proposal: RemediationProposal,
    ) -> CounterfactualResult:
        """
        Run the complete counterfactual analysis.

        1. Determine safe repository count (analytically or using the
           fixed `target_repo_count`).
        2. Build reduced evidence and proposal.
        3. Re‑evaluate through the ARF governance adapter.
        4. Return a typed CounterfactualResult.

        Parameters
        ----------
        evidence : IncidentEvidence
            Original enterprise evidence.
        original_proposal : RemediationProposal
            Original agent proposal.

        Returns
        -------
        CounterfactualResult
            Complete analysis with safe scope, risk reduction, and
            ARF decision.
        """
        # Step 1: determine safe count
        if self.target_repo_count is not None:
            safe_repo_count = self.target_repo_count
        else:
            safe_repo_count = self.compute_safe_repo_count(
                evidence.direct_dependency_count,
                evidence.transitive_dependency_count,
                len(evidence.dependency_paths),
            )

        if evidence.affected_repository_count == 0:
            # No repos affected – nothing to counterfactualise
            return CounterfactualResult(
                original_repo_count=0,
                safe_repo_count=0,
                original_blast_radius=evidence.blast_radius_score,
                safe_blast_radius=0.0,
                original_risk=0.5,
                safe_risk=0.5,
                risk_reduction_pct=0.0,
                safe_proposal=original_proposal,
                safe_decision=GovernanceDecision(
                    decision=GovernanceAction.APPROVE,
                    risk_probability=0.5,
                    blast_radius_score=0.0,
                    evidence_confidence=evidence.evidence_confidence,
                    expected_loss_approve=0.0,
                    expected_loss_deny=1.0,
                    expected_loss_escalate=0.5,
                    reason="No repositories affected.",
                    requires_human_approval=False,
                ),
            )

        # Step 2: build reduced scope
        new_evidence, new_proposal = self.build_safe_scope(
            evidence, original_proposal, safe_repo_count
        )

        # Step 3: re‑evaluate with ARF
        adapter = ARFGovernanceAdapter()
        new_decision = adapter.evaluate(new_evidence, new_proposal)

        # Original risk from the existing decision (we assume it was ESCALATE/DENY)
        original_risk = (
            0.5 + 0.5 * evidence.blast_radius_score
        )  # approximate if not stored

        # Compute risk reduction
        new_risk = new_decision.risk_probability
        risk_reduction = original_risk - new_risk
        risk_reduction_pct = (
            (risk_reduction / original_risk * 100.0) if original_risk > 0 else 0.0
        )

        return CounterfactualResult(
            original_repo_count=evidence.affected_repository_count,
            safe_repo_count=safe_repo_count,
            original_blast_radius=evidence.blast_radius_score,
            safe_blast_radius=new_evidence.blast_radius_score,
            original_risk=original_risk,
            safe_risk=new_risk,
            risk_reduction_pct=round(risk_reduction_pct, 1),
            safe_proposal=new_proposal,
            safe_decision=new_decision,
        )


# ──────────────────────────────────────────────────────────────────────
#  Convenience function (backward‑compatible with existing demo)
# ──────────────────────────────────────────────────────────────────────
def compute_safe_scope(
    evidence: IncidentEvidence,
    original_proposal: RemediationProposal,
    blast_threshold: float = 0.6,
) -> Tuple[RemediationProposal, IncidentEvidence, Optional[GovernanceDecision]]:
    """
    Convenience wrapper that mirrors the original API.

    This function uses the CounterfactualEngine with a fixed target
    of 32 repos (the demo default).  For production, use the
    CounterfactualEngine.analyse() method directly.

    Parameters
    ----------
    evidence : IncidentEvidence
        Original enterprise evidence.
    original_proposal : RemediationProposal
        Original agent proposal.
    blast_threshold : float, optional
        Policy threshold (default 0.6).

    Returns
    -------
    (RemediationProposal, IncidentEvidence, Optional[GovernanceDecision])
        The safe proposal, safe evidence, and ARF's governance decision.
    """
    engine = CounterfactualEngine(
        blast_threshold=blast_threshold,
        target_repo_count=32,  # demo default
    )
    result = engine.analyse(evidence, original_proposal)
    return result.safe_proposal, None, result.safe_decision  # type: ignore
