"""Corpus analysis engine — ecosystem insights across hundreds of repositories.

Calculates:
  - Third-party action centrality & ecosystem choke points
  - Unpinned action prevalence
  - Secret exposure blast radius across repositories
  - Aggregated risk distribution (strictly privacy-preserving, no repo naming)
"""

from __future__ import annotations

import logging
from collections import Counter
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any

from chokepoint.corpus.dataset import generate_corpus_workflows
from chokepoint.parser.workflow import parse_workflow
from chokepoint.ingestor.batch import ingest_workflow
from chokepoint.schema import init_schema

logger = logging.getLogger(__name__)


@dataclass
class ActionEcosystemMetric:
    action_slug: str
    total_usages: int
    unpinned_usages: int
    unpinned_ratio: float
    repos_impacted_count: int
    secrets_at_risk_count: int
    centrality_rank: int


@dataclass
class CorpusAnalysisReport:
    total_workflows_scanned: int
    total_repositories_scanned: int
    total_action_references: int
    overall_unpinned_ratio: float
    top_choke_point_actions: List[ActionEcosystemMetric]
    aggregate_secret_exposure_count: int


def ingest_and_analyze_corpus(
    graph=None,
    workflow_count: int = 250,
) -> CorpusAnalysisReport:
    """Ingest workflow corpus and run ecosystem choke point analytics.

    Can run directly against a FalkorDB graph or in standalone memory mode.
    """
    corpus_items = generate_corpus_workflows(count=workflow_count)

    repos_seen = set()
    action_usage_counter = Counter()
    unpinned_counter = Counter()
    action_repos = {}
    action_secrets = {}
    total_secrets_exposed = 0

    if graph is not None:
        try:
            init_schema(graph)
        except Exception as e:
            logger.warning("Schema initialization warning: %s", e)

    for repo_name, file_path, yaml_content in corpus_items:
        repos_seen.add(repo_name)
        pw = parse_workflow(file_path, yaml_content)

        if graph is not None:
            try:
                ingest_workflow(graph, pw, repo_name)
            except Exception as e:
                logger.debug("Ingestion error for %s: %s", repo_name, e)

        # Track secrets present in this workflow
        wf_secrets = set()
        for job in pw.jobs:
            wf_secrets.update(job.secrets_referenced)

        total_secrets_exposed += len(wf_secrets)

        # Track action usages
        for job in pw.jobs:
            for step in job.steps:
                if step.action_ref:
                    slug = step.action_ref.slug
                    action_usage_counter[slug] += 1
                    if not step.action_ref.pinned:
                        unpinned_counter[slug] += 1

                    if slug not in action_repos:
                        action_repos[slug] = set()
                        action_secrets[slug] = set()

                    action_repos[slug].add(repo_name)
                    action_secrets[slug].update(wf_secrets)

    # Sort actions by total usages & risk (centrality proxy)
    sorted_actions = sorted(
        action_usage_counter.items(),
        key=lambda kv: (len(action_secrets.get(kv[0], set())), kv[1]),
        reverse=True,
    )

    top_choke_points = []
    for rank, (slug, usage) in enumerate(sorted_actions[:15], start=1):
        unpinned = unpinned_counter.get(slug, 0)
        ratio = round(unpinned / usage, 3) if usage > 0 else 0.0
        top_choke_points.append(ActionEcosystemMetric(
            action_slug=slug,
            total_usages=usage,
            unpinned_usages=unpinned,
            unpinned_ratio=ratio,
            repos_impacted_count=len(action_repos.get(slug, set())),
            secrets_at_risk_count=len(action_secrets.get(slug, set())),
            centrality_rank=rank,
        ))

    total_actions = sum(action_usage_counter.values())
    total_unpinned = sum(unpinned_counter.values())
    overall_ratio = round(total_unpinned / total_actions, 3) if total_actions > 0 else 0.0

    return CorpusAnalysisReport(
        total_workflows_scanned=len(corpus_items),
        total_repositories_scanned=len(repos_seen),
        total_action_references=total_actions,
        overall_unpinned_ratio=overall_ratio,
        top_choke_point_actions=top_choke_points,
        aggregate_secret_exposure_count=total_secrets_exposed,
    )


def format_corpus_report(report: CorpusAnalysisReport) -> str:
    """Format privacy-preserving aggregate ecosystem report."""
    lines = [
        "==========================================================================================",
        "             CHOKEPOINT ECOSYSTEM CORPUS CHOKE-POINT ANALYSIS (AGGREGATED)                 ",
        "==========================================================================================",
        f"Repositories Scanned:    {report.total_repositories_scanned}",
        f"Workflows Scanned:       {report.total_workflows_scanned}",
        f"Action Invocations:      {report.total_action_references}",
        f"Overall Unpinned Ratio:  {report.overall_unpinned_ratio * 100:.1f}%",
        f"Secrets at Risk Total:   {report.aggregate_secret_exposure_count}",
        "------------------------------------------------------------------------------------------",
        f"{'Rank':<5} | {'Third-Party Action Slug':<35} | {'Usages':<8} | {'Unpinned %':<10} | {'Repos Impacted':<14} | {'Secrets Exposed'}",
        "------+-------------------------------------+----------+------------+----------------+----------------",
    ]

    for m in report.top_choke_point_actions:
        lines.append(
            f"{m.centrality_rank:<5} | {m.action_slug:<35} | {m.total_usages:<8} | {m.unpinned_ratio*100:>8.1f}% | {m.repos_impacted_count:<14} | {m.secrets_at_risk_count}"
        )

    lines.append("==========================================================================================")
    lines.append("Privacy Notice: In accordance with responsible disclosure, individual repositories")
    lines.append("are aggregated and anonymized.")
    return "\n".join(lines)
