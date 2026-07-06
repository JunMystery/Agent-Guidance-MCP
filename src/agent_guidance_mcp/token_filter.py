"""Pure text filtering pipeline used by token optimization phases."""


import re
from dataclasses import dataclass, field
from enum import Enum
from typing import Pattern, Sequence


RegexValue = str | Pattern[str]

_ANSI_RE = re.compile(r"\x1b\[[0-9;]*[a-zA-Z]")


class FilterLevel(Enum):
    """Filter levels used by token optimization phases."""

    NONE = "none"
    MINIMAL = "minimal"
    AGGRESSIVE = "aggressive"


@dataclass(frozen=True)
class ReplaceRule:
    """A compiled regex substitution rule."""

    pattern: Pattern[str]
    replacement: str


@dataclass(frozen=True)
class MatchOutputRule:
    """A full-output match rule that can short-circuit the pipeline."""

    pattern: Pattern[str]
    message: str
    unless: Pattern[str] | None = None


class LineFilter:
    """Filter lines by regex patterns. Strip and keep modes are mutually exclusive."""

    def __init__(
        self,
        strip_patterns: Sequence[RegexValue] | None = None,
        keep_patterns: Sequence[RegexValue] | None = None,
    ) -> None:
        if strip_patterns and keep_patterns:
            raise ValueError("strip and keep are mutually exclusive")
        self.strip_set = [_compile_pattern(pattern) for pattern in (strip_patterns or [])]
        self.keep_set = [_compile_pattern(pattern) for pattern in (keep_patterns or [])]

    def apply(self, lines: list[str]) -> list[str]:
        """Apply configured strip or keep filtering to lines."""
        if self.strip_set:
            return [
                line
                for line in lines
                if not any(pattern.search(line) for pattern in self.strip_set)
            ]
        if self.keep_set:
            return [
                line
                for line in lines
                if any(pattern.search(line) for pattern in self.keep_set)
            ]
        return lines


@dataclass(frozen=True)
class CompiledFilter:
    """Configuration for the 8-stage token filter pipeline."""

    strip_ansi: bool = False
    replace_rules: list[ReplaceRule] = field(default_factory=list)
    match_output_rules: list[MatchOutputRule] = field(default_factory=list)
    line_filter: LineFilter = field(default_factory=LineFilter)
    truncate_lines_at: int | None = None
    head_lines: int | None = None
    tail_lines: int | None = None
    max_lines: int | None = None
    on_empty: str | None = None


class FilterRegistry:
    """Named collection of compiled filters."""

    def __init__(self) -> None:
        self._filters: dict[str, CompiledFilter] = {}

    def register(self, name: str, compiled_filter: CompiledFilter) -> None:
        """Register or replace a filter by name."""
        self._filters[name] = compiled_filter

    def get(self, name: str) -> CompiledFilter:
        """Return a filter by name."""
        return self._filters[name]

    def apply(self, name: str, text: str) -> str:
        """Apply a named filter to text."""
        return apply_filter(self.get(name), text)


def strip_ansi(text: str) -> str:
    """Remove ANSI escape codes such as colors and styles from text."""
    return _ANSI_RE.sub("", text)


def apply_replace(lines: list[str], rules: list[ReplaceRule]) -> list[str]:
    """Apply chained regex substitutions line-by-line."""
    for rule in rules:
        lines = [rule.pattern.sub(rule.replacement, line) for line in lines]
    return lines


def check_match_output(lines: list[str], rules: list[MatchOutputRule]) -> str | None:
    """Return the first matching output message, respecting optional unless patterns."""
    if not rules:
        return None

    blob = "\n".join(lines)
    for rule in rules:
        if not rule.pattern.search(blob):
            continue
        if rule.unless and rule.unless.search(blob):
            continue
        return rule.message
    return None


def truncate_line(text: str, max_len: int) -> str:
    """Truncate a string to max_len characters, appending an ellipsis marker."""
    if len(text) <= max_len:
        return text
    if max_len < 3:
        return "..."
    return text[: max_len - 3] + "..."


def apply_head_tail(lines: list[str], head: int | None, tail: int | None) -> list[str]:
    """Keep first and/or last lines with omission markers."""
    total = len(lines)
    if head is not None and tail is not None:
        if total <= head + tail:
            return lines
        result = lines[:head]
        result.append(f"... ({total - head - tail} lines omitted)")
        if tail > 0:
            result.extend(lines[total - tail :])
        return result
    if head is not None and total > head:
        result = lines[:head]
        result.append(f"... ({total - head} lines omitted)")
        return result
    if tail is not None and total > tail:
        omitted = total - tail
        result = [f"... ({omitted} lines omitted)"]
        result.extend(lines[omitted:])
        return result
    return lines


def apply_max_lines(lines: list[str], max_lines: int | None) -> list[str]:
    """Apply an absolute line cap after head/tail filtering."""
    if max_lines is None or len(lines) <= max_lines:
        return lines
    truncated = len(lines) - max_lines
    result = lines[:max_lines]
    result.append(f"... ({truncated} lines truncated)")
    return result


def apply_on_empty(result: str, on_empty: str | None) -> str:
    """Return a fallback message if the final output is empty."""
    if result.strip() == "" and on_empty:
        return on_empty
    return result


def apply_filter(filter_config: CompiledFilter, text: str) -> str:
    """Apply the full 8-stage filter pipeline."""
    lines = text.splitlines()

    if filter_config.strip_ansi:
        lines = [strip_ansi(line) for line in lines]

    if filter_config.replace_rules:
        lines = apply_replace(lines, filter_config.replace_rules)

    short_circuit = check_match_output(lines, filter_config.match_output_rules)
    if short_circuit is not None:
        return short_circuit

    lines = filter_config.line_filter.apply(lines)

    if filter_config.truncate_lines_at is not None:
        lines = [
            truncate_line(line, filter_config.truncate_lines_at)
            for line in lines
        ]

    lines = apply_head_tail(lines, filter_config.head_lines, filter_config.tail_lines)
    lines = apply_max_lines(lines, filter_config.max_lines)

    result = "\n".join(lines)
    return apply_on_empty(result, filter_config.on_empty)


def _compile_pattern(pattern: RegexValue) -> Pattern[str]:
    if isinstance(pattern, str):
        return re.compile(pattern)
    return pattern
