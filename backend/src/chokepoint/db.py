"""FalkorDB connection management — sync and async clients."""

from __future__ import annotations

import logging
from typing import Optional

from falkordb import FalkorDB as SyncFalkorDB

from chokepoint.config import get_settings

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Sync client (used for schema setup, smoke tests, and simple queries)
# ---------------------------------------------------------------------------

_sync_db: Optional[SyncFalkorDB] = None


def get_sync_db() -> SyncFalkorDB:
    """Get or create a synchronous FalkorDB client."""
    global _sync_db
    if _sync_db is None:
        s = get_settings()
        _sync_db = SyncFalkorDB(host=s.falkordb_host, port=s.falkordb_port)
        logger.info("Connected to FalkorDB at %s:%d", s.falkordb_host, s.falkordb_port)
    return _sync_db


def get_graph(name: str = "chokepoint"):
    """Select a named graph from the sync client."""
    db = get_sync_db()
    return db.select_graph(name)


def graph_key(tenant: str, sha: str) -> str:
    """Build the canonical graph key:  cp:<tenant>:<sha>"""
    return f"cp:{tenant}:{sha}"


def whatif_key(tenant: str, sha: str) -> str:
    """Build the what-if graph key:  whatif:<tenant>:<sha>"""
    return f"whatif:{tenant}:{sha}"


# ---------------------------------------------------------------------------
# Algorithm verification (P0 exit criterion)
# ---------------------------------------------------------------------------

def verify_algorithms() -> dict:
    """Call dbms.procedures() and confirm the algorithms we need exist.

    Returns a dict mapping algo name → bool(exists).
    """
    db = get_sync_db()
    g = db.select_graph("__algo_check__")  # throwaway graph

    result = g.query("CALL dbms.procedures() YIELD name RETURN name")
    all_procs = {row[0] for row in result.result_set}

    needed = [
        "algo.maxFlow",
        "algo.SPpaths",
        "algo.pageRank",        # centrality
        "algo.BFS",             # residual BFS fallback
    ]
    status = {proc: proc in all_procs for proc in needed}

    # Log findings
    for proc, exists in status.items():
        level = logging.INFO if exists else logging.WARNING
        logger.log(level, "Algorithm %-20s %s", proc, "✓" if exists else "✗ MISSING")

    return status


# ---------------------------------------------------------------------------
# Cleanup
# ---------------------------------------------------------------------------

def close():
    """Close the sync client connection."""
    global _sync_db
    if _sync_db is not None:
        try:
            _sync_db.close()
        except Exception:
            pass
        _sync_db = None
