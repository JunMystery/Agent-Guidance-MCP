# Phase 03: Response Optimizer

Status: ⬜ Pending
Dependencies: Phase 01 (Core Filter Engine), Phase 02 (Content Compressor)

## Objective

Create the **intelligent response optimizer** (`response_optimizer.py`) that automatically reduces token usage in every MCP tool response. This module sits between the MCP pipeline dispatchers and the response serialization layer, applying content-aware compression based on the type of content being returned.

## Background: MCP Response Token Problem

The current MCP server returns content **RAW with ZERO token optimization**. Analysis shows:

| MCP Response Type | Current Behavior | Token Waste |
|-------------------|-----------------|-------------|
| `catalog.read_path()` | Raw `path.read_text()` | Full markdown docs (2K-10K tokens each) |
| `project_context.read_project_file()` | Raw line-by-line read | Full source files with comments |
| `export_project_snapshot()` | Full file contents embedded | 2MB+ of raw source |
| `guidance(operation="get")` | Raw catalog entry content | Full document text |
| `task_pipeline()` | Aggregated recommendations | Redundant metadata |
| `workflow_prompt()` | Raw markdown workflow | Full workflow scripts |

### Where to Inject (from MCP Server research)

The research identified **3 primary injection points**:

1. **`catalog.read_path()`** (catalog.py L92-94) — THE central bottleneck for all document reads
2. **`project_context.read_project_file()`** (project_context.py L131) — Source file content
3. **`pipelines.py` dispatcher functions** — Composite results before return

## What to Build

### 1. Token Estimation
**RTK Source:** `src/core/tracking.rs` — `ceil(chars / 4)`

```python
import math

def estimate_tokens(text: str) -> int:
    """Estimate token count for text. RTK uses ~4 chars per token average."""
    return math.ceil(len(text) / 4)

def format_tokens(n: int) -> str:
    """Format token count with K/M suffixes (from RTK utils.rs)."""
    if n >= 1_000_000:
        return f"{n / 1_000_000:.1f}M"
    if n >= 1_000:
        return f"{n / 1_000:.1f}K"
    return str(n)
```

### 2. Markdown Content Optimizer

For standards documents (the bulk of MCP content), apply markdown-specific compression:

```python
def optimize_markdown(content: str, max_tokens: int | None = None) -> str:
    """Reduce markdown document token usage while preserving key information.
    
    Strategies applied:
    1. Collapse consecutive blank lines to single blank line
    2. Strip trailing whitespace
    3. Strip HTML comments
    4. Strip badge/shield image links
    5. Collapse redundant list formatting
    6. Smart section truncation if over budget
    """
    # Phase 1: Whitespace normalization
    content = re.sub(r'\n{3,}', '\n\n', content)
    content = re.sub(r'[ \t]+$', '', content, flags=re.MULTILINE)
    
    # Phase 2: Strip noise
    content = re.sub(r'<!--.*?-->', '', content, flags=re.DOTALL)
    content = re.sub(r'!\[.*?\]\(https://img\.shields\.io/.*?\)', '', content)
    content = re.sub(r'!\[.*?\]\(https://badge.*?\)', '', content)
    
    # Phase 3: Token budget enforcement
    if max_tokens and estimate_tokens(content) > max_tokens:
        content = truncate_to_budget(content, max_tokens)
    
    return content.strip()
```

### 3. Section-Aware Truncation

When a document exceeds its token budget, use section-aware truncation that preserves document structure:

```python
def truncate_to_budget(content: str, max_tokens: int) -> str:
    """Intelligently truncate markdown preserving section headers."""
    if estimate_tokens(content) <= max_tokens:
        return content
    
    lines = content.splitlines()
    sections: list[tuple[str, list[str]]] = []
    current_header = ""
    current_lines: list[str] = []
    
    for line in lines:
        if line.startswith('#'):
            if current_header or current_lines:
                sections.append((current_header, current_lines))
            current_header = line
            current_lines = []
        else:
            current_lines.append(line)
    
    if current_header or current_lines:
        sections.append((current_header, current_lines))
    
    # Keep sections until budget is exhausted
    result_lines = []
    remaining_tokens = max_tokens
    
    for header, body in sections:
        section_text = header + '\n' + '\n'.join(body)
        section_tokens = estimate_tokens(section_text)
        
        if remaining_tokens <= 0:
            break
        
        if section_tokens <= remaining_tokens:
            result_lines.append(section_text)
            remaining_tokens -= section_tokens
        else:
            # Partially include this section
            result_lines.append(header)
            remaining_tokens -= estimate_tokens(header)
            for body_line in body:
                line_tokens = estimate_tokens(body_line)
                if remaining_tokens <= estimate_tokens("[truncated]"):
                    break
                result_lines.append(body_line)
                remaining_tokens -= line_tokens
            result_lines.append(f"\n[...truncated — {estimate_tokens(content) - max_tokens} tokens over budget]")
            break
    
    return '\n'.join(result_lines)
```

### 4. Source File Content Optimizer

For source code returned by `project_context.read_project_file()`:

```python
def optimize_source_content(
    content: str,
    language_hint: str,
    level: FilterLevel = FilterLevel.MINIMAL,
) -> tuple[str, dict[str, int]]:
    """Optimize source file content for token efficiency.
    
    Returns:
        (optimized_content, stats)
        stats contains: original_tokens, optimized_tokens, savings_pct
    """
    from .content_compressor import detect_language, filter_content, Language
    
    lang = _hint_to_language(language_hint)
    original_tokens = estimate_tokens(content)
    
    optimized = filter_content(content, lang, level)
    optimized_tokens = estimate_tokens(optimized)
    
    savings_pct = round((1 - optimized_tokens / max(1, original_tokens)) * 100)
    
    stats = {
        "original_tokens": original_tokens,
        "optimized_tokens": optimized_tokens,
        "savings_pct": savings_pct,
    }
    
    return optimized, stats
```

### 5. Dictionary/JSON Response Compressor

For structured dict responses, recursively optimize string values:

```python
def optimize_response(response: dict[str, object], max_content_tokens: int = 4000) -> dict[str, object]:
    """Recursively optimize string values in a response dict.
    
    Applies to:
    - "content" keys: full optimization (markdown or source)
    - "description" keys: truncation to 220 chars
    - "snippet" keys: already small, skip
    - Nested dicts/lists: recurse
    """
    result = {}
    for key, value in response.items():
        if key == "content" and isinstance(value, str):
            result[key] = optimize_markdown(value, max_tokens=max_content_tokens)
        elif key == "description" and isinstance(value, str):
            result[key] = value[:220]
        elif isinstance(value, dict):
            result[key] = optimize_response(value, max_content_tokens)
        elif isinstance(value, list):
            result[key] = [
                optimize_response(item, max_content_tokens) if isinstance(item, dict) else item
                for item in value
            ]
        else:
            result[key] = value
    return result
```

### 6. Snapshot Optimizer

For `export_project_snapshot()` which embeds full file contents:

```python
def optimize_snapshot_content(
    files: list[dict[str, object]],
    max_total_tokens: int = 50_000,
) -> list[dict[str, object]]:
    """Optimize file contents in a snapshot for token efficiency.
    
    Strategy:
    1. Apply minimal source filtering to all files
    2. Enforce per-file token budget
    3. Track total token budget
    """
    per_file_budget = max_total_tokens // max(1, len(files))
    optimized_files = []
    total_tokens = 0
    
    for file_entry in files:
        content = file_entry.get("content", "")
        if not isinstance(content, str):
            optimized_files.append(file_entry)
            continue
        
        lang_hint = file_entry.get("language_hint", "text")
        optimized, stats = optimize_source_content(
            content, lang_hint, FilterLevel.MINIMAL
        )
        
        # Enforce per-file budget
        file_tokens = estimate_tokens(optimized)
        if file_tokens > per_file_budget:
            optimized = truncate_to_budget(optimized, per_file_budget)
            file_tokens = estimate_tokens(optimized)
        
        total_tokens += file_tokens
        optimized_files.append({
            **file_entry,
            "content": optimized,
            "token_stats": stats,
        })
        
        if total_tokens >= max_total_tokens:
            remaining = len(files) - len(optimized_files)
            if remaining > 0:
                optimized_files.append({
                    "note": f"... {remaining} more files omitted (token budget exhausted)"
                })
            break
    
    return optimized_files
```

### 7. Token Budget Constants

**Inspired by RTK's `src/core/truncate.rs` cap system:**

```python
# Token budget caps (configurable defaults)
class TokenBudget:
    """Token budget caps for different content types."""
    
    # Per-document caps (standards/skills documents)
    DOCUMENT_MAX = 4_000        # Max tokens per individual document
    SKILL_MAX = 6_000           # Skills can be larger (they contain detailed guides)
    WORKFLOW_MAX = 8_000        # Workflow prompts are the largest
    
    # Per-response caps (composite responses)
    GUIDANCE_CONTENT_MAX = 4_000  # guidance(include_content=True)
    TASK_PIPELINE_MAX = 12_000    # task_pipeline total response
    
    # Source file caps
    SOURCE_FILE_MAX = 3_000     # project_context(operation="read")
    SNAPSHOT_TOTAL_MAX = 50_000  # project snapshot total
    SNAPSHOT_PER_FILE_MAX = 2_000  # snapshot per-file
    
    # Truncation caps matching RTK's truncate.rs
    CAP_ERRORS = 20
    CAP_WARNINGS = 10
    CAP_LIST = 20
    CAP_INVENTORY = 50
```

## Implementation Steps

1. [ ] Create `src/agent_guidance_mcp/response_optimizer.py`
2. [ ] Implement `estimate_tokens()` and `format_tokens()`
3. [ ] Implement `optimize_markdown()` with noise stripping
4. [ ] Implement `truncate_to_budget()` with section awareness
5. [ ] Implement `optimize_source_content()` using content_compressor
6. [ ] Implement `optimize_response()` for recursive dict optimization
7. [ ] Implement `optimize_snapshot_content()` for project snapshots
8. [ ] Define `TokenBudget` constants class
9. [ ] Add helper: `_hint_to_language()` mapping language_hint strings to Language enum

## Files to Create/Modify

- `src/agent_guidance_mcp/response_optimizer.py` — **[NEW]** Response optimization engine
- `tests/test_response_optimizer.py` — **[NEW]** Unit tests

## Test Criteria

- [ ] `estimate_tokens()` returns ~4 chars per token
- [ ] `format_tokens()` formats with K/M suffixes correctly
- [ ] `optimize_markdown()` strips HTML comments
- [ ] `optimize_markdown()` strips badge images
- [ ] `optimize_markdown()` collapses blank lines
- [ ] `truncate_to_budget()` preserves section headers
- [ ] `truncate_to_budget()` adds truncation notice
- [ ] `optimize_source_content()` reduces Python file by >40%
- [ ] `optimize_response()` recursively optimizes nested dicts
- [ ] `optimize_snapshot_content()` enforces per-file budget
- [ ] `optimize_snapshot_content()` stops at total budget
- [ ] End-to-end: a typical `guidance(operation="get")` response is 40-60% smaller

## Notes

- **Token estimation**: RTK uses `ceil(chars/4)` which is a rough heuristic. For GPT-4/Claude tokenizers the actual ratio varies (3-5 chars/token for English, higher for code). The heuristic is good enough for budgeting.
- **No semantic loss**: The optimizer never removes content that would change the meaning. Comments, blank lines, and formatting noise are the targets.
- **Configurable**: All budgets are in the `TokenBudget` class and can be overridden per-call or via configuration.

---
Next Phase: [Phase 04 — MCP Pipeline Integration](./phase-04-mcp-pipeline-integration.md)
