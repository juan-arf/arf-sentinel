from pydantic import BaseModel, Field
from typing import Literal, Any, Optional
from datetime import datetime, timezone

class RemediationProposal(BaseModel):
    action_type: str = Field(description="e.g., upgrade, rollback, patch")
    target_package: str
    proposed_version: Optional[str] = None
    affected_repository_count: int
    rationale: str
    confidence: float = Field(ge=0.0, le=1.0)
    execution_scope: str = Field(description="blast radius description")

class IncidentEvidence(BaseModel):
    incident_id: str
    package_name: str
    vulnerability_description: str
    affected_repositories: list[dict[str, Any]]
    dependency_paths: list[dict[str, Any]]
    direct_dependency_count: int
    transitive_dependency_count: int
    affected_repository_count: int
    evidence_confidence: float = Field(ge=0.0, le=1.0)
    blast_radius_score: float = Field(ge=0.0, le=1.0)
    investigation_summary: str

class GovernanceDecision(BaseModel):
    decision: Literal["APPROVE", "DENY", "ESCALATE"]
    risk_probability: float = Field(ge=0.0, le=1.0)
    blast_radius_score: float = Field(ge=0.0, le=1.0)
    evidence_confidence: float = Field(ge=0.0, le=1.0)
    expected_loss_approve: float
    expected_loss_deny: float
    expected_loss_escalate: float
    policy_violations: list[str] = []
    reason: str
    requires_human_approval: bool

class ExecutionResult(BaseModel):
    status: Literal["AUTHORIZED_SIMULATION", "BLOCKED_POLICY", "BLOCKED_PENDING_HUMAN_APPROVAL"]
    governance_decision: GovernanceDecision
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

class AuditRecord(BaseModel):
    timestamp: str
    incident_id: str
    event_type: str
    actor: str
    action: str
    decision: Optional[str] = None
    metadata: dict[str, Any] = {}
