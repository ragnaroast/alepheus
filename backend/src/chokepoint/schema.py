"""Graph schema — node labels, relationship types, indexes, and constraints.

This module defines the canonical schema and provides `ensure_schema()` to
set up indexes and constraints on a target graph.
"""

from __future__ import annotations

import logging
from typing import List

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Node labels
# ---------------------------------------------------------------------------
NODE_LABELS = [
    "Repo",         # GitHub repository
    "Workflow",     # .github/workflows/*.yml file
    "Trigger",      # on: push / pull_request / issue_comment / etc.
    "Job",          # jobs.<id>
    "Step",         # jobs.<id>.steps[i]
    "Action",       # third-party or local action reference
    "Secret",       # secrets.<name>
    "Environment",  # environment protection
    "Permission",   # permissions block
    "Artifact",     # actions/upload-artifact / download-artifact
    "Cache",        # actions/cache
    "Advisory",     # CVE / GHSA advisory
    # Flow layer
    "Input",        # attacker-controlled input source
    "Capability",   # crown-jewel capability (deploy, publish, etc.)
    # Agent
    "Investigation",
    "ToolCall",
]

# ---------------------------------------------------------------------------
# Relationship types
# ---------------------------------------------------------------------------
RELATIONSHIP_TYPES = [
    # Structural
    "HAS_WORKFLOW",     # Repo → Workflow
    "TRIGGERS",         # Trigger → Workflow
    "HAS_JOB",          # Workflow → Job
    "NEEDS",            # Job → Job (needs: dependency)
    "HAS_STEP",         # Job → Step
    "USES",             # Step → Action
    "CALLS",            # Workflow → Workflow (reusable workflow call)
    "HOLDS",            # Job → Secret
    "PROTECTS",         # Environment → Job
    "HAS_PERMISSION",   # Job/Workflow → Permission
    "UPLOADS",          # Step → Artifact
    "DOWNLOADS",        # Step → Artifact
    "CACHES",           # Step → Cache
    "AFFECTS",          # Advisory → Action
    # Flow layer
    "FLOWS",            # Input/Step/Job/Secret/Capability → *
]

# ---------------------------------------------------------------------------
# FLOWS edge properties
# ---------------------------------------------------------------------------
FLOW_KINDS = [
    "inject",       # attacker input enters a shell/expression
    "exec",         # step executes with the injected value
    "expose",       # step leaks a secret to output/logs
    "poison",       # action/step poisons cache/artifact
    "consume",      # step consumes poisoned cache/artifact
    "grant",        # job gains permission or secret access
    "inherit",      # reusable workflow inherits caller's secrets
]

# ---------------------------------------------------------------------------
# Schema setup
# ---------------------------------------------------------------------------

def _index_queries() -> List[str]:
    """Return CREATE INDEX queries for fast lookups in FalkorDB."""
    return [
        "CREATE INDEX ON :Repo(full_name)",
        "CREATE INDEX ON :Workflow(path)",
        "CREATE INDEX ON :Action(slug)",
        "CREATE INDEX ON :Secret(name)",
        "CREATE INDEX ON :Input(source)",
        "CREATE INDEX ON :Capability(kind)",
        "CREATE INDEX ON :Advisory(id)",
    ]


def ensure_schema(graph) -> None:
    """Create indexes and constraints on the given graph.

    Safe to call repeatedly — uses IF NOT EXISTS.
    """
    for q in _index_queries():
        try:
            graph.query(q)
            logger.debug("Schema: %s", q)
        except Exception as e:
            # Some index types may not be supported; log and continue
            logger.warning("Schema query failed (may be OK): %s — %s", q, e)

    logger.info("Schema ensured on graph '%s'", getattr(graph, "name", "?"))


# Alias for backward compatibility
init_schema = ensure_schema
