"""Shared helper utilities for Agent Guidance MCP."""

from __future__ import annotations

import json
from typing import Any

from .response_optimizer import estimate_tokens
from .token_analytics import TokenTracker


def record_savings(
    tracker: TokenTracker | None,
    tool_name: str,
    operation: str,
    original: Any,
    optimized: Any,
) -> None:
    """Record token savings if tracker is active."""
    if tracker is None:
        return
    original_text = original if isinstance(original, str) else json.dumps(original, default=str)
    optimized_text = optimized if isinstance(optimized, str) else json.dumps(optimized, default=str)
    tracker.record(
        tool_name=tool_name,
        operation=operation,
        original_tokens=estimate_tokens(original_text),
        optimized_tokens=estimate_tokens(optimized_text),
    )
