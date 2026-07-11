from typing import Any, Optional
from typing_extensions import TypedDict

class SentinelState(TypedDict):
    incident_id: str
    package_name: str
    vulnerability_description: str
    discovered_schema: dict[str, Any]
    affected_repositories: list[dict[str, Any]]
    dependency_paths: list[dict[str, Any]]
    direct_dependency_count: int
    transitive_dependency_count: int
    affected_repository_count: int
    evidence_confidence: float
    blast_radius_score: float
    investigation_summary: str
    proposed_action: dict[str, Any]
    arf_event: dict[str, Any]
    arf_decision: dict[str, Any]
    execution_status: str
    sql_queries: list[str]
    reasoning_trace: list[str]
    errors: list[str]
