"""Investigation trace — records every tool call and decision for explainability."""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class TraceStep:
    """One step in the investigation trace."""
    iteration: int
    action: str                    # llm_call, tool:name, final_response
    details: List[str] = field(default_factory=list)
    duration_ms: int = 0
    timestamp: float = field(default_factory=time.time)


@dataclass
class InvestigationTrace:
    """Full trace of an investigation — stored in the graph for explainability."""
    prompt: str
    model: str
    steps: List[TraceStep] = field(default_factory=list)
    started_at: float = field(default_factory=time.time)
    completed_at: Optional[float] = None

    def complete(self):
        self.completed_at = time.time()

    @property
    def total_duration_ms(self) -> int:
        if self.completed_at:
            return int((self.completed_at - self.started_at) * 1000)
        return sum(s.duration_ms for s in self.steps)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "prompt": self.prompt,
            "model": self.model,
            "total_duration_ms": self.total_duration_ms,
            "steps": [
                {
                    "iteration": s.iteration,
                    "action": s.action,
                    "details": s.details,
                    "duration_ms": s.duration_ms,
                }
                for s in self.steps
            ],
        }
