"""Response-level token optimization helpers."""

from __future__ import annotations

import math
import re
from typing import Any

from .content_compressor import (
    Language,
    detect_language,
    filter_content,
    filter_markdown,
)
from .token_config import TokenOptimizationConfig
from .token_filter import FilterLevel


_HTML_COMMENT = re.compile(r"<!--.*?-->", re.DOTALL)
_SHIELDS_BADGE = re.compile(r"!\[.*?\]\(https://img\.shields\.io/.*?\)")
_BADGE_IMAGE = re.compile(r"!\[.*?\]\(https://badge.*?\)")


class TokenBudget:
    """Token budget caps for different content types."""

    DOCUMENT_MAX = 4_000
    SKILL_MAX = 6_000
    WORKFLOW_MAX = 8_000

    GUIDANCE_CONTENT_MAX = 4_000
    TASK_PIPELINE_MAX = 12_000

    SOURCE_FILE_MAX = 3_000
    SNAPSHOT_TOTAL_MAX = 50_000
    SNAPSHOT_PER_FILE_MAX = 2_000

    CAP_ERRORS = 20
    CAP_WARNINGS = 10
    CAP_LIST = 20
    CAP_INVENTORY = 50


def estimate_tokens(text: str) -> int:
    """Estimate token count using RTK's chars/4 heuristic."""
    return math.ceil(len(text) / 4)


def format_tokens(n: int) -> str:
    """Format token counts with K/M suffixes."""
    if n >= 1_000_000:
        return f"{n / 1_000_000:.1f}M"
    if n >= 1_000:
        return f"{n / 1_000:.1f}K"
    return str(n)


def optimize_markdown(
    content: str,
    max_tokens: int | None = None,
    config: TokenOptimizationConfig | None = None,
) -> str:
    """Reduce markdown token usage while preserving core document content."""
    if config and not config.enabled:
        return content
    if config and config.markdown_filter_level == "none":
        return content

    if config is None or config.strip_html_comments:
        content = _HTML_COMMENT.sub("", content)
    if config is None or config.strip_badge_images:
        content = _SHIELDS_BADGE.sub("", content)
        content = _BADGE_IMAGE.sub("", content)
    if config is None or config.collapse_whitespace:
        content = filter_markdown(content)

    if max_tokens and estimate_tokens(content) > max_tokens:
        content = truncate_to_budget(content, max_tokens)

    return content.strip()


def truncate_to_budget(content: str, max_tokens: int) -> str:
    """Truncate markdown while preserving section headers."""
    if max_tokens <= 0:
        return _truncation_notice(estimate_tokens(content), max_tokens)
    if estimate_tokens(content) <= max_tokens:
        return content

    sections = _split_markdown_sections(content)
    result_lines: list[str] = []
    remaining_tokens = max_tokens
    notice_tokens = estimate_tokens(_truncation_notice(estimate_tokens(content), max_tokens))

    for header, body in sections:
        if remaining_tokens <= notice_tokens:
            break

        section_lines = [line for line in [header, *body] if line != ""]
        section_text = "\n".join(section_lines)
        section_tokens = estimate_tokens(section_text)

        if section_tokens <= remaining_tokens - notice_tokens:
            result_lines.extend(section_lines)
            remaining_tokens -= section_tokens
            continue

        if header:
            result_lines.append(header)
            remaining_tokens -= estimate_tokens(header)
        for body_line in body:
            line_tokens = estimate_tokens(body_line)
            if remaining_tokens - line_tokens <= notice_tokens:
                break
            result_lines.append(body_line)
            remaining_tokens -= line_tokens
        break

    result_lines.append(_truncation_notice(estimate_tokens(content), max_tokens))
    return "\n".join(line for line in result_lines if line != "").strip()


def optimize_source_content(
    content: str,
    language_hint: str,
    level: FilterLevel = FilterLevel.MINIMAL,
    config: TokenOptimizationConfig | None = None,
) -> tuple[str, dict[str, int]]:
    """Optimize source content and return token savings stats."""
    lang = _hint_to_language(language_hint)
    original_tokens = estimate_tokens(content)
    if config and not config.enabled:
        return content, {
            "original_tokens": original_tokens,
            "optimized_tokens": original_tokens,
            "savings_pct": 0,
        }
    if config:
        level = _filter_level_from_config(config.source_filter_level)
    optimized = filter_content(content, lang, level)
    optimized_tokens = estimate_tokens(optimized)
    savings_pct = round((1 - optimized_tokens / max(1, original_tokens)) * 100)

    return optimized, {
        "original_tokens": original_tokens,
        "optimized_tokens": optimized_tokens,
        "savings_pct": savings_pct,
    }


def optimize_response(
    response: dict[str, object],
    max_content_tokens: int = TokenBudget.GUIDANCE_CONTENT_MAX,
    config: TokenOptimizationConfig | None = None,
) -> dict[str, object]:
    """Recursively optimize string values in a response dictionary."""
    if config and not config.enabled:
        return dict(response)
    result: dict[str, object] = {}
    for key, value in response.items():
        if key == "content" and isinstance(value, str):
            result[key] = optimize_markdown(
                value, max_tokens=max_content_tokens, config=config
            )
        elif key == "description" and isinstance(value, str):
            result[key] = value[:220]
        elif key == "snippet":
            result[key] = value
        elif isinstance(value, dict):
            result[key] = optimize_response(value, max_content_tokens, config=config)
        elif isinstance(value, list):
            result[key] = [
                optimize_response(item, max_content_tokens, config=config)
                if isinstance(item, dict)
                else item
                for item in value
            ]
        else:
            result[key] = value
    return result


def optimize_snapshot_content(
    files: list[dict[str, object]],
    max_total_tokens: int = TokenBudget.SNAPSHOT_TOTAL_MAX,
    config: TokenOptimizationConfig | None = None,
) -> list[dict[str, object]]:
    """Optimize file contents in snapshot entries under a total token budget."""
    if not files:
        return []
    if config and not config.enabled:
        return [dict(file_entry) for file_entry in files]

    per_file_budget = max(
        1,
        min(
            config.snapshot_per_file_max_tokens if config else TokenBudget.SNAPSHOT_PER_FILE_MAX,
            max(1, max_total_tokens) // max(1, len(files)),
        ),
    )
    optimized_files: list[dict[str, object]] = []
    total_tokens = 0

    for index, file_entry in enumerate(files):
        content = file_entry.get("content", "")
        if not isinstance(content, str):
            optimized_files.append(dict(file_entry))
            continue

        language_hint = str(file_entry.get("language_hint", "text"))
        optimized, stats = optimize_source_content(
            content, language_hint, FilterLevel.MINIMAL, config=config
        )

        if estimate_tokens(optimized) > per_file_budget:
            optimized = truncate_to_budget(optimized, per_file_budget)

        final_tokens = estimate_tokens(optimized)
        if optimized_files and total_tokens + final_tokens > max_total_tokens:
            _append_omission_note(optimized_files, len(files) - index)
            break

        stats = _stats_for_final_content(content, optimized)
        optimized_files.append(
            {
                **file_entry,
                "content": optimized,
                "token_stats": stats,
            }
        )
        total_tokens += final_tokens

        if total_tokens >= max_total_tokens and index < len(files) - 1:
            _append_omission_note(optimized_files, len(files) - index - 1)
            break

    return optimized_files


def _hint_to_language(language_hint: str) -> Language:
    """Map scanner language hints or extensions to compressor languages."""
    normalized = language_hint.lower().strip().lstrip(".")
    hint_map = {
        "csharp": Language.CPP,
        "css": Language.DATA,
        "html": Language.DATA,
        "javascript": Language.JAVASCRIPT,
        "json": Language.DATA,
        "markdown": Language.DATA,
        "python": Language.PYTHON,
        "shell": Language.SHELL,
        "text": Language.DATA,
        "toml": Language.DATA,
        "typescript": Language.TYPESCRIPT,
        "xml": Language.DATA,
        "yaml": Language.DATA,
        "yml": Language.DATA,
    }
    if normalized in hint_map:
        return hint_map[normalized]
    return detect_language(normalized)


def _split_markdown_sections(content: str) -> list[tuple[str, list[str]]]:
    sections: list[tuple[str, list[str]]] = []
    current_header = ""
    current_lines: list[str] = []

    for line in content.splitlines():
        if line.startswith("#"):
            if current_header or current_lines:
                sections.append((current_header, current_lines))
            current_header = line
            current_lines = []
        else:
            current_lines.append(line)

    if current_header or current_lines:
        sections.append((current_header, current_lines))
    return sections


def _truncation_notice(original_tokens: int, max_tokens: int) -> str:
    over_budget = max(0, original_tokens - max_tokens)
    return f"[...truncated - {over_budget} tokens over budget]"


def _stats_for_final_content(original: str, optimized: str) -> dict[str, int]:
    original_tokens = estimate_tokens(original)
    optimized_tokens = estimate_tokens(optimized)
    savings_pct = round((1 - optimized_tokens / max(1, original_tokens)) * 100)
    return {
        "original_tokens": original_tokens,
        "optimized_tokens": optimized_tokens,
        "savings_pct": savings_pct,
    }


def _append_omission_note(entries: list[dict[str, Any]], remaining: int) -> None:
    if remaining > 0:
        entries.append({"note": f"... {remaining} more files omitted (token budget exhausted)"})


def _filter_level_from_config(value: str) -> FilterLevel:
    normalized = value.lower()
    if normalized == "none":
        return FilterLevel.NONE
    if normalized == "aggressive":
        return FilterLevel.AGGRESSIVE
    return FilterLevel.MINIMAL
