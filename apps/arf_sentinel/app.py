"""
Streamlit demo application for ARF Sentinel - cinematic 8-phase experience.

This module drives the interactive, auto‑playing demo that walks judges through
a software supply‑chain vulnerability investigation, governance by ARF, and a
counterfactual re‑planning flow.  It integrates with CRAFT (mocked), Nemotron
(mocked), ARF (via the adapter), an execution boundary, and a PDF audit trail.
"""

import sys, os, time, random
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import streamlit as st
from datetime import datetime, timezone
import plotly.graph_objects as go

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

# -- Page config & Global CSS (cyberpunk terminal style) --
st.set_page_config(page_title="ARF SENTINEL", layout="wide")
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Share+Tech+Mono&display=swap');
    body, .stApp {
        background: radial-gradient(circle at 20% 30%, #0d1117 0%, #010101 90%);
        color: #e0e0e0;
        font-family: 'Share Tech Mono', monospace;
    }
    .stApp::before {
        content: "";
        position: fixed;
        top: 0; left: 0; width: 100%; height: 100%;
        background: url('data:image/svg+xml;utf8,<svg xmlns="http://www.w3.org/2000/svg" width="4" height="4"><circle cx="2" cy="2" r="1" fill="rgba(0,255,136,0.08)"/></svg>') repeat;
        pointer-events: none;
        animation: drift 60s linear infinite;
    }
    @keyframes drift { 0% { background-position: 0 0; } 100% { background-position: 200px 200px; } }

    .stButton > button {
        background: linear-gradient(135deg, #00FF88 0%, #00cc66 100%);
        color: #000; font-weight: bold; font-size: 1.1rem;
        border: none; border-radius: 6px; padding: 0.8rem 2rem;
        width: 100%; letter-spacing: 2px; text-transform: uppercase;
        box-shadow: 0 0 20px rgba(0,255,136,0.3);
        transition: all 0.3s ease;
    }
    .stButton > button:hover {
        box-shadow: 0 0 40px rgba(0,255,136,0.6);
        transform: translateY(-2px);
    }

    .phase-title {
        color: #00FF88; font-size: 1.8rem; margin-top: 1.5rem;
        text-shadow: 0 0 10px rgba(0,255,136,0.5);
        border-bottom: 1px solid #00FF88; padding-bottom: 0.5rem;
    }
    .big-number {
        font-size: 4rem; font-weight: bold; color: #00FF88;
        text-shadow: 0 0 20px rgba(0,255,136,0.7);
        display: inline-block;
    }
    .card {
        background: rgba(20,20,30,0.8); backdrop-filter: blur(10px);
        border: 1px solid #00FF88; padding: 2rem; border-radius: 15px;
        margin: 1rem 0; box-shadow: 0 0 15px rgba(0,255,136,0.1);
    }
    .risk-bar {
        height: 25px; border-radius: 12px; background: #1e1e1e;
        box-shadow: inset 0 0 10px rgba(0,0,0,0.7); margin: 1rem 0;
    }
    .fade-in {
        animation: fadeIn 0.8s ease;
    }
    @keyframes fadeIn {
        from { opacity: 0; transform: translateY(20px); }
        to { opacity: 1; transform: translateY(0); }
    }

    .battle-container { width: 80%; margin: 20px auto; }
    .battle-label { font-size: 18px; font-weight: bold; margin-bottom: 5px; }
    .battle-bar { height: 40px; border-radius: 8px; margin: 10px 0; }

    @media (max-width: 768px) {
        .big-number { font-size: 2.5rem; }
        .phase-title { font-size: 1.3rem; }
    }
</style>
""", unsafe_allow_html=True)

# -- Sidebar auto-play --
with st.sidebar:
    st.header("Demo Settings")
    auto_play = st.checkbox("Auto-play (5 sec/phase)", value=False)
    if auto_play:
        st.info("Cinema mode active - sit back and watch the story unfold.")
    st.markdown("---")

# -- Session State --
if "phase" not in st.session_state:
    st.session_state.phase = 0
    st.session_state.state = None
    st.session_state.arf_decision = None
    st.session_state.execution_result = None
    st.session_state.safe_proposal = None
    st.session_state.safe_decision = None
    st.session_state.incident_id = None
    st.session_state.pdf_bytes = None
    st.session_state.phase_start_time = time.time()

graph = build_graph()

def next_phase():
    """ Advance the demo to the next phase and reset the auto-play timer. """
    st.session_state.phase += 1
    st.session_state.phase_start_time = time.time()

if auto_play and st.session_state.phase < 8:
    elapsed = time.time() - st.session_state.phase_start_time
    if elapsed > 5:
        next_phase()
        st.rerun()

# -- Reusable Bayesian explanation (LaTeX) --
def render_bayesian_explanation(prior_risk, evidence_conf, posterior_risk):
    """ Display Bayesian formula (LaTeX), prior/posterior metrics, and risk bar. """
    likelihood_ratio = posterior_risk / prior_risk if prior_risk > 0 else 1
    st.latex(r"P(Risk \mid Evidence) = \frac{P(Evidence \mid Risk) \, P(Risk)}{P(Evidence)}")
    col1, col2, col3 = st.columns(3)
    col1.metric("Prior Risk", f"{prior_risk:.0%}")
    col2.metric("Evidence Strength", f"{evidence_conf:.0%}")
    col3.metric("Likelihood Ratio", f"{likelihood_ratio:.1f}x")
    st.markdown(f"""
    <div class="risk-bar">
        <div style="width:{posterior_risk*100}%; height:100%;
                    background:linear-gradient(90deg, #00FF88, #e74c3c);
                    border-radius:12px; transition: width 0.5s ease;">
        </div>
    </div>
    <div style="display:flex; justify-content:space-between;">
        <span>Prior: {prior_risk:.0%}</span>
        <span style="color:#00bcd4;">-- Evidence update --</span>
        <span>Posterior: {posterior_risk:.0%}</span>
    </div>
    """, unsafe_allow_html=True)

# -- Phase 0: Mission Control --
if st.session_state.phase == 0:
    st.markdown('<div class="fade-in">', unsafe_allow_html=True)
    st.components.v1.html("""
    <style>
        @import url('https://fonts.googleapis.com/css2?family=Share+Tech+Mono&display=swap');
        .workflow { width: 100%; max-width: 900px; display: block; margin: auto; }
        .node { font-family: 'Share Tech Mono', monospace; font-size: 14px; fill: #fff; }
        .edge { stroke-width: 3; fill: none; stroke-dasharray: 8 4; animation: dash 1.2s linear infinite; }
        @keyframes dash { to { stroke-dashoffset: -24; } }
        .glow { filter: drop-shadow(0 0 8px); }
        .pulse { animation: pulse 2s infinite; }
        @keyframes pulse { 0% { opacity: 0.8; } 50% { opacity: 1; } 100% { opacity: 0.8; } }
    </style>
    <svg class="workflow" viewBox="0 0 850 300">
        <defs>
            <marker id="arrow" markerWidth="8" markerHeight="6" refX="8" refY="3" orient="auto">
                <polygon points="0 0, 8 3, 0 6" fill="#e0e0e0"/>
            </marker>
        </defs>
        <circle cx="40" cy="150" r="12" fill="#e74c3c" class="pulse"/>
        <text x="40" y="155" text-anchor="middle" class="node" font-size="14">!</text>
        <rect x="30" y="110" width="110" height="70" rx="10" fill="#1e1e1e" stroke="#00bcd4" stroke-width="2" class="glow"/>
        <text x="85" y="150" text-anchor="middle" class="node" fill="#00bcd4">CRAFT</text>
        <rect x="250" y="110" width="130" height="70" rx="10" fill="#1e1e1e" stroke="#9b59b6" stroke-width="2" class="glow"/>
        <text x="315" y="150" text-anchor="middle" class="node" fill="#9b59b6">NEMOTRON</text>
        <rect x="490" y="110" width="110" height="70" rx="10" fill="#1e1e1e" stroke="#00FF88" stroke-width="2" class="glow"/>
        <text x="545" y="150" text-anchor="middle" class="node" fill="#00FF88">ARF</text>
        <rect x="710" y="110" width="130" height="70" rx="10" fill="#1e1e1e" stroke="#e74c3c" stroke-width="2" class="glow"/>
        <text x="775" y="150" text-anchor="middle" class="node" fill="#e74c3c">EXECUTION</text>
        <line x1="140" y1="145" x2="240" y2="145" class="edge" stroke="#00bcd4" marker-end="url(#arrow)"/>
        <line x1="380" y1="145" x2="480" y2="145" class="edge" stroke="#9b59b6" marker-end="url(#arrow)"/>
        <line x1="600" y1="145" x2="700" y2="145" class="edge" stroke="#00FF88" marker-end="url(#arrow)"/>
        <text x="190" y="105" text-anchor="middle" class="node" font-size="10" fill="#888">Enterprise Evidence</text>
        <text x="430" y="105" text-anchor="middle" class="node" font-size="10" fill="#888">Remediation Proposal</text>
        <text x="650" y="105" text-anchor="middle" class="node" font-size="10" fill="#888">Governance Decision</text>
        <text x="85" y="220" text-anchor="middle" class="node" font-size="12" fill="#666">Discover</text>
        <text x="315" y="220" text-anchor="middle" class="node" font-size="12" fill="#666">Reason</text>
        <text x="545" y="220" text-anchor="middle" class="node" font-size="12" fill="#666">Authorize</text>
        <text x="775" y="220" text-anchor="middle" class="node" font-size="12" fill="#666">Enforce</text>
    </svg>
    """, height=300)

    st.markdown("""
    <div class="card fade-in" style="text-align:center;">
        <h2 style="color:#e74c3c; text-shadow:0 0 20px rgba(231,76,60,0.8);">!! CRITICAL THREAT DETECTED !!</h2>
        <div style="display:flex; justify-content:center; gap:40px; margin:30px 0;">
            <div>
                <span class="big-number">147</span><br>
                <span style="color:#e74c3c;">REPOS EXPOSED</span>
            </div>
            <div>
                <span class="big-number">92%</span><br>
                <span style="color:#9b59b6;">AGENT CONFIDENCE</span>
            </div>
            <div>
                <span class="big-number">63%</span><br>
                <span style="color:#e74c3c;">BLAST RADIUS</span>
            </div>
        </div>
        <p style="color:#888; font-size:1.2rem;">
            <b>urllib3</b> -- Remote Code Execution (CVE-2025-1234)<br>
            Your agent proposes an automated upgrade. Should it be authorized?
        </p>
    </div>
    """, unsafe_allow_html=True)

    if st.button("[INVESTIGATE THREAT]"):
        st.session_state.incident_id = f"incident_{int(time.time())}"
        state = SentinelState(
            incident_id=st.session_state.incident_id,
            package_name="urllib3",
            vulnerability_description="CVE-2025-1234 - Remote code execution in urllib3 < 2.0.1",
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
        next_phase()
        st.rerun()

# -- Phase 1: CRAFT Investigation (live scanning) --
elif st.session_state.phase == 1:
    st.markdown('<p class="phase-title">PHASE 1 - CRAFT INVESTIGATION</p>', unsafe_allow_html=True)
    progress_bar = st.progress(0)
    status_text = st.empty()
    for i in range(101):
        progress_bar.progress(i)
        status_text.text(f"Scanning dependency graph... {i}%")
        time.sleep(0.03)
    progress_bar.empty()
    status_text.empty()

    # SAFETY GUARD: auto‑play may reach this phase without manual init
    if st.session_state.state is None:
        st.session_state.state = SentinelState(
            incident_id=f"incident_{int(time.time())}",
            package_name="urllib3",
            vulnerability_description="CVE-2025-1234 - Remote code execution in urllib3 < 2.0.1",
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

    state = st.session_state.state
    state["affected_repositories"] = [{"repo": f"repo_{i}", "dependency": "urllib3"} for i in range(147)]
    state["dependency_paths"] = [{"from": "urllib3", "to": f"repo_{i}"} for i in range(23)]
    state["direct_dependency_count"] = 89
    state["transitive_dependency_count"] = 58
    state["affected_repository_count"] = 147
    st.session_state.state = state

    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Total Repos", "147")
    col2.metric("Direct Dependencies", "89")
    col3.metric("Transitive Dependencies", "58")
    col4.metric("Dependency Paths", "23")

    st.markdown("""
    <div class="card fade-in">
        <span style="color:#00bcd4; font-size:1.2rem;">
            [OK] Schema discovered  [OK] Dependency graph mapped  [OK] Blast radius calculated
        </span>
    </div>
    """, unsafe_allow_html=True)

    if st.button("CONTINUE TO AGENT PROPOSAL -->"):
        next_phase()
        st.rerun()

# -- Phase 2: Agent Proposal --
elif st.session_state.phase == 2:
    st.markdown('<p class="phase-title">PHASE 2 - NEMOTRON PROPOSAL</p>', unsafe_allow_html=True)
    if not st.session_state.state.get("proposed_action"):
        result = graph.invoke(st.session_state.state)
        st.session_state.state = result
    proposal = RemediationProposal(**st.session_state.state["proposed_action"])
    st.info(f"""
    ### AGENT PROPOSED ACTION
    Upgrade **{proposal.target_package}** to **{proposal.proposed_version}**  
    across **{proposal.affected_repository_count}** repositories.

    Confidence: **{proposal.confidence:.0%}**

    *Agent recommendation -- not execution authorization.*
    """)
    if st.button("REQUEST EXECUTION"):
        next_phase()
        st.rerun()

# -- Phase 3: ARF Interception (animated battle bar) --
elif st.session_state.phase == 3:
    st.markdown('<p class="phase-title">PHASE 3 - ARF GOVERNANCE INTERCEPTION</p>', unsafe_allow_html=True)
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

    # Confidence vs Risk animated battle bar
    st.components.v1.html(f"""
    <style>
        .battle-container {{ width: 80%; margin: 20px auto; }}
        .battle-label {{ font-size: 18px; font-weight: bold; margin-bottom: 5px; }}
        .conf-bar {{
            height: 40px; border-radius: 8px; background: #9b59b6;
            width: {proposal.confidence*100}%;
            transition: width 0.5s ease;
        }}
        .risk-bar {{
            height: 40px; border-radius: 8px; background: #e74c3c;
            width: 0%;
            animation: grow-risk 2s ease forwards;
        }}
        @keyframes grow-risk {{
            0% {{ width: 0%; }}
            100% {{ width: {decision.risk_probability*100}%; }}
        }}
    </style>
    <div class="battle-container">
        <div class="battle-label" style="color:#9b59b6;">Agent Confidence</div>
        <div class="conf-bar"></div>
        <div class="battle-label" style="color:#e74c3c;">ARF Risk Posterior</div>
        <div class="risk-bar"></div>
    </div>
    """, height=200)

    st.markdown('<div style="text-align:center; font-size:2rem;">NEMOTRON -- X -- EXECUTION</div>', unsafe_allow_html=True)
    st.markdown('<div style="text-align:center; font-size:2rem; color:#e74c3c; text-shadow:0 0 10px #e74c3c;">ARF GATE</div>', unsafe_allow_html=True)

    col1, col2 = st.columns(2)
    col1.metric("Agent Confidence", f"{proposal.confidence:.0%}")
    col2.metric("ARF Posterior Risk", f"{decision.risk_probability:.0%}", delta="+32%", delta_color="inverse")
    st.caption("*Confidence does not equal execution safety.*")

    if st.button("VIEW BAYESIAN ANALYSIS -->"):
        next_phase()
        st.rerun()

# -- Phase 4: Bayesian Decision Engine --
elif st.session_state.phase == 4:
    st.markdown('<p class="phase-title">PHASE 4 - BAYESIAN DECISION ENGINE</p>', unsafe_allow_html=True)
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
    ### ARF DECISION: <span style='color:#f39c12; text-shadow:0 0 10px #f39c12;'>ESCALATE</span>
    **Reason:** Blast radius exceeds autonomous execution threshold.
    """)
    col1, col2 = st.columns(2)
    if col1.button("EXECUTE ANYWAYS (will be blocked)"):
        next_phase()
        st.rerun()
    if col2.button("FIND SAFE-SCOPE ALTERNATIVE -->"):
        st.session_state.phase = 6  # skip to counterfactual
        st.rerun()

# -- Phase 5: Blocked Execution --
elif st.session_state.phase == 5:
    st.markdown('<p class="phase-title">PHASE 5 - EXECUTION BOUNDARY</p>', unsafe_allow_html=True)
    boundary = ExecutionBoundary()
    proposal = RemediationProposal(**st.session_state.state["proposed_action"])
    result = boundary.execute(proposal, st.session_state.arf_decision)
    st.session_state.execution_result = result
    if result.status == "BLOCKED_PENDING_HUMAN_APPROVAL":
        st.error("BLOCKED BY ARF -- Human approval required.")
        st.markdown("**Agent execution authority denied.**")
        st.markdown("The agent proposed the action. The agent did not authorize it. ARF independently evaluated execution risk.")
    if st.button("SEE COUNTERFACTUAL ANALYSIS"):
        next_phase()
        st.rerun()

# -- Phase 6: Counterfactual --
elif st.session_state.phase == 6:
    st.markdown('<p class="phase-title">PHASE 6 - COUNTERFACTUAL ANALYSIS</p>', unsafe_allow_html=True)
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
    <div class="card fade-in">
        <h3 style="color:#00FF88;">Risk Reduction Through Scope Limitation</h3>
        <span class="big-number">147</span> --> <span class="big-number">32</span> repos<br><br>
        Blast radius: 63% --> <span style="color:#00FF88;">41%</span><br>
        Risk: {original_risk:.0%} --> <span style="color:#00FF88;">{safe_dec.risk_probability:.0%}</span><br>
        <b>Expected loss reduced by 73%</b> (0.71 --> 0.19)
    </div>
    """, unsafe_allow_html=True)

    st.markdown("#### Bayesian Update for Safe Scope")
    render_bayesian_explanation(0.5, safe_dec.evidence_confidence, safe_dec.risk_probability)
    st.plotly_chart(blast_radius_treemap(32, 10, 5), width="stretch")
    st.success(f"ARF APPROVES canary upgrade of {safe_prop.affected_repository_count} repos with continuous monitoring.")

    if st.button("REQUEST RE-PLANNED EXECUTION"):
        next_phase()
        st.rerun()

# -- Phase 7: Agent Re-Planning --
elif st.session_state.phase == 7:
    st.markdown('<p class="phase-title">PHASE 7 - AGENT RE-PLANNING</p>', unsafe_allow_html=True)
    safe_prop = st.session_state.safe_proposal
    st.info(f"""
    ### RE-PLANNED ACTION
    Canary upgrade **urllib3** to **2.0.1** across **{safe_prop.affected_repository_count}** repos.  
    Confidence: **{safe_prop.confidence:.0%}**  
    *Execution scope bounded by ARF.*
    """)
    if st.button("REQUEST FINAL APPROVAL"):
        st.session_state.arf_decision = st.session_state.safe_decision
        st.session_state.state["proposed_action"] = safe_prop.model_dump()
        next_phase()
        st.rerun()

# -- Phase 8: Approval & Final --
elif st.session_state.phase == 8:
    st.markdown('<p class="phase-title">PHASE 8 - APPROVAL</p>', unsafe_allow_html=True)
    decision = st.session_state.arf_decision
    st.markdown(f"### ARF DECISION: <span style='color:#00FF88; text-shadow:0 0 10px #00FF88;'>APPROVE</span>")
    st.success("EXECUTION AUTHORITY GRANTED")
    st.balloons()

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
        label="DOWNLOAD FULL AUDIT TRAIL (PDF)",
        data=st.session_state.pdf_bytes,
        file_name=f"ARF_Audit_{st.session_state.incident_id}.pdf",
        mime="application/pdf",
    )

    st.markdown("## Enterprise AI needs an execution control plane.")
    col1, col2, col3 = st.columns(3)
    with col1:
        st.markdown("CRAFT\n*Discover*")
    with col2:
        st.markdown("NEMOTRON\n*Reason*")
    with col3:
        st.markdown("ARF\n*Authorize*")
    st.markdown("---")
    st.markdown("[OK] Bayesian Risk Assessment  |  [OK] Counterfactual Planning  |  [OK] Bounded Execution Authority")
    st.markdown("**ARF finds the maximum safe action an agent can take.**")

# -- Silent audit logging --
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
