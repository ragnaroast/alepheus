"""GitHub Actions workflow YAML parser.

Parses .github/workflows/*.yml files into structured data for graph ingestion.
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Set

from ruamel.yaml import YAML

logger = logging.getLogger(__name__)
yaml = YAML()
yaml.preserve_quotes = True


# ---------------------------------------------------------------------------
# Data classes for parsed workflow structure
# ---------------------------------------------------------------------------

@dataclass
class ParsedTrigger:
    event: str                     # push, pull_request, issue_comment, etc.
    attacker_controlled: bool      # True if fork-PR / issue / comment
    branches: List[str] = field(default_factory=list)
    types: List[str] = field(default_factory=list)


@dataclass
class ParsedAction:
    slug: str                      # e.g. "actions/checkout"
    ref: str                       # e.g. "v4", "main", sha
    pinned: bool                   # True if ref is a full SHA
    is_local: bool = False         # True if uses: ./path
    is_reusable_workflow: bool = False  # True if uses: org/repo/.github/workflows/x.yml@ref


@dataclass
class UntrustedInputRef:
    expression: str
    step_name: str = ""
    job_id: str = ""
    line: int = 1


@dataclass
class ParsedStep:
    index: int
    id: Optional[str]
    name: Optional[str]
    uses: Optional[ParsedAction]
    run: Optional[str]
    env: Dict[str, str] = field(default_factory=dict)
    with_inputs: Dict[str, str] = field(default_factory=dict)
    # Analysis results
    injects_untrusted: bool = False
    untrusted_expressions: List[str] = field(default_factory=list)
    line_start: int = 0
    line_end: int = 0

    @property
    def action_ref(self) -> Optional[ParsedAction]:
        return self.uses


@dataclass
class ParsedJob:
    id: str
    name: Optional[str]
    needs: List[str] = field(default_factory=list)
    runs_on: str = ""
    permissions: Dict[str, str] = field(default_factory=dict)
    environment: Optional[str] = None
    secrets: List[str] = field(default_factory=list)
    steps: List[ParsedStep] = field(default_factory=list)
    outputs: Dict[str, str] = field(default_factory=dict)
    if_condition: Optional[str] = None

    @property
    def secrets_referenced(self) -> List[str]:
        return self.secrets


@dataclass
class ParsedWorkflow:
    path: str                      # relative path from repo root
    name: Optional[str]
    triggers: List[ParsedTrigger] = field(default_factory=list)
    permissions: Dict[str, str] = field(default_factory=dict)
    env: Dict[str, str] = field(default_factory=dict)
    jobs: List[ParsedJob] = field(default_factory=list)
    calls_reusable: List[str] = field(default_factory=list)
    raw_yaml: Optional[str] = None

    @property
    def untrusted_inputs(self) -> List[UntrustedInputRef]:
        items = []
        for j in self.jobs:
            for s in j.steps:
                for expr in s.untrusted_expressions:
                    items.append(UntrustedInputRef(
                        expression=expr,
                        step_name=s.name or "",
                        job_id=j.id,
                        line=s.line_start,
                    ))
        return items


# ---------------------------------------------------------------------------
# Untrusted input detection
# ---------------------------------------------------------------------------

# GitHub expression contexts that are attacker-controlled
UNTRUSTED_CONTEXTS = [
    r"github\.event\.issue\.title",
    r"github\.event\.issue\.body",
    r"github\.event\.pull_request\.title",
    r"github\.event\.pull_request\.body",
    r"github\.event\.pull_request\.head\.ref",
    r"github\.event\.pull_request\.head\.label",
    r"github\.event\.comment\.body",
    r"github\.event\.review\.body",
    r"github\.event\.review_comment\.body",
    r"github\.event\.discussion\.title",
    r"github\.event\.discussion\.body",
    r"github\.event\.pages\.\*\.page_name",
    r"github\.event\.commits\.\*\.message",
    r"github\.event\.commits\.\*\.author\.email",
    r"github\.event\.commits\.\*\.author\.name",
    r"github\.event\.head_commit\.message",
    r"github\.event\.head_commit\.author\.email",
    r"github\.event\.head_commit\.author\.name",
    r"github\.head_ref",
    r"github\.event\.workflow_run\.head_branch",
    r"github\.event\.inputs\.\w+",
]

# Regex expression pattern: ${{ ... }}
EXPRESSION_PATTERN = re.compile(r"\$\{\{\s*(.+?)\s*\}\}")

# Triggers that allow attacker-controlled events
ATTACKER_TRIGGERS = {
    "pull_request_target",
    "issue_comment",
    "issues",
    "discussion",
    "discussion_comment",
    "fork",
    "workflow_run",
}


def _find_untrusted_expressions(text: str) -> List[str]:
    """Find all ${{ }} expressions referencing attacker-controlled contexts."""
    if not text:
        return []
    found = []
    for match in EXPRESSION_PATTERN.finditer(text):
        expr = match.group(1).strip()
        for pattern in UNTRUSTED_CONTEXTS:
            if re.search(pattern, expr, re.IGNORECASE):
                found.append(expr)
                break
    return found


def _is_sha_pinned(ref: str) -> bool:
    """Check if an action ref is a full commit SHA (40 hex chars)."""
    return bool(ref and re.fullmatch(r"[0-9a-fA-F]{40}", ref))


def _parse_uses(uses_str: str) -> Optional[ParsedAction]:
    """Parse a `uses:` value into a ParsedAction."""
    if not uses_str:
        return None

    # Local action: ./path/to/action
    if uses_str.startswith("./"):
        return ParsedAction(slug=uses_str, ref="local", pinned=True, is_local=True)

    # Docker action: docker://...
    if uses_str.startswith("docker://"):
        return ParsedAction(slug=uses_str, ref="docker", pinned=False)

    # Standard: owner/repo@ref or owner/repo/path@ref
    if "@" in uses_str:
        parts = uses_str.rsplit("@", 1)
        slug = parts[0]
        ref = parts[1] if len(parts) > 1 else "unknown"

        # Check if this is a reusable workflow call
        is_reusable = ".github/workflows/" in slug and slug.endswith(".yml")

        return ParsedAction(
            slug=slug,
            ref=ref,
            pinned=_is_sha_pinned(ref),
            is_reusable_workflow=is_reusable,
        )

    return ParsedAction(slug=uses_str, ref="unknown", pinned=False)


# ---------------------------------------------------------------------------
# Main parser
# ---------------------------------------------------------------------------

def parse_workflow(path: str, content: str) -> ParsedWorkflow:
    """Parse a single GitHub Actions workflow YAML string.

    Args:
        path: Relative path like `.github/workflows/ci.yml`
        content: Raw YAML content

    Returns:
        ParsedWorkflow with all structure populated
    """
    data = yaml.load(content)
    if not isinstance(data, dict):
        logger.warning("Workflow %s is not a valid YAML dict", path)
        return ParsedWorkflow(path=path, name=None, raw_yaml=content)

    wf = ParsedWorkflow(
        path=path,
        name=data.get("name"),
        raw_yaml=content,
    )

    # --- Triggers ---
    on_block = data.get("on", data.get(True, {}))  # YAML `on:` parses as True key
    if isinstance(on_block, str):
        on_block = {on_block: {}}
    elif isinstance(on_block, list):
        on_block = {ev: {} for ev in on_block}

    if isinstance(on_block, dict):
        for event, config in on_block.items():
            event_str = str(event)
            config = config or {}
            trigger = ParsedTrigger(
                event=event_str,
                attacker_controlled=event_str in ATTACKER_TRIGGERS,
                branches=config.get("branches", []) if isinstance(config, dict) else [],
                types=config.get("types", []) if isinstance(config, dict) else [],
            )
            wf.triggers.append(trigger)

    # --- Top-level permissions ---
    wf.permissions = data.get("permissions", {}) or {}
    if isinstance(wf.permissions, str):
        wf.permissions = {wf.permissions: wf.permissions}

    # --- Top-level env ---
    wf.env = data.get("env", {}) or {}

    # --- Jobs ---
    jobs_block = data.get("jobs", {}) or {}
    for job_id, job_data in jobs_block.items():
        if not isinstance(job_data, dict):
            continue

        job = ParsedJob(
            id=str(job_id),
            name=job_data.get("name"),
            needs=_normalize_list(job_data.get("needs")),
            runs_on=str(job_data.get("runs-on", "")),
            permissions=job_data.get("permissions", {}) or {},
            environment=_extract_environment(job_data.get("environment")),
            if_condition=job_data.get("if"),
        )

        # Extract secrets from env vars and step contexts
        job.secrets = _extract_secrets(job_data)

        # --- Steps ---
        steps_data = job_data.get("steps", []) or []
        for i, step_data in enumerate(steps_data):
            if not isinstance(step_data, dict):
                continue

            step = ParsedStep(
                index=i,
                id=step_data.get("id"),
                name=step_data.get("name"),
                uses=_parse_uses(step_data.get("uses", "")),
                run=step_data.get("run"),
                env=step_data.get("env", {}) or {},
                with_inputs=step_data.get("with", {}) or {},
            )

            # Check for reusable workflow calls
            if step.uses and step.uses.is_reusable_workflow:
                wf.calls_reusable.append(step.uses.slug)

            # Detect untrusted input injection in run: blocks
            if step.run:
                step.untrusted_expressions = _find_untrusted_expressions(step.run)
                step.injects_untrusted = len(step.untrusted_expressions) > 0

            # Also check `with:` values for untrusted input
            for val in step.with_inputs.values():
                if isinstance(val, str):
                    exprs = _find_untrusted_expressions(val)
                    step.untrusted_expressions.extend(exprs)
                    if exprs:
                        step.injects_untrusted = True

            job.steps.append(step)

        # Job outputs
        job.outputs = job_data.get("outputs", {}) or {}

        wf.jobs.append(job)

    return wf


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _normalize_list(value) -> List[str]:
    """Convert `needs: foo` or `needs: [foo, bar]` to a list."""
    if value is None:
        return []
    if isinstance(value, str):
        return [value]
    if isinstance(value, list):
        return [str(v) for v in value]
    return []


def _extract_environment(env_block) -> Optional[str]:
    """Extract environment name from various formats."""
    if env_block is None:
        return None
    if isinstance(env_block, str):
        return env_block
    if isinstance(env_block, dict):
        return env_block.get("name")
    return None


def _extract_secrets(job_data: dict) -> List[str]:
    """Find all secret references in a job's env, steps, and with blocks."""
    secrets: Set[str] = set()
    text = str(job_data)
    for match in re.finditer(r"secrets\.(\w+)", text):
        secrets.add(match.group(1))
    return sorted(secrets)


def parse_workflow_file(file_path: Path) -> ParsedWorkflow:
    """Parse a workflow from a file path."""
    content = file_path.read_text(encoding="utf-8")
    rel_path = str(file_path).replace("\\", "/")
    # Try to extract relative path from .github/
    idx = rel_path.find(".github/")
    if idx >= 0:
        rel_path = rel_path[idx:]
    return parse_workflow(rel_path, content)
