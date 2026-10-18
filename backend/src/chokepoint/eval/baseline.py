"""Per-file flat baseline detector simulating traditional CI/CD linters (zizmor / poutine / actionlint).

Traditional linters inspect each AST node or line in isolation, producing flat finding lists
without cross-job, cross-file, or reachability-to-crown-jewels context.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import List, Dict, Any
from ruamel.yaml import YAML

yaml = YAML(typ="safe")


@dataclass
class FlatFinding:
    """A single finding emitted by a per-file flat scanner."""
    file_path: str
    rule_id: str
    severity: str
    line: int
    message: str
    fix_suggestion: str


class PerFileBaselineScanner:
    """Simulates a flat rule-based linter without graph awareness."""

    def scan_workflow(self, file_path: str, content: str) -> List[FlatFinding]:
        findings: List[FlatFinding] = []
        lines = content.splitlines()

        try:
            data = yaml.load(content)
        except Exception:
            return findings

        if not isinstance(data, dict):
            return findings

        # Rule 1: Check pull_request_target trigger
        on_val = data.get("on", data.get(True, {}))
        if isinstance(on_val, dict) and "pull_request_target" in on_val:
            findings.append(FlatFinding(
                file_path=file_path,
                rule_id="PR_TARGET_TRIGGER",
                severity="HIGH",
                line=self._find_line(lines, "pull_request_target"),
                message="Workflow triggers on pull_request_target which grants repo write tokens to PRs",
                fix_suggestion="Change trigger to pull_request",
            ))

        # Rule 2: Check wildcard or default permissions
        perms = data.get("permissions")
        if perms == "write-all" or perms is None:
            findings.append(FlatFinding(
                file_path=file_path,
                rule_id="UNRESTRICTED_PERMISSIONS",
                severity="MEDIUM",
                line=self._find_line(lines, "permissions") or 1,
                message="Workflow does not restrict GITHUB_TOKEN permissions",
                fix_suggestion="Explicitly set read-only permissions: permissions: contents: read",
            ))

        # Inspect jobs and steps
        jobs = data.get("jobs", {}) or {}
        if isinstance(jobs, dict):
            for job_id, job in jobs.items():
                if not isinstance(job, dict):
                    continue

                steps = job.get("steps", []) or []
                for step in steps:
                    if not isinstance(step, dict):
                        continue

                    # Rule 3: Unpinned third-party actions
                    uses = step.get("uses", "")
                    if isinstance(uses, str) and "@" in uses:
                        slug, ref = uses.rsplit("@", 1)
                        if not re.fullmatch(r"[0-9a-fA-F]{40}", ref):
                            findings.append(FlatFinding(
                                file_path=file_path,
                                rule_id="UNPINNED_ACTION",
                                severity="MEDIUM",
                                line=self._find_line(lines, uses),
                                message=f"Action '{uses}' is pinned to a mutable tag/branch instead of full commit SHA",
                                fix_suggestion="Pin action to full 40-character commit SHA",
                            ))

                    # Rule 4: Untrusted expression in inline run script
                    run_val = step.get("run", "")
                    if isinstance(run_val, str):
                        exprs = re.findall(r"\$\{\{\s*(github\.event\.\S+?)\s*\}\}", run_val)
                        for expr in exprs:
                            findings.append(FlatFinding(
                                file_path=file_path,
                                rule_id="SCRIPT_INJECTION",
                                severity="HIGH",
                                line=self._find_line(lines, expr),
                                message=f"Untrusted expression '{expr}' directly interpolated into shell command",
                                fix_suggestion="Pass expression via an intermediate environment variable",
                            ))

                    # Rule 5: Checkout of untrusted head branch
                    with_block = step.get("with", {}) or {}
                    if isinstance(with_block, dict):
                        ref_val = str(with_block.get("ref", ""))
                        if "pull_request.head" in ref_val:
                            findings.append(FlatFinding(
                                file_path=file_path,
                                rule_id="DANGEROUS_CHECKOUT",
                                severity="HIGH",
                                line=self._find_line(lines, ref_val),
                                message="Checking out untrusted pull request head code inside privileged context",
                                fix_suggestion="Do not checkout PR head in pull_request_target workflows",
                            ))

        return findings

    def _find_line(self, lines: List[str], target: str) -> int:
        for idx, line in enumerate(lines, start=1):
            if target in line:
                return idx
        return 1
