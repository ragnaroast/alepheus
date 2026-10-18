"""GitHub repo cloner — fetches workflow files from repositories."""

from __future__ import annotations

import logging
import tempfile
import shutil
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import httpx

from chokepoint.config import get_settings

logger = logging.getLogger(__name__)


def fetch_workflow_files(
    repo_full_name: str,
    branch: str = "main",
    clone_dir: Optional[Path] = None,
) -> List[Tuple[str, str]]:
    """Fetch all workflow files from a GitHub repo via the API.

    Uses the GitHub Contents API to avoid full clones. Falls back to
    Trees API for repos with many workflows.

    Args:
        repo_full_name: e.g. "octocat/hello-world"
        branch: branch to fetch from
        clone_dir: optional local directory (if already cloned)

    Returns:
        List of (relative_path, content) tuples
    """
    if clone_dir:
        return _read_local_workflows(clone_dir)

    return _fetch_via_api(repo_full_name, branch)


def _fetch_via_api(repo_full_name: str, branch: str) -> List[Tuple[str, str]]:
    """Fetch workflow files using GitHub Contents API."""
    s = get_settings()
    headers = {"Accept": "application/vnd.github.v3+json"}
    if s.github_token:
        headers["Authorization"] = f"Bearer {s.github_token}"

    workflows: List[Tuple[str, str]] = []

    # First, list the workflows directory
    url = f"https://api.github.com/repos/{repo_full_name}/contents/.github/workflows"
    params = {"ref": branch}

    try:
        with httpx.Client(timeout=30) as client:
            resp = client.get(url, headers=headers, params=params)

            if resp.status_code == 404:
                logger.info("No workflows directory in %s", repo_full_name)
                return []

            resp.raise_for_status()
            files = resp.json()

            if not isinstance(files, list):
                logger.warning("Unexpected response for %s workflows", repo_full_name)
                return []

            for f in files:
                name = f.get("name", "")
                if not (name.endswith(".yml") or name.endswith(".yaml")):
                    continue

                # Fetch file content
                file_url = f.get("download_url")
                if file_url:
                    file_resp = client.get(file_url, headers=headers)
                    if file_resp.status_code == 200:
                        rel_path = f".github/workflows/{name}"
                        workflows.append((rel_path, file_resp.text))
                    else:
                        logger.warning("Failed to download %s: %d", name, file_resp.status_code)

    except httpx.HTTPError as e:
        logger.error("GitHub API error for %s: %s", repo_full_name, e)

    logger.info("Fetched %d workflow files from %s", len(workflows), repo_full_name)
    return workflows


def _read_local_workflows(repo_dir: Path) -> List[Tuple[str, str]]:
    """Read workflow files from a local directory."""
    wf_dir = repo_dir / ".github" / "workflows"
    if not wf_dir.exists():
        return []

    workflows = []
    for f in wf_dir.iterdir():
        if f.suffix in (".yml", ".yaml") and f.is_file():
            content = f.read_text(encoding="utf-8")
            rel_path = f".github/workflows/{f.name}"
            workflows.append((rel_path, content))

    return workflows


def fetch_action_yml(
    action_slug: str,
    ref: str = "main",
) -> Optional[str]:
    """Fetch action.yml for a third-party action.

    Args:
        action_slug: e.g. "actions/checkout"
        ref: version ref

    Returns:
        Content string or None
    """
    s = get_settings()
    headers = {"Accept": "application/vnd.github.v3.raw"}
    if s.github_token:
        headers["Authorization"] = f"Bearer {s.github_token}"

    # Try action.yml then action.yaml
    for filename in ("action.yml", "action.yaml"):
        url = f"https://raw.githubusercontent.com/{action_slug}/{ref}/{filename}"
        try:
            with httpx.Client(timeout=15) as client:
                resp = client.get(url, headers=headers)
                if resp.status_code == 200:
                    return resp.text
        except httpx.HTTPError:
            continue

    return None


def list_public_repos(
    query: str = "stars:>1000 language:JavaScript",
    max_repos: int = 100,
) -> List[Dict]:
    """Search GitHub for public repos (for corpus building).

    Args:
        query: GitHub search query
        max_repos: maximum repos to return

    Returns:
        List of repo dicts with 'full_name', 'stargazers_count', etc.
    """
    s = get_settings()
    headers = {"Accept": "application/vnd.github.v3+json"}
    if s.github_token:
        headers["Authorization"] = f"Bearer {s.github_token}"

    repos = []
    page = 1
    per_page = min(100, max_repos)

    with httpx.Client(timeout=30) as client:
        while len(repos) < max_repos:
            url = "https://api.github.com/search/repositories"
            params = {"q": query, "sort": "stars", "per_page": per_page, "page": page}

            try:
                resp = client.get(url, headers=headers, params=params)
                resp.raise_for_status()
                data = resp.json()
                items = data.get("items", [])
                if not items:
                    break
                repos.extend(items)
                page += 1
            except httpx.HTTPError as e:
                logger.error("GitHub search error: %s", e)
                break

    return repos[:max_repos]
