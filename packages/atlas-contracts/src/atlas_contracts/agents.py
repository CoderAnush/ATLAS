"""Minimal future-facing agent request and response contracts."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class AgentRequest(BaseModel):
    """Placeholder input envelope for a future agent invocation."""

    run_id: str | None = None
    instructions: str
    context_refs: list[str] = Field(default_factory=list)
    constraints: dict[str, Any] = Field(default_factory=dict)


class AgentResponse(BaseModel):
    """Placeholder output envelope for a future agent invocation."""

    status: str = "not_implemented"
    messages: list[str] = Field(default_factory=list)
    artifacts: list[str] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)
