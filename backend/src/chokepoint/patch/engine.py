"""Patch engine — generates YAML fixes using ruamel.yaml (comment-preserving).

Fix strategies:
1. SHA pin: replace tag ref with full commit SHA
2. env-var indirection: move ${{ github.event.* }} from run: to env:
3. least-privilege permissions: restrict permissions to minimum needed
4. trigger change: switch pull_request_target → pull_request where safe
"""

from __future__ import annotations

import logging
import re
import copy
from dataclasses import dataclass, field
from io import StringIO
from typing import Any, Dict, List, Optional

from ruamel.yaml import YAML

logger = logging.getLogger(__name__)

yaml = YAML()
yaml.preserve_quotes = True
yaml.width = 1000  # avoid wrapping


@dataclass
class Patch:
    """A single fix patch."""
    file_path: str
    fix_kind: str         # pin, env_var, permission, trigger
    description: str
    original: str         # original YAML content
    patched: str          # patched YAML content
    diff_lines: List[str] = field(default_factory=list)


def generate_patches(
    workflow_path: str,
    workflow_content: str,
    fix_actions: list,
) -> List[Patch]:
    """Generate YAML patches for a set of fix actions.

    Args:
        workflow_path: path to the workflow file
        workflow_content: original YAML content
        fix_actions: list of FixAction objects from min_fix_set

    Returns:
        List of Patch objects
    """
    patches = []

    for fix in fix_actions:
        try:
            if fix.fix_kind == "pin":
                patch = _generate_pin_patch(workflow_path, workflow_content, fix)
            elif fix.fix_kind == "env_var":
                patch = _generate_env_var_patch(workflow_path, workflow_content, fix)
            elif fix.fix_kind == "permission":
                patch = _generate_permission_patch(workflow_path, workflow_content, fix)
            elif fix.fix_kind == "trigger":
                patch = _generate_trigger_patch(workflow_path, workflow_content, fix)
            else:
                logger.warning("Unknown fix kind: %s", fix.fix_kind)
                continue

            if patch:
                patches.append(patch)
        except Exception as e:
            logger.error("Failed to generate %s patch: %s", fix.fix_kind, e)

    return patches


def _generate_pin_patch(path: str, content: str, fix) -> Optional[Patch]:
    """Pin an action to its current SHA.

    Changes: uses: actions/checkout@v4 → uses: actions/checkout@<sha>
    """
    data = yaml.load(content)
    if not isinstance(data, dict):
        return None

    modified = False
    for job_id, job in (data.get("jobs", {}) or {}).items():
        if not isinstance(job, dict):
            continue
        for step in (job.get("steps", []) or []):
            if not isinstance(step, dict):
                continue
            uses = step.get("uses", "")
            if isinstance(uses, str) and "@" in uses:
                slug, ref = uses.rsplit("@", 1)
                # Check if this matches the fix target
                if slug in fix.source or slug in str(getattr(fix, "edge_id", "")):
                    if not re.fullmatch(r"[0-9a-fA-F]{40}", ref):
                        # Replace with a placeholder SHA (real SHA lookup in production)
                        placeholder_sha = "0" * 40  # marker for "needs real SHA"
                        step["uses"] = f"{slug}@{placeholder_sha}"
                        step.yaml_set_comment_before_after_key(
                            "uses",
                            before=f" TODO: verify SHA for {slug}@{ref}",
                        ) if hasattr(step, "yaml_set_comment_before_after_key") else None
                        modified = True

    if not modified:
        return None

    patched = _dump(data)
    return Patch(
        file_path=path,
        fix_kind="pin",
        description=f"Pin action to commit SHA in {path}",
        original=content,
        patched=patched,
        diff_lines=_simple_diff(content, patched),
    )


def _generate_env_var_patch(path: str, content: str, fix) -> Optional[Patch]:
    """Move untrusted expressions from run: to env: block.

    Before:
        run: echo "${{ github.event.issue.title }}"

    After:
        env:
          ISSUE_TITLE: ${{ github.event.issue.title }}
        run: echo "$ISSUE_TITLE"
    """
    data = yaml.load(content)
    if not isinstance(data, dict):
        return None

    modified = False
    expr_pattern = re.compile(r"\$\{\{\s*(github\.event\.\S+?)\s*\}\}")

    for job_id, job in (data.get("jobs", {}) or {}).items():
        if not isinstance(job, dict):
            continue
        for step in (job.get("steps", []) or []):
            if not isinstance(step, dict):
                continue
            run_val = step.get("run", "")
            if not isinstance(run_val, str):
                continue

            matches = expr_pattern.findall(run_val)
            if not matches:
                continue

            # Create env block
            env = step.get("env", {}) or {}
            new_run = run_val

            for expr in matches:
                # Generate env var name
                env_name = expr.split(".")[-1].upper().replace("-", "_")
                env_name = re.sub(r"[^A-Z0-9_]", "_", env_name)

                env[env_name] = f"${{{{ {expr} }}}}"
                new_run = new_run.replace(f"${{{{ {expr} }}}}", f"${env_name}")

            step["env"] = env
            step["run"] = new_run
            modified = True

    if not modified:
        return None

    patched = _dump(data)
    return Patch(
        file_path=path,
        fix_kind="env_var",
        description=f"Move untrusted expressions to env vars in {path}",
        original=content,
        patched=patched,
        diff_lines=_simple_diff(content, patched),
    )


def _generate_permission_patch(path: str, content: str, fix) -> Optional[Patch]:
    """Restrict permissions to minimum required."""
    data = yaml.load(content)
    if not isinstance(data, dict):
        return None

    # Set least-privilege at workflow level if not set
    if "permissions" not in data or data["permissions"] is None:
        data["permissions"] = {"contents": "read"}

    # Set per-job permissions
    modified = False
    for job_id, job in (data.get("jobs", {}) or {}).items():
        if not isinstance(job, dict):
            continue
        if "permissions" not in job:
            job["permissions"] = {"contents": "read"}
            modified = True

    if not modified and data.get("permissions") == {"contents": "read"}:
        return None

    patched = _dump(data)
    return Patch(
        file_path=path,
        fix_kind="permission",
        description=f"Restrict permissions to least-privilege in {path}",
        original=content,
        patched=patched,
        diff_lines=_simple_diff(content, patched),
    )


def _generate_trigger_patch(path: str, content: str, fix) -> Optional[Patch]:
    """Switch pull_request_target → pull_request where safe."""
    data = yaml.load(content)
    if not isinstance(data, dict):
        return None

    on_block = data.get("on", data.get(True, {}))
    if not isinstance(on_block, dict):
        return None

    modified = False
    if "pull_request_target" in on_block:
        on_block["pull_request"] = on_block.pop("pull_request_target")
        modified = True

    if not modified:
        return None

    patched = _dump(data)
    return Patch(
        file_path=path,
        fix_kind="trigger",
        description=f"Switch pull_request_target → pull_request in {path}",
        original=content,
        patched=patched,
        diff_lines=_simple_diff(content, patched),
    )


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _dump(data) -> str:
    """Dump YAML data to string, preserving comments."""
    stream = StringIO()
    yaml.dump(data, stream)
    return stream.getvalue()


def _simple_diff(original: str, patched: str) -> List[str]:
    """Generate a simple unified diff."""
    import difflib
    orig_lines = original.splitlines(keepends=True)
    patch_lines = patched.splitlines(keepends=True)
    diff = difflib.unified_diff(
        orig_lines, patch_lines,
        fromfile="original", tofile="patched",
        lineterm="",
    )
    return list(diff)
