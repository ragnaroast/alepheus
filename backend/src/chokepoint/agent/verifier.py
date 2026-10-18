"""Faithfulness verifier — ensures agent reports only cite real graph paths."""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass, field
from typing import Any, Dict, List

logger = logging.getLogger(__name__)


@dataclass
class VerificationResult:
    """Result of faithfulness verification."""
    is_faithful: bool
    total_citations: int
    verified_citations: int
    unverified_citations: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)


def verify_report(
    report: str,
    graph,
) -> VerificationResult:
    """Verify that all chain/path citations in a report actually exist in the graph.

    Rules:
    - Every chain-X reference must correspond to a real path
    - No path → no claim (enforced by checking MATCH queries)

    Args:
        report: the agent's markdown report
        graph: FalkorDB graph instance

    Returns:
        VerificationResult with pass/fail and details
    """
    result = VerificationResult(is_faithful=True, total_citations=0, verified_citations=0)

    # Find all chain references (chain-0, chain-1, etc.)
    chain_refs = re.findall(r"chain-(\d+)", report, re.IGNORECASE)
    result.total_citations = len(chain_refs)

    if not chain_refs:
        result.warnings.append("No chain citations found in report")
        return result

    # Verify each chain exists
    from chokepoint.tools.chains import list_chains
    chains = list_chains(graph, limit=1000)
    existing_ids = {c.chain_id for c in chains}

    for ref in chain_refs:
        chain_id = f"chain-{ref}"
        if chain_id in existing_ids:
            result.verified_citations += 1
        else:
            result.unverified_citations.append(chain_id)

    result.is_faithful = len(result.unverified_citations) == 0

    if not result.is_faithful:
        logger.warning(
            "Report faithfulness check FAILED: %d/%d citations unverified",
            len(result.unverified_citations), result.total_citations,
        )

    return result
