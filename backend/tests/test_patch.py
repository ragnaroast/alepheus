"""Unit tests for comment-preserving ruamel.yaml patch engine."""

import pytest
from chokepoint.parser.workflow import parse_workflow
from chokepoint.patch.engine import generate_patches
from chokepoint.tools.cuts import FixAction


def test_generate_env_var_patch(vulnerable_issue_workflow_yaml):
    fix = FixAction(
        edge_id="e1",
        fix_kind="env_var",
        source="input:issue.title",
        target="step:Echo Title",
        cost=1,
        file_path=".github/workflows/issue.yml",
        line=10,
        description="Move untrusted expression to env",
    )
    patches = generate_patches(
        ".github/workflows/issue.yml",
        vulnerable_issue_workflow_yaml,
        [fix],
    )
    assert len(patches) == 1
    p = patches[0]
    assert p.fix_kind == "env_var"
    # Should replace ${{ github.event.issue.title }} with $TITLE and set env block
    assert "env:" in p.patched
    assert "TITLE:" in p.patched
    assert "$TITLE" in p.patched


def test_generate_pin_patch(tj_actions_workflow_yaml):
    fix = FixAction(
        edge_id="e2",
        fix_kind="pin",
        source="action:tj-actions/changed-files",
        target="step:check",
        cost=1,
        file_path=".github/workflows/tj.yml",
        line=10,
        description="Pin tj-actions",
    )
    patches = generate_patches(
        ".github/workflows/tj.yml",
        tj_actions_workflow_yaml,
        [fix],
    )
    assert len(patches) == 1
    p = patches[0]
    assert p.fix_kind == "pin"
    assert "0000000000000000000000000000000000000000" in p.patched
