"""Documentation Agent implementation placeholder.

Replace `run` with a real agent that validates contracts from atlas-contracts.
"""

from __future__ import annotations

from typing import Any

AGENT_NAME = "documentation"


def run(request: dict[str, Any]) -> dict[str, Any]:
    """Execute the agent (stub)."""
    return {
        "status": "not_implemented",
        "agent": AGENT_NAME,
        "artifacts": [],
        "metrics": {},
        "messages": ["Placeholder agent — implement in later phases."],
        "next_hints": [],
        "echo": request,
    }