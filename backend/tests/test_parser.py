"""Unit tests for GitHub Actions YAML parser."""

import pytest
from chokepoint.parser.workflow import parse_workflow


def test_parse_vulnerable_issue_workflow(vulnerable_issue_workflow_yaml):
    pw = parse_workflow(".github/workflows/issue.yml", vulnerable_issue_workflow_yaml)
    assert pw.name == "Issue Handler"
    assert len(pw.jobs) == 1
    job = pw.jobs[0]
    assert job.id == "comment-job"
    assert len(job.steps) == 3
    assert "DEPLOY_KEY" in job.secrets_referenced
    assert len(pw.untrusted_inputs) >= 1
    assert any("issue.title" in u.expression for u in pw.untrusted_inputs)


def test_parse_unpinned_action(tj_actions_workflow_yaml):
    pw = parse_workflow(".github/workflows/tj.yml", tj_actions_workflow_yaml)
    job = pw.jobs[0]
    actions = [s.action_ref for s in job.steps if s.action_ref]
    assert len(actions) == 2
    assert actions[0].slug == "actions/checkout"
    assert not actions[0].pinned
    assert actions[1].slug == "tj-actions/changed-files"
    assert actions[1].ref == "v44"
    assert not actions[1].pinned


def test_parse_safe_workflow_pinned_sha(safe_workflow_yaml):
    pw = parse_workflow(".github/workflows/safe.yml", safe_workflow_yaml)
    job = pw.jobs[0]
    actions = [s.action_ref for s in job.steps if s.action_ref]
    assert len(actions) == 1
    assert actions[0].pinned is True
    assert actions[0].ref == "b4ffde65f46336ab88eb53be808477a3936bae11"
