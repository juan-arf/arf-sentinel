""" Blast‑radius normalisation and evidence confidence calculation. """

from .models import IncidentEvidence

def compute_blast_radius(
    """ Normalise dependency impact into a [0,1] score.  Parameters:
    affected_repository_count: number of repos.   transitive_dependency_count:
    transitive deps.   dependency_path_count: unique dependency paths.  Returns:
    float: weighted blast radius score."""
    affected_repository_count: int,
    transitive_dependency_count: int,
    dependency_path_count: int
) -> float:
    """
    Prototype normalisation heuristic.
    Components clamped to [0,1] then weighted.
    """
    repo_component = min(affected_repository_count / 200, 1.0)
    transitive_component = min(transitive_dependency_count / 100, 1.0)
    path_component = min(dependency_path_count / 50, 1.0)
    score = (0.50 * repo_component) + (0.30 * transitive_component) + (0.20 * path_component)
    return round(score, 4)

def calculate_evidence_confidence(
    """ Estimate confidence in the CRAFT investigation.  Parameters:
    has_schema: whether schema was discovered.   query_success: whether queries
    succeeded.   data_completeness: fraction of expected data returned.
    Returns:   float: confidence [0,1]."""
    has_schema: bool,
    query_success: bool,
    data_completeness: float
) -> float:
    factors = [has_schema, query_success, data_completeness > 0.7]
    return round(sum(factors) / 3, 4)

def build_evidence_from_investigation(
    """ Create a complete IncidentEvidence object from raw investigation
    results."""
    incident_id: str,
    package_name: str,
    vulnerability_description: str,
    affected_repos: list[dict],
    dependency_paths: list[dict],
    direct_count: int,
    transitive_count: int,
    summary: str,
    schema_found: bool,
    query_success: bool,
    data_completeness: float
) -> IncidentEvidence:
    repo_count = len(affected_repos)
    path_count = len(dependency_paths)
    blast = compute_blast_radius(repo_count, transitive_count, path_count)
    conf = calculate_evidence_confidence(schema_found, query_success, data_completeness)

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
        investigation_summary=summary
    )
