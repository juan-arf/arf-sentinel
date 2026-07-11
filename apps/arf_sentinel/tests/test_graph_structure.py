from apps.arf_sentinel.graph import build_graph

def test_graph_has_arf_node():
    graph = build_graph()
    nodes = graph.get_graph().nodes.keys()
    assert "arf_governance" in nodes

def test_no_direct_path_bypassing_arf():
    graph = build_graph()
    edges = graph.get_graph().edges

    # Check that there is an edge from propose_remediation to arf_governance
    has_propose_to_arf = any(
        edge.source == "propose_remediation" and edge.target == "arf_governance"
        for edge in edges
    )
    assert has_propose_to_arf, "Missing required edge: propose_remediation -> arf_governance"

    # Ensure there is NO direct edge from propose_remediation to prepare_execution_boundary
    direct_bypass = any(
        edge.source == "propose_remediation" and edge.target == "prepare_execution_boundary"
        for edge in edges
    )
    if direct_bypass:
        raise AssertionError("Found direct edge from propose_remediation to prepare_execution_boundary")
