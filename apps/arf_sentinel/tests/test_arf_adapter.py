import sys, os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../../..')))
try:
    from apps.arf_sentinel.arf_adapter import ARFGovernanceAdapter
except ImportError:
    import pytest
    pytest.skip("ARF library not available", allow_module_level=True)

from apps.arf_sentinel.models import IncidentEvidence, RemediationProposal

def test_arf_returns_valid_decision():
    evidence = IncidentEvidence(
        incident_id="test1",
        package_name="test-pkg",
        vulnerability_description="test",
        affected_repositories=[{"repo": "a"}],
        dependency_paths=[{"from": "x", "to": "y"}],
        direct_dependency_count=10,
        transitive_dependency_count=5,
        affected_repository_count=10,
        evidence_confidence=0.9,
        blast_radius_score=0.8,
        investigation_summary="test"
    )
    proposal = RemediationProposal(
        action_type="upgrade",
        target_package="test-pkg",
        proposed_version="1.0.0",
        affected_repository_count=10,
        rationale="fix",
        confidence=0.9,
        execution_scope="all"
    )
    adapter = ARFGovernanceAdapter()
    decision = adapter.evaluate(evidence, proposal)
    assert decision.decision in ("APPROVE", "DENY", "ESCALATE")
