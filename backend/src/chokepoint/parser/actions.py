"""Composite action resolver.

Resolves `uses: ./local/action` and third-party composite action references
to their actual action.yml definitions, enabling cross-file flow tracking.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional

from ruamel.yaml import YAML

logger = logging.getLogger(__name__)
yaml = YAML()
yaml.preserve_quotes = True


@dataclass
class CompositeStep:
    """A step inside a composite action's runs.steps."""
    index: int
    id: Optional[str]
    run: Optional[str]
    uses: Optional[str]
    shell: Optional[str]
    env: Dict[str, str] = field(default_factory=dict)
    with_inputs: Dict[str, str] = field(default_factory=dict)


@dataclass
class CompositeAction:
    """Parsed composite action definition (action.yml)."""
    name: str
    description: Optional[str]
    inputs: Dict[str, dict] = field(default_factory=dict)  # name → {description, required, default}
    outputs: Dict[str, dict] = field(default_factory=dict)
    steps: List[CompositeStep] = field(default_factory=list)
    path: str = ""  # path to action.yml
    is_composite: bool = True


def parse_action_yml(content: str, path: str = "") -> Optional[CompositeAction]:
    """Parse an action.yml/action.yaml file.

    Returns None if the action is not a composite action (e.g., JavaScript or Docker).
    """
    data = yaml.load(content)
    if not isinstance(data, dict):
        return None

    runs = data.get("runs", {})
    if not isinstance(runs, dict):
        return None

    # Only composite actions have `using: composite`
    if runs.get("using") != "composite":
        return None

    action = CompositeAction(
        name=data.get("name", ""),
        description=data.get("description"),
        inputs=data.get("inputs", {}) or {},
        outputs=data.get("outputs", {}) or {},
        path=path,
    )

    # Parse composite steps
    for i, step_data in enumerate(runs.get("steps", [])):
        if not isinstance(step_data, dict):
            continue
        step = CompositeStep(
            index=i,
            id=step_data.get("id"),
            run=step_data.get("run"),
            uses=step_data.get("uses"),
            shell=step_data.get("shell"),
            env=step_data.get("env", {}) or {},
            with_inputs=step_data.get("with", {}) or {},
        )
        action.steps.append(step)

    return action


def resolve_local_action(repo_root: Path, action_path: str) -> Optional[CompositeAction]:
    """Resolve a local action reference (e.g., `./my-action`) to its parsed definition."""
    action_dir = repo_root / action_path.lstrip("./")
    for filename in ("action.yml", "action.yaml"):
        action_file = action_dir / filename
        if action_file.exists():
            content = action_file.read_text(encoding="utf-8")
            return parse_action_yml(content, str(action_file))
    return None
