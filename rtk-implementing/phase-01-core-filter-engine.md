# Phase 01: Core Filter Engine

Status: ⬜ Pending
Dependencies: None (foundation phase)

## Objective

Port RTK's 8-stage text filter pipeline from Rust to Python. This is the foundational building block that all other phases depend on. The module will be a standalone, testable Python module (`token_filter.py`) with no external dependencies beyond stdlib.

## Background: What RTK Does

RTK applies an **8-stage filter pipeline** to command/text output:

```
Input Text → [1.strip_ansi] → [2.replace] → [3.match_output] → [4.strip/keep_lines]
           → [5.truncate_lines_at] → [6.head/tail_lines] → [7.max_lines] → [8.on_empty] → Output
```

Each stage is optional and configured per-filter. This architecture is defined in RTK's `src/core/toml_filter.rs`.

## What to Port (from RTK Rust → Python)

### 1. ANSI Strip (`strip_ansi`)
**RTK Source:** `src/core/utils.rs` lines 48-53
```rust
pub fn strip_ansi(text: &str) -> String {
    lazy_static! {
        static ref ANSI_RE: Regex = Regex::new(r"\x1b\[[0-9;]*[a-zA-Z]").unwrap();
    }
    ANSI_RE.replace_all(text, "").to_string()
}
```

**Python Implementation:**
```python
import re

_ANSI_RE = re.compile(r'\x1b\[[0-9;]*[a-zA-Z]')

def strip_ansi(text: str) -> str:
    """Remove ANSI escape codes (colors, styles) from text."""
    return _ANSI_RE.sub('', text)
```

### 2. Regex Replace (`replace`)
**RTK Source:** `src/core/toml_filter.rs` lines 447-461
- Line-by-line regex substitution
- Rules chained sequentially (rule N+1 operates on output of rule N)
- Backreferences supported

**Python Implementation:**
```python
@dataclass
class ReplaceRule:
    pattern: re.Pattern
    replacement: str

def apply_replace(lines: list[str], rules: list[ReplaceRule]) -> list[str]:
    """Apply chained regex substitutions line-by-line."""
    for rule in rules:
        lines = [rule.pattern.sub(rule.replacement, line) for line in lines]
    return lines
```

### 3. Match Output Short-Circuit (`match_output`)
**RTK Source:** `src/core/toml_filter.rs` lines 463-477
- Joins all lines into blob, checks against patterns
- First matching rule wins → returns its `message` immediately
- Optional `unless` pattern: if also matches, skip this rule

**Python Implementation:**
```python
@dataclass
class MatchOutputRule:
    pattern: re.Pattern
    message: str
    unless: re.Pattern | None = None

def check_match_output(lines: list[str], rules: list[MatchOutputRule]) -> str | None:
    """Short-circuit: if full output matches a pattern, return message immediately."""
    if not rules:
        return None
    blob = '\n'.join(lines)
    for rule in rules:
        if rule.pattern.search(blob):
            if rule.unless and rule.unless.search(blob):
                continue  # errors/warnings present — skip
            return rule.message
    return None
```

### 4. Line Filtering (`strip_lines_matching` / `keep_lines_matching`)
**RTK Source:** `src/core/toml_filter.rs` lines 479-484
- Strip: remove lines matching any regex in set
- Keep: keep ONLY lines matching any regex in set
- Mutually exclusive

**Python Implementation:**
```python
class LineFilter:
    """Filter lines by regex patterns. Strip and Keep are mutually exclusive."""
    
    def __init__(self, strip_patterns: list[str] | None = None,
                 keep_patterns: list[str] | None = None):
        if strip_patterns and keep_patterns:
            raise ValueError("strip and keep are mutually exclusive")
        self.strip_set = [re.compile(p) for p in (strip_patterns or [])]
        self.keep_set = [re.compile(p) for p in (keep_patterns or [])]
    
    def apply(self, lines: list[str]) -> list[str]:
        if self.strip_set:
            return [l for l in lines if not any(p.search(l) for p in self.strip_set)]
        if self.keep_set:
            return [l for l in lines if any(p.search(l) for p in self.keep_set)]
        return lines
```

### 5. Line Truncation (`truncate_lines_at`)
**RTK Source:** `src/core/utils.rs` lines 25-35 + toml_filter.rs lines 487-492
- Truncate each line to N characters (unicode-safe)
- Append "..." if truncated

**Python Implementation:**
```python
def truncate_line(text: str, max_len: int) -> str:
    """Truncate a string to max_len characters, appending '...' if needed."""
    if len(text) <= max_len:
        return text
    if max_len < 3:
        return "..."
    return text[:max_len - 3] + "..."
```

### 6. Head/Tail Lines (`head_lines`, `tail_lines`)
**RTK Source:** `src/core/toml_filter.rs` lines 494-514
- Keep first N and/or last M lines
- Insert "... (X lines omitted)" marker

**Python Implementation:**
```python
def apply_head_tail(lines: list[str], head: int | None, tail: int | None) -> list[str]:
    """Keep first/last N lines with omission markers."""
    total = len(lines)
    if head is not None and tail is not None and total > head + tail:
        result = lines[:head]
        result.append(f"... ({total - head - tail} lines omitted)")
        result.extend(lines[total - tail:])
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
```

### 7. Max Lines Cap (`max_lines`)
**RTK Source:** `src/core/toml_filter.rs` lines 516-523

**Python Implementation:**
```python
def apply_max_lines(lines: list[str], max_lines: int | None) -> list[str]:
    """Absolute line cap applied after head/tail."""
    if max_lines is None or len(lines) <= max_lines:
        return lines
    truncated = len(lines) - max_lines
    result = lines[:max_lines]
    result.append(f"... ({truncated} lines truncated)")
    return result
```

### 8. On-Empty Message (`on_empty`)
**RTK Source:** `src/core/toml_filter.rs` lines 525-531

**Python Implementation:**
```python
def apply_on_empty(result: str, on_empty: str | None) -> str:
    """Return fallback message if result is empty."""
    if result.strip() == "" and on_empty:
        return on_empty
    return result
```

### 9. Combined Pipeline — `apply_filter()`
**RTK Source:** `src/core/toml_filter.rs` lines 436-534

```python
def apply_filter(filter_config: CompiledFilter, text: str) -> str:
    """Apply the full 8-stage filter pipeline. Pure str → str."""
    lines = text.splitlines()
    
    # 1. strip_ansi
    if filter_config.strip_ansi:
        lines = [strip_ansi(line) for line in lines]
    
    # 2. replace
    if filter_config.replace_rules:
        lines = apply_replace(lines, filter_config.replace_rules)
    
    # 3. match_output (short-circuit)
    short_circuit = check_match_output(lines, filter_config.match_output_rules)
    if short_circuit is not None:
        return short_circuit
    
    # 4. strip/keep lines
    lines = filter_config.line_filter.apply(lines)
    
    # 5. truncate each line
    if filter_config.truncate_lines_at is not None:
        lines = [truncate_line(l, filter_config.truncate_lines_at) for l in lines]
    
    # 6. head/tail
    lines = apply_head_tail(lines, filter_config.head_lines, filter_config.tail_lines)
    
    # 7. max_lines
    lines = apply_max_lines(lines, filter_config.max_lines)
    
    # 8. on_empty
    result = '\n'.join(lines)
    return apply_on_empty(result, filter_config.on_empty)
```

## Implementation Steps

1. [ ] Create `src/agent_guidance_mcp/token_filter.py` with all 8 pipeline stages
2. [ ] Create `CompiledFilter` dataclass to hold filter configuration
3. [ ] Create `FilterRegistry` class for managing filter collections
4. [ ] Implement `apply_filter()` — the main pipeline function
5. [ ] Add utility functions: `strip_ansi()`, `truncate_line()`, etc.
6. [ ] Create `FilterLevel` enum (None, Minimal, Aggressive) matching RTK's `src/core/filter.rs`

## Files to Create/Modify

- `src/agent_guidance_mcp/token_filter.py` — **[NEW]** Core filter pipeline engine
- `tests/test_token_filter.py` — **[NEW]** Unit tests for all pipeline stages

## Test Criteria

- [ ] `strip_ansi()` removes ANSI codes from colored text
- [ ] `apply_replace()` chains regex substitutions correctly
- [ ] `check_match_output()` short-circuits on matching patterns
- [ ] `check_match_output()` respects `unless` patterns
- [ ] `LineFilter` strips lines matching patterns
- [ ] `LineFilter` keeps only lines matching patterns
- [ ] `LineFilter` rejects both strip and keep simultaneously
- [ ] `truncate_line()` handles unicode (Thai, CJK, emoji)
- [ ] `apply_head_tail()` correctly slices and inserts markers
- [ ] `apply_max_lines()` caps output with truncation notice
- [ ] `apply_on_empty()` returns fallback for empty results
- [ ] Full `apply_filter()` pipeline produces correct output end-to-end
- [ ] Verify pipeline matches RTK's `brew-install.toml` test cases

## Notes

- **No TOML dependency needed**: The MCP server will define filters in Python code (dicts/dataclasses) rather than TOML files, keeping zero new dependencies
- **Thread-safe**: All functions are pure `str → str` transformations, no global state
- **Performance**: Pre-compile regex patterns at module load time using module-level `re.compile()`, matching RTK's `lazy_static!` pattern

---
Next Phase: [Phase 02 — Content Compressor](./phase-02-content-compressor.md)
