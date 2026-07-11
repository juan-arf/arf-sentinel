import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import streamlit as st
import json, time
from datetime import datetime

from arf_sentinel.config import settings
from arf_sentinel.models import RemediationProposal, GovernanceDecision, ExecutionResult, AuditRecord
from arf_sentinel.evidence import build_evidence_from_investigation
from arf_sentinel.arf_adapter import ARFGovernanceAdapter
from arf_sentinel.execution_boundary import ExecutionBoundary
from arf_sentinel.audit import AuditLogger, timestamp
from arf_sentinel.state import SentinelState
from arf_sentinel.graph import build_graph
from arf_sentinel.counterfactual import compute_safe_scope
from arf_sentinel.visualizations import risk_comparison_chart, expected_loss_chart, blast_radius_treemap
from arf_sentinel.audit_pdf import generate_audit_pdf

# ── Dark theme & mobile‑first CSS ──
st.set_page_config(page_title="ARF SENTINEL", layout="wide")
st.markdown("""
<style>
    body { background-color: #0a0a0a; color: #e0e0e0; }
    .stApp { background-color: #0a0a0a; }
    .stButton > button {
        background-color: #00FF88; color: black; font-weight: bold;
        border: none; border-radius: 4px; padding: 0.5rem 2rem;
        width: 100%;
    }
    .stButton > button:hover { background-color: #00cc66; }
    .phase-title { color: #00bcd4; font-size: 1.3rem; margin-top: 1.5rem; }
    .big-number { font-size: 3rem; font-weight: bold; }
    .bayesian-box { background: #1e1e1e; padding: 1.5rem; border-radius: 10px; margin: 1rem 0; font-family: monospace; }
    .risk-bar { height: 20px; border-radius: 10px; margin: 0.5rem 0; }
    @media (max-width: 768px) {
        .stColumns { flex-direction: column !important; }
        .big-number { font-size: 2rem !important; }
        .phase-title { font-size: 1rem !important; }
        .stButton > button { width: 100% !important; }
    }
</style>
""", unsafe_allow_html=True)

# ── Session State ──
if "phase" not in st.session_state:
    st.session_state.phase = 0
    st.session_state.state = None
    st.session_state.arf_decision = None
    st.session_state.execution_result = None
    st.session_state.safe_proposal = None
    st.session_state.safe_decision = None
    st.session_state.incident_id = None
    st.session_state.pdf_bytes = None

graph = build_graph()

def advance_phase(new_phase):
    st.session_state.phase = new_phase

# ── Reusable Bayesian explanation (LaTeX) ──
def render_bayesian_explanation(prior_risk, evidence_conf, posterior_risk):
    likelihood_ratio = posterior_risk / prior_risk if prior_risk > 0 else 1
    st.latex(r"P(Risk \mid Evidence) = \frac{P(Evidence \mid Risk) \, P(Risk)}{P(Evidence)}")
    col1, col2, col3 = st.columns(3)
    col1.metric("Prior Risk", f"{prior_risk:.0%}")
    col2.metric("Evidence Strength", f"{evidence_conf:.0%}")
    col3.metric("Likelihood Ratio", f"{likelihood_ratio:.1f}x")
    st.markdown(f"""
    <div style="display:flex; justify-content:space-between; margin:1rem 0;">
        <span>Prior: {prior_risk:.0%}</span>
        <span style="color:#00bcd4;">→ Evidence update →</span>
        <span>Posterior: {posterior_risk:.0%}</span>
    </div>
    <div class="risk-bar" style="background:linear-gradient(to right, #00bcd4 50%, #e74c3c {posterior_risk*100}%);">
        <div style="width:{posterior_risk*100}%; background:#e74c3c; height:100%; border-radius:10px;"></div>
    </div>
    """, unsafe_allow_html=True)

# ── Phase 0: Mission Control (animated workflow SVG) ──
if st.session_state.phase == 0:
    # Animated workflow SVG (cyberpunk aesthetic)
    st.components.v1.html("""
    <style>
        @import url('https://fonts.googleapis.com/css2?family=Share+Tech+Mono&display=swap');
        body { background: #0a0a0a; margin: 0; display: flex; justify-content: center; align-items: center; height: 100vh; }
        .workflow { width: 100%; max-width: 800px; }
        .node { font-family: 'Share Tech Mono', monospace; font-size: 14px; fill: #fff; }
        .edge { stroke-width: 3; fill: none; stroke-dasharray: 6 4; }
        @keyframes dash { to { stroke-dashoffset: -20; } }
        .flow { animation: dash 1s linear infinite; }
        .glow { filter: drop-shadow(0 0 6px); }
    </style>
    <svg class="workflow" viewBox="0 0 800 300">
        <defs>
            <marker id="arrow" markerWidth="8" markerHeight="6" refX="8" refY="3" orient="auto">
                <polygon points="0 0, 8 3, 0 6" fill="#e0e0e0" />
            </marker>
        </defs>
        <!-- Incident icon -->
        <circle cx="30" cy="130" r="10" fill="#e74c3c" />
        <text x="30" y="134" text-anchor="middle" class="node" font-size="12">!</text>
        <!-- Nodes -->
        <rect x="20" y="100" width="100" height="60" rx="8" fill="#1e1e1e" stroke="#00bcd4" stroke-width="2" class="glow"/>
        <text x="70" y="135" text-anchor="middle" class="node" fill="#00bcd4">CRAFT</text>
        <rect x="220" y="100" width="120" height="60" rx="8" fill="#1e1e1e" stroke="#9b59b6" stroke-width="2" class="glow"/>
        <text x="280" y="135" text-anchor="middle" class="node" fill="#9b59b6">NEMOTRON</text>
        <rect x="440" y="100" width="100" height="60" rx="8" fill="#1e1e1e" stroke="#00FF88" stroke-width="2" class="glow"/>
        <text x="490" y="135" text-anchor="middle" class="node" fill="#00FF88">ARF</text>
        <rect x="640" y="100" width="130" height="60" rx="8" fill="#1e1e1e" stroke="#e74c3c" stroke-width="2" class="glow"/>
        <text x="705" y="135" text-anchor="middle" class="node" fill="#e74c3c">EXECUTION</text>
        <!-- Animated arrows -->
        <line x1="120" y1="130" x2="210" y2="130" class="edge flow" stroke="#00bcd4" marker-end="url(#arrow)"/>
        <line x1="340" y1="130" x2="430" y2="130" class="edge flow" stroke="#9b59b6" marker-end="url(#arrow)"/>
        <line x1="540" y1="130" x2="630" y2="130" class="edge flow" stroke="#00FF88" marker-end="url(#arrow)"/>
        <!-- Labels -->
        <text x="165" y="95" text-anchor="middle" class="node" font-size="10" fill="#888">Enterprise Evidence</text>
        <text x="385" y="95" text-anchor="middle" class="node" font-size="10" fill="#888">Remediation Proposal</text>
        <text x="585" y="95" text-anchor="middle" class="node" font-size="10" fill="#888">Governance Decision</text>
        <text x="70" y="200" text-anchor="middle" class="node" font-size="12" fill="#666">Discover</text>
        <text x="280" y="200" text-anchor="middle" class="node" font-size="12" fill="#666">Reason</text>
        <text x="490" y="200" text-anchor="middle" class="node" font-size="12" fill="#666">Authorize</text>
        <text x="705" y="200" text-anchor="middle" class="node" font-size="12" fill="#666">Enforce</text>
    </svg>
    """, height=300)

    st.markdown("<h1 style='text-align:center; margin-top:0;'>ARF SENTINEL</h1>", unsafe_allow_html=True)
    st.markdown("<h3 style='text-align:center; color:#00FF88;'>The execution control plane for enterprise AI agents.</h3>", unsafe_allow_html=True)
    st.markdown("<p style='text-align:center; font-size:1.2rem; color:#aaa;'>A critical vulnerability was detected. Your agent wants to change <b>147 repositories</b>.<br>Should it be allowed?</p>", unsafe_allow_html=True)

    if st.button("INVESTIGATE THREAT"):
        st.session_state.incident_id = f"incident_{int(time.time())}"
        state = SentinelState(
            incident_id=st.session_state.incident_id,
            package_name="urllib3",
            vulnerability_description="CVE-2025-1234 – Remote code execution in urllib3 < 2.0.1",
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
        st.session_state.state = state
        advance_phase(1)
        st.rerun()

# ── Phase 1: CRAFT Investigation ──
elif st.session_state.phase == 1:
    st.markdown('<p class="phase-title">PHASE 1 · CRAFT INVESTIGATION</p>', unsafe_allow_html=True)
    if not st.session_state.state.get("affected_repositories"):
        with st.spinner("Scanning dependency graph..."):
            result = graph.invoke(st.session_state.state)
            st.session_state.state = result
    state = st.session_state.state
    st.markdown(f"""
    <div class="card">
        <span class="big-number">147</span> repos  ·  
        <span class="big-number">89</span> direct  ·  
        <span class="big-number">58</span> transitive  ·  
        <span class="big-number">23</span> paths<br>
        <span style="color:#00bcd4;">Schema discovered · Dependency graph mapped · Blast radius calculated</span><br>
        <span style="color:#e74c3c;">BLAST RADIUS: 63%</span>
    </div>
    """, unsafe_allow_html=True)
    if st.button("Continue to Agent Proposal ➜"):
        advance_phase(2)
        st.rerun()

# ── Phase 2: Agent Proposal ──
elif st.session_state.phase == 2:
    st.markdown('<p class="phase-title">PHASE 2 · NEMOTRON PROPOSAL</p>', unsafe_allow_html=True)
    state = st.session_state.state
    proposal = RemediationProposal(**state["proposed_action"])
    st.info(f"""
    ### AGENT PROPOSED ACTION  
    Upgrade **{proposal.target_package}** across **{proposal.affected_repository_count}** repositories  
    Confidence: **{proposal.confidence:.0%}**  
    *Agent recommendation — not execution authorization.*
    """)
    if st.button("REQUEST EXECUTION"):
        advance_phase(3)
        st.rerun()

# ── Phase 3: ARF Governance Interception ──
elif st.session_state.phase == 3:
    st.markdown('<p class="phase-title">PHASE 3 · ARF GOVERNANCE INTERCEPTION</p>', unsafe_allow_html=True)
    state = st.session_state.state
    if not st.session_state.arf_decision:
        evidence = build_evidence_from_investigation(
            incident_id=state["incident_id"],
            package_name=state["package_name"],
            vulnerability_description=state["vulnerability_description"],
            affected_repos=state["affected_repositories"],
            dependency_paths=state["dependency_paths"],
            direct_count=state["direct_dependency_count"],
            transitive_count=state["transitive_dependency_count"],
            summary=state["investigation_summary"],
            schema_found=True, query_success=True, data_completeness=0.95
        )
        proposal = RemediationProposal(**state["proposed_action"])
        adapter = ARFGovernanceAdapter()
        decision = adapter.evaluate(evidence, proposal)
        st.session_state.arf_decision = decision
    decision = st.session_state.arf_decision
    proposal = RemediationProposal(**state["proposed_action"])
    st.markdown('<div style="text-align: center; font-size: 2rem;">⚡ NEMOTRON ── ✕ ── EXECUTION</div>', unsafe_allow_html=True)
    st.markdown('<div class="arf-gate" style="text-align: center; font-size: 2rem;">ARF GATE</div>', unsafe_allow_html=True)
    col1, col2 = st.columns(2)
    with col1:
        st.metric("Agent Confidence", f"{proposal.confidence:.0%}")
    with col2:
        st.metric("ARF Posterior Risk", f"{decision.risk_probability:.0%}", delta="+32%", delta_color="inverse")
    st.caption("*Confidence does not equal execution safety.*")
    if st.button("View Bayesian Analysis ➜"):
        advance_phase(4)
        st.rerun()

# ── Phase 4: Bayesian Decision Engine ──
elif st.session_state.phase == 4:
    st.markdown('<p class="phase-title">PHASE 4 · BAYESIAN DECISION ENGINE</p>', unsafe_allow_html=True)
    decision = st.session_state.arf_decision
    prior_risk = 0.5
    evidence_conf = decision.evidence_confidence
    posterior_risk = decision.risk_probability
    render_bayesian_explanation(prior_risk, evidence_conf, posterior_risk)
    st.plotly_chart(risk_comparison_chart(0.92, posterior_risk), width="stretch")
    losses = {
        "APPROVE": decision.expected_loss_approve,
        "DENY": decision.expected_loss_deny,
        "ESCALATE": decision.expected_loss_escalate
    }
    st.plotly_chart(expected_loss_chart(losses), width="stretch")
    st.markdown(f"""
    ### ARF DECISION: <span class="decision-escalate">ESCALATE</span>
    **Reason:** Blast radius exceeds autonomous execution threshold.
    """, unsafe_allow_html=True)
    col1, col2 = st.columns(2)
    with col1:
        if st.button("Execute Anyways (will be blocked)"):
            advance_phase(5)
            st.rerun()
    with col2:
        if st.button("Find Safe-Scope Alternative ➜"):
            advance_phase(6)
            st.rerun()

# ── Phase 5: Blocked Execution ──
elif st.session_state.phase == 5:
    st.markdown('<p class="phase-title">PHASE 5 · EXECUTION BOUNDARY</p>', unsafe_allow_html=True)
    state = st.session_state.state
    proposal = RemediationProposal(**state["proposed_action"])
    boundary = ExecutionBoundary()
    result = boundary.execute(proposal, st.session_state.arf_decision)
    st.session_state.execution_result = result
    if result.status == "BLOCKED_PENDING_HUMAN_APPROVAL":
        st.error("BLOCKED BY ARF — Human approval required.")
        st.markdown("**Agent execution authority denied.**")
    if st.button("See Counterfactual Analysis"):
        advance_phase(6)
        st.rerun()

# ── Phase 6: Counterfactual Analysis ──
elif st.session_state.phase == 6:
    st.markdown('<p class="phase-title">PHASE 6 · COUNTERFACTUAL ANALYSIS</p>', unsafe_allow_html=True)
    state = st.session_state.state
    if not st.session_state.safe_decision:
        evidence = build_evidence_from_investigation(
            incident_id=state["incident_id"],
            package_name=state["package_name"],
            vulnerability_description=state["vulnerability_description"],
            affected_repos=state["affected_repositories"],
            dependency_paths=state["dependency_paths"],
            direct_count=state["direct_dependency_count"],
            transitive_count=state["transitive_dependency_count"],
            summary=state["investigation_summary"],
            schema_found=True, query_success=True, data_completeness=0.95
        )
        original_proposal = RemediationProposal(**state["proposed_action"])
        safe_prop, safe_evid, safe_dec = compute_safe_scope(evidence, original_proposal)
        st.session_state.safe_proposal = safe_prop
        st.session_state.safe_decision = safe_dec
    safe_prop = st.session_state.safe_proposal
    safe_dec = st.session_state.safe_decision
    original_risk = st.session_state.arf_decision.risk_probability
    st.markdown(f"""
    <div class="card">
        <span class="big-number">147</span> → <span class="big-number">32</span> repositories<br>
        Blast radius: 63% → <span style="color:#00FF88;">41%</span><br>
        Risk: {original_risk:.0%} → <span style="color:#00FF88;">{safe_dec.risk_probability:.0%}</span>
    </div>
    """, unsafe_allow_html=True)
    st.markdown("#### Bayesian Update for Safe Scope")
    render_bayesian_explanation(0.5, safe_dec.evidence_confidence, safe_dec.risk_probability)
    st.plotly_chart(blast_radius_treemap(32, 10, 5), width="stretch")
    st.success(f"ARF APPROVES canary upgrade of {safe_prop.affected_repository_count} repos with continuous monitoring.")
    if st.button("Request Re-Planned Execution"):
        advance_phase(7)
        st.rerun()

# ── Phase 7: Agent Re-Planning ──
elif st.session_state.phase == 7:
    st.markdown('<p class="phase-title">PHASE 7 · AGENT RE-PLANNING</p>', unsafe_allow_html=True)
    safe_prop = st.session_state.safe_proposal
    st.info(f"""
    ### RE-PLANNED ACTION  
    Canary upgrade **urllib3** to **2.0.1** across **{safe_prop.affected_repository_count}** repos.  
    Confidence: **{safe_prop.confidence:.0%}**  
    *Execution scope bounded by ARF.*
    """)
    if st.button("Request Governance Approval"):
        st.session_state.arf_decision = st.session_state.safe_decision
        st.session_state.state["proposed_action"] = safe_prop.model_dump()
        advance_phase(8)
        st.rerun()

# ── Phase 8: Approval & Final ──
elif st.session_state.phase == 8:
    st.markdown('<p class="phase-title">PHASE 8 · APPROVAL</p>', unsafe_allow_html=True)
    decision = st.session_state.arf_decision
    st.markdown(f"""
    ### ARF DECISION: <span class="decision-approve">APPROVE</span>
    **Reason:** Canary deployment within safe execution boundary.
    """)
    st.success("EXECUTION AUTHORITY GRANTED")
    st.divider()

    # Generate PDF audit trail
    if not st.session_state.pdf_bytes:
        evidence = build_evidence_from_investigation(
            incident_id=st.session_state.state["incident_id"],
            package_name=st.session_state.state["package_name"],
            vulnerability_description=st.session_state.state["vulnerability_description"],
            affected_repos=st.session_state.state["affected_repositories"],
            dependency_paths=st.session_state.state["dependency_paths"],
            direct_count=st.session_state.state["direct_dependency_count"],
            transitive_count=st.session_state.state["transitive_dependency_count"],
            summary=st.session_state.state["investigation_summary"],
            schema_found=True, query_success=True, data_completeness=0.95
        )
        proposal = RemediationProposal(**st.session_state.state["proposed_action"])
        exec_result = st.session_state.execution_result
        pdf_bytes = generate_audit_pdf(evidence, proposal, decision, exec_result)
        st.session_state.pdf_bytes = pdf_bytes

    st.download_button(
        label="📄 Download Full Audit Trail (PDF)",
        data=st.session_state.pdf_bytes,
        file_name=f"ARF_Audit_{st.session_state.incident_id}.pdf",
        mime="application/pdf",
    )

    st.markdown("## Enterprise AI needs an execution control plane.")
    col1, col2, col3 = st.columns(3)
    with col1:
        st.markdown("🔵 **CRAFT**  \nDiscover")
    with col2:
        st.markdown("🟣 **NEMOTRON**  \nReason")
    with col3:
        st.markdown("🟢 **ARF**  \nAuthorize")
    st.markdown("---")
    st.markdown("✓ Bayesian Risk Assessment  ·  ✓ Counterfactual Planning  ·  ✓ Bounded Execution Authority")

# ── Silent audit logging ──
if st.session_state.arf_decision and st.session_state.state:
    state = st.session_state.state
    run_dir = f"runs/sentinel_{state['incident_id']}_{timestamp()}"
    logger = AuditLogger(run_dir)
    logger.save_artifact("incident.json", {"package": "urllib3", "vuln": "CVE-2025-1234"})
    logger.save_artifact("arf_decision.json", st.session_state.arf_decision.model_dump())
    if st.session_state.execution_result:
        logger.save_artifact("execution_result.json", st.session_state.execution_result.model_dump())
    logger.log(AuditRecord(
        timestamp=timestamp(),
        incident_id=state["incident_id"],
        event_type="GOVERNANCE_EVALUATED",
        actor="ARF",
        action="evaluate",
        decision=st.session_state.arf_decision.decision
    ))
