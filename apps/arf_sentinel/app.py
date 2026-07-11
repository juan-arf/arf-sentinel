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

def render_bayesian_explanation(prior_risk, evidence_conf, posterior_risk):
    likelihood_ratio = posterior_risk / prior_risk if prior_risk > 0 else 1
    st.latex(r"P(Risk \mid Evidence) = rac{P(Evidence \mid Risk) \, P(Risk)}{P(Evidence)}")
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

# Phase 0 - Mission Control with animated SVG
if st.session_state.phase == 0:
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
        <rect x="20" y="100" width="100" height="60" rx="8" fill="#1e1e1e" stroke="#00bcd4" stroke-width="2" class="glow"/>
        <text x="70" y="135" text-anchor="middle" class="node" fill="#00bcd4">CRAFT</text>
        <rect x="220" y="100" width="120" height="60" rx="8" fill="#1e1e1e" stroke="#9b59b6" stroke-width="2" class="glow"/>
        <text x="280" y="135" text-anchor="middle" class="node" fill="#9b59b6">NEMOTRON</text>
        <rect x="440" y="100" width="100" height="60" rx="8" fill="#1e1e1e" stroke="#00FF88" stroke-width="2" class="glow"/>
        <text x="490" y="135" text-anchor="middle" class="node" fill="#00FF88">ARF</text>
        <rect x="640" y="100" width="130" height="60" rx="8" fill="#1e1e1e" stroke="#e74c3c" stroke-width="2" class="glow"/>
        <text x="705" y="135" text-anchor="middle" class="node" fill="#e74c3c">EXECUTION</text>
        <line x1="120" y1="130" x2="210" y2="130" class="edge flow" stroke="#00bcd4" marker-end="url(#arrow)"/>
        <line x1="340" y1="130" x2="430" y2="130" class="edge flow" stroke="#9b59b6" marker-end="url(#arrow)"/>
        <line x1="540" y1="130" x2="630" y2="130" class="edge flow" stroke="#00FF88" marker-end="url(#arrow)"/>
        <circle cx="30" cy="130" r="10" fill="#e74c3c" />
        <text x="30" y="134" text-anchor="middle" class="node" font-size="12">!</text>
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
