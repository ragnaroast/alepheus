"""Unit tests for agent investigation trace and faithfulness verifier."""

import pytest
from chokepoint.agent.trace import InvestigationTrace, TraceStep
from chokepoint.agent.verifier import verify_report, VerificationResult


def test_investigation_trace():
    trace = InvestigationTrace(prompt="Analyze tj-actions exposure", model="gemini-2.5-flash")
    step1 = TraceStep(iteration=0, action="tool:list_chains", details=["Found 2 chains"], duration_ms=45)
    trace.steps.append(step1)
    trace.complete()

    assert len(trace.steps) == 1
    assert trace.steps[0].action == "tool:list_chains"
    d = trace.to_dict()
    assert d["prompt"] == "Analyze tj-actions exposure"
    assert len(d["steps"]) == 1


class MockGraph:
    def query(self, *args, **kwargs):
        class MockResult:
            result_set = [["chain-0", 1, 2, "chain-0", "mock-evidence", 1]]
        return MockResult()


def test_faithfulness_verifier():
    report_text = "Discovered vulnerability along chain-0 reaching AWS_DEPLOY_ROLE."
    mock_g = MockGraph()
    res = verify_report(report_text, mock_g)
    assert res.total_citations == 1
    assert res.verified_citations == 1
    assert res.is_faithful is True
