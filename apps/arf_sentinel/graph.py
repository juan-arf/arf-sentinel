"""
LangGraph state machine builder for the ARF Sentinel investigation pipeline.

This module constructs a directed, acyclic graph that guarantees the
following architectural invariant:

    "The agent may propose an action. The agent cannot grant itself authority."

The graph topology is:

    START
      │
      v
    discover_schema
      │
      v
    investigate_dependencies
      │
      v
    assess_blast_radius
      │
      v
    propose_remediation    ← the agent speaks here
      │
      v
    arf_governance          ← independent evaluation (MANDATORY)
      │
      v
    prepare_execution_boundary
      │
      v
    END

There is no edge from `propose_remediation` directly to
`prepare_execution_boundary`.  The LangGraph compiler enforces that every
path from the agent's proposal to the execution boundary MUST pass through
the `arf_governance` node.  This structural guarantee is verified by tests
in `tests/test_graph_structure.py`.

The state object shared by all nodes is `SentinelState`, a TypedDict
defined in `state.py`.  It carries incident metadata, dependency counts,
blast‑radius scores, the agent's proposal, the ARF decision, and an
execution status.
"""

from langgraph.graph import StateGraph, END
from .state import SentinelState
from .nodes import (
    discover_schema_node,
    investigate_dependencies_node,
    assess_blast_radius_node,
    propose_remediation_node,
    arf_governance_node,
    prepare_execution_boundary_node,
)


def build_graph() -> StateGraph:
    """
    Construct and compile the ARF Sentinel investigation graph.

    Nodes (in execution order):
        - discover_schema: simulate CRAFT schema discovery
        - investigate_dependencies: mock dependency graph scan
        - assess_blast_radius: compute blast‑radius score & evidence confidence
        - propose_remediation: generate a Nemotron proposal (mock)
        - arf_governance: evaluate proposal through ARF (Bayesian)
        - prepare_execution_boundary: placeholder for final validation

    Edges:
        Each node has exactly one outgoing edge to the next node, forming a
        strictly linear pipeline.  The `arf_governance` node is mandatory;
        there is no alternative path.

    Returns
    -------
    langgraph.graph.StateGraph
        A compiled StateGraph ready for invocation via `.invoke(state)`.
    """
    builder = StateGraph(SentinelState)

    # -- Register nodes --
    builder.add_node("discover_schema", discover_schema_node)
    builder.add_node("investigate_dependencies", investigate_dependencies_node)
    builder.add_node("assess_blast_radius", assess_blast_radius_node)
    builder.add_node("propose_remediation", propose_remediation_node)
    builder.add_node("arf_governance", arf_governance_node)
    builder.add_node("prepare_execution_boundary", prepare_execution_boundary_node)

    # -- Define entry point --
    builder.set_entry_point("discover_schema")

    # -- Linear edge chain (no bypass) --
    builder.add_edge("discover_schema", "investigate_dependencies")
    builder.add_edge("investigate_dependencies", "assess_blast_radius")
    builder.add_edge("assess_blast_radius", "propose_remediation")
    builder.add_edge("propose_remediation", "arf_governance")
    builder.add_edge("arf_governance", "prepare_execution_boundary")
    builder.add_edge("prepare_execution_boundary", END)

    return builder.compile()
