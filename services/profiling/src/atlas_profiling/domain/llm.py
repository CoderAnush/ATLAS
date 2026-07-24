"""LLM provider port — optional; deterministic templates are default."""

from __future__ import annotations

from typing import Protocol, runtime_checkable


@runtime_checkable
class LLMProvider(Protocol):
    def summarize(self, prompt: str) -> str:
        """Return a natural-language summary, or raise if unavailable."""


class StubLLMProvider:
    """Explicitly not configured — callers must fall back to templates."""

    def summarize(self, prompt: str) -> str:
        raise RuntimeError("llm_provider_not_configured")
