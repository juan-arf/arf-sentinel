from fpdf import FPDF
from datetime import datetime, timezone
from .models import IncidentEvidence, RemediationProposal, GovernanceDecision, ExecutionResult

def generate_audit_pdf(
    evidence: IncidentEvidence,
    proposal: RemediationProposal,
    decision: GovernanceDecision,
    execution: ExecutionResult = None
) -> bytes:
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Helvetica", size=14)
    pdf.cell(0, 10, "ARF SENTINEL - Audit Trail", ln=True, align='C')
    pdf.ln(5)
    pdf.set_font(size=10)

    # Incident details
    pdf.cell(0, 8, f"Incident ID: {evidence.incident_id}", ln=True)
    pdf.cell(0, 8, f"Package: {evidence.package_name}", ln=True)
    pdf.cell(0, 8, f"Vulnerability: {evidence.vulnerability_description}", ln=True)
    pdf.ln(3)

    # Investigation evidence
    pdf.set_font(style='B')
    pdf.cell(0, 8, "CRAFT Investigation Evidence", ln=True)
    pdf.set_font(style='')
    pdf.cell(0, 8, f"- Repositories affected: {evidence.affected_repository_count}", ln=True)
    pdf.cell(0, 8, f"- Direct dependencies: {evidence.direct_dependency_count}", ln=True)
    pdf.cell(0, 8, f"- Transitive dependencies: {evidence.transitive_dependency_count}", ln=True)
    pdf.cell(0, 8, f"- Blast radius score: {evidence.blast_radius_score:.2f}", ln=True)
    pdf.cell(0, 8, f"- Evidence confidence: {evidence.evidence_confidence:.2f}", ln=True)
    pdf.ln(3)

    # Agent proposal
    pdf.set_font(style='B')
    pdf.cell(0, 8, "Remediation Proposal (Nemotron)", ln=True)
    pdf.set_font(style='')
    pdf.cell(0, 8, f"- Action: {proposal.action_type} {proposal.target_package} to {proposal.proposed_version}", ln=True)
    pdf.cell(0, 8, f"- Scope: {proposal.execution_scope}", ln=True)
    pdf.cell(0, 8, f"- Agent confidence: {proposal.confidence:.2f}", ln=True)
    pdf.ln(3)

    # ARF governance decision
    pdf.set_font(style='B')
    pdf.cell(0, 8, "ARF Governance Decision", ln=True)
    pdf.set_font(style='')
    pdf.cell(0, 8, f"- Decision: {decision.decision}", ln=True)
    pdf.cell(0, 8, f"- Risk probability: {decision.risk_probability:.2f}", ln=True)
    pdf.cell(0, 8, f"- Expected loss APPROVE: {decision.expected_loss_approve:.2f}", ln=True)
    pdf.cell(0, 8, f"- Expected loss DENY: {decision.expected_loss_deny:.2f}", ln=True)
    pdf.cell(0, 8, f"- Expected loss ESCALATE: {decision.expected_loss_escalate:.2f}", ln=True)
    pdf.cell(0, 8, f"- Policy violations: {', '.join(decision.policy_violations) if decision.policy_violations else 'None'}", ln=True)
    pdf.cell(0, 8, f"- Reason: {decision.reason}", ln=True)
    pdf.ln(3)

    # Execution result (if any)
    if execution:
        pdf.set_font(style='B')
        pdf.cell(0, 8, "Execution Result", ln=True)
        pdf.set_font(style='')
        pdf.cell(0, 8, f"- Status: {execution.status}", ln=True)
        pdf.cell(0, 8, f"- Timestamp: {execution.timestamp.isoformat()}", ln=True)
        pdf.ln(3)

    # Footer
    pdf.set_font(size=8)
    pdf.cell(0, 8, f"Generated: {datetime.now(timezone.utc).isoformat()} UTC", ln=True)

    return pdf.output(dest='S').encode('latin-1')
