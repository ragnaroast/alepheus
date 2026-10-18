"""Search tools — full-text advisory search and guarded Cypher."""

from __future__ import annotations

import logging
import re
from typing import Any, Dict, List

logger = logging.getLogger(__name__)


def search_advisories(
    graph,
    query: str,
    limit: int = 20,
) -> List[Dict[str, Any]]:
    """Search advisories by keyword.

    Args:
        graph: FalkorDB graph instance
        query: search text
        limit: max results

    Returns:
        List of advisory dicts
    """
    # Use CONTAINS for simple text search (full-text index is optional)
    cypher = """
        MATCH (a:Advisory)
        WHERE a.title CONTAINS $query OR a.description CONTAINS $query OR a.id CONTAINS $query
        RETURN a.id AS id, a.title AS title, a.severity AS severity,
               a.description AS description
        LIMIT $limit
    """
    try:
        res = graph.query(cypher, {"query": query, "limit": limit})
        return [
            {"id": r[0], "title": r[1], "severity": r[2], "description": r[3]}
            for r in res.result_set
        ]
    except Exception as e:
        logger.error("Advisory search failed: %s", e)
        return []
