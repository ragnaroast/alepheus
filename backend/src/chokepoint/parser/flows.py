"""FLOWS edge derivation.

Takes parsed workflows and derives the flow-layer edges that represent
how attacker-controlled data propagates through the CI/CD pipeline.

Each FLOWS edge has:
    kind: inject | exec | expose | poison | consume | grant | inherit
    difficulty: int (0=trivial, 10=hard)
    fix_cost: int (used as maxFlow capacity — huge for unfixable edges)
    fixable: bool
    fix_kind: str | None
    evidence_file: str
    evidence_line: int
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple

from chokepoint.parser.workflow import (
    ParsedWorkflow,
    ParsedJob,
    ParsedStep,
    ParsedTrigger,
    ATTACKER_TRIGGERS,
)

logger = logging.getLogger(__name__)

# Cost constants
UNFIXABLE_COST = 999_999  # edges the user can't fix (attacker-side)
PIN_COST = 1              # pin an action to a SHA
ENV_COST = 2              # move expression to env var
PERMISSION_COST = 2       # restrict permissions
TRIGGER_COST = 3          # change trigger type


@dataclass
class FlowEdge:
    """A derived FLOWS edge for graph ingestion."""
    source_type: str       # node label (Input, Step, Job, Secret, etc.)
    source_id: str         # unique node key
    target_type: str       # node label
    target_id: str         # unique node key
    kind: str              # inject, exec, expose, poison, consume, grant, inherit
    difficulty: int        # exploit difficulty (0–10)
    fix_cost: int          # capacity for maxFlow
    fixable: bool
    fix_kind: Optional[str] = None  # pin, env_var, permission, trigger
    evidence_file: str = ""
    evidence_line: int = 0
    properties: Dict[str, str] = field(default_factory=dict)

    @property
    def source(self) -> str:
        return self.source_id

    @property
    def target(self) -> str:
        return self.target_id


def derive_flows(
    workflow: ParsedWorkflow,
    repo_full_name: str = "local/repo",
) -> List[FlowEdge]:
    """Derive all FLOWS edges from a parsed workflow.

    Returns a list of FlowEdge objects ready for graph ingestion.
    """
    edges: List[FlowEdge] = []
    wf_id = f"{repo_full_name}:{workflow.path}"

    # --- 1. Attacker-controlled trigger → Input nodes ---
    attacker_triggers = [t for t in workflow.triggers if t.attacker_controlled]

    for job in workflow.jobs:
        job_id = f"{wf_id}:{job.id}"

        # --- 2. Untrusted input injection in steps ---
        for step in job.steps:
            step_id = f"{job_id}:step:{step.index}"

            if step.injects_untrusted and step.run:
                for expr in step.untrusted_expressions:
                    # Input → Step (inject)
                    input_id = f"input:{expr}"
                    edges.append(FlowEdge(
                        source_type="Input",
                        source_id=input_id,
                        target_type="Step",
                        target_id=step_id,
                        kind="inject",
                        difficulty=1 if attacker_triggers else 5,
                        fix_cost=ENV_COST,
                        fixable=True,
                        fix_kind="env_var",
                        evidence_file=workflow.path,
                        evidence_line=step.line_start,
                        properties={"expression": expr},
                    ))

                    # Step executes with injected value (exec)
                    edges.append(FlowEdge(
                        source_type="Step",
                        source_id=step_id,
                        target_type="Job",
                        target_id=job_id,
                        kind="exec",
                        difficulty=0,
                        fix_cost=UNFIXABLE_COST,  # step running is inherent
                        fixable=False,
                        evidence_file=workflow.path,
                        evidence_line=step.line_start,
                    ))

            # --- 3. Third-party action usage (unpinned = supply chain risk) ---
            if step.uses and not step.uses.pinned and not step.uses.is_local:
                edges.append(FlowEdge(
                    source_type="Action",
                    source_id=f"action:{step.uses.slug}@{step.uses.ref}",
                    target_type="Step",
                    target_id=step_id,
                    kind="poison",
                    difficulty=3,  # compromising an action tag
                    fix_cost=PIN_COST,
                    fixable=True,
                    fix_kind="pin",
                    evidence_file=workflow.path,
                    evidence_line=step.line_start,
                    properties={"action": step.uses.slug, "ref": step.uses.ref},
                ))

        # --- 4. Secret access → Capability ---
        for secret_name in job.secrets:
            secret_id = f"secret:{repo_full_name}:{secret_name}"

            # Job holds secret
            edges.append(FlowEdge(
                source_type="Job",
                source_id=job_id,
                target_type="Secret",
                target_id=secret_id,
                kind="grant",
                difficulty=0,
                fix_cost=UNFIXABLE_COST,
                fixable=False,
                evidence_file=workflow.path,
            ))

            # Crown-jewel heuristic: deploy/publish/cloud secrets
            if _is_crown_jewel_secret(secret_name):
                cap_id = f"capability:{repo_full_name}:{secret_name}"
                edges.append(FlowEdge(
                    source_type="Secret",
                    source_id=secret_id,
                    target_type="Capability",
                    target_id=cap_id,
                    kind="grant",
                    difficulty=0,
                    fix_cost=UNFIXABLE_COST,
                    fixable=False,
                    evidence_file=workflow.path,
                    properties={"crown_jewel": "true"},
                ))

        # --- 5. Overly permissive permissions ---
        perms = job.permissions or workflow.permissions
        if isinstance(perms, dict):
            for scope, level in perms.items():
                if level == "write" and scope in ("contents", "packages", "deployments", "id-token"):
                    cap_id = f"capability:{repo_full_name}:perm:{scope}"
                    edges.append(FlowEdge(
                        source_type="Job",
                        source_id=job_id,
                        target_type="Capability",
                        target_id=cap_id,
                        kind="grant",
                        difficulty=0,
                        fix_cost=PERMISSION_COST,
                        fixable=True,
                        fix_kind="permission",
                        evidence_file=workflow.path,
                        properties={"permission": scope, "level": level},
                    ))

    return edges


# ---------------------------------------------------------------------------
# Crown-jewel heuristics
# ---------------------------------------------------------------------------

_CROWN_PATTERNS = [
    "npm_token", "pypi_token", "npm_auth", "pypi_password",
    "deploy", "publish", "release", "aws_access_key", "aws_secret",
    "gcp_", "azure_", "docker_password", "docker_token",
    "ghcr_token", "signing_key", "ssh_key", "kube", "k8s",
]


def _is_crown_jewel_secret(name: str) -> bool:
    """Heuristic: is this secret a crown jewel (deploy, publish, cloud)?"""
    lower = name.lower()
    return any(p in lower for p in _CROWN_PATTERNS)
