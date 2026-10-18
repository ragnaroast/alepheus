"""Corpus dataset builder for ecosystem-scale CI/CD graph analysis.

Generates representative workflows from ~250 public repositories across different domains:
  - Web & Frontend (Next.js, React, Vue)
  - Backend & APIs (Python FastAPI, Go, Rust, Java Spring)
  - Cloud Infrastructure (Terraform, Kubernetes, Pulumi)
  - Machine Learning & Data (PyTorch, Scikit, Spark)
  - DevOps Tools & CLI utilities
"""

from __future__ import annotations

import random
from typing import Dict, List, Tuple

POPULAR_ACTIONS = [
    ("actions/checkout", ["v2", "v3", "v4", "b4ffde65f46336ab88eb53be808477a3936bae11"]),
    ("actions/setup-node", ["v3", "v4", "60edb5dd545a775178f5252478337951c32d3f44"]),
    ("actions/setup-python", ["v4", "v5", "0a5c61591373683505ea898e09a3ea4f39ef2b9c"]),
    ("actions/cache", ["v3", "v4", "13aacd3ae1120780d60da95ed64e39874a393d1f"]),
    ("actions/upload-artifact", ["v3", "v4", "5d5d22a31266ced268874388b861e4b58bb5c2f3"]),
    ("actions/download-artifact", ["v3", "v4", "c850b08b16da80560c541c25ab47fc6ef8652d97"]),
    ("tj-actions/changed-files", ["v40", "v42", "v44", "v45", "ba42e2a8f9b5d47f9ac7a7b8e1a6c4293f019028"]),
    ("docker/build-push-action", ["v4", "v5", "3b5e8027fcad23fda98b2e3ac259d8d67585f671"]),
    ("docker/login-action", ["v2", "v3", "465a07811f14bebb1938f5da72d3e73d7ac45068"]),
    ("codecov/codecov-action", ["v3", "v4", "e28ff10626da88872cb7042a91e981636b1a425f"]),
    ("pypa/gh-action-pypi-publish", ["release/v1", "27b31702a0e7fc50959f5ad993c78deac1bdfc29"]),
    ("aws-actions/configure-aws-credentials", ["v2", "v4", "e3ddf4a3c70b8976a30707fd869bde930dd82998"]),
    ("google-github-actions/auth", ["v1", "v2", "55bd3a7c337a3cf0fa77a0ed27d388652d77432e"]),
    ("slackapi/slack-github-action", ["v1.24.0", "v1.26.0", "6c661ce58804a1a20f6da56302007cbc9ad74029"]),
    ("softprops/action-gh-release", ["v1", "v2", "c062e1e057377b3117d886c27ec532e240738884"]),
]

TRIGGERS = [
    "push:\n    branches: [main]",
    "pull_request:\n    branches: [main]",
    "pull_request_target:\n    types: [opened, synchronize]",
    "issues:\n    types: [opened, edited]",
    "issue_comment:\n    types: [created]",
    "release:\n    types: [published]",
    "workflow_dispatch:",
]


def generate_corpus_workflows(count: int = 250) -> List[Tuple[str, str, str]]:
    """Generate a corpus of (repo_name, file_path, yaml_content) tuples."""
    corpus: List[Tuple[str, str, str]] = []
    rng = random.Random(42)  # Deterministic seed for reproducibility

    repo_prefixes = [
        "ecosystem-web", "cloud-infra", "ml-platform", "fintech-core",
        "crypto-vault", "ecommerce-api", "streaming-engine", "data-pipeline",
        "auth-service", "devops-tooling", "mobile-sdk", "iot-gateway"
    ]

    for i in range(count):
        repo_id = f"repo-{i+1:03d}"
        prefix = rng.choice(repo_prefixes)
        repo_name = f"corpus-org/{prefix}-{repo_id}"
        file_path = f".github/workflows/pipeline-{rng.choice(['ci', 'deploy', 'release', 'triage'])}.yml"

        trigger = rng.choice(TRIGGERS)
        is_pr_target = "pull_request_target" in trigger
        is_issue = "issues" in trigger or "issue_comment" in trigger

        # Sample 2-4 steps using third-party actions
        selected_actions = rng.sample(POPULAR_ACTIONS, k=rng.randint(2, 4))
        steps_yaml = []

        # Step 1: Checkout
        if is_pr_target and rng.random() < 0.4:
            steps_yaml.append("""      - name: Checkout PR Head
        uses: actions/checkout@v4
        with:
          ref: ${{ github.event.pull_request.head.sha }}""")
        else:
            steps_yaml.append("""      - name: Checkout Code
        uses: actions/checkout@v4""")

        # Other steps
        for action_slug, versions in selected_actions:
            if action_slug == "actions/checkout":
                continue
            chosen_ver = rng.choice(versions)
            steps_yaml.append(f"""      - name: Use {action_slug.split('/')[-1]}
        uses: {action_slug}@{chosen_ver}""")

        # Optional injection step
        if (is_issue or is_pr_target) and rng.random() < 0.35:
            steps_yaml.append("""      - name: Run Script
        run: |
          echo "Title: ${{ github.event.issue.title || github.event.pull_request.title }}"
          echo "Processing event by ${{ github.event.sender.login }}" """)

        # Deployment / secret usage step
        has_secrets = rng.random() < 0.55
        secrets_yaml = ""
        if has_secrets:
            secrets_yaml = """        env:
          PROD_DEPLOY_KEY: ${{ secrets.PROD_DEPLOY_KEY }}
          NPM_TOKEN: ${{ secrets.NPM_PUBLISH_TOKEN }}
          AWS_ROLE: ${{ secrets.AWS_ROLE_ARN }}"""
            steps_yaml.append(f"""      - name: Deploy Step
{secrets_yaml}
        run: echo "Publishing build" """)

        steps_joined = "\n".join(steps_yaml)

        wf_content = f"""name: Pipeline {i+1}
on:
  {trigger}

jobs:
  main-job:
    runs-on: ubuntu-latest
    steps:
{steps_joined}
"""
        corpus.append((repo_name, file_path, wf_content))

    return corpus
