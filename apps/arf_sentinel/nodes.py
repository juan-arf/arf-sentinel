"""
LangGraph nodes for the ARF Sentinel investigation pipeline.

These functions implement the staged workflow that processes an incident
from initial discovery through ARF governance to execution boundary.

The pipeline order is strictly enforced by the StateGraph in `graph.py`:

    discover_schema → investigate_dependencies → assess_blast_radius
    → propose_remediation → arf_governance → prepare_execution_boundary

Important: In this hackathon prototype, the nodes produce deterministic,
pre‑seeded results (147 repos, 89 direct, 58 transitive, etc.). In a
production deployment they would be replaced with live CRAFT queries,
Nemotron LLM calls, and the real ARF RiskEngine.  The mock data is
clearly marked in each function's docstring.
"""

import sys, os, time, asyncio
from .models import RemediationProposal, IncidentEvidence, GovernanceDecision
from .evidence import build_evidence_from_investigation
from .arf_adapter import ARFGovernanceAdapter
from .execution_boundary import ExecutionBoundary
from .audit import AuditLogger, timestamp
from .state import SentinelState


def discover_schema_node(state: SentinelState) -> SentinelState:
    """
    Simulate CRAFT schema discovery.

    In the demo, this returns a fixed schema with two tables:

        - GITHUB_REPOS: repo_name, dependencies
        - DEPS_DEV_V1: package, version, dependents

    In production, this node would call CRAFT `search_schema` and
    `get_schema` MCP tools to discover the actual database structure.

    Args:
        state: The shared SentinelState dictionary.

    Returns:
        Updated SentinelState with `discovered_schema` set.
    """
    state["reasoning_trace"].append("Discovering enterprise schema via CRAFT...")
    state["discovered_schema"] = {
        "tables": ["GITHUB_REPOS", "DEPS_DEV_V1"],
        "columns": {
            "GITHUB_REPOS": ["repo_name", "dependencies"],
            "DEPS_DEV_V1": ["package", "version", "dependents"],
        },
    }
    return state


def investigate_dependencies_node(state: SentinelState) -> SentinelState:
    """
    Mock dependency graph scan.

    Returns pre‑seeded demo data:

        - 147 affected repositories
        - 89 direct dependencies
        - 58 transitive dependencies
        - 23 unique dependency paths

    In production, this node would generate SQL via CRAFT `generate_sql`
    and execute queries with `execute_query` to obtain real dependency
    data from the GITHUB_REPOS and DEPS_DEV_V1 datasets.

    Args:
        state: The shared SentinelState dictionary.

    Returns:
        Updated SentinelState with dependency counts and lists.
    """
    state["reasoning_trace"].append("Investigating dependency graph...")
    package = state["package_name"]

    state["affected_repositories"] = [
        {"repo": f"repo_{i}", "dependency": package} for i in range(147)
    ]
    state["dependency_paths"] = [
        {"from": package, "to": f"repo_{i}"} for i in range(23)
    ]
    state["direct_dependency_count"] = 89
    state["transitive_dependency_count"] = 58
    state["affected_repository_count"] = 147
    return state


def assess_blast_radius_node(state: SentinelState) -> SentinelState:
    """
    Calculate blast‑radius score and evidence confidence.

    Uses the `evidence.build_evidence_from_investigation` function to
    normalise dependency metrics into:

        - blast_radius_score (B ∈ [0,1])
        - evidence_confidence (C ∈ [0,1])

    These two signals feed directly into the ARF Bayesian Risk Engine.

    Args:
        state: The shared SentinelState dictionary.

    Returns:
        Updated SentinelState with blast_radius_score, evidence_confidence,
        and investigation_summary set.
    """
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
        data_completeness=0.95,
    )

    state["blast_radius_score"] = evidence.blast_radius_score
    state["evidence_confidence"] = evidence.evidence_confidence
    state["investigation_summary"] = evidence.investigation_summary
    return state


def propose_remediation_node(state: SentinelState) -> SentinelState:
    """
    Generate a remediation proposal (mock Nemotron).

    Produces a deterministic proposal:

        - Action: upgrade urllib3 to 2.0.1
        - Scope: all 147 affected repositories
        - Confidence: 0.92

    In production, this node would call the Nebius Nemotron LLM with
    the evidence bundle and extract a structured RemediationProposal.

    Args:
        state: The shared SentinelState dictionary.

    Returns:
        Updated SentinelState with `proposed_action` set.
    """
    state["reasoning_trace"].append("Nemotron reasoning over evidence...")

    proposal = RemediationProposal(
        action_type="upgrade",
        target_package=state["package_name"],
        proposed_version="2.0.1",
        affected_repository_count=state["affected_repository_count"],
        rationale=(
            "Critical CVE requires immediate fix; however, upgrade may "
            "break dependent repos."
        ),
        confidence=0.92,
        execution_scope=(
            f"All {state['affected_repository_count']} repositories directly "
            f"or transitively depending on {state['package_name']}"
        ),
    )
    state["proposed_action"] = proposal.model_dump()
    return state


def arf_governance_node(state: SentinelState) -> SentinelState:
    """
    Submit the proposal and evidence to ARF governance.

    Constructs an IncidentEvidence and RemediationProposal from the
    current state, invokes the ARFGovernanceAdapter, and stores the
    resulting GovernanceDecision.

    This node is **mandatory** – the graph topology ensures that no
    execution can occur without passing through this node.

    Args:
        state: The shared SentinelState dictionary.

    Returns:
        Updated SentinelState with `arf_decision` set.
    """
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
        investigation_summary=state["investigation_summary"],
    )

    proposal = RemediationProposal(**state["proposed_action"])
    adapter = ARFGovernanceAdapter()
    decision = adapter.evaluate(evidence, proposal)
    state["arf_decision"] = decision.model_dump()
    return state


def prepare_execution_boundary_node(state: SentinelState) -> SentinelState:
    """
    Placeholder node that signals readiness for the execution boundary.

    In a full deployment, this node might perform final validation or
    logging before the ExecutionBoundary is invoked.  In the demo, it
    simply adds a trace entry.

    Args:
        state: The shared SentinelState dictionary.

    Returns:
        The unchanged state.
    """
    state["reasoning_trace"].append("Preparing execution boundary...")
    return state
