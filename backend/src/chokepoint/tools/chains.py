"""Chain discovery tools — list_chains, explain_chain.

Finds attacker-controlled input → crown-jewel capability paths
using bounded variable-length FLOWS traversal and algo.SPpaths.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


@dataclass
class ChainHop:
    """One hop in an attack chain."""
    source_label: str
    source_id: str
    edge_kind: str
    target_label: str
    target_id: str
    difficulty: int
    fix_cost: int
    fixable: bool
    fix_kind: str
    evidence_file: str
    evidence_line: int


@dataclass
class AttackChain:
    """A complete attacker → crown-jewel path."""
    chain_id: str
    attacker: str
    input_source: str
    capability: str
    total_difficulty: int
    hops: List[ChainHop] = field(default_factory=list)
    fixable_hops: int = 0


def list_chains(
    graph,
    attacker: Optional[str] = None,
    max_depth: int = 8,
    limit: int = 50,
) -> List[AttackChain]:
    """Find all attack chains from attacker-controlled inputs to crown jewels.

    Args:
        graph: FalkorDB graph instance
        attacker: optional filter by attacker type (fork_pr_author, issue_author, etc.)
        max_depth: maximum traversal depth
        limit: max chains to return

    Returns:
        List of AttackChain objects, sorted by total difficulty (easiest first)
    """
    # Build the query with optional attacker filter
    attacker_filter = ""
    params: Dict[str, Any] = {"limit": limit}

    if attacker:
        attacker_filter = "{attacker: $attacker}"
        params["attacker"] = attacker

    query = f"""
        MATCH p = (i:Input {attacker_filter})-[:FLOWS*1..{max_depth}]->(c:Capability {{crown: true}})
        WITH p, i, c,
             reduce(w = 0, e IN relationships(p) | w + e.difficulty) AS cost
        RETURN p, i, c, cost
        ORDER BY cost
        LIMIT $limit
    """

    try:
        result = graph.query(query, params)
    except Exception as e:
        logger.error("Chain query failed: %s", e)
        return []

    chains: List[AttackChain] = []
    for idx, row in enumerate(result.result_set):
        path = row[0]  # Path object
        input_node = row[1]
        cap_node = row[2]
        total_cost = row[3]

        chain = AttackChain(
            chain_id=f"chain-{idx}",
            attacker=getattr(input_node, "attacker", "unknown"),
            input_source=getattr(input_node, "source", "unknown"),
            capability=getattr(cap_node, "kind", "unknown"),
            total_difficulty=total_cost,
        )

        # Extract hops from path
        if hasattr(path, "nodes") and hasattr(path, "edges"):
            nodes = path.nodes()
            edges = path.edges()
        else:
            nodes = []
            edges = []
        for i, edge in enumerate(edges):
            src_node = nodes[i] if i < len(nodes) else None
            tgt_node = nodes[i + 1] if i + 1 < len(nodes) else None

            hop = ChainHop(
                source_label=_get_label(src_node),
                source_id=_get_id(src_node),
                edge_kind=edge.properties.get("kind", ""),
                target_label=_get_label(tgt_node),
                target_id=_get_id(tgt_node),
                difficulty=edge.properties.get("difficulty", 0),
                fix_cost=edge.properties.get("fix_cost", 0),
                fixable=edge.properties.get("fixable", False),
                fix_kind=edge.properties.get("fix_kind", ""),
                evidence_file=edge.properties.get("evidence_file", ""),
                evidence_line=edge.properties.get("evidence_line", 0),
            )
            chain.hops.append(hop)
            if hop.fixable:
                chain.fixable_hops += 1

        chains.append(chain)

    logger.info("Found %d attack chains", len(chains))
    return chains


def explain_chain(
    graph,
    chain_id: str,
    chains: Optional[List[AttackChain]] = None,
) -> Dict[str, Any]:
    """Generate a detailed explanation of a specific chain.

    Args:
        graph: FalkorDB graph instance
        chain_id: ID of the chain to explain
        chains: optional pre-computed chains list

    Returns:
        Dict with chain details and evidence
    """
    if chains is None:
        chains = list_chains(graph)

    target = None
    for c in chains:
        if c.chain_id == chain_id:
            target = c
            break

    if target is None:
        return {"error": f"Chain {chain_id} not found"}

    explanation = {
        "chain_id": target.chain_id,
        "attacker": target.attacker,
        "input": target.input_source,
        "capability": target.capability,
        "total_difficulty": target.total_difficulty,
        "fixable_hops": target.fixable_hops,
        "total_hops": len(target.hops),
        "narrative": _build_narrative(target),
        "hops": [
            {
                "step": i + 1,
                "from": f"{h.source_label}({h.source_id})",
                "to": f"{h.target_label}({h.target_id})",
                "kind": h.edge_kind,
                "difficulty": h.difficulty,
                "fixable": h.fixable,
                "fix": h.fix_kind if h.fixable else "N/A",
                "evidence": f"{h.evidence_file}:{h.evidence_line}" if h.evidence_file else "N/A",
            }
            for i, h in enumerate(target.hops)
        ],
    }
    return explanation


def _build_narrative(chain: AttackChain) -> str:
    """Build a human-readable narrative for a chain."""
    parts = [
        f"An attacker ({chain.attacker}) controls {chain.input_source}.",
    ]

    for hop in chain.hops:
        if hop.edge_kind == "inject":
            parts.append(
                f"This value is injected into a shell step via ${{{{ {hop.target_id} }}}}."
            )
        elif hop.edge_kind == "exec":
            parts.append(f"The step executes with the injected value in job {hop.target_id}.")
        elif hop.edge_kind == "poison":
            parts.append(f"Unpinned action {hop.source_id} could be compromised.")
        elif hop.edge_kind == "grant":
            parts.append(f"This grants access to {hop.target_id}.")
        elif hop.edge_kind == "expose":
            parts.append(f"This exposes {hop.target_id} in logs or outputs.")
        elif hop.edge_kind == "inherit":
            parts.append(f"Secrets are inherited via reusable workflow call.")

    parts.append(f"Ultimately compromising crown jewel: {chain.capability}.")
    return " ".join(parts)


def _get_label(node) -> str:
    """Extract the primary label from a graph node."""
    if node is None:
        return "Unknown"
    # FalkorDB nodes have a .labels property
    labels = getattr(node, "labels", [])
    if labels:
        return labels[0] if isinstance(labels, list) else str(labels)
    return "Unknown"


def _get_id(node) -> str:
    """Extract a readable ID from a graph node."""
    if node is None:
        return "?"
    props = getattr(node, "properties", {})
    for key in ("source", "step_id", "job_id", "name", "slug", "kind", "full_name", "path"):
        if key in props:
            return str(props[key])
    return str(getattr(node, "id", "?"))
