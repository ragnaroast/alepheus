"""Snapshot diff tool — PR gate logic.

Compares two graph snapshots to detect new attack chains introduced by a PR.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Set

from chokepoint.tools.chains import list_chains, AttackChain

logger = logging.getLogger(__name__)


@dataclass
class DiffResult:
    """Result of comparing two snapshots."""
    base_sha: str
    head_sha: str
    new_chains: List[AttackChain] = field(default_factory=list)
    removed_chains: List[AttackChain] = field(default_factory=list)
    unchanged_chains: int = 0
    verdict: str = "pass"  # pass | fail | warn
    summary: str = ""


def diff_snapshots(
    base_graph,
    head_graph,
    base_sha: str = "base",
    head_sha: str = "head",
) -> DiffResult:
    """Compare attack chains between two graph snapshots.

    Used for PR gate: fails if the head introduces new chains.

    Args:
        base_graph: FalkorDB graph for the base branch
        head_graph: FalkorDB graph for the head branch
        base_sha: identifier for base
        head_sha: identifier for head

    Returns:
        DiffResult with new/removed chains and verdict
    """
    base_chains = list_chains(base_graph, limit=1000)
    head_chains = list_chains(head_graph, limit=1000)

    # Fingerprint chains by their input→capability path
    base_fingerprints = {_fingerprint(c) for c in base_chains}
    head_fingerprints = {_fingerprint(c) for c in head_chains}

    new_fps = head_fingerprints - base_fingerprints
    removed_fps = base_fingerprints - head_fingerprints

    result = DiffResult(
        base_sha=base_sha,
        head_sha=head_sha,
    )

    # Map fingerprints back to chains
    for c in head_chains:
        fp = _fingerprint(c)
        if fp in new_fps:
            result.new_chains.append(c)

    for c in base_chains:
        fp = _fingerprint(c)
        if fp in removed_fps:
            result.removed_chains.append(c)

    result.unchanged_chains = len(base_fingerprints & head_fingerprints)

    # Verdict
    if result.new_chains:
        result.verdict = "fail"
        result.summary = (
            f"PR introduces {len(result.new_chains)} new attack chain(s). "
            f"({len(result.removed_chains)} removed, {result.unchanged_chains} unchanged)"
        )
    elif result.removed_chains:
        result.verdict = "pass"
        result.summary = (
            f"PR removes {len(result.removed_chains)} attack chain(s). "
            f"({result.unchanged_chains} unchanged)"
        )
    else:
        result.verdict = "pass"
        result.summary = f"No change in attack chains. ({result.unchanged_chains} total)"

    logger.info("Diff: %s", result.summary)
    return result


def _fingerprint(chain: AttackChain) -> str:
    """Create a stable fingerprint for a chain (input→capability via edge kinds)."""
    hops_str = "→".join(f"{h.edge_kind}:{h.target_id}" for h in chain.hops)
    return f"{chain.input_source}→{hops_str}→{chain.capability}"
