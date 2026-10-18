"""Unit tests for FLOWS edge derivation."""

import pytest
from chokepoint.parser.workflow import parse_workflow
from chokepoint.parser.flows import derive_flows


def test_derive_flows_injection(vulnerable_issue_workflow_yaml):
    pw = parse_workflow(".github/workflows/issue.yml", vulnerable_issue_workflow_yaml)
    flows = derive_flows(pw)

    # Check for script injection flow edge
    injection_flows = [f for f in flows if f.kind == "inject"]
    assert len(injection_flows) >= 1
    flow = injection_flows[0]
    assert flow.fixable is True
    assert flow.fix_kind == "env_var"
    assert flow.fix_cost in (1, 2)


def test_derive_flows_compromised_action(tj_actions_workflow_yaml):
    pw = parse_workflow(".github/workflows/tj.yml", tj_actions_workflow_yaml)
    flows = derive_flows(pw)

    # Should detect unpinned third party action flow
    expose_flows = [f for f in flows if f.kind == "expose" or f.fix_kind == "pin"]
    assert len(expose_flows) >= 1
    assert any(f.fix_kind == "pin" for f in expose_flows)
