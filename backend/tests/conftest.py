"""Pytest configuration and shared test fixtures."""

import pytest


@pytest.fixture
def vulnerable_issue_workflow_yaml():
    return """name: Issue Handler
on:
  issues:
    types: [opened]

jobs:
  comment-job:
    runs-on: ubuntu-latest
    steps:
      - name: Checkout
        uses: actions/checkout@v3
      - name: Echo Title
        run: echo "${{ github.event.issue.title }}"
      - name: Deploy
        env:
          PROD_KEY: ${{ secrets.DEPLOY_KEY }}
        run: ./deploy.sh
"""


@pytest.fixture
def tj_actions_workflow_yaml():
    return """name: Changed Files Checker
on:
  pull_request:

jobs:
  check:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - name: Get Changed Files
        id: changed-files
        uses: tj-actions/changed-files@v44
      - name: Echo
        run: echo "Done"
"""


@pytest.fixture
def safe_workflow_yaml():
    return """name: Secure Pipeline
on:
  push:
    branches: [main]

permissions:
  contents: read

jobs:
  build:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@b4ffde65f46336ab88eb53be808477a3936bae11
      - name: Run Build
        run: npm run build
"""
