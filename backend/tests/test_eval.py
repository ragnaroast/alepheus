"""Unit tests for evaluation benchmark harness and planted fixtures."""

import pytest
from chokepoint.eval.generator import generate_eval_fixtures
from chokepoint.eval.baseline import PerFileBaselineScanner
from chokepoint.eval.harness import EvaluationHarness


def test_eval_fixtures_generation():
    fixtures = generate_eval_fixtures()
    assert len(fixtures) >= 4
    for f in fixtures:
        assert f.planted_chains_count >= 1
        assert len(f.workflow_files) >= 1
        assert f.expected_min_cut_size >= 1


def test_baseline_scanner_detects_flaws():
    scanner = PerFileBaselineScanner()
    fixtures = generate_eval_fixtures()
    f1 = fixtures[0]
    file_path, content = next(iter(f1.workflow_files.items()))
    findings = scanner.scan_workflow(file_path, content)
    assert len(findings) > 0
    rule_ids = {item.rule_id for item in findings}
    assert "PR_TARGET_TRIGGER" in rule_ids or "SCRIPT_INJECTION" in rule_ids


def test_benchmark_harness_fix_reduction():
    harness = EvaluationHarness()
    results = harness.run_benchmark()
    assert len(results) >= 4
    for r in results:
        # ChokePoint min-cut should require fewer or equal fixes compared to flat linters
        assert r.chokepoint_min_cut_fixes <= r.baseline_fixes_required
        assert r.fix_reduction_percent >= 0.0
