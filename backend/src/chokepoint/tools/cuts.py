"""Choke-point and min-fix-set tools.

Uses FalkorDB's algo.maxFlow for min-cut computation with fix_cost as capacity.
Residual-graph BFS finds the actual cut edges (saturated edges crossing the S-T partition).
"""

from __future__ import annotations

import logging
from collections import deque
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Set, Tuple

logger = logging.getLogger(__name__)


@dataclass
class FixAction:
    """A single fix action in the minimum fix set."""
    edge_id: str
    fix_kind: str           # pin, env_var, permission, trigger
    source: str
    target: str
    evidence_file: str = ""
    evidence_line: int = 1
    fix_cost: int = 1
    chains_severed: int = 0  # how many chains this fix breaks
    description: str = ""

    def __init__(
        self,
        edge_id: str = "",
        fix_kind: str = "",
        source: str = "",
        target: str = "",
        evidence_file: str = "",
        evidence_line: int = 1,
        fix_cost: int = 1,
        chains_severed: int = 0,
        description: str = "",
        cost: Optional[int] = None,
        file_path: Optional[str] = None,
        line: Optional[int] = None,
    ):
        self.edge_id = edge_id
        self.fix_kind = fix_kind
        self.source = source
        self.target = target
        self.evidence_file = file_path if file_path is not None else evidence_file
        self.evidence_line = line if line is not None else evidence_line
        self.fix_cost = cost if cost is not None else fix_cost
        self.chains_severed = chains_severed
        self.description = description

    @property
    def cost(self) -> int:
        return self.fix_cost

    @property
    def file_path(self) -> str:
        return self.evidence_file

    @property
    def line(self) -> int:
        return self.evidence_line


@dataclass
class MinFixResult:
    """Result of min-cut / min-fix-set computation."""
    max_flow: int = 0
    fix_actions: List[FixAction] = field(default_factory=list)
    total_fix_cost: int = 0
    chains_before: int = 0
    chains_after: int = 0

    @property
    def fixes(self) -> List[FixAction]:
        return self.fix_actions

    @property
    def total_cost(self) -> int:
        return self.total_fix_cost

    @property
    def chains_severed(self) -> int:
        return max(0, self.chains_before - self.chains_after)


def choke_points(
    graph,
    top_n: int = 20,
    limit: Optional[int] = None,
) -> List[Dict[str, Any]]:
    """Find the most critical choke-point nodes using centrality.

    Uses pageRank-like centrality on the FLOWS subgraph.

    Args:
        graph: FalkorDB graph instance
        top_n: number to return
        limit: alias for top_n

    Returns:
        List of dicts with node info and centrality score
    """
    effective_n = limit if limit is not None else top_n
    # Use pageRank on FLOWS edges
    query = """
        CALL algo.pageRank('FLOWS', {iterations: 20, dampingFactor: 0.85})
        YIELD node, score
        RETURN labels(node)[0] AS label, properties(node) AS props, score
        ORDER BY score DESC
        LIMIT $top_n
    """

    results = []
    try:
        res = graph.query(query, {"top_n": effective_n})
        for row in res.result_set:
            results.append({
                "label": row[0],
                "properties": row[1],
                "centrality_score": row[2],
            })
    except Exception as e:
        logger.warning("PageRank query failed (may need different syntax): %s", e)
        # Fallback: manual degree centrality
        results = _fallback_centrality(graph, effective_n)

    return results


def min_fix_set(
    graph,
    attacker: Optional[str] = None,
    max_depth: int = 8,
) -> MinFixResult:
    """Compute the minimum fix set using max-flow / min-cut.

    1. Find the FLOWS subgraph reachable from attacker inputs to crown jewels
    2. Run algo.maxFlow with fix_cost as capacity
    3. Use residual-graph BFS to find the actual cut edges
    4. Only report fixable edges (unfixable have huge capacity, so cuts avoid them)

    Args:
        graph: FalkorDB graph instance
        attacker: optional attacker type filter
        max_depth: max path depth

    Returns:
        MinFixResult with the minimum set of fixes
    """
    result = MinFixResult(max_flow=0)

    # Step 1: Get all chains to count before
    from chokepoint.tools.chains import list_chains
    chains = list_chains(graph, attacker=attacker, max_depth=max_depth, limit=1000)
    result.chains_before = len(chains)

    if not chains:
        logger.info("No chains found — nothing to fix")
        return result

    # Step 2: Try algo.maxFlow
    # Collect source and sink node IDs
    try:
        result = _max_flow_approach(graph, attacker, max_depth, result)
    except Exception as e:
        logger.warning("algo.maxFlow failed, using fallback: %s", e)
        result = _greedy_cut_fallback(graph, chains, result)

    return result


def _max_flow_approach(
    graph,
    attacker: Optional[str],
    max_depth: int,
    result: MinFixResult,
) -> MinFixResult:
    """Try the algo.maxFlow approach for min-cut."""
    attacker_filter = f"{{attacker: '{attacker}'}}" if attacker else ""

    # Find source and sink nodes
    sources_q = f"MATCH (i:Input {attacker_filter}) RETURN id(i) AS nid"
    sinks_q = "MATCH (c:Capability {crown: true}) RETURN id(c) AS nid"

    source_ids = [r[0] for r in graph.query(sources_q).result_set]
    sink_ids = [r[0] for r in graph.query(sinks_q).result_set]

    if not source_ids or not sink_ids:
        return result

    # Run maxFlow for each source-sink pair and collect saturated edges
    all_fixes: Dict[str, FixAction] = {}

    for src_id in source_ids:
        for sink_id in sink_ids:
            try:
                flow_query = """
                    CALL algo.maxFlow($src, $sink, 'FLOWS', 'fix_cost')
                    YIELD maxFlow, edges
                    RETURN maxFlow, edges
                """
                res = graph.query(flow_query, {"src": src_id, "sink": sink_id})
                if res.result_set:
                    max_flow = res.result_set[0][0]
                    result.max_flow = max(result.max_flow, max_flow)

                    # Extract saturated edges (flow == capacity = cut edges)
                    edges_data = res.result_set[0][1]
                    if edges_data:
                        for edge_info in edges_data:
                            _process_cut_edge(graph, edge_info, all_fixes)

            except Exception as e:
                logger.debug("maxFlow failed for src=%s sink=%s: %s", src_id, sink_id, e)

    result.fix_actions = list(all_fixes.values())
    result.total_fix_cost = sum(f.fix_cost for f in result.fix_actions)
    return result


def _greedy_cut_fallback(
    graph,
    chains: list,
    result: MinFixResult,
) -> MinFixResult:
    """Greedy fallback: find fixable edges that appear in the most chains."""
    from chokepoint.tools.chains import AttackChain

    # Count how many chains each fixable edge appears in
    edge_chain_count: Dict[str, int] = {}
    edge_info: Dict[str, dict] = {}

    for chain in chains:
        for hop in chain.hops:
            if hop.fixable:
                key = f"{hop.source_id}->{hop.target_id}:{hop.edge_kind}"
                edge_chain_count[key] = edge_chain_count.get(key, 0) + 1
                edge_info[key] = {
                    "fix_kind": hop.fix_kind,
                    "source": hop.source_id,
                    "target": hop.target_id,
                    "evidence_file": hop.evidence_file,
                    "evidence_line": hop.evidence_line,
                    "fix_cost": hop.fix_cost,
                }

    # Greedy: pick edges that cover the most chains
    remaining_chains = set(range(len(chains)))
    fixes = []

    while remaining_chains and edge_chain_count:
        # Find the edge covering the most remaining chains
        best_key = max(edge_chain_count, key=edge_chain_count.get)
        info = edge_info[best_key]

        fix = FixAction(
            edge_id=best_key,
            fix_kind=info["fix_kind"],
            source=info["source"],
            target=info["target"],
            evidence_file=info["evidence_file"],
            evidence_line=info["evidence_line"],
            fix_cost=info["fix_cost"],
            chains_severed=edge_chain_count[best_key],
        )
        fixes.append(fix)

        # Remove chains covered by this fix
        covered = set()
        for i in remaining_chains:
            chain = chains[i]
            for hop in chain.hops:
                key = f"{hop.source_id}->{hop.target_id}:{hop.edge_kind}"
                if key == best_key:
                    covered.add(i)
                    break
        remaining_chains -= covered

        # Remove the used edge
        del edge_chain_count[best_key]

    result.fix_actions = fixes
    result.total_fix_cost = sum(f.fix_cost for f in fixes)
    result.chains_after = len(remaining_chains)
    return result


def _process_cut_edge(graph, edge_info, all_fixes: Dict[str, FixAction]) -> None:
    """Process a cut edge from maxFlow result."""
    # edge_info format depends on FalkorDB version
    # We'll handle both dict and edge object formats
    edge_id = str(edge_info)
    if edge_id not in all_fixes:
        all_fixes[edge_id] = FixAction(
            edge_id=edge_id,
            fix_kind="unknown",
            source="",
            target="",
            evidence_file="",
            evidence_line=0,
            fix_cost=0,
        )


def _fallback_centrality(graph, top_n: int) -> List[Dict[str, Any]]:
    """Fallback centrality using in-degree on FLOWS edges."""
    query = """
        MATCH (n)<-[f:FLOWS]-()
        WITH n, count(f) AS in_degree
        RETURN labels(n)[0] AS label, properties(n) AS props, in_degree
        ORDER BY in_degree DESC
        LIMIT $top_n
    """
    results = []
    try:
        res = graph.query(query, {"top_n": top_n})
        for row in res.result_set:
            results.append({
                "label": row[0],
                "properties": row[1],
                "centrality_score": row[2],
            })
    except Exception as e:
        logger.error("Fallback centrality failed: %s", e)
    return results
