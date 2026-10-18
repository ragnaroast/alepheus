"""Batch graph writer — UNWIND MERGE for efficient bulk ingestion."""

from __future__ import annotations

import logging
from typing import Any, Dict, List

from chokepoint.parser.workflow import ParsedWorkflow, ParsedJob, ParsedStep
from chokepoint.parser.flows import FlowEdge, derive_flows
from chokepoint.schema import ensure_schema

logger = logging.getLogger(__name__)

BATCH_SIZE = 500


def ingest_workflow(graph, workflow: ParsedWorkflow, repo_full_name: str) -> Dict[str, int]:
    """Ingest a parsed workflow into the graph.

    Uses UNWIND MERGE for batch writes. Returns counts of created entities.

    Args:
        graph: FalkorDB graph instance
        workflow: Parsed workflow data
        repo_full_name: e.g. "octocat/hello-world"

    Returns:
        Dict with counts: {nodes: int, edges: int, flows: int}
    """
    counts = {"nodes": 0, "edges": 0, "flows": 0}
    wf_id = f"{repo_full_name}:{workflow.path}"

    # --- Repo node ---
    graph.query(
        "MERGE (r:Repo {full_name: $name})",
        {"name": repo_full_name},
    )
    counts["nodes"] += 1

    # --- Workflow node ---
    graph.query(
        """MERGE (w:Workflow {path: $path, repo: $repo})
           SET w.name = $name""",
        {"path": workflow.path, "repo": repo_full_name, "name": workflow.name or ""},
    )
    counts["nodes"] += 1

    # --- Repo → Workflow edge ---
    graph.query(
        """MATCH (r:Repo {full_name: $repo}), (w:Workflow {path: $path, repo: $repo})
           MERGE (r)-[:HAS_WORKFLOW]->(w)""",
        {"repo": repo_full_name, "path": workflow.path},
    )
    counts["edges"] += 1

    # --- Triggers ---
    for trigger in workflow.triggers:
        graph.query(
            """MERGE (t:Trigger {event: $event, workflow: $wf_id})
               SET t.attacker_controlled = $ac""",
            {"event": trigger.event, "wf_id": wf_id, "ac": trigger.attacker_controlled},
        )
        graph.query(
            """MATCH (t:Trigger {event: $event, workflow: $wf_id}),
                     (w:Workflow {path: $path, repo: $repo})
               MERGE (t)-[:TRIGGERS]->(w)""",
            {"event": trigger.event, "wf_id": wf_id, "path": workflow.path, "repo": repo_full_name},
        )
        counts["nodes"] += 1
        counts["edges"] += 1

    # --- Jobs ---
    for job in workflow.jobs:
        job_id = f"{wf_id}:{job.id}"
        graph.query(
            """MERGE (j:Job {job_id: $job_id})
               SET j.name = $name, j.runs_on = $runs_on, j.workflow = $wf_id""",
            {"job_id": job_id, "name": job.name or job.id, "runs_on": job.runs_on, "wf_id": wf_id},
        )
        counts["nodes"] += 1

        # Workflow → Job
        graph.query(
            """MATCH (w:Workflow {path: $path, repo: $repo}), (j:Job {job_id: $job_id})
               MERGE (w)-[:HAS_JOB]->(j)""",
            {"path": workflow.path, "repo": repo_full_name, "job_id": job_id},
        )
        counts["edges"] += 1

        # Job NEEDS dependencies
        for dep in job.needs:
            dep_id = f"{wf_id}:{dep}"
            graph.query(
                """MERGE (d:Job {job_id: $dep_id})
                   WITH d
                   MATCH (j:Job {job_id: $job_id})
                   MERGE (j)-[:NEEDS]->(d)""",
                {"dep_id": dep_id, "job_id": job_id},
            )
            counts["edges"] += 1

        # Environment
        if job.environment:
            graph.query(
                """MERGE (e:Environment {name: $env_name, repo: $repo})
                   WITH e
                   MATCH (j:Job {job_id: $job_id})
                   MERGE (e)-[:PROTECTS]->(j)""",
                {"env_name": job.environment, "repo": repo_full_name, "job_id": job_id},
            )
            counts["nodes"] += 1
            counts["edges"] += 1

        # Secrets
        for secret_name in job.secrets:
            secret_id = f"{repo_full_name}:{secret_name}"
            graph.query(
                """MERGE (s:Secret {name: $name, repo: $repo})
                   WITH s
                   MATCH (j:Job {job_id: $job_id})
                   MERGE (j)-[:HOLDS]->(s)""",
                {"name": secret_name, "repo": repo_full_name, "job_id": job_id},
            )
            counts["nodes"] += 1
            counts["edges"] += 1

        # --- Steps ---
        _ingest_steps(graph, job, job_id, wf_id, repo_full_name, workflow.path, counts)

    # --- FLOWS edges ---
    flow_edges = derive_flows(workflow, repo_full_name)
    _ingest_flows_batch(graph, flow_edges, counts)

    logger.info(
        "Ingested %s: %d nodes, %d struct edges, %d flow edges",
        wf_id, counts["nodes"], counts["edges"], counts["flows"],
    )
    return counts


def _ingest_steps(
    graph, job: ParsedJob, job_id: str, wf_id: str,
    repo_full_name: str, wf_path: str, counts: Dict[str, int],
) -> None:
    """Ingest all steps of a job."""
    for step in job.steps:
        step_id = f"{job_id}:step:{step.index}"
        graph.query(
            """MERGE (s:Step {step_id: $step_id})
               SET s.name = $name, s.index = $idx,
                   s.has_run = $has_run, s.injects_untrusted = $injects""",
            {
                "step_id": step_id,
                "name": step.name or f"step-{step.index}",
                "idx": step.index,
                "has_run": step.run is not None,
                "injects": step.injects_untrusted,
            },
        )
        counts["nodes"] += 1

        # Job → Step
        graph.query(
            """MATCH (j:Job {job_id: $job_id}), (s:Step {step_id: $step_id})
               MERGE (j)-[:HAS_STEP]->(s)""",
            {"job_id": job_id, "step_id": step_id},
        )
        counts["edges"] += 1

        # Step → Action
        if step.uses:
            action_id = f"{step.uses.slug}@{step.uses.ref}"
            graph.query(
                """MERGE (a:Action {slug: $slug})
                   SET a.ref = $ref, a.pinned = $pinned,
                       a.is_local = $local, a.is_reusable = $reusable""",
                {
                    "slug": step.uses.slug,
                    "ref": step.uses.ref,
                    "pinned": step.uses.pinned,
                    "local": step.uses.is_local,
                    "reusable": step.uses.is_reusable_workflow,
                },
            )
            graph.query(
                """MATCH (s:Step {step_id: $step_id}), (a:Action {slug: $slug})
                   MERGE (s)-[:USES]->(a)""",
                {"step_id": step_id, "slug": step.uses.slug},
            )
            counts["nodes"] += 1
            counts["edges"] += 1

        # Input nodes for untrusted expressions
        if step.injects_untrusted:
            for expr in step.untrusted_expressions:
                graph.query(
                    """MERGE (i:Input {source: $source, attacker: $attacker})""",
                    {"source": expr, "attacker": _attacker_for_expr(expr)},
                )
                counts["nodes"] += 1


def _ingest_flows_batch(graph, edges: List[FlowEdge], counts: Dict[str, int]) -> None:
    """Batch-ingest FLOWS edges using UNWIND MERGE."""
    if not edges:
        return

    # Process in batches
    for i in range(0, len(edges), BATCH_SIZE):
        batch = edges[i:i + BATCH_SIZE]
        params_list = []

        for e in batch:
            params_list.append({
                "src_type": e.source_type,
                "src_id": e.source_id,
                "tgt_type": e.target_type,
                "tgt_id": e.target_id,
                "kind": e.kind,
                "difficulty": e.difficulty,
                "fix_cost": e.fix_cost,
                "fixable": e.fixable,
                "fix_kind": e.fix_kind or "",
                "evidence_file": e.evidence_file,
                "evidence_line": e.evidence_line,
            })

        # We use individual MERGE for correctness (UNWIND MERGE with dynamic
        # labels is not supported in Cypher). This is fine for workflow-scale
        # data. For corpus scale, we batch by source/target type pairs.
        for p in params_list:
            _create_flow_edge(graph, p)
            counts["flows"] += 1


def _create_flow_edge(graph, p: dict) -> None:
    """Create a single FLOWS edge with all properties."""
    # Dynamic label handling: we use a two-pass approach
    # First ensure source and target nodes exist, then create edge
    src_q = _merge_query_for_type(p["src_type"], p["src_id"])
    tgt_q = _merge_query_for_type(p["tgt_type"], p["tgt_id"])

    graph.query(src_q["query"], src_q["params"])
    graph.query(tgt_q["query"], tgt_q["params"])

    # Create FLOWS edge
    graph.query(
        f"""MATCH (src:{p['src_type']} {{{src_q['key_prop']}: $src_id}}),
                  (tgt:{p['tgt_type']} {{{tgt_q['key_prop']}: $tgt_id}})
            MERGE (src)-[f:FLOWS {{kind: $kind}}]->(tgt)
            SET f.difficulty = $difficulty,
                f.fix_cost = $fix_cost,
                f.fixable = $fixable,
                f.fix_kind = $fix_kind,
                f.evidence_file = $evidence_file,
                f.evidence_line = $evidence_line""",
        {
            "src_id": p["src_id"],
            "tgt_id": p["tgt_id"],
            "kind": p["kind"],
            "difficulty": p["difficulty"],
            "fix_cost": p["fix_cost"],
            "fixable": p["fixable"],
            "fix_kind": p["fix_kind"],
            "evidence_file": p["evidence_file"],
            "evidence_line": p["evidence_line"],
        },
    )


def _merge_query_for_type(node_type: str, node_id: str) -> dict:
    """Generate a MERGE query for a node type."""
    key_props = {
        "Input": "source",
        "Step": "step_id",
        "Job": "job_id",
        "Secret": "name",
        "Capability": "kind",
        "Action": "slug",
    }
    key_prop = key_props.get(node_type, "id")

    # Special handling for Capability — also set crown:true
    if node_type == "Capability":
        return {
            "query": f"MERGE (n:{node_type} {{kind: $id}}) SET n.crown = true",
            "params": {"id": node_id},
            "key_prop": "kind",
        }

    return {
        "query": f"MERGE (n:{node_type} {{{key_prop}: $id}})",
        "params": {"id": node_id},
        "key_prop": key_prop,
    }


def _attacker_for_expr(expr: str) -> str:
    """Determine the attacker type from an expression."""
    if "issue" in expr or "comment" in expr:
        return "issue_author"
    if "pull_request" in expr or "head_ref" in expr:
        return "fork_pr_author"
    if "discussion" in expr:
        return "discussion_author"
    if "commits" in expr or "head_commit" in expr:
        return "commit_author"
    return "external"


def ingest_repo(graph, repo_full_name: str, workflows: List[ParsedWorkflow]) -> Dict[str, int]:
    """Ingest all workflows for a repo.

    Args:
        graph: FalkorDB graph instance
        repo_full_name: e.g. "octocat/hello-world"
        workflows: List of parsed workflows

    Returns:
        Aggregated counts
    """
    ensure_schema(graph)

    total = {"nodes": 0, "edges": 0, "flows": 0}
    for wf in workflows:
        counts = ingest_workflow(graph, wf, repo_full_name)
        for k in total:
            total[k] += counts[k]

    logger.info(
        "Repo %s ingested: %d nodes, %d edges, %d flows",
        repo_full_name, total["nodes"], total["edges"], total["flows"],
    )
    return total
