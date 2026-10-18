"""Guarded read-only Cypher execution.

Allows expert users to run arbitrary Cypher queries, but only read-only ones.
"""

from __future__ import annotations

import logging
import re
from typing import Any, Dict, List

logger = logging.getLogger(__name__)

# Patterns that indicate write operations
WRITE_PATTERNS = re.compile(
    r"\b(CREATE|MERGE|SET|DELETE|REMOVE|DETACH|DROP|CALL\s+db\.(idx|constraint))\b",
    re.IGNORECASE,
)


def run_cypher_ro(
    graph,
    query: str,
    params: Dict[str, Any] = None,
    limit: int = 100,
) -> Dict[str, Any]:
    """Execute a read-only Cypher query.

    Guards against write operations by pattern matching.

    Args:
        graph: FalkorDB graph instance
        query: Cypher query string
        params: optional parameters
        limit: max rows to return

    Returns:
        Dict with columns, rows, and metadata
    """
    # Guard: reject write queries
    if WRITE_PATTERNS.search(query):
        return {
            "error": "Write operations are not allowed. Use read-only queries only.",
            "blocked_query": query,
        }

    # Append LIMIT if not present
    if "LIMIT" not in query.upper():
        query = f"{query} LIMIT {limit}"

    try:
        result = graph.query(query, params or {})
        rows = []
        for row in result.result_set:
            rows.append([_serialize_value(v) for v in row])

        return {
            "columns": result.header if hasattr(result, "header") else [],
            "rows": rows,
            "row_count": len(rows),
            "query": query,
        }
    except Exception as e:
        logger.error("Cypher query failed: %s", e)
        return {"error": str(e), "query": query}


def _serialize_value(val: Any) -> Any:
    """Convert graph objects to JSON-safe values."""
    if val is None:
        return None
    if isinstance(val, (str, int, float, bool)):
        return val
    if isinstance(val, list):
        return [_serialize_value(v) for v in val]
    if isinstance(val, dict):
        return {k: _serialize_value(v) for k, v in val.items()}
    # Graph nodes/edges — extract properties
    if hasattr(val, "properties"):
        return {
            "labels": getattr(val, "labels", []),
            "properties": val.properties,
        }
    return str(val)
