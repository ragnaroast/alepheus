"""FastAPI REST API and SSE Event Stream for ChokePoint.

Provides endpoints for:
  - Workflow & Repository Ingestion
  - Attack Chain Traversal & Hop-by-Hop Explanation
  - Minimum Cut / Fix Set Computation (algo.maxFlow + residual BFS)
  - Blast Radius & Compromised Action Incident Response
  - Comment-Preserving ruamel.yaml Patch Generation
  - What-If Simulation via GRAPH.COPY
  - Real-time SSE Investigation Streaming from the Gemini Agent
  - PR Gate Snapshot Comparison
  - Corpus Ecosystem Aggregation
"""

from __future__ import annotations

import asyncio
import json
import logging
from typing import Any, Dict, List, Optional

from fastapi import FastAPI, HTTPException, Query, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from sse_starlette.sse import EventSourceResponse

from chokepoint.config import get_settings
from chokepoint.db import get_sync_db, graph_key
from chokepoint.schema import init_schema
from chokepoint.parser.workflow import parse_workflow
from chokepoint.ingestor.batch import ingest_workflow
from chokepoint.tools.chains import list_chains, explain_chain
from chokepoint.tools.blast import blast_radius, corpus_exposure
from chokepoint.tools.cuts import choke_points, min_fix_set
from chokepoint.tools.diff import diff_snapshots
from chokepoint.tools.search import search_advisories
from chokepoint.patch.engine import generate_patches, Patch
from chokepoint.patch.whatif import simulate_patch
from chokepoint.agent.loop import run_agent, AgentResult
from chokepoint.agent.llm import ToolDef, create_llm_client
from chokepoint.agent.trace import TraceStep

logger = logging.getLogger(__name__)
settings = get_settings()

app = FastAPI(
    title="ChokePoint CI/CD Security Engine",
    description="Attack-path traversal, minimum-cut remediation, and verified YAML patching",
    version="1.0.0",
)

# Enable CORS for the React console
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ---------------------------------------------------------------------------
# Models
# ---------------------------------------------------------------------------

class IngestWorkflowRequest(BaseModel):
    repo: str
    workflow_path: str
    content: str
    tenant: str = "default"
    snapshot: str = "latest"


class GeneratePatchRequest(BaseModel):
    workflow_path: str
    content: str
    tenant: str = "default"
    snapshot: str = "latest"


class SimulatePatchRequest(BaseModel):
    repo: str
    workflow_path: str
    original_content: str
    patched_content: str
    tenant: str = "default"
    snapshot: str = "latest"


class InvestigateRequest(BaseModel):
    prompt: str
    tenant: str = "default"
    snapshot: str = "latest"
    max_iterations: Optional[int] = 10


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _resolve_graph(tenant: str = "default", snapshot: str = "latest"):
    try:
        db = get_sync_db()
        name = graph_key(tenant, snapshot)
        graph = db.select_graph(name)
        return graph
    except Exception as e:
        logger.error("Failed to connect to FalkorDB graph: %s", e)
        raise HTTPException(status_code=503, detail=f"Graph database unavailable: {e}")


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@app.get("/api/health")
def health():
    """Health check endpoint and version info."""
    return {
        "status": "healthy",
        "service": "chokepoint",
        "version": "1.0.0",
        "llm_model": settings.agent_model,
        "falkordb_host": settings.falkordb_host,
    }


@app.post("/api/ingest")
def ingest_workflow_endpoint(req: IngestWorkflowRequest):
    """Parse and ingest a GitHub Actions workflow YAML directly into FalkorDB."""
    graph = _resolve_graph(req.tenant, req.snapshot)
    try:
        init_schema(graph)
        wf = parse_workflow(req.workflow_path, req.content)
        ingest_workflow(graph, wf, req.repo)
        return {
            "status": "ingested",
            "repo": req.repo,
            "workflow": wf.name,
            "path": req.workflow_path,
            "jobs_count": len(wf.jobs),
            "untrusted_inputs_count": len(wf.untrusted_inputs),
        }
    except Exception as e:
        logger.exception("Ingest failed: %s", e)
        raise HTTPException(status_code=400, detail=str(e))


@app.get("/api/chains")
def get_chains(
    tenant: str = "default",
    snapshot: str = "latest",
    max_depth: int = Query(default=8, ge=1, le=15),
    limit: int = Query(default=50, ge=1, le=200),
):
    """List attack paths from attacker-controlled inputs to crown-jewel capabilities."""
    graph = _resolve_graph(tenant, snapshot)
    chains = list_chains(graph, max_depth=max_depth, limit=limit)
    return [c.__dict__ for c in chains]


@app.get("/api/chains/{chain_id}")
def get_chain_detail(
    chain_id: str,
    tenant: str = "default",
    snapshot: str = "latest",
):
    """Get hop-by-hop evidence for a specific chain."""
    graph = _resolve_graph(tenant, snapshot)
    detail = explain_chain(graph, chain_id)
    if not detail or (isinstance(detail, dict) and "error" in detail):
        raise HTTPException(status_code=404, detail=f"Chain {chain_id} not found")
    return detail if isinstance(detail, dict) else detail.__dict__


@app.get("/api/blast-radius")
def get_blast_radius(
    action_slug: str = Query(..., description="Action slug, e.g. tj-actions/changed-files"),
    tenant: str = "default",
    snapshot: str = "latest",
):
    """Incident mode: Find all secrets and workflows exposed if this action is compromised."""
    graph = _resolve_graph(tenant, snapshot)
    radius = blast_radius(graph, action_slug)
    return radius if isinstance(radius, dict) else radius.__dict__


@app.get("/api/choke-points")
def get_choke_points(
    tenant: str = "default",
    snapshot: str = "latest",
    limit: int = Query(default=15, ge=1, le=50),
):
    """Compute centrality across the pipeline graph to identify high-leverage bottlenecks."""
    graph = _resolve_graph(tenant, snapshot)
    cps = choke_points(graph, limit=limit) if hasattr(choke_points, "__call__") else []
    return [c if isinstance(c, dict) else c.__dict__ for c in cps]


@app.get("/api/min-fix-set")
def get_min_fix_set(
    tenant: str = "default",
    snapshot: str = "latest",
):
    """Compute the minimum cut that severs all attack chains to crown jewels."""
    graph = _resolve_graph(tenant, snapshot)
    cut = min_fix_set(graph)
    return {
        "total_cost": cut.total_cost,
        "fix_count": len(cut.fixes),
        "chains_severed": cut.chains_severed,
        "fixes": [f.__dict__ for f in cut.fixes],
    }


@app.get("/api/diff")
def get_diff(
    base: str = Query(..., description="Base commit SHA"),
    head: str = Query(..., description="Head commit SHA"),
    tenant: str = "default",
):
    """PR gate diff comparing attack chains between base and head snapshots."""
    db = get_sync_db()
    base_graph = db.select_graph(graph_key(tenant, base))
    head_graph = db.select_graph(graph_key(tenant, head))
    diff = diff_snapshots(base_graph, head_graph)
    return diff.__dict__


@app.post("/api/patch/generate")
def generate_patch_endpoint(req: GeneratePatchRequest):
    """Generate comment-preserving ruamel.yaml patches to eliminate discovered attack chains."""
    graph = _resolve_graph(req.tenant, req.snapshot)
    cut = min_fix_set(graph)
    patches = generate_patches(req.workflow_path, req.content, cut.fixes)
    return [p.__dict__ for p in patches]


@app.post("/api/patch/simulate")
def simulate_patch_endpoint(req: SimulatePatchRequest):
    """Verify that a patch eliminates attack chains via isolated GRAPH.COPY what-if re-analysis."""
    graph_name = graph_key(req.tenant, req.snapshot)
    test_patch = Patch(
        file_path=req.workflow_path,
        fix_kind="verified_simulation",
        description="Candidate verification patch",
        original=req.original_content,
        patched=req.patched_content,
    )
    result = simulate_patch(
        source_graph_name=graph_name,
        patches=[test_patch],
        repo_full_name=req.repo,
        tenant=req.tenant,
    )
    return result.__dict__


@app.get("/api/corpus")
def get_corpus_summary(
    action_slug: Optional[str] = None,
    corpus_graph: str = "cp:corpus",
):
    """Ecosystem view: Query aggregate metrics across public corpus repos without exposing repo names."""
    db = get_sync_db()
    graph = db.select_graph(corpus_graph)
    if action_slug:
        exposure = corpus_exposure(graph, action_slug)
        return exposure.__dict__

    # General aggregate corpus metrics
    try:
        res = graph.query(
            """
            MATCH (a:Action)
            OPTIONAL MATCH (s:Step)-[:USES]->(a)
            RETURN a.slug AS action, count(DISTINCT s) AS step_count
            ORDER BY step_count DESC
            LIMIT 20
            """
        )
        return {
            "top_actions": [
                {"action": r[0], "usages": r[1]}
                for r in (res.result_set if res else [])
            ]
        }
    except Exception as e:
        return {"top_actions": [], "error": str(e)}


@app.get("/api/investigate/stream")
async def investigate_stream(
    prompt: str = Query(...),
    tenant: str = "default",
    snapshot: str = "latest",
):
    """Real-time SSE event stream for agent investigation trace."""
    graph = _resolve_graph(tenant, snapshot)

    async def event_generator():
        queue: asyncio.Queue[TraceStep] = asyncio.Queue()

        def step_callback(step: TraceStep):
            queue.put_nowait(step)

        # Build tools dictionary for agent
        tools_dict = {
            "list_chains": ToolDef(
                name="list_chains",
                description="List attack chains from attacker inputs to crown jewels",
                parameters={"type": "object", "properties": {"limit": {"type": "integer"}}},
                function=lambda limit=50: [c.__dict__ for c in list_chains(graph, limit=limit)],
            ),
            "blast_radius": ToolDef(
                name="blast_radius",
                description="Check exposed secrets and workflows for a compromised action",
                parameters={"type": "object", "properties": {"action_slug": {"type": "string"}}, "required": ["action_slug"]},
                function=lambda action_slug: blast_radius(graph, action_slug).__dict__,
            ),
            "min_fix_set": ToolDef(
                name="min_fix_set",
                description="Compute the minimum cut of fixes to sever all chains",
                parameters={"type": "object", "properties": {}},
                function=lambda: min_fix_set(graph).__dict__,
            ),
        }

        # Run agent in background thread
        loop = asyncio.get_event_loop()
        agent_task = loop.run_in_executor(
            None,
            lambda: run_agent(
                prompt=prompt,
                tools=tools_dict,
                on_step=step_callback,
            ),
        )

        yield {
            "event": "start",
            "data": json.dumps({"prompt": prompt, "model": settings.agent_model}),
        }

        while not agent_task.done() or not queue.empty():
            try:
                step = await asyncio.wait_for(queue.get(), timeout=0.3)
                yield {
                    "event": "step",
                    "data": json.dumps({
                        "iteration": step.iteration,
                        "action": step.action,
                        "details": step.details,
                        "duration_ms": step.duration_ms,
                    }),
                }
            except asyncio.TimeoutError:
                continue

        agent_result: AgentResult = await agent_task
        yield {
            "event": "complete",
            "data": json.dumps({
                "report": agent_result.report,
                "tool_calls_made": agent_result.tool_calls_made,
                "iterations": agent_result.iterations,
                "success": agent_result.success,
            }),
        }

    return EventSourceResponse(event_generator())
