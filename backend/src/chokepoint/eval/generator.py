"""Synthetic workflow generator with planted attack chains.

Generates realistic GitHub Actions workflows containing planted vulnerabilities:
  1. Script Injection: ${{ github.event.issue.title }} in inline bash run: step
  2. Pwn Request: pull_request_target trigger + checkout of PR head branch + secret access
  3. Compromised Action: Unpinned third-party action (e.g. tj-actions/changed-files@v44)
  4. Poisoned Artifact: Upload artifact from untrusted PR, download in deploy workflow
  5. Cache Poison: Write-access cache manipulated by untrusted pull request
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List


@dataclass
class PlantedGroundTruth:
    """Ground truth metadata for an evaluation fixture."""
    repo_name: str
    workflow_files: Dict[str, str]  # filename -> yaml content
    planted_chains_count: int
    vulnerability_types: List[str]
    expected_min_cut_size: int
    choke_point_descriptions: List[str]


def generate_eval_fixtures() -> List[PlantedGroundTruth]:
    """Generate a suite of evaluation fixtures with known planted chains."""
    fixtures = []

    # Fixture 1: Classic Pwn Request with Inline Script Injection
    f1_yaml = """name: Issue Automation & Deploy
on:
  issues:
    types: [opened, edited]
  pull_request_target:
    types: [opened, synchronize]

jobs:
  triage:
    runs-on: ubuntu-latest
    steps:
      - name: Checkout Code
        uses: actions/checkout@v3
        with:
          ref: ${{ github.event.pull_request.head.sha }}
      - name: Parse Title
        run: |
          echo "Processing issue: ${{ github.event.issue.title }}"
          echo "Author: ${{ github.event.sender.login }}"
      - name: Run Build
        run: npm run build

  deploy:
    needs: triage
    runs-on: ubuntu-latest
    permissions:
      contents: write
      id-token: write
    steps:
      - name: Checkout
        uses: actions/checkout@v3
      - name: Publish to Prod
        env:
          AWS_ROLE_ARN: ${{ secrets.AWS_PROD_ROLE }}
          NPM_TOKEN: ${{ secrets.NPM_PUBLISH_TOKEN }}
        run: |
          npm publish
"""
    fixtures.append(PlantedGroundTruth(
        repo_name="org/issue-automation-app",
        workflow_files={".github/workflows/triage-deploy.yml": f1_yaml},
        planted_chains_count=2,
        vulnerability_types=["script_injection", "pwn_request_checkout"],
        expected_min_cut_size=1,  # Switching trigger or env var indirection
        choke_point_descriptions=[
            "Move ${{ github.event.issue.title }} to env: block or restrict PR checkout",
        ],
    ))

    # Fixture 2: tj-actions Incident Scenario (Compromised Third-Party Action)
    f2_yaml = """name: CI Matrix and Release
on:
  pull_request:

jobs:
  detect-changes:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - name: Get Changed Files
        id: changed-files
        uses: tj-actions/changed-files@v44
        with:
          files: "**/*.py"
      - name: Report
        run: |
          echo "Files changed: ${{ steps.changed-files.outputs.all_changed_files }}"

  release:
    needs: detect-changes
    runs-on: ubuntu-latest
    environment: production
    steps:
      - uses: actions/checkout@v4
      - name: Release Artifacts
        env:
          PROD_DEPLOY_KEY: ${{ secrets.PROD_DEPLOY_KEY }}
          DOCKER_PASSWORD: ${{ secrets.DOCKER_PASSWORD }}
        run: ./deploy.sh
"""
    fixtures.append(PlantedGroundTruth(
        repo_name="org/tj-actions-pipeline",
        workflow_files={".github/workflows/ci-release.yml": f2_yaml},
        planted_chains_count=1,
        vulnerability_types=["compromised_unpinned_action"],
        expected_min_cut_size=1,  # SHA pin of tj-actions
        choke_point_descriptions=[
            "Pin tj-actions/changed-files@v44 to immutable full commit SHA",
        ],
    ))

    # Fixture 3: Cross-Job Artifact Poisoning
    f3_yaml = """name: Cross Job Poison
on:
  pull_request_target:

jobs:
  build-untrusted:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
        with:
          ref: ${{ github.event.pull_request.head.sha }}
      - name: Build
        run: |
          make build-dist
      - name: Upload Dist
        uses: actions/upload-artifact@v3
        with:
          name: dist-package
          path: dist/

  prod-publish:
    needs: build-untrusted
    runs-on: ubuntu-latest
    steps:
      - uses: actions/download-artifact@v3
        with:
          name: dist-package
          path: dist/
      - name: Deploy to Cluster
        env:
          KUBE_CONFIG_DATA: ${{ secrets.KUBE_CONFIG_DATA }}
        run: |
          kubectl apply -f dist/
"""
    fixtures.append(PlantedGroundTruth(
        repo_name="org/artifact-poison-app",
        workflow_files={".github/workflows/artifact-pipeline.yml": f3_yaml},
        planted_chains_count=1,
        vulnerability_types=["artifact_poisoning", "pwn_request_checkout"],
        expected_min_cut_size=1,  # Change trigger to pull_request or isolate checkout
        choke_point_descriptions=[
            "Switch pull_request_target to pull_request to isolate untrusted build from secrets",
        ],
    ))

    # Fixture 4: Complex Multi-Vector Corporate Monorepo Pipeline
    f4_yaml = """name: Corporate Monorepo CI
on:
  issue_comment:
    types: [created]
  pull_request_target:
    types: [opened]

permissions: write-all

jobs:
  comment-command:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2
      - name: Run Slash Command
        run: |
          COMMAND="${{ github.event.comment.body }}"
          eval "run_$COMMAND"

  pr-build:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2
        with:
          ref: ${{ github.event.pull_request.head.sha }}
      - uses: unpinned/build-helper@v1
      - name: Run Test
        run: make test

  release-gate:
    needs: [comment-command, pr-build]
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2
      - name: Publish Cloud Infrastructure
        env:
          AWS_ACCESS_KEY_ID: ${{ secrets.AWS_ACCESS_KEY_ID }}
          AWS_SECRET_ACCESS_KEY: ${{ secrets.AWS_SECRET_ACCESS_KEY }}
          TERRAFORM_TOKEN: ${{ secrets.TERRAFORM_TOKEN }}
        run: terraform apply -auto-approve
"""
    fixtures.append(PlantedGroundTruth(
        repo_name="org/monorepo-enterprise",
        workflow_files={".github/workflows/monorepo.yml": f4_yaml},
        planted_chains_count=3,
        vulnerability_types=["comment_eval_injection", "unpinned_action", "pwn_request_checkout", "wildcard_permissions"],
        expected_min_cut_size=2,  # Fix permissions + comment env var
        choke_point_descriptions=[
            "Restrict top-level write-all permissions and quote/env-var comment body",
        ],
    ))

    return fixtures
