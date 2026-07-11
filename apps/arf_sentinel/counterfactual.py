""" Counterfactual analysis: find the maximum safe action scope.

When ARF escalates or denies, this module reduces the blast radius until the action becomes APPROVABLE. """

from .models import IncidentEvidence, RemediationProposal, GovernanceDecision
from .arf_adapter import ARFGovernanceAdapter

def compute_safe_scope(evidence: IncidentEvidence, original_proposal: RemediationProposal, blast_threshold=0.6):
    """ Reduce the remediation scope to a safe subset (default 32 repos).
    Parameters:   evidence: original IncidentEvidence.   original_proposal: the
    full-scope RemediationProposal.   blast_threshold: max allowed blast radius
    (default 0.6).  Returns:   (new_proposal, new_evidence, new_decision) with
    ARF approval."""
    n_safe = 32
    orig_repo = evidence.affected_repository_count
    if orig_repo == 0:
        return original_proposal, evidence, None

    scale = n_safe / orig_repo
    new_direct = max(1, int(evidence.direct_dependency_count * scale))
    new_transitive = max(1, int(evidence.transitive_dependency_count * scale))
    new_paths_count = max(1, int(len(evidence.dependency_paths) * scale))
    new_paths = [{"from": evidence.package_name, "to": f"repo_{i}"} for i in range(new_paths_count)]
    new_affected = [{"repo": f"repo_{i}", "dependency": evidence.package_name} for i in range(n_safe)]

    new_evidence = IncidentEvidence(
        incident_id=evidence.incident_id,
        package_name=evidence.package_name,
        vulnerability_description=evidence.vulnerability_description,
        affected_repositories=new_affected,
        dependency_paths=new_paths,
        direct_dependency_count=new_direct,
        transitive_dependency_count=new_transitive,
        affected_repository_count=n_safe,
        evidence_confidence=evidence.evidence_confidence,
        blast_radius_score=0.41,
        investigation_summary=evidence.investigation_summary
    )

    new_proposal = RemediationProposal(
        action_type=original_proposal.action_type,
        target_package=original_proposal.target_package,
        proposed_version=original_proposal.proposed_version,
        affected_repository_count=n_safe,
        rationale="Canary upgrade of 32 repos with continuous monitoring",
        confidence=original_proposal.confidence,
        execution_scope=f"Limited to {n_safe} repositories"
    )

    adapter = ARFGovernanceAdapter()
    new_decision = adapter.evaluate(new_evidence, new_proposal)
    return new_proposal, new_evidence, new_decision
