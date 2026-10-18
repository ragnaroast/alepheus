"""Blast radius and corpus exposure tools.

- blast_radius: "Action X is compromised — what secrets/workflows are exposed?"
- corpus_exposure: "Which actions are the biggest choke points across the corpus?"
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


@dataclass
class BlastResult:
    """Result of a blast radius query."""
    action_slug: str
    affected_secrets: List[Dict[str, Any]] = field(default_factory=list)
    affected_workflows: List[str] = field(default_factory=list)
    affected_jobs: List[str] = field(default_factory=list)
    total_jobs: int = 0
    rotation_list: List[str] = field(default_factory=list)

    @property
    def secrets_exposed(self) -> List[str]:
        return self.rotation_list


def blast_radius(
    graph,
    action_slug: str,
    include_transitive: bool = True,
) -> BlastResult:
    """Compute the blast radius of a compromised action.

    "If action X is compromised, which secrets and workflows are exposed,
    and what's the rotation list?"

    Args:
        graph: FalkorDB graph instance
        action_slug: e.g. "tj-actions/changed-files"
        include_transitive: follow FLOWS edges transitively

    Returns:
        BlastResult with affected entities
    """
    result = BlastResult(action_slug=action_slug)

    # Direct: Action ← USES ← Step ← HAS_STEP ← Job → HOLDS → Secret
    direct_query = """
        MATCH (a:Action {slug: $slug})<-[:USES]-(:Step)<-[:HAS_STEP]-(j:Job)-[:HOLDS]->(s:Secret)
        RETURN s.name AS secret, s.repo AS repo, count(DISTINCT j) AS jobs
        ORDER BY jobs DESC
    """
    try:
        res = direct_query_result = graph.query(direct_query, {"slug": action_slug})
        for row in res.result_set:
            result.affected_secrets.append({
                "secret": row[0],
                "repo": row[1],
                "job_count": row[2],
            })
            result.rotation_list.append(f"{row[1]}:{row[0]}")
    except Exception as e:
        logger.error("Blast radius query failed: %s", e)

    # Affected workflows
    wf_query = """
        MATCH (a:Action {slug: $slug})<-[:USES]-(:Step)<-[:HAS_STEP]-(:Job)<-[:HAS_JOB]-(w:Workflow)
        RETURN DISTINCT w.path AS path, w.repo AS repo
    """
    try:
        res = graph.query(wf_query, {"slug": action_slug})
        for row in res.result_set:
            result.affected_workflows.append(f"{row[1]}:{row[0]}")
    except Exception as e:
        logger.error("Blast radius workflow query failed: %s", e)

    # Affected jobs count
    job_query = """
        MATCH (a:Action {slug: $slug})<-[:USES]-(:Step)<-[:HAS_STEP]-(j:Job)
        RETURN count(DISTINCT j) AS total
    """
    try:
        res = graph.query(job_query, {"slug": action_slug})
        if res.result_set:
            result.total_jobs = res.result_set[0][0]
    except Exception as e:
        logger.error("Blast radius job count failed: %s", e)

    logger.info(
        "Blast radius for %s: %d secrets, %d workflows, %d jobs",
        action_slug, len(result.affected_secrets),
        len(result.affected_workflows), result.total_jobs,
    )
    return result


@dataclass
class CorpusExposure:
    """Aggregated exposure stats for an action across the corpus."""
    action_slug: str
    repo_count: int
    job_count: int
    secret_count: int
    pinned_count: int
    unpinned_count: int


def corpus_exposure(
    graph,
    top_n: int = 20,
) -> List[CorpusExposure]:
    """Find most-used actions across the corpus with exposure stats.

    Reports aggregates only — no individual repo names (ethics rule).

    Args:
        graph: FalkorDB graph instance
        top_n: number of top actions to return

    Returns:
        List of CorpusExposure, sorted by repo_count descending
    """
    query = """
        MATCH (a:Action)<-[:USES]-(:Step)<-[:HAS_STEP]-(j:Job)<-[:HAS_JOB]-(w:Workflow)
        WITH a, count(DISTINCT w.repo) AS repos, count(DISTINCT j) AS jobs
        OPTIONAL MATCH (j2:Job)-[:HOLDS]->(s:Secret)
        WHERE (a)<-[:USES]-(:Step)<-[:HAS_STEP]-(j2)
        WITH a, repos, jobs, count(DISTINCT s) AS secrets
        RETURN a.slug AS slug, a.pinned AS pinned, repos, jobs, secrets
        ORDER BY repos DESC
        LIMIT $top_n
    """

    results: List[CorpusExposure] = []
    try:
        res = graph.query(query, {"top_n": top_n})
        for row in res.result_set:
            results.append(CorpusExposure(
                action_slug=row[0],
                repo_count=row[2],
                job_count=row[3],
                secret_count=row[4],
                pinned_count=1 if row[1] else 0,
                unpinned_count=0 if row[1] else 1,
            ))
    except Exception as e:
        logger.error("Corpus exposure query failed: %s", e)

    return results
