"""
Audit PDF Generator – formal, self-contained documentation of the
entire ARF Sentinel governance process.

Produces a multi‑page PDF report containing:

    * Cover page with ARF Sentinel logo/title
    * Incident summary
    * CRAFT investigation evidence
    * Nemotron agent proposal
    * ARF Bayesian governance decision (expected losses, policy violations)
    * Execution boundary result (if any)
    * Footer with generation timestamp

The output is a bytes object suitable for download or storage. It uses
the `fpdf2` library for layout and styling.

Note: All text is ASCII‑safe to guarantee portability. The report is
designed for archival and audit purposes – it provides a human‑readable
record of why an AI agent was or was not allowed to act.
"""

from fpdf import FPDF
from datetime import datetime, timezone
from typing import Optional
from .models import (
    IncidentEvidence,
    RemediationProposal,
    GovernanceDecision,
    ExecutionResult,
)


class AuditPDF(FPDF):
    """Custom PDF class with consistent styling for ARF Sentinel reports."""

    def __init__(self):
        super().__init__()
        self.set_auto_page_break(auto=True, margin=20)
        # Use built‑in Helvetica (ASCII safe)
        self.set_font("Helvetica", size=12)

    def header(self):
        """Page header with ARF Sentinel branding."""
        if self.page_no() == 1:
            # Title page – no header
            return
        self.set_font("Helvetica", "B", 10)
        self.set_text_color(0, 200, 0)  # ARF green
        self.cell(0, 8, "ARF SENTINEL - AUDIT TRAIL", align="L")
        self.ln(8)
        self.set_draw_color(0, 200, 0)
        self.line(self.l_margin, self.get_y(), self.w - self.r_margin, self.get_y())
        self.ln(4)

    def footer(self):
        """Page footer with timestamp."""
        if self.page_no() == 1:
            return
        self.set_y(-20)
        self.set_font("Helvetica", "I", 8)
        self.set_text_color(128, 128, 128)
        self.cell(0, 8, f"Generated: {datetime.now(timezone.utc).isoformat()} UTC", align="C")

    # ── Helper: section title ──
    def section_title(self, title: str):
        """Print a styled section title."""
        self.ln(4)
        self.set_font("Helvetica", "B", 13)
        self.set_text_color(0, 200, 0)
        self.cell(0, 10, title, ln=True)
        self.set_draw_color(0, 200, 0)
        self.line(self.l_margin, self.get_y(), self.w - self.r_margin, self.get_y())
        self.ln(4)
        self.set_text_color(50, 50, 50)

    # ── Helper: key‑value line ──
    def kv(self, key: str, value: str):
        """Print a key: value line with bold key."""
        self.set_font("Helvetica", "B", 10)
        self.cell(60, 7, key + ":")
        self.set_font("Helvetica", "", 10)
        self.multi_cell(0, 7, value)

    # ── Helper: metric table (simple two‑column) ──
    def metric_table(self, rows: list[tuple[str, str]]):
        """Print a table of metrics."""
        self.set_font("Helvetica", "B", 10)
        col_width = (self.w - self.l_margin - self.r_margin) / 2
        for key, val in rows:
            self.cell(col_width, 7, key + ":")
            self.cell(col_width, 7, val, ln=True)


def generate_audit_pdf(
    evidence: IncidentEvidence,
    proposal: RemediationProposal,
    decision: GovernanceDecision,
    execution: Optional[ExecutionResult] = None,
) -> bytes:
    """
    Generate a complete audit trail PDF for a single incident.

    Parameters
    ----------
    evidence : IncidentEvidence
        CRAFT investigation evidence.
    proposal : RemediationProposal
        Agent's proposed remediation.
    decision : GovernanceDecision
        ARF governance decision.
    execution : ExecutionResult, optional
        Outcome of the execution boundary check.

    Returns
    -------
    bytes
        PDF file content.
    """
    pdf = AuditPDF()

    # ── Cover Page ──
    pdf.add_page()
    pdf.set_font("Helvetica", "B", 28)
    pdf.set_text_color(0, 200, 0)
    pdf.ln(50)
    pdf.cell(0, 15, "ARF SENTINEL", ln=True, align="C")
    pdf.set_font("Helvetica", "", 16)
    pdf.set_text_color(100, 100, 100)
    pdf.cell(0, 10, "Autonomous Blast-Radius Governance", ln=True, align="C")
    pdf.cell(0, 10, "Enterprise AI Agent Execution Control Plane", ln=True, align="C")
    pdf.ln(30)
    pdf.set_draw_color(0, 200, 0)
    pdf.line(pdf.l_margin + 20, pdf.get_y(), pdf.w - pdf.r_margin - 20, pdf.get_y())
    pdf.ln(20)
    pdf.set_font("Helvetica", "B", 14)
    pdf.set_text_color(50, 50, 50)
    pdf.cell(0, 10, "Incident Audit Trail", ln=True, align="C")
    pdf.set_font("Helvetica", "", 12)
    pdf.cell(0, 10, f"Incident ID: {evidence.incident_id}", ln=True, align="C")
    pdf.cell(0, 10, f"Package: {evidence.package_name}", ln=True, align="C")
    pdf.cell(0, 10, f"Vulnerability: {evidence.vulnerability_description}", ln=True, align="C")
    pdf.ln(20)
    pdf.set_font("Helvetica", "I", 10)
    pdf.set_text_color(128, 128, 128)
    pdf.cell(0, 8, f"Generated: {datetime.now(timezone.utc).isoformat()} UTC", ln=True, align="C")

    # ── Section 1: CRAFT Investigation Evidence ──
    pdf.add_page()
    pdf.section_title("1. CRAFT Investigation Evidence")
    pdf.metric_table([
        ("Repositories affected", str(evidence.affected_repository_count)),
        ("Direct dependencies", str(evidence.direct_dependency_count)),
        ("Transitive dependencies", str(evidence.transitive_dependency_count)),
        ("Dependency paths", str(len(evidence.dependency_paths))),
        ("Blast radius score", f"{evidence.blast_radius_score:.2f}"),
        ("Evidence confidence", f"{evidence.evidence_confidence:.2f}"),
    ])
    pdf.ln(5)
    pdf.kv("Summary", evidence.investigation_summary)
    pdf.ln(5)
    pdf.set_font("Helvetica", "I", 9)
    pdf.set_text_color(100, 100, 100)
    pdf.multi_cell(0, 7,
        "Blast radius score is computed as a weighted sum of repository count, "
        "transitive dependencies, and path multiplicity, normalised to [0,1]. "
        "Evidence confidence is a heuristic based on schema discovery, query "
        "success, and data completeness."
    )

    # ── Section 2: Agent Proposal (Nemotron) ──
    pdf.section_title("2. Remediation Proposal (Nemotron)")
    pdf.kv("Action", f"{proposal.action_type} {proposal.target_package} "
                     f"to {proposal.proposed_version}")
    pdf.kv("Scope", proposal.execution_scope)
    pdf.kv("Agent confidence", f"{proposal.confidence:.2f}")
    pdf.kv("Rationale", proposal.rationale)
    pdf.ln(3)
    pdf.set_font("Helvetica", "I", 9)
    pdf.set_text_color(100, 100, 100)
    pdf.cell(0, 7, "This proposal was generated by the agent. It does NOT carry execution authority.", ln=True)

    # ── Section 3: ARF Governance Decision ──
    pdf.section_title("3. ARF Governance Decision")
    pdf.kv("Decision", decision.decision)
    pdf.kv("Risk probability", f"{decision.risk_probability:.2f}")
    pdf.kv("Evidence confidence", f"{decision.evidence_confidence:.2f}")
    pdf.ln(4)
    pdf.set_font("Helvetica", "B", 11)
    pdf.cell(0, 7, "Expected Losses (Bayesian Expected Loss Minimisation)", ln=True)
    pdf.metric_table([
        ("APPROVE", f"{decision.expected_loss_approve:.4f}"),
        ("DENY", f"{decision.expected_loss_deny:.4f}"),
        ("ESCALATE", f"{decision.expected_loss_escalate:.4f}"),
    ])
    pdf.ln(3)
    pdf.kv("Minimum expected loss", decision.decision)
    pdf.kv("Policy violations", ", ".join(decision.policy_violations) if decision.policy_violations else "None")
    pdf.kv("Reason", decision.reason)
    pdf.kv("Requires human approval", str(decision.requires_human_approval))

    # Bayesian methodology note
    pdf.ln(5)
    pdf.set_font("Helvetica", "I", 9)
    pdf.set_text_color(100, 100, 100)
    pdf.multi_cell(0, 7,
        "ARF uses Bayesian Expected Loss Minimisation: it selects the action "
        "(APPROVE, DENY, or ESCALATE) with the lowest expected loss. The risk "
        "probability is derived from the blast radius via a conservative mapping "
        "R = 0.5 + 0.5 * B, and the prior is updated with evidence confidence. "
        "Policy rules may override the mathematical minimum."
    )

    # ── Section 4: Execution Boundary Result ──
    if execution:
        pdf.section_title("4. Execution Boundary Result")
        pdf.kv("Status", execution.status)
        pdf.kv("Timestamp", execution.timestamp.isoformat())
        pdf.kv("Message", execution.message)
        pdf.ln(3)
        if "BLOCKED" in execution.status:
            pdf.set_font("Helvetica", "B", 12)
            pdf.set_text_color(200, 0, 0)
            pdf.cell(0, 10, "EXECUTION DENIED", ln=True, align="C")
        elif "AUTHORIZED" in execution.status:
            pdf.set_font("Helvetica", "B", 12)
            pdf.set_text_color(0, 200, 0)
            pdf.cell(0, 10, "EXECUTION AUTHORIZED (SIMULATED)", ln=True, align="C")
        pdf.set_text_color(50, 50, 50)

    # ── Final GTM statement ──
    pdf.ln(10)
    pdf.set_font("Helvetica", "I", 10)
    pdf.set_text_color(80, 80, 80)
    pdf.multi_cell(0, 7,
        "Enterprise AI needs an execution control plane. "
        "ARF Sentinel finds the maximum safe action an agent can take, "
        "ensuring that AI proposals are independently governed before "
        "they become real‑world changes."
    )

    # Output PDF as bytes
    return pdf.output()  # returns bytes in fpdf2
