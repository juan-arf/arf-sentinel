import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import streamlit as st
import json, time, asyncio
from pathlib import Path
from datetime import datetime

from arf_sentinel.config import settings
from arf_sentinel.models import RemediationProposal, GovernanceDecision, ExecutionResult, AuditRecord
from arf_sentinel.evidence import build_evidence_from_investigation
from arf_sentinel.arf_adapter import ARFGovernanceAdapter
from arf_sentinel.execution_boundary import ExecutionBoundary
from arf_sentinel.audit import AuditLogger, timestamp
from arf_sentinel.state import SentinelState
from arf_sentinel.graph import build_graph

st.set_page_config(page_title="ARF Sentinel", layout="wide")
st.title("ARF SENTINEL")
st.markdown("### Autonomous Blast-Radius Governance for Enterprise Agents")
st.caption("CRAFT investigates. Nemotron reasons. ARF decides whether the agent is allowed to act.")

with st.sidebar:
    st.header("Incident Input")
    package_name = st.text_input("Package Name", value="urllib3")
    vuln_desc = st.text_area("Vulnerability Description", value="CVE-2025-1234 – Remote code execution in urllib3 < 2.0.1")
    demo_mode = st.checkbox("Use Demo Fixture", value=settings.DEMO_MODE)
    investigate_btn = st.button("INVESTIGATE INCIDENT")

if "state" not in st.session_state:
    st.session_state.state = None
    st.session_state.graph_result = None
    st.session_state.arf_decision = None
    st.session_state.execution_result = None
    st.session_state.step = 0

graph = build_graph()

if investigate_btn:
    incident_id = f"incident_{int(time.time())}"
    state = SentinelState(
        incident_id=incident_id,
        package_name=package_name,
        vulnerability_description=vuln_desc,
        discovered_schema={},
        affected_repositories=[],
        dependency_paths=[],
        direct_dependency_count=0,
        transitive_dependency_count=0,
        affected_repository_count=0,
        evidence_confidence=0.0,
        blast_radius_score=0.0,
        investigation_summary="",
        proposed_action={},
        arf_event={},
        arf_decision={},
        execution_status="",
        sql_queries=[],
        reasoning_trace=[],
        errors=[]
    )

    with st.spinner("Running investigation graph..."):
        result = graph.invoke(state)
        st.session_state.state = result
        st.session_state.graph_result = result

    arf_dec_raw = result.get("arf_decision", {})
    if arf_dec_raw:
        st.session_state.arf_decision = GovernanceDecision(**arf_dec_raw)
    st.session_state.step = 1

if st.session_state.state:
    state = st.session_state.state
    col1, col2 = st.columns([2, 3])

    with col1:
        st.subheader("Phase 1 – Enterprise Investigation")
        st.write(f"**Repositories affected:** {state['affected_repository_count']}")
        st.write(f"**Direct dependencies:** {state['direct_dependency_count']}")
        st.write(f"**Transitive dependencies:** {state['transitive_dependency_count']}")
        st.write(f"**Dependency paths:** {len(state['dependency_paths'])}")
        with st.expander("Investigation Trace"):
            for trace in state["reasoning_trace"]:
                st.write(f"- {trace}")

    with col2:
        st.subheader("Phase 2 – Agent Proposal")
        if state["proposed_action"]:
            proposal = RemediationProposal(**state["proposed_action"])
            st.info(f"""
            **AGENT PROPOSED ACTION**  
            Upgrade `{proposal.target_package}` across {proposal.affected_repository_count} repositories.  
            **Confidence:** {proposal.confidence:.2f}  
            *Agent recommendation — not execution authorization.*
            """)

        st.subheader("Phase 3 – ARF Governance Decision")
        if st.session_state.arf_decision:
            decision = st.session_state.arf_decision
            color = {
                "APPROVE": "green",
                "DENY": "red",
                "ESCALATE": "orange"
            }.get(decision.decision, "grey")
            st.markdown(f"### ARF DECISION: <span style='color:{color}'>{decision.decision}</span>", unsafe_allow_html=True)
            st.write(f"**Risk Probability:** {decision.risk_probability:.2f}")
            st.write(f"**Blast Radius:** {decision.blast_radius_score:.2f}")
            st.write(f"**Evidence Confidence:** {decision.evidence_confidence:.2f}")
            st.write("**Expected Losses:**")
            st.write(f"- APPROVE: {decision.expected_loss_approve:.2f}")
            st.write(f"- DENY: {decision.expected_loss_deny:.2f}")
            st.write(f"- ESCALATE: {decision.expected_loss_escalate:.2f}")
            st.write(f"**Policy Violations:** {decision.policy_violations}")
            st.write(f"**Reason:** {decision.reason}")

        st.subheader("Phase 4 – Execution Boundary")
        if st.button("EXECUTE REMEDIATION"):
            if not st.session_state.arf_decision:
                st.error("No governance decision available.")
            else:
                boundary = ExecutionBoundary()
                proposal = RemediationProposal(**state["proposed_action"])
                result = boundary.execute(proposal, st.session_state.arf_decision)
                st.session_state.execution_result = result

                if result.status == "AUTHORIZED_SIMULATION":
                    st.success("Execution authorized (simulated).")
                elif result.status == "BLOCKED_POLICY":
                    st.error("BLOCKED BY ARF — Policy violation.")
                elif result.status == "BLOCKED_PENDING_HUMAN_APPROVAL":
                    st.error("BLOCKED BY ARF — Human approval required.")
                    st.markdown("**Agent execution authority denied.**")
                    st.markdown("The agent proposed the action. The agent did not authorize it. ARF independently evaluated execution risk.")

    if st.session_state.arf_decision:
        run_dir = f"runs/sentinel_{state['incident_id']}_{timestamp()}"
        logger = AuditLogger(run_dir)
        logger.save_artifact("incident.json", {"package": package_name, "vuln": vuln_desc})
        logger.save_artifact("evidence_bundle.json", {
            "affected_repos": state["affected_repositories"],
            "paths": state["dependency_paths"]
        })
        logger.save_artifact("remediation_proposal.json", state["proposed_action"])
        logger.save_artifact("arf_decision.json", st.session_state.arf_decision.dict())
        if st.session_state.execution_result:
            logger.save_artifact("execution_result.json", st.session_state.execution_result.dict())
        logger.log(AuditRecord(
            timestamp=timestamp(),
            incident_id=state["incident_id"],
            event_type="GOVERNANCE_EVALUATED",
            actor="ARF",
            action="evaluate",
            decision=st.session_state.arf_decision.decision
        ))
        st.success(f"Audit artifacts saved to `{run_dir}`")
