# Phase 04: MCP Pipeline Integration

Status: ⬜ Pending
Dependencies: Phase 01, 02, 03

## Objective

Wire the token optimization modules (from Phases 01-03) into the existing MCP server's data flow. This is the **integration phase** — modifying existing files (`catalog.py`, `pipelines.py`, `project_context.py`, `server.py`) to automatically apply token reduction to every MCP response.

## Architecture: Before vs After

```
BEFORE (current):
  MCP Tool Call → pipelines.py → catalog.read_path() → raw text → JSON response (5K tokens)

AFTER (with RTK integration):
  MCP Tool Call → pipelines.py → catalog.read_path() → response_optimizer → JSON response (1.5K tokens)
                                                              ↓
                                              [content_compressor] + [token_filter]
```

## Integration Points (6 locations)

### 1. `catalog.py` — Central Read Path
**File:** `src/agent_guidance_mcp/catalog.py`
**Lines:** 88-94 (read_entry, read_path)

This is **THE central bottleneck** — every document/skill/resource read goes through here.

**Current code:**
```python
def read_entry(self, identifier: str) -> str:
    entry = self.get_entry(identifier)
    return self.read_path(entry.path)

def read_path(self, relative_path: str) -> str:
    path = resolve_inside_root(self.root, relative_path)
    return path.read_text(encoding="utf-8")
```

**Modified code:**
```python
def read_entry(self, identifier: str, optimize: bool = True) -> str:
    entry = self.get_entry(identifier)
    content = self.read_path(entry.path)
    if optimize:
        from .response_optimizer import optimize_markdown, TokenBudget
        budget = TokenBudget.SKILL_MAX if entry.kind == "skill" else TokenBudget.DOCUMENT_MAX
        content = optimize_markdown(content, max_tokens=budget)
    return content

def read_path(self, relative_path: str) -> str:
    path = resolve_inside_root(self.root, relative_path)
    return path.read_text(encoding="utf-8")
```

**Key design decision:** `read_path()` stays RAW because it's used internally for search scoring. Optimization happens in `read_entry()` which is the public-facing method.

---

### 2. `pipelines.py` — Guidance Pipeline
**File:** `src/agent_guidance_mcp/pipelines.py`
**Lines:** 50-71 (guidance function)

When `include_content=True`, raw content is injected:

**Current code (L60-62):**
```python
if include_content:
    result["content"] = catalog.read_entry(entry.identifier)
```

**Modified code:**
```python
if include_content:
    result["content"] = catalog.read_entry(entry.identifier, optimize=True)
```

This is already handled by the `catalog.read_entry()` change above, but we also need to optimize the search results:

**Search operation (L68-69):**
```python
# Current:
return catalog.search_entries(query=query, limit=limit, kind=kind)

# Modified — optimize snippets in results:
from .response_optimizer import optimize_response
results = catalog.search_entries(query=query, limit=limit, kind=kind)
return optimize_response({"results": results})["results"]
```

---

### 3. `pipelines.py` — Task Pipeline
**File:** `src/agent_guidance_mcp/pipelines.py`
**Lines:** 174-215 (task_pipeline function)

This is the "one-call" aggregator — the highest token-consuming endpoint:

**Add optimization wrapper at the end (after L215):**
```python
def task_pipeline(...) -> dict[str, object]:
    # ... existing code builds `result` dict ...
    
    # NEW: Apply token budget to entire response
    from .response_optimizer import optimize_response, TokenBudget
    return optimize_response(result, max_content_tokens=TokenBudget.TASK_PIPELINE_MAX)
```

---

### 4. `project_context.py` — File Read
**File:** `src/agent_guidance_mcp/project_context.py`
**Lines:** 96-132 (read_project_file)

Source code content can be optimized:

**Current code (L130-131):**
```python
return {
    ...
    "content": "\n".join(selected),
}
```

**Modified code:**
```python
from .response_optimizer import optimize_source_content
from .content_compressor import FilterLevel

raw_content = "\n".join(selected)
lang_hint = language_hint(path)
optimized, token_stats = optimize_source_content(
    raw_content, lang_hint, FilterLevel.MINIMAL
)

return {
    ...
    "content": optimized,
    "token_stats": token_stats,
}
```

---

### 5. `project_context.py` — Snapshot Export
**File:** `src/agent_guidance_mcp/project_context.py`
**Lines:** 27-85 (export_project_snapshot)

Snapshot embeds full file contents — biggest token consumer:

**Add optimization after files are collected (before writing JSON):**
```python
from .response_optimizer import optimize_snapshot_content

# After files list is built (after L62):
files = optimize_snapshot_content(files, max_total_tokens=50_000)
```

---

### 6. `server.py` — Workflow Prompt
**File:** `src/agent_guidance_mcp/server.py`
**Lines:** 146-184 (workflow_prompt)

Workflow prompts return raw markdown (often 5K+ tokens):

**Current code (L176-184):**
```python
content = catalog.read_path(workflow_references[mode_key])
# ...
return content
```

**Modified code:**
```python
from .response_optimizer import optimize_markdown, TokenBudget

content = catalog.read_path(workflow_references[mode_key])
content = optimize_markdown(content, max_tokens=TokenBudget.WORKFLOW_MAX)
# ...
return content
```

## Backward Compatibility

All changes are **additive and backward-compatible**:

1. **Same return types**: All tool signatures return the same types (`dict`, `str`, `list`)
2. **Same JSON structure**: Response dict keys are identical — only values are smaller
3. **No new parameters exposed**: Optimization is automatic and internal
4. **Opt-out possible**: `read_entry(optimize=False)` for internal use (search scoring)
5. **No new dependencies**: Everything uses stdlib (`re`, `math`, `dataclasses`)

## Performance Considerations

- **First call**: Pre-compiled regexes have a one-time compilation cost (~1ms each)
- **Per-call overhead**: <5ms for typical documents (RTK's budget: <10ms)
- **Memory**: No additional memory — all transformations are streaming/in-place
- **Caching**: `read_path()` is not cached (files may change). Optimization is applied per-read.

## Implementation Steps

1. [ ] Modify `catalog.py` — Add `optimize` parameter to `read_entry()`
2. [ ] Modify `pipelines.py:guidance()` — Optimize search results and content
3. [ ] Modify `pipelines.py:task_pipeline()` — Apply response-level optimization
4. [ ] Modify `project_context.py:read_project_file()` — Source file optimization
5. [ ] Modify `project_context.py:export_project_snapshot()` — Snapshot optimization
6. [ ] Modify `server.py:workflow_prompt()` — Workflow markdown optimization
7. [ ] Add `token_stats` to responses where applicable (non-breaking addition)
8. [ ] Update `__init__.py` to export new modules

## Files to Modify

- `src/agent_guidance_mcp/catalog.py` — **[MODIFY]** Add optimize parameter
- `src/agent_guidance_mcp/pipelines.py` — **[MODIFY]** Wrap dispatchers with optimization
- `src/agent_guidance_mcp/project_context.py` — **[MODIFY]** Source file + snapshot optimization
- `src/agent_guidance_mcp/server.py` — **[MODIFY]** Workflow prompt optimization
- `src/agent_guidance_mcp/__init__.py` — **[MODIFY]** Export new modules

## Test Criteria

- [ ] All existing tests pass without modification
- [ ] `guidance(operation="get", include_content=True)` returns optimized content
- [ ] `guidance(operation="search")` returns optimized snippets
- [ ] `task_pipeline()` response is within `TASK_PIPELINE_MAX` token budget
- [ ] `project_context(operation="read")` applies source optimization
- [ ] `project_context(operation="snapshot")` enforces file budgets
- [ ] `workflow_prompt()` returns markdown within `WORKFLOW_MAX` budget
- [ ] All resources (document, skill) return optimized content
- [ ] `read_path()` still returns raw content (for internal search use)
- [ ] Token stats are included in file-read responses

## Estimated Token Savings Per Endpoint

| Endpoint | Before (avg tokens) | After (avg tokens) | Savings |
|----------|--------------------|--------------------|---------|
| `guidance(get)` | ~4,000 | ~1,500 | -62% |
| `guidance(search)` | ~2,000 | ~1,200 | -40% |
| `task_pipeline()` | ~8,000 | ~3,000 | -62% |
| `project_context(read)` | ~3,000 | ~1,200 | -60% |
| `project_context(snapshot)` | ~50,000 | ~15,000 | -70% |
| `workflow_prompt()` | ~5,000 | ~2,500 | -50% |

---
Next Phase: [Phase 05 — Token Analytics & Config](./phase-05-token-analytics-config.md)
