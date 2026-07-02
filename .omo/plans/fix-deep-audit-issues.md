# fix-deep-audit-issues - Work Plan

## TL;DR (For humans)

**What you'll get:** All 12 deep-audit findings fixed — 1 critical (bare exception swallowing), 2 high (snapshot overwrite risk, fragile YAML parsing), 6 medium (per-search disk I/O, per-call JSON parsing, no recursion guard, inconsistent error handling), and 3 low polish items.

**Why this approach:** Fix security and correctness issues first (exception handling, path restrictions, input limits), then performance caches (content + framework), then API consistency. All independent fixes run in parallel within each wave. Tests verify every change.

**What it will NOT do:** No content caching that outlives the process. No architectural rewrites. No new dependencies.

**Effort:** Short
**Risk:** Low — 12 surgical changes, each under 15 lines, all verified by automated tests
**Decisions to sanity-check:** Content cache stored in CatalogEntry (memory tradeoff for 231 entries ~2MB). Framework cache keyed by project_path with mtime check. Snapshot restricted to .agent-context/ prefix only.

Your next move: Approve to begin execution. Full execution detail follows below.

---

> TL;DR (machine): Short effort, Low risk — 12 todos across 3 implementation waves + 1 test wave, 3 commits.

## Scope
### Must have
- Fix 5 bare `except Exception: pass` to specific exception types
- Restrict snapshot output_path to `.agent-context/` prefix
- Add task string size limit (10K chars)
- Fix parse_frontmatter BOM/whitespace/list edge cases
- Cache file contents in CatalogEntry to eliminate per-search disk I/O
- Cache framework detection results with mtime validation
- Add recursion depth guard to optimize_response (max 50 levels)
- Return consistent error dicts from project_tree and project_context read
- Make guidance() list results wrapped in dict for consistent return type
### Must NOT have
- No persistent caching (disk-based)
- No new dependencies
- No changes to search scoring algorithm
- No changes to bundled CSV data or skill content
- No breaking changes to MCP tool signatures

## Verification strategy
- Test decision: tests-after (fixes first, then verify with tests) + pytest
- Evidence: .omo/evidence/task-<N>-fix-deep-audit-issues.md
- All 28 existing tests must continue passing

## Execution strategy
### Parallel execution waves
Wave 1 (4 todos): Security — bare excepts, snapshot restrict, task limit, frontmatter fix
Wave 2 (5 todos): Perf + quality — content cache, framework cache, recursion guard, error dicts, return consistency
Wave 3 (3 todos): Test coverage for all fixes

### Dependency matrix
| Todo | Depends on | Blocks | Can parallelize with |
| --- | --- | --- | --- |
| 1 | none | none | 2,3,4 |
| 2 | none | none | 1,3,4 |
| 3 | none | none | 1,2,4 |
| 4 | none | none | 1,2,3 |
| 5 | none | none | 6,7,8,9 |
| 6 | none | none | 5,7,8,9 |
| 7 | none | none | 5,6,8,9 |
| 8 | none | none | 5,6,7,9 |
| 9 | none | none | 5,6,7,8 |
| 10 | 1,2,3,4,5,6,7,8,9 | none | 11,12 |
| 11 | 1,2,3,4,5,6,7,8,9 | none | 10,12 |
| 12 | 1,2,3,4,5,6,7,8,9 | none | 10,11 |

## Todos

### Wave 1 — Security Fixes (parallel, 4 todos)

- [ ] 1. Replace 5 bare `except Exception: pass` with specific exception types
  What to do: In `pipelines.py`, `_detect_frameworks()` function (lines 286, 296, 301, 332, 344), replace all `except Exception: pass` with `except (OSError, json.JSONDecodeError, UnicodeDecodeError): pass`. The JS section (line 249-286) already uses `except Exception: pass` on the `json.load` — change that to `except (OSError, json.JSONDecodeError): pass`.
  MUST DO: Catch only I/O and parse errors. Import `json` module for `JSONDecodeError` (already imported at top of pipelines.py line 239 as `import json`). Keep the `pass` body — framework detection is best-effort and should never crash the pipeline.
  MUST NOT DO: Do not add logging inside the except blocks. Do not change the detection logic. Do not catch `KeyboardInterrupt` or `SystemExit`.
  References: src/agent_guidance_mcp/pipelines.py:286, 296, 301, 332, 344
  Acceptance criteria: Run existing tests — all pass. Manually verify with a corrupted package.json — function doesn't crash, just returns empty frameworks list.
  QA: Happy: normal project detection unchanged. Failure: permission-denied package.json silently skipped. Evidence: .omo/evidence/task-1-fix-deep-audit-issues.md
  Commit: Y | fix(pipelines): replace bare except:pass with specific exception types

- [ ] 2. Restrict snapshot output_path to `.agent-context/` prefix
  What to do: In `project_context.py`, `export_project_snapshot()` line 46-47, after `output = resolve_inside_project(root, output_path)`, add a check: if the resolved output path's relative path doesn't start with `.agent-context/`, raise `ValueError("output_path must be within .agent-context/ directory")`. Update docstring and `docs/project-context-tools.md` to reflect this restriction. Update the tool description in server.py line 157.
  MUST DO: Validate the path BEFORE writing. Allow any subpath under `.agent-context/` (e.g., `.agent-context/custom-name.json`). Keep the default as `.agent-context/code-snapshot.json`.
  MUST NOT DO: Do not remove the `resolve_inside_project` path escape check. Do not change the default path. Do not break existing snapshot behavior for the default path.
  References: src/agent_guidance_mcp/project_context.py:44-48, src/agent_guidance_mcp/server.py:157
  Acceptance criteria: Call with output_path=".agent-context/test.json" → works. Call with output_path="src/main.py" → raises ValueError. Default path unchanged. Existing snapshot test passes.
  QA: Happy: default path works, custom .agent-context/ path works. Failure: non-.agent-context path rejected. Evidence: .omo/evidence/task-2-fix-deep-audit-issues.md
  Commit: Y | fix(project_context): restrict snapshot output to .agent-context/ directory

- [ ] 3. Add task string size limit (10K chars)
  What to do: In `pipelines.py`, `task_pipeline()` function, add at the top: `task = task[:10000]`. This silently truncates overly long task descriptions to 10,000 characters. Also add the limit documentation in the tool's docstring in server.py line 107.
  MUST DO: Truncate at the character level (not token level). Use Python slice. Do NOT raise an error — truncate silently so the pipeline still works.
  MUST NOT DO: Do not change the task parameter type. Do not apply this limit to other string parameters.
  References: src/agent_guidance_mcp/pipelines.py:349, src/agent_guidance_mcp/server.py:107
  Acceptance criteria: Call task_pipeline with task="x" * 20000 → task is truncated to 10000 chars, pipeline executes normally. Call with normal task → unchanged.
  QA: Happy: normal tasks unchanged. Failure: 100MB task doesn't OOM. Evidence: .omo/evidence/task-3-fix-deep-audit-issues.md
  Commit: Y | fix(pipelines): truncate task string to 10K chars to prevent resource exhaustion

- [ ] 4. Fix `parse_frontmatter` for BOM, trailing whitespace, and quoted list items
  What to do: In `text.py`, `parse_frontmatter()`:
  1. Line 219: Change `in_frontmatter = lines[:1] == ["---"]` to `in_frontmatter = bool(lines) and lines[0].strip() == "---"`
  2. Line 223: Change `if line == "---":` to `if line.strip() == "---":`
  3. Lines 229-231: Replace the naive list parsing with a simple JSON-compatible fallback: strip brackets, then split by comma, but handle the case where the value is already a valid JSON array by trying `json.loads(val)` first, falling back to the split approach.
  MUST DO: Import `json` at top of text.py if not already present. Use `try: json.loads(val) except (json.JSONDecodeError, ValueError):` for the fallback path.
  MUST NOT DO: Do not add a full YAML parser dependency. Do not change the output format of the function.
  References: src/agent_guidance_mcp/text.py:217-234
  Acceptance criteria: parse_frontmatter("---\nkey: [\"a, b\", \"c\"]\n---") → data["key"] == ["a, b", "c"]. parse_frontmatter("\ufeff---\nkey: val\n---") → correctly detects frontmatter. parse_frontmatter("--- \nkey: val\n---") → correctly detects frontmatter (trailing space on opener). Existing catalog tests pass.
  QA: Happy: normal frontmatter unchanged. Failure: BOM file, trailing space, quoted list values all handled. Evidence: .omo/evidence/task-4-fix-deep-audit-issues.md
  Commit: Y | fix(text): handle BOM, trailing whitespace, and quoted lists in frontmatter parsing

### Wave 2 — Perf + Quality (parallel, 5 todos)

- [ ] 5. Cache file contents in CatalogEntry to eliminate per-search disk I/O
  What to do: In `catalog.py`, add a `_content: str | None = None` field to `CatalogEntry` (non-frozen since it's internal). In `StandardsCatalog.read_path`, after reading from disk, cache the result in the entry's `_content` field. In `search_entries`, instead of calling `self.read_path(entry.path)` repeatedly, check `entry._content` first and fall back to `self.read_path(entry.path)` on cache miss. Also update `read_entry` to use the cache.
  MUST DO: Make `CatalogEntry` non-frozen by removing `frozen=True` from the dataclass decorator (or use `object.__setattr__` to set `_content`). The `_content` field should have `compare=False, repr=False`. Use `field(default=None, compare=False, repr=False)` for `_content`.
  MUST NOT DO: Do not persist the cache to disk. Do not invalidate on config change (content is raw text).
  References: src/agent_guidance_mcp/catalog.py:33-63 (CatalogEntry), catalog.py:136-138 (read_path), catalog.py:159-196 (search_entries)
  Acceptance criteria: Build catalog, search for a term, search again for same term — second call reads from cache. Run existing tests — all pass. Catalog entry_count unchanged.
  QA: Happy: search results identical with and without cache. Cache hit: no disk I/O on repeat search. Evidence: .omo/evidence/task-5-fix-deep-audit-issues.md
  Commit: Y | perf(catalog): cache file contents in CatalogEntry to avoid repeated disk reads

- [ ] 6. Cache framework detection results with mtime check
  What to do: In `pipelines.py`, `_detect_frameworks()` function, add module-level cache: `_FRAMEWORK_CACHE: dict[str, tuple[float, list[str]]] = {}` mapping `str(project_path.resolve()) -> (mtime, [tags])`. Before scanning, check cache using the package.json mtime (or pyproject.toml if no package.json). If mtime matches, return cached result. Clear the cache on each new `task_pipeline` call with a different project_path.
  MUST DO: Use `base_path / "package.json"` mtime as the cache key timestamp (fallback to `base_path.stat().st_mtime` if no package.json). Use `resolve_project_root` to get the canonical path. Keep cache size bounded — simple LRU-like: if more than 10 entries, clear oldest half.
  MUST NOT DO: Do not cache across process restarts. Do not over-complicate — a simple dict with mtime is sufficient.
  References: src/agent_guidance_mcp/pipelines.py:249-347 (_detect_frameworks function), pipelines.py:349-423 (task_pipeline calling it)
  Acceptance criteria: Call task_pipeline twice with same project_path, no file changes → second call uses cache. Modify package.json mtime → cache invalidated, re-detection runs. Different project_paths get separate cache entries.
  QA: Happy: cache hit on repeated calls, cache miss on file change. Memory: bounded at 10 entries. Evidence: .omo/evidence/task-6-fix-deep-audit-issues.md
  Commit: Y | perf(pipelines): cache framework detection results with mtime validation

- [ ] 7. Add recursion depth guard to `optimize_response`
  What to do: In `response_optimizer.py`, `optimize_response()` function, add a `_depth: int = 0` parameter. At function entry, check `if _depth > 50: return str(response)[:500]`. On recursive calls to itself (for nested dicts and list items), pass `_depth=_depth + 1`. This prevents infinite recursion on deeply nested or circular structures.
  MUST DO: Add the parameter with default 0 so existing callers are unaffected. Use a reasonable limit of 50 levels. Return a truncated string representation on overflow. Update the internal recursive calls on lines 170 and 173.
  MUST NOT DO: Do not change the function signature for external callers. Do not use `sys.setrecursionlimit`.
  References: src/agent_guidance_mcp/response_optimizer.py:151-180
  Acceptance criteria: Create a deeply nested dict (100 levels). Call optimize_response → returns without RecursionError. Normal responses still optimized correctly. Existing tests pass.
  QA: Happy: normal optimization unchanged. Failure: deep nesting returns truncated string, no crash. Evidence: .omo/evidence/task-7-fix-deep-audit-issues.md
  Commit: Y | fix(response_optimizer): add recursion depth guard to prevent stack overflow

- [ ] 8. Return error dict from project_tree on non-existent directory
  What to do: In `project_context.py`, `get_project_tree()` and in `pipelines.py`, the `project_context()` dispatcher for operation="tree". In `project_scan.py`, `resolve_project_root()` raises `NotADirectoryError`. Wrap the call in `get_project_tree` with try/except `(NotADirectoryError, FileNotFoundError)` and return `{"error": str(e), "project_path": project_path}` instead. Same for `search_project_code` and `read_project_file` which also call `resolve_project_root`.
  MUST DO: Catch `NotADirectoryError` and `FileNotFoundError`. Return a dict with "error" key. This makes the API consistent with other tools that return error dicts.
  MUST NOT DO: Do not catch other exception types. Do not change the return type annotation (dict is still correct).
  References: src/agent_guidance_mcp/project_scan.py:131-137, src/agent_guidance_mcp/project_context.py:107-112, src/agent_guidance_mcp/pipelines.py:140-143
  Acceptance criteria: Call get_project_tree("/nonexistent/path") → returns {"error": "...", "project_path": "/nonexistent/path"}. Does not raise. Valid paths still work. Run tests — pass.
  QA: Happy: valid project tree unchanged. Failure: missing directory returns error dict. Evidence: .omo/evidence/task-8-fix-deep-audit-issues.md
  Commit: Y | fix(project_context): return error dict instead of crashing on missing directory

- [ ] 9. Make `guidance()` list results wrapped in dict for consistent return type
  What to do: In `pipelines.py`, `guidance()` function line 58: `return catalog.list_entries(...)`. Wrap this in a dict: `return {"operation": "list", "entries": catalog.list_entries(category=category, kind=kind)}`. Update the function's return type annotation from `dict[str, object] | list[dict[str, object]]` to just `dict[str, object]`. Update server.py tool description docstring accordingly.
  MUST DO: Add "operation" key matching the operation name. Use "entries" as the key for the list. Check for any client code or tests that depend on list return type — update them.
  MUST NOT DO: Do not change the list content format. Do not change other operation return formats.
  References: src/agent_guidance_mcp/pipelines.py:50, 58, src/agent_guidance_mcp/server.py:131
  Acceptance criteria: Call guidance(operation="list") → returns dict with "operation" and "entries" keys. entries is a list. Existing pipeline tests that check list results must be updated — test_guidance_list should check result["entries"] instead of result directly. All 28 tests pass after update.
  QA: Happy: wrapped dict returned. Failure: N/A (pure refactor). Evidence: .omo/evidence/task-9-fix-deep-audit-issues.md
  Commit: Y | refactor(pipelines): wrap guidance list results in dict for consistent return type

### Wave 3 — Tests (parallel, 3 todos)

- [ ] 10. Add tests for security fixes (tasks 1-4)
  What to do: Add tests to existing test files:
  - test_pipelines.py: test_framework_detection_handles_corrupt_files — create tmp_path with unreadable package.json (chmod 000 if possible, or binary content), call _detect_frameworks via task_pipeline, assert no crash, frameworks list is empty
  - test_pipelines.py: test_task_pipeline_truncates_long_task — call with 20K char task, assert pipeline succeeds, task is truncated
  - test_catalog.py or new: test_parse_frontmatter_bom — call parse_frontmatter with BOM-prefixed content, assert correct parsing
  - test_parse_frontmatter_quoted_list — test list with quoted commas
  - test_parse_frontmatter_trailing_space — test "--- " opener
  MUST DO: Import parse_frontmatter from agent_guidance_mcp.text. Use tmp_path for file-based tests. Run all tests after.
  MUST NOT DO: Do not modify existing test assertions beyond what's needed.
  Acceptance criteria: pytest tests/ -v — new tests pass, all 28 existing tests pass.
  QA: Happy: new tests catch regressions. Evidence: .omo/evidence/task-10-fix-deep-audit-issues.md
  Commit: Y | test: add tests for security fixes (exception handling, truncation, frontmatter)

- [ ] 11. Add tests for performance + quality fixes (tasks 5-9)
  What to do: Add tests:
  - test_catalog.py: test_search_uses_content_cache — build catalog, search once, monkeypatch read_path to track calls, search again, assert read_path not called (cache hit)
  - test_pipelines.py: test_framework_detection_cache — create project with package.json, call task_pipeline twice, second call should use cache (verify with monkeypatch on file reads)
  - test_token.py: test_optimize_response_depth_guard — create 100-level nested dict, assert no RecursionError, result is truncated string
  - test_project_context.py: test_tree_missing_directory — call get_project_tree("/nonexistent"), assert returns error dict not raises
  - test_pipelines.py: test_guidance_list_returns_dict — update existing test_guidance_list to check result["entries"]
  MUST DO: Update test_guidance_list assertion to use result["entries"] (for task 9 change). All other tests must still pass.
  MUST NOT DO: Do not create new test files unless necessary — extend existing ones.
  Acceptance criteria: pytest tests/ -v — all tests pass (existing 28 + new ones).
  QA: Happy: cache tests verify no redundant I/O, depth guard prevents crash. Evidence: .omo/evidence/task-11-fix-deep-audit-issues.md
  Commit: Y | test: add tests for content cache, framework cache, recursion guard, error dicts

- [ ] 12. Add test for snapshot path restriction (task 2)
  What to do: In test_project_context.py, add test_snapshot_rejects_non_agent_context_path — create tmp_path project, call export_project_snapshot with output_path="src/main.py", assert raises ValueError with message about .agent-context/. Also add test_snapshot_accepts_agent_context_subpath — call with output_path=".agent-context/custom.json", assert succeeds.
  MUST DO: Use tmp_path fixture. Create minimal project with .agent-context/ dir. Test both rejection and acceptance paths.
  MUST NOT DO: Do not modify existing snapshot test. Do not write to actual project files.
  Acceptance criteria: Both new assertions pass alongside all existing tests.
  QA: Happy: custom .agent-context path works. Failure: non-.agent-context path rejected. Evidence: .omo/evidence/task-12-fix-deep-audit-issues.md
  Commit: Y | test: add snapshot path restriction tests

## Final verification wave
- [ ] F1. Full test suite — `python -m pytest tests/ -v` — all tests pass (28 original + new)
- [ ] F2. Catalog integrity — `build_catalog()` returns 231 entries
- [ ] F3. Content cache functional — search returns same results with cache
- [ ] F4. Framework detection — task_pipeline still detects project frameworks

## Commit strategy
3 commits:
1. `fix: harden exception handling, restrict snapshot path, limit task size, fix frontmatter parsing` (W1: T1-4)
2. `perf: cache content and framework detection, add recursion guard, consistent error handling` (W2: T5-9)
3. `test: add coverage for security, performance, and consistency fixes` (W3: T10-12)

## Success criteria
- All 12 deep-audit findings resolved
- 28 existing tests pass + new tests pass
- No bare `except Exception: pass` remaining
- Snapshot only writes to `.agent-context/`
- Per-search disk I/O eliminated via content cache
- Framework detection cached per project
- Consistent error handling across all tools
- Consistent return types for guidance operations
