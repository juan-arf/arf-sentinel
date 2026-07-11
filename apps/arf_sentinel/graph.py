from langgraph.graph import StateGraph, END
from .state import SentinelState
from .nodes import (
    discover_schema_node,
    investigate_dependencies_node,
    assess_blast_radius_node,
    propose_remediation_node,
    arf_governance_node,
    prepare_execution_boundary_node
)

def build_graph() -> StateGraph:
    builder = StateGraph(SentinelState)

    builder.add_node("discover_schema", discover_schema_node)
    builder.add_node("investigate_dependencies", investigate_dependencies_node)
    builder.add_node("assess_blast_radius", assess_blast_radius_node)
    builder.add_node("propose_remediation", propose_remediation_node)
    builder.add_node("arf_governance", arf_governance_node)
    builder.add_node("prepare_execution_boundary", prepare_execution_boundary_node)

    builder.set_entry_point("discover_schema")
    builder.add_edge("discover_schema", "investigate_dependencies")
    builder.add_edge("investigate_dependencies", "assess_blast_radius")
    builder.add_edge("assess_blast_radius", "propose_remediation")
    builder.add_edge("propose_remediation", "arf_governance")
    builder.add_edge("arf_governance", "prepare_execution_boundary")
    builder.add_edge("prepare_execution_boundary", END)

    return builder.compile()
