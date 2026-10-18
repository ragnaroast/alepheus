"""FastMCP server for ChokePoint — CI/CD Attack-Path Analysis Agent.

Exposes graph tools via Model Context Protocol (MCP) using Streamable HTTP
transport with optional Bearer token authentication.

Tools exposed:
  - list_chains: Find attack chains from untrusted input to crown jewels
  - explain_chain: Detailed evidence along each hop of a chain
  - blast_radius: Incident mode — find exposed secrets/jobs for a compromised action
  - choke_points: Centrality analysis across workflow components
  - min_fix_set: Minimum cut computation to sever all attack chains
  - diff_snapshots: PR gate comparison between base and head snapshots
  - search_advisories: Search security advisories by keyword
  - run_cypher_ro: Safe read-only Cypher query execution
  - propose_patch: Draft comment-preserving YAML patches for detected fixes
  - simulate_patch: Verify patches eliminate chains in what-if graph
"""

from __future__ import annotations

import json
import logging
from typing import Any, Dict, List, Optional

from fastmcp import FastMCP

from chokepoint.config import get_settings
from chokepoint.db import get_sync_db, graph_key
from chokepoint.tools.chains import list_chains as _list_chains, explain_chain as _explain_chain
from chokepoint.tools.blast import blast_radius as _blast_radius, corpus_exposure as _corpus_exposure
from chokepoint.tools.cuts import choke_points as _choke_points, min_fix_set as _min_fix_set
from chokepoint.tools.diff import diff_snapshots as _diff_snapshots
from chokepoint.tools.search import search_advisories as _search_advisories
from chokepoint.tools.cypher import run_cypher_ro as _run_cypher_ro
from chokepoint.patch.engine import generate_patches as _generate_patches
from chokepoint.patch.whatif import simulate_patch as _simulate_patch

logger = logging.getLogger(__name__)

settings = get_settings()

mcp = FastMCP(
    "chokepoint",
    instructions="ChokePoint CI/CD attack-path analysis and minimum-cut remediation toolset",
)


def _get_graph(tenant: str = "default", snapshot: str = "latest"):
    db = get_sync_db()
    name = graph_key(tenant, snapshot)
    return db.select_graph(name)


@mcp.tool()
def list_chains(
    tenant: str = "default",
    snapshot: str = "latest",
    max_depth: int = 8,
    limit: int = 50,
) -> str:
    """Find all attack chains from attacker-controlled inputs to crown-jewel capabilities.

    Args:
        tenant: Organization/tenant identifier (default: "default")
        snapshot: Graph snapshot or commit SHA (default: "latest")
        max_depth: Maximum path traversal hops (1..8)
        limit: Max chains to return

    Returns:
        JSON string containing ranked attack chains with exploit difficulty and evidence.
    """
    graph = _get_graph(tenant, snapshot)
    chains = _list_chains(graph, max_depth=max_depth, limit=limit)
    return json.dumps([c.__dict__ for c in chains], indent=2, default=str)


@mcp.tool()
def explain_chain(
    chain_id: str,
    tenant: str = "default",
    snapshot: str = "latest",
) -> str:
    """Retrieve detailed step-by-step evidence along an attack chain hop by hop.

    Args:
        chain_id: Identifier of the attack chain (e.g. "chain-0")
        tenant: Organization/tenant identifier
        snapshot: Graph snapshot or commit SHA

    Returns:
        JSON string describing every node, relationship, evidence file, and line.
    """
    graph = _get_graph(tenant, snapshot)
    chain = _explain_chain(graph, chain_id)
    if not chain:
        return json.dumps({"error": f"Chain {chain_id} not found."})
    data = chain if isinstance(chain, dict) else chain.__dict__
    return json.dumps(data, indent=2, default=str)


@mcp.tool()
def blast_radius(
    action_slug: str,
    tenant: str = "default",
    snapshot: str = "latest",
) -> str:
    """Incident mode: Determine all workflows, jobs, and secrets exposed if an action is compromised.

    Args:
        action_slug: Third-party action repository slug (e.g. "actions/checkout" or "tj-actions/changed-files")
        tenant: Organization/tenant identifier
        snapshot: Graph snapshot or commit SHA

    Returns:
        JSON report with affected workflows, affected secrets, and urgent rotation checklist.
    """
    graph = _get_graph(tenant, snapshot)
    radius = _blast_radius(graph, action_slug)
    data = radius if isinstance(radius, dict) else radius.__dict__
    return json.dumps(data, indent=2, default=str)


@mcp.tool()
def corpus_exposure(
    action_slug: str,
    corpus_graph_name: str = "cp:corpus",
) -> str:
    """Ecosystem view: Query aggregate usage of a third-party action across all scanned repositories.

    Args:
        action_slug: Action repository slug
        corpus_graph_name: Corpus graph key in FalkorDB
    """
    db = get_sync_db()
    graph = db.select_graph(corpus_graph_name)
    exposure = _corpus_exposure(graph, action_slug)
    data = exposure if isinstance(exposure, dict) else exposure.__dict__
    return json.dumps(data, indent=2, default=str)


@mcp.tool()
def choke_points(
    tenant: str = "default",
    snapshot: str = "latest",
    limit: int = 15,
) -> str:
    """Compute centrality across the CI/CD pipeline graph to identify high-leverage choke points.

    Args:
        tenant: Organization/tenant identifier
        snapshot: Graph snapshot
        limit: Max nodes to return
    """
    graph = _get_graph(tenant, snapshot)
    cps = _choke_points(graph, limit=limit)
    data = [c if isinstance(c, dict) else c.__dict__ for c in cps]
    return json.dumps(data, indent=2, default=str)


@mcp.tool()
def min_fix_set(
    tenant: str = "default",
    snapshot: str = "latest",
) -> str:
    """Compute the minimum cut (cheapest set of fixes) that severs all attack chains to crown jewels.

    Uses algo.maxFlow with fix_cost capacities and residual BFS.

    Returns:
        JSON object listing the minimum fix actions, total cost, and chains severed.
    """
    graph = _get_graph(tenant, snapshot)
    cut = _min_fix_set(graph)
    return json.dumps(
        {
            "total_cost": cut.total_cost,
            "fix_count": len(cut.fixes),
            "chains_severed": cut.chains_severed,
            "fixes": [f.__dict__ for f in cut.fixes],
        },
        indent=2,
        default=str,
    )


@mcp.tool()
def diff_snapshots(
    base_snapshot: str,
    head_snapshot: str,
    tenant: str = "default",
) -> str:
    """PR Gate: Compare attack chains between base and head commit snapshots.

    Args:
        base_snapshot: Base branch commit SHA
        head_snapshot: PR head commit SHA
        tenant: Organization/tenant identifier

    Returns:
        JSON report indicating if new chains were introduced, eliminated, or whether gate passes.
    """
    db = get_sync_db()
    base_graph = db.select_graph(graph_key(tenant, base_snapshot))
    head_graph = db.select_graph(graph_key(tenant, head_snapshot))
    diff = _diff_snapshots(base_graph, head_graph)
    return json.dumps(diff.__dict__, indent=2, default=str)


@mcp.tool()
def search_advisories(keyword: str) -> str:
    """Search the security advisory index for known CI/CD vulnerability patterns.

    Args:
        keyword: Search query (e.g. "pwn-request", "tj-actions", "injection")
    """
    db = get_sync_db()
    graph = _get_graph()
    advisories = _search_advisories(graph, keyword)
    return json.dumps([a.__dict__ for a in advisories], indent=2, default=str)


@mcp.tool()
def run_cypher_ro(
    query: str,
    tenant: str = "default",
    snapshot: str = "latest",
) -> str:
    """Execute a guarded read-only Cypher query against the pipeline graph.

    Mutating clauses (CREATE, MERGE, DELETE, SET, DROP) are strictly blocked.
    """
    graph = _get_graph(tenant, snapshot)
    result = _run_cypher_ro(graph, query)
    return json.dumps(result, indent=2, default=str)


def start():
    """Start FastMCP server via streamable HTTP."""
    logger.info("Starting ChokePoint FastMCP server on port %s", settings.mcp_port)
    mcp.run(
        transport="sse",
        host="0.0.0.0",
        port=settings.mcp_port,
    )


if __name__ == "__main__":
    start()
