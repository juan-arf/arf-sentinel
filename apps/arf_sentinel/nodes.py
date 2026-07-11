""" LangGraph nodes implementing the investigation -> proposal -> ARF governance -> execution boundary pipeline. """

import sys, os, time, asyncio
from .models import RemediationProposal, IncidentEvidence, GovernanceDecision
from .evidence import build_evidence_from_investigation
from .arf_adapter import ARFGovernanceAdapter
from .execution_boundary import ExecutionBoundary
from .audit import AuditLogger, timestamp
from .state import SentinelState

def discover_schema_node(state: SentinelState) -> SentinelState:
    """ Simulate CRAFT schema discovery (tables GITHUB_REPOS, DEPS_DEV_V1)."""
    state["reasoning_trace"].append("Discovering enterprise schema via CRAFT...")
    state["discovered_schema"] = {
        "tables": ["GITHUB_REPOS", "DEPS_DEV_V1"],
        "columns": {"GITHUB_REPOS": ["repo_name", "dependencies"], "DEPS_DEV_V1": ["package", "version", "dependents"]}
    }
    return state

def investigate_dependencies_node(state: SentinelState) -> SentinelState:
    """ Mock dependency graph scan returning 147 repos, 89 direct, 58
    transitive, 23 paths."""
    state["reasoning_trace"].append("Investigating dependency graph...")
    state["affected_repositories"] = [{"repo": f"repo_{i}", "dependency": state["package_name"]} for i in range(147)]
    state["dependency_paths"] = [{"from": state["package_name"], "to": f"repo_{i}"} for i in range(23)]
    state["direct_dependency_count"] = 89
    state["transitive_dependency_count"] = 58
    state["affected_repository_count"] = 147
    return state

def assess_blast_radius_node(state: SentinelState) -> SentinelState:
    """ Calculate blast radius and evidence confidence from dependency data."""
    state["reasoning_trace"].append("Calculating blast radius...")
    evidence = build_evidence_from_investigation(
        incident_id=state["incident_id"],
        package_name=state["package_name"],
        vulnerability_description=state["vulnerability_description"],
        affected_repos=state["affected_repositories"],
        dependency_paths=state["dependency_paths"],
        direct_count=state["direct_dependency_count"],
        transitive_count=state["transitive_dependency_count"],
        summary="147 repositories affected across 23 transitive paths.",
        schema_found=True,
        query_success=True,
        data_completeness=0.95
    )
    state["blast_radius_score"] = evidence.blast_radius_score
    state["evidence_confidence"] = evidence.evidence_confidence
    state["investigation_summary"] = evidence.investigation_summary
    return state

def propose_remediation_node(state: SentinelState) -> SentinelState:
    """ Generate a Nemotron remediation proposal (mock)."""
    state["reasoning_trace"].append("Nemotron reasoning over evidence...")
    proposal = RemediationProposal(
        action_type="upgrade",
        target_package=state["package_name"],
        proposed_version="2.0.1",
        affected_repository_count=state["affected_repository_count"],
        rationale="Critical CVE requires immediate fix; however, upgrade may break dependent repos.",
        confidence=0.92,
        execution_scope=f"All {state['affected_repository_count']} repositories directly or transitively depending on {state['package_name']}"
    )
    state["proposed_action"] = proposal.dict()
    return state

def arf_governance_node(state: SentinelState) -> SentinelState:
    """ Evaluate the proposal through the ARFGovernanceAdapter."""
    state["reasoning_trace"].append("Submitting to ARF governance...")
    evidence = IncidentEvidence(
        incident_id=state["incident_id"],
        package_name=state["package_name"],
        vulnerability_description=state["vulnerability_description"],
        affected_repositories=state["affected_repositories"],
        dependency_paths=state["dependency_paths"],
        direct_dependency_count=state["direct_dependency_count"],
        transitive_dependency_count=state["transitive_dependency_count"],
        affected_repository_count=state["affected_repository_count"],
        evidence_confidence=state["evidence_confidence"],
        blast_radius_score=state["blast_radius_score"],
        investigation_summary=state["investigation_summary"]
    )
    proposal = RemediationProposal(**state["proposed_action"])
    adapter = ARFGovernanceAdapter()
    decision = adapter.evaluate(evidence, proposal)
    state["arf_decision"] = decision.dict()
    return state

def prepare_execution_boundary_node(state: SentinelState) -> SentinelState:
    """ Placeholder node that marks the execution boundary ready."""
    state["reasoning_trace"].append("Preparing execution boundary...")
    return state
