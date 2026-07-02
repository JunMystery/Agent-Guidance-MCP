"""Shared helper utilities for Agent Guidance MCP."""


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
    if isinstance(original, str):
        original_text = original
    elif isinstance(original, (list, dict)):
        original_text = json.dumps(original, default=str)
    else:
        original_text = str(original)
    if isinstance(optimized, str):
        optimized_text = optimized
    elif isinstance(optimized, (list, dict)):
        optimized_text = json.dumps(optimized, default=str)
    else:
        optimized_text = str(optimized)
    tracker.record(
        tool_name=tool_name,
        operation=operation,
        original_tokens=estimate_tokens(original_text),
        optimized_tokens=estimate_tokens(optimized_text),
    )
