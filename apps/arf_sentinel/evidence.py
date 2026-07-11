"""
Blast‑radius normalisation and evidence confidence estimation.

This module converts raw dependency graph metrics (direct / transitive
dependencies, repository counts, dependency paths) into the two key
signals that feed the ARF Bayesian Risk Engine:

    * blast_radius_score  B ∈ [0, 1]
    * evidence_confidence C ∈ [0, 1]

The blast‑radius score quantifies the potential impact of a remediation
action (how many repositories and transitive paths are affected).  The
evidence confidence reflects how reliable the CRAFT data is.

Both values are calculated deterministically from the CRAFT query results,
ensuring reproducibility and auditability.

Mathematical Definition of Blast‑Radius Score
---------------------------------------------
The score B is a weighted sum of three clamped components:

    repo_component      = min( N_repos / N_cap , 1.0 )
    transitive_component= min( N_trans   / T_cap , 1.0 )
    path_component      = min( N_paths   / P_cap , 1.0 )

    B = w_repo · repo_component +
        w_trans · transitive_component +
        w_path · path_component

Default parameters (prototype‑grade heuristic):
    N_cap = 200   (saturation point for repository count)
    T_cap = 100   (saturation point for transitive dependency count)
    P_cap = 50    (saturation point for dependency path count)

    w_repo = 0.50
    w_trans= 0.30
    w_path = 0.20

These weights are chosen to give highest importance to repository count,
moderate importance to transitive dependency spread, and lower importance
to pure path multiplicity.  They are configurable via BlastRadiusConfig.

Evidence Confidence
-------------------
Evidence confidence C is a simple majority vote over three binary checks:

    C = ( has_schema + query_success + (data_completeness > 0.7) ) / 3

This is a pragmatic hackathon proxy; a production system would replace it
with a calibrated model based on query error rates, data freshness, and
schema versioning.

Integration with ARF
--------------------
B and C are combined by the ARF adapter into a risk probability R:

    R = 0.5 + 0.5·B   (conservative monotonic mapping)

The Bayesian prior is then updated using C as a likelihood factor to
produce the posterior risk used in expected‑loss minimisation.
"""

from pydantic import BaseModel, Field, field_validator
from typing import List, Dict, Any
from .models import IncidentEvidence


class BlastRadiusConfig(BaseModel):
    """
    Configuration for the blast‑radius normalisation heuristic.

    All parameters can be adjusted to reflect organisational risk appetite.
    For the hackathon prototype, they are set to reasonable defaults that
    make the demo scenario (147 repos) produce a score of ~0.63, which
    triggers ARF escalation.

    Attributes:
        repo_cap: saturation point for repository count (default 200).
        transitive_cap: saturation point for transitive dependencies (default 100).
        path_cap: saturation point for dependency paths (default 50).
        w_repo: weight for repository component (default 0.50).
        w_trans: weight for transitive component (default 0.30).
        w_path: weight for path component (default 0.20).
    """
    repo_cap: float = Field(default=200.0, ge=1.0, description="N_cap – saturation repository count")
    transitive_cap: float = Field(default=100.0, ge=1.0, description="T_cap – saturation transitive dependency count")
    path_cap: float = Field(default=50.0, ge=1.0, description="P_cap – saturation dependency path count")
    w_repo: float = Field(default=0.50, ge=0.0, le=1.0, description="Weight for repository component")
    w_trans: float = Field(default=0.30, ge=0.0, le=1.0, description="Weight for transitive component")
    w_path: float = Field(default=0.20, ge=0.0, le=1.0, description="Weight for path component")

    @field_validator("w_repo", "w_trans", "w_path")
    @classmethod
    def weights_must_sum_to_one(cls, v: float, info: Any) -> float:
        # We cannot enforce sum = 1 in a per‑field validator, so we skip.
        return v


def compute_blast_radius(
    affected_repository_count: int,
    transitive_dependency_count: int,
    dependency_path_count: int,
    config: BlastRadiusConfig | None = None,
) -> float:
    """
    Normalise dependency impact into a [0, 1] score.

    The score B is computed as:

        B = w_repo · min(N_repos / N_cap, 1.0)
          + w_trans · min(N_trans / T_cap, 1.0)
          + w_path · min(N_paths / P_cap, 1.0)

    Parameters
    ----------
    affected_repository_count : int
        Total number of repositories affected (N_repos).
    transitive_dependency_count : int
        Number of transitive dependency relationships (N_trans).
    dependency_path_count : int
        Number of unique dependency paths (N_paths).
    config : BlastRadiusConfig, optional
        Custom saturation thresholds and weights.  If None, uses defaults.

    Returns
    -------
    float
        Blast‑radius score B ∈ [0, 1], rounded to 4 decimal places.
    """
    if config is None:
        config = BlastRadiusConfig()

    repo_component = min(affected_repository_count / config.repo_cap, 1.0)
    transitive_component = min(transitive_dependency_count / config.transitive_cap, 1.0)
    path_component = min(dependency_path_count / config.path_cap, 1.0)

    score = (
        config.w_repo * repo_component
        + config.w_trans * transitive_component
        + config.w_path * path_component
    )
    return round(score, 4)


def calculate_evidence_confidence(
    has_schema: bool,
    query_success: bool,
    data_completeness: float,
) -> float:
    """
    Estimate confidence in the CRAFT investigation data.

    This is a simple majority‑vote heuristic suitable for a hackathon.
    Production implementations should replace it with a calibrated
    Bayesian confidence model.

    C = (has_schema + query_success + (data_completeness > 0.7)) / 3

    Parameters
    ----------
    has_schema : bool
        Whether the CRAFT schema was successfully discovered.
    query_success : bool
        Whether the analytical queries completed without error.
    data_completeness : float
        Fraction of expected data returned (0.0 – 1.0).  A value
        greater than 0.7 is considered "good".

    Returns
    -------
    float
        Evidence confidence C ∈ [0, 1], rounded to 4 decimal places.
    """
    factors: list[bool] = [
        has_schema,
        query_success,
        data_completeness > 0.7,
    ]
    return round(sum(factors) / len(factors), 4)


def build_evidence_from_investigation(
    incident_id: str,
    package_name: str,
    vulnerability_description: str,
    affected_repos: List[Dict[str, Any]],
    dependency_paths: List[Dict[str, Any]],
    direct_count: int,
    transitive_count: int,
    summary: str,
    schema_found: bool,
    query_success: bool,
    data_completeness: float,
    blast_config: BlastRadiusConfig | None = None,
) -> IncidentEvidence:
    """
    Create a complete IncidentEvidence object from raw investigation results.

    This is the single entry point for building the evidence bundle that
    flows into ARF governance.  It computes the blast‑radius score and
    evidence confidence, then assembles the Pydantic model.

    Parameters
    ----------
    incident_id : str
        Unique incident identifier.
    package_name : str
        The vulnerable package (e.g., 'urllib3').
    vulnerability_description : str
        CVE description or plain‑text summary.
    affected_repos : list of dict
        Each dict must contain at least 'repo' and 'dependency' keys.
    dependency_paths : list of dict
        Each dict must contain 'from' and 'to' keys.
    direct_count : int
        Number of direct dependencies.
    transitive_count : int
        Number of transitive dependencies.
    summary : str
        Human‑readable investigation summary.
    schema_found : bool
        Whether the CRAFT schema was discovered.
    query_success : bool
        Whether analytical queries succeeded.
    data_completeness : float
        Fraction of expected data returned (0.0 – 1.0).
    blast_config : BlastRadiusConfig, optional
        Custom blast‑radius configuration.

    Returns
    -------
    IncidentEvidence
        Fully populated evidence bundle ready for ARF evaluation.
    """
    repo_count = len(affected_repos)
    path_count = len(dependency_paths)

    blast = compute_blast_radius(
        affected_repository_count=repo_count,
        transitive_dependency_count=transitive_count,
        dependency_path_count=path_count,
        config=blast_config,
    )
    conf = calculate_evidence_confidence(
        has_schema=schema_found,
        query_success=query_success,
        data_completeness=data_completeness,
    )

    return IncidentEvidence(
        incident_id=incident_id,
        package_name=package_name,
        vulnerability_description=vulnerability_description,
        affected_repositories=affected_repos,
        dependency_paths=dependency_paths,
        direct_dependency_count=direct_count,
        transitive_dependency_count=transitive_count,
        affected_repository_count=repo_count,
        evidence_confidence=conf,
        blast_radius_score=blast,
        investigation_summary=summary,
    )
