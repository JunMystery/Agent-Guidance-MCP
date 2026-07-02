# fix-all-audit-issues - Work Plan

## TL;DR (For humans)
<!-- Fill this LAST, after the detailed plan below is written, so it summarizes the REAL plan. -->
<!-- Plain English for a non-engineer: NO file paths, NO todo numbers, NO wave/agent/tool names. -->

**What you'll get:** All 16 audit issues fixed — 3 crash bugs eliminated, 3 high-severity gaps closed, 5 medium improvements applied, 4 low-severity polish items done, plus comprehensive test coverage where there was almost none before.

**Why this approach:** Fix the things that can crash the server first (dependency cycles, unreadable files, missing prompt files), then work down the severity ladder. All independent fixes run in parallel waves to maximize throughput. Tests come last so they verify every fix, not just the original code.

**What it will NOT do:** No new features beyond the listed fixes. No tiktoken dependency. No FastMCP version migration. No changes to bundled guidance content.

**Effort:** Medium
**Risk:** Low — fixes are surgical and localized, each under 10 lines changed, verified by automated tests
**Decisions to sanity-check:** The mcp upper bound pin (<2.0.0), the BM25 cache being in-memory only (not persisted), and the version string being hardcoded rather than parsed from pyproject.toml

Your next move: Approve to begin execution, or ask for changes. Full execution detail follows below.

---

> TL;DR (machine): Medium effort, Low risk — 18 todos across 5 waves: 3 critical crash fixes, 3 high-severity fixes, 4 medium improvements, 5 low polish items, 3 test batches. 5 commits planned.

## Scope
### Must have
- Fix 3 critical crash vectors (dependency cycle, catalog build, workflow prompt)
- Fix 3 high-severity gaps (type guard, mcp pin, dead code removal)
- Fix 4 medium improvements (skip lists, BM25 cache, root discovery, version resource)
- Fix 5 low polish items (limit clamping, health tool, future imports, tracker config, CSV guard)
- Add comprehensive test coverage: catalog (4 tests), pipelines (10 tests), ui_ux + tokens (10 tests)
- All existing tests continue passing
### Must NOT have (guardrails, anti-slop, scope boundaries)
- NO new features beyond the listed audit fixes
- NO new dependencies (tiktoken, etc.)
- NO changes to bundled content (skills/, agent-guidance/, karpathy/)
- NO FastMCP or MCP SDK version migration
- NO architectural redesigns or refactors beyond the specified changes
- NO changes to CSV data files under skills/ui-ux-pro-max/data/

## Verification strategy
> Zero human intervention - all verification is agent-executed.
- Test decision: tests-after (tests verify all fixes) + pytest
- Evidence: .omo/evidence/task-<N>-fix-all-audit-issues.md

## Execution strategy
### Parallel execution waves
> Target 5-8 todos per wave. Fewer than 3 (except the final) means you under-split.

Wave 1 (3 todos): Critical crash fixes — all parallel, no cross-dependencies
Wave 2 (3 todos): High-severity fixes — all parallel, no cross-dependencies
Wave 3 (4 todos): Medium-severity fixes — all parallel, no cross-dependencies
Wave 4 (5 todos): Low-severity fixes — all parallel, no cross-dependencies
Wave 5 (3 todos): Test coverage — all parallel, depends on ALL wave 1-4 fixes

### Dependency matrix
| Todo | Depends on | Blocks | Can parallelize with |
| --- | --- | --- | --- |
| 1 | none | 17 (tests verify cycle fix) | 2, 3 |
| 2 | none | 16 (tests verify error handling) | 1, 3 |
| 3 | none | 17 (tests verify prompt error handling) | 1, 2 |
| 4 | none | 18 (tests verify type guard) | 5, 6 |
| 5 | none | none | 4, 6 |
| 6 | none | none | 4, 5 |
| 7 | none | none | 8, 9, 10 |
| 8 | none | 18 (tests verify BM25 cache) | 7, 9, 10 |
| 9 | none | none | 7, 8, 10 |
| 10 | none | none | 7, 8, 9 |
| 11 | none | none | 12, 13, 14, 15 |
| 12 | none | none | 11, 13, 14, 15 |
| 13 | none | none | 11, 12, 14, 15 |
| 14 | none | 18 (tests verify configurable caps) | 11, 12, 13, 15 |
| 15 | none | 18 (tests verify CSV guard) | 11, 12, 13, 14 |
| 16 | 2 (needs error-handling logic) | none | 17, 18 |
| 17 | 1, 3 (needs cycle + prompt fixes) | none | 16, 18 |
| 18 | 4, 8, 14, 15 (needs type guard + BM25 + caps + CSV) | none | 16, 17 |

## Todos
> Implementation + Test = ONE todo. Never separate.
<!-- APPEND TASK BATCHES BELOW THIS LINE WITH edit/apply_patch - never rewrite the headers above. -->

### Wave 1 — Critical Crash Fixes (parallel, 3 todos)

- [ ] 1. Fix infinite recursion in dependency resolution — add cycle detection
  What to do: In `pipelines.py`, `guidance()` function, the `visit()` closure at line 80 recursively resolves dependencies without cycle detection. If A depends on B and B depends on A, this produces infinite recursion → stack overflow → server crash.
  MUST DO: Add a `visiting: set[str]` that tracks nodes currently in the recursion stack. Before recursing into a child, check if it's already in `visiting`. If so, add it to a `cycle_warnings: list[str]` list and skip (do not recurse). Pass this list back to the caller to include in the result dict as `"dependency_cycles_detected": cycle_warnings`. Move `resolved.add(dep_id)` BEFORE the for-loop over children so children can detect the parent as already resolved.
  MUST NOT DO: Do not change the topological ordering logic. Do not raise an exception on cycles — warn only. Do not change dependency entry format in the result.
  References: src/agent_guidance_mcp/pipelines.py:80-98 (visit closure inside guidance())
  Acceptance criteria: Write a pytest test with two skill entries where A dep→B and B dep→A. Call guidance(operation="get", identifier="a", include_content=True). Assert no RecursionError, result contains "dependency_cycles_detected" with both identifiers, result contains both A and B content.
  QA scenarios: Happy: normal dependency resolution still works. Failure: cycle A→B, B→C, C→A handled correctly. Evidence: .omo/evidence/task-1-fix-all-audit-issues.md
  Commit: Y | fix(pipelines): add cycle detection to dependency resolution

- [ ] 2. Wrap catalog `make_entry()` in try/except — prevent startup crash on unreadable files
  What to do: In `catalog.py`, `make_entry()` at line 270 calls `path.read_text(encoding="utf-8")` without error handling. If any file in the corpus (150+ skill dirs) is unreadable, `build_catalog()` crashes and the MCP server fails to start.
  MUST DO: Wrap the `content = path.read_text(...)` call in try/except (catch OSError, UnicodeDecodeError). On failure, print a warning to stderr: `print(f"Warning: skipping unreadable file {relative_path}: {e}", file=sys.stderr)` and return None (which build_catalog already handles by filtering None entries). Add `import sys` at top of catalog.py.
  MUST NOT DO: Do not silence the warning — it must go to stderr. Do not modify the entry format or parsing logic.
  References: src/agent_guidance_mcp/catalog.py:267-303 (make_entry function), catalog.py:255-264 (build_catalog filter loop)
  Acceptance criteria: Create a temp directory with a valid SKILL.md and a corrupted file (binary garbage with .md extension). Call build_catalog(temp_dir). Assert no exception, catalog contains only the valid entry, stderr contains "skipping unreadable file".
  QA scenarios: Happy: normal catalog build unchanged. Failure: permission-denied file, UTF-16 file with .md extension, empty file (still readable, should produce entry with empty content). Evidence: .omo/evidence/task-2-fix-all-audit-issues.md
  Commit: Y | fix(catalog): handle unreadable files gracefully during catalog build

- [ ] 3. Wrap `workflow_prompt` file reads in try/except
  What to do: In `server.py`, `workflow_prompt()` at line 237 calls `catalog.read_path(workflow_references[mode_key])`. If the referenced file doesn't exist (deleted, renamed, corrupted install), this raises FileNotFoundError unhandled → prompt crashes → MCP client gets an error.
  MUST DO: Wrap the `catalog.read_path()` call in try/except FileNotFoundError. On failure, return `f"Workflow prompt '{mode}' is referenced but its file could not be found. Please verify your Agent Guidance installation."`. Also extract the `workflow_references` dict (lines 209-230) into a module-level constant `WORKFLOW_MODE_MAP: dict[str, str]` in server.py (or a new constants entry in constants.py), since a 20-entry dict literal inside a handler function is harder to test and maintain.
  MUST NOT DO: Do not change the mode name → file path mapping. Do not change the subject/target append logic.
  References: src/agent_guidance_mcp/server.py:206-254 (workflow_prompt handler, especially line 237)
  Acceptance criteria: Call workflow_prompt with mode="nonexistent" — returns error string about unsupported mode. Mock catalog.read_path to raise FileNotFoundError for a valid mode key — returns graceful error string, not a crash. Existing valid modes still work.
  QA scenarios: Happy: mode="plan" returns plan prompt content. Failure: mode="nonexistent" returns supported modes list, missing file returns installation error. Evidence: .omo/evidence/task-3-fix-all-audit-issues.md
  Commit: Y | fix(server): handle missing workflow prompt files gracefully

### Wave 2 — High-Severity Fixes (parallel, 3 todos)

- [ ] 4. Add type guard to `optimize_response` for non-dict list items
  What to do: In `response_optimizer.py`, `optimize_response()` lines 171-177 process list items. If any list item is a non-dict, the `isinstance(item, dict)` check passes it through as `else item`, which is correct. But the recursive call `optimize_response(item, ...)` on line 173 assumes dict input and will fail on `dict(response)` or `response.items()` if a non-dict slips through somehow due to a type annotation violation at the call site.
  MUST DO: Add an explicit `elif isinstance(item, (str, int, float, bool, type(None))): result_item = item` branch, with a final `else: result_item = str(item)` fallback. This makes the function defensive against any input shape without crashing.
  MUST NOT DO: Do not change the optimization logic for dicts, strings, descriptions, or snippets. Do not add logging — this is a defensive guard, not an expected path.
  References: src/agent_guidance_mcp/response_optimizer.py:151-180 (optimize_response function)
  Acceptance criteria: Call optimize_response({"items": [{"key": "val"}, 42, "string", None]}) — assert no TypeError, returns list with dict optimized, scalars passed through, None preserved.
  QA scenarios: Happy: existing optimization unchanged. Failure: list with mixed dict+scalar+None types doesn't crash. Evidence: .omo/evidence/task-4-fix-all-audit-issues.md
  Commit: Y | fix(response_optimizer): add defensive type guard for mixed-type lists

- [ ] 5. Pin `mcp` dependency with upper bound
  What to do: In `pyproject.toml` line 16, change `"mcp>=1.0.0"` to `"mcp>=1.0.0,<2.0.0"`. The MCP Python SDK has had breaking changes between minor versions within 1.x, and an unbounded spec risks silent breakage on future releases.
  MUST DO: Only change the version constraint string. Verify `pip install -e .` still resolves correctly.
  MUST NOT DO: Do not add other dependency pins. Do not change the dev dependencies.
  References: pyproject.toml:16 (dependencies list)
  Acceptance criteria: Run `.venv/bin/pip install -e .` — succeeds. Run `.venv/bin/pip show mcp` — installed version satisfies >=1.0.0,<2.0.0.
  QA scenarios: Happy: existing install works. Failure: attempt to install mcp 2.0.0 would be rejected by pip resolver. Evidence: .omo/evidence/task-5-fix-all-audit-issues.md
  Commit: Y | fix(build): pin mcp dependency with upper bound <2.0.0

- [ ] 6. Remove dead `ai_agent_standards_mcp` directory
  What to do: Delete `src/ai_agent_standards_mcp/` directory. It contains only `__pycache__/` with no .py files. This is abandoned/renamed code that clutters the source tree.
  MUST DO: Run `rm -rf src/ai_agent_standards_mcp/`. Verify `python -m pytest tests/` still passes (no imports reference this module).
  MUST NOT DO: Do not remove any other directory. Do not modify pyproject.toml wheel config (it only packages agent_guidance_mcp, not ai_agent_standards_mcp).
  References: src/ai_agent_standards_mcp/ (dead directory)
  Acceptance criteria: `src/ai_agent_standards_mcp/` no longer exists. `python -m pytest tests/` passes. `grep -r "ai_agent_standards_mcp" src/` returns no results.
  QA scenarios: Happy: tests pass, no imports broken. Evidence: .omo/evidence/task-6-fix-all-audit-issues.md
  Commit: Y | chore: remove dead ai_agent_standards_mcp directory

### Wave 3 — Medium-Severity Fixes (parallel, 4 todos)

- [ ] 7. Unify divergent skip-lists into `constants.py`
  What to do: Two skip-lists exist: `project_scan.py:16-29` (`IGNORED_PARTS` = 11 entries) and `constants.py:4` (`SKIP_PARTS` = 5 entries). They serve different code paths but should be unified to a single source of truth. The `project_scan.py` list (11 entries) is more comprehensive.
  MUST DO: Move the comprehensive list to `constants.py` as a new constant `PROJECT_IGNORED_PARTS: frozenset[str]`. Import it in `project_scan.py`, replacing `IGNORED_PARTS`. In `paths.py:iter_content_files` line 57, use `SKIP_PARTS` for its current purpose (catalog content scanning) since catalog scanning needs fewer exclusions (it only scans known directories). Add a comment explaining why the two lists differ: `SKIP_PARTS` is for catalog content scanning (limited known paths), `PROJECT_IGNORED_PARTS` is for arbitrary project scanning (more conservative). Keep both but cross-reference them — add any missing common entries.
  MUST NOT DO: Do not merge them into one list — they serve different purposes. Do not change what files are skipped.
  References: src/agent_guidance_mcp/constants.py:4 (SKIP_PARTS), src/agent_guidance_mcp/project_scan.py:16-29 (IGNORED_PARTS), src/agent_guidance_mcp/paths.py:57 (usage of SKIP_PARTS in iter_content_files)
  Acceptance criteria: `IGNORED_PARTS` in project_scan.py imports from constants. Both lists documented. Run existing tests — tree/skip behavior unchanged.
  QA scenarios: Happy: project tree skips same items as before. Failure: new entry accidentally added to wrong list. Evidence: .omo/evidence/task-7-fix-all-audit-issues.md
  Commit: Y | refactor: unify skip-list constants with documentation

- [ ] 8. Pre-build BM25 indexes at catalog construction time
  What to do: In `ui_ux.py`, every `search_ui_ux_guidance()` call reads CSVs and rebuilds BM25 indexes from scratch — identical work on every call. Pre-build these indexes once during `build_catalog()` or lazily on first use.
  MUST DO: Add a `_BM25_CACHE: dict[str, tuple[BM25, list[dict[str, str]]]]` module-level cache in ui_ux.py. In `_search_csv()`, check the cache first using the filepath as key. If not cached, build BM25 + load rows, cache them, then search. This keeps the change localized to ui_ux.py without coupling to catalog.py. Use `frozenset` of output column names as part of cache key to handle config changes.
  MUST NOT DO: Do not change the BM25 algorithm or scoring. Do not add thread synchronization (Stdio transport is single-threaded). Do not modify catalog.py — the cache is internal to ui_ux.py.
  References: src/agent_guidance_mcp/ui_ux.py:321-374 (BM25 class), ui_ux.py:527-546 (_search_csv function), ui_ux.py:14 (DATA_RELATIVE_PATH)
  Acceptance criteria: Call search_ui_ux_guidance with same domain+query twice. Verify second call returns identical results. Verify via code inspection that CSV is only read once per domain+config combination. Add a `clear_bm25_cache()` function for testing and call it in test setup.
  QA scenarios: Happy: results identical to before cache. Performance: no user-visible change but fewer disk reads. Evidence: .omo/evidence/task-8-fix-all-audit-issues.md
  Commit: Y | perf(ui_ux): cache BM25 indexes to avoid per-query rebuild

- [ ] 9. Tighten `find_standards_root` parent search to prevent escaping intended root
  What to do: In `paths.py:20-22`, `find_standards_root()` walks `here.parents` and `parent.parent` from `__file__`. In a system-wide install, this can reach `/usr/` and pick up a coincidental match. Add a depth limit and prefer `AGENT_GUIDANCE_ROOT` env var over parent walking.
  MUST DO: Restructure `find_standards_root` to check candidates in this priority order: (1) explicit `--root` CLI arg, (2) `AGENT_GUIDANCE_ROOT` env var, (3) parent chain of `__file__` limited to 4 levels up (package → site-packages → lib → prefix, which covers editable installs and venvs), (4) parent chain of `cwd` limited to 4 levels up. Stop checking parents beyond 4 levels. Add `import os` at top if not already present (it is — line 5).
  MUST NOT DO: Do not break editable install detection (the primary use case). Do not change the `is_standards_root` check.
  References: src/agent_guidance_mcp/paths.py:13-31 (find_standards_root function)
  Acceptance criteria: In a venv with the package installed, `find_standards_root()` resolves correctly. Set AGENT_GUIDANCE_ROOT=/tmp/fake — returns that path (even if it fails `is_standards_root` — the function should return what the user specified and let callers handle the invalid root).
  QA scenarios: Happy: editable install finds bundled corpus. Failure: accidental match at filesystem root ignored. Evidence: .omo/evidence/task-9-fix-all-audit-issues.md
  Commit: Y | fix(paths): limit find_standards_root parent search depth

- [ ] 10. Expose server version via MCP resource
  What to do: Add a `standards://version` resource that returns the server version string. Currently version (3.4.0) is only in pyproject.toml and README.
  MUST DO: In `server.py`, register a new resource `@mcp.resource("standards://version", mime_type="application/json")` that returns `{"server": "agent-guidance-mcp", "version": "3.4.0", "mcp_protocol": "2024-11-05"}`. Read the version from `agent_guidance_mcp.__version__` — add `__version__ = "3.4.0"` to `__init__.py`. Document it in `docs/mcp-surface.md` under Resources table.
  MUST NOT DO: Do not parse pyproject.toml at runtime — hardcode the version as a module-level constant and keep it in sync manually (it changes rarely).
  References: src/agent_guidance_mcp/__init__.py, src/agent_guidance_mcp/server.py:74-95 (existing resource registrations), docs/mcp-surface.md:7-13 (Resources table)
  Acceptance criteria: URI `standards://version` returns JSON with version "3.4.0". docs/mcp-surface.md lists the new resource.
  QA scenarios: Happy: resource returns correct version JSON. Failure: N/A (static resource). Evidence: .omo/evidence/task-10-fix-all-audit-issues.md
  Commit: Y | feat: expose server version via standards://version resource

### Wave 4 — Low-Severity Fixes (parallel, 5 todos)

- [ ] 11. Add `limit` bounds validation to `task_pipeline` and `guidance`
  What to do: `task_pipeline` accepts `limit: int` with default 8 but no bounds checking — negative or zero values produce broken results. Same for `guidance` (default 10) and `ui_ux` (default 3). Add clamping.
  MUST DO: In `pipelines.py`, add `limit = max(1, min(limit, 100))` at the top of `task_pipeline()`, `guidance()`, `project_context()`, and `ui_ux()` functions. This clamps all limit parameters to [1, 100].
  MUST NOT DO: Do not change the default values. Do not raise exceptions — clamp silently.
  References: src/agent_guidance_mcp/pipelines.py:105 (task_pipeline limit), pipelines.py:46 (guidance limit), pipelines.py:130 (project_context limit), pipelines.py:184 (ui_ux limit)
  Acceptance criteria: Call task_pipeline with limit=-5 → clamped to 1. Call with limit=500 → clamped to 100. Call with limit=8 → unchanged. All 4 functions have the clamp.
  QA scenarios: Happy: normal limits unchanged. Failure: negative, zero, and excessive limits all clamped safely. Evidence: .omo/evidence/task-11-fix-all-audit-issues.md
  Commit: Y | fix(pipelines): clamp limit parameter to [1, 100] across all tools

- [ ] 12. Add `health`/`ping` tool
  What to do: Add a `health_check()` MCP tool that returns server status. Standard MCP convention for monitoring and diagnostics.
  MUST DO: Register `@mcp.tool() def health_check() -> dict[str, object]:` in server.py that returns `{"status": "ok", "server": "agent-guidance-mcp", "version": "3.4.0", "entries": catalog.manifest()["entry_count"]}`. This gives clients a lightweight way to verify connectivity and get basic server info. Document in docs/mcp-surface.md under Tools table.
  MUST NOT DO: Do not add complex health checks (DB, filesystem, etc.) — keep it simple. Do not expose internal metrics.
  References: src/agent_guidance_mcp/server.py:97-119 (existing tool registrations), server.py:68-70 (catalog available in create_server closure)
  Acceptance criteria: Call health_check() → returns dict with status="ok" and version. Documented in mcp-surface.md.
  QA scenarios: Happy: tool returns expected structure. Evidence: .omo/evidence/task-12-fix-all-audit-issues.md
  Commit: Y | feat: add health_check tool for server diagnostics

- [ ] 13. Remove unnecessary `from __future__ import annotations` imports
  What to do: The project requires Python 3.10+ per pyproject.toml. `from __future__ import annotations` enables PEP 604 syntax (`str | None`) for 3.9 and earlier. Since 3.10 supports this natively, the import is unnecessary. Removing it improves startup time marginally and reduces visual noise.
  MUST DO: Remove `from __future__ import annotations` from ALL .py files under `src/agent_guidance_mcp/`. Verify all type annotations still work with `str | None`, `dict[str, object]`, etc. Run existing tests. Do NOT remove from `scripts/run-mcp.py` (it might run on older Pythons).
  MUST NOT DO: Do not change any type annotations. Do not add new imports. Do not touch files outside src/agent_guidance_mcp/.
  References: All 16 files under src/agent_guidance_mcp/ that start with `from __future__ import annotations`
  Acceptance criteria: `grep -r "from __future__ import annotations" src/agent_guidance_mcp/` returns no results. `python -m pytest tests/` passes.
  QA scenarios: Happy: all existing tests pass, type annotations still valid. Evidence: .omo/evidence/task-13-fix-all-audit-issues.md
  Commit: Y | chore: remove unnecessary __future__ annotations imports (3.10+)

- [ ] 14. Make `TokenTracker` record cap configurable
  What to do: In `token_analytics.py:62`, `self._records = self._records[-500:]` uses hardcoded magic numbers (1000 max, keep 500). Make these configurable.
  MUST DO: Add `max_records: int = 1000` and `trim_to: int = 500` parameters to `TokenTracker.__init__()`. Update the trim logic to use these. Add a brief comment explaining the sliding window behavior. Update `token_config.py` to accept `tracker_max_records` and `tracker_trim_to` via env vars `AGENT_GUIDANCE_TRACKER_MAX_RECORDS` and `AGENT_GUIDANCE_TRACKER_TRIM_TO`.
  MUST NOT DO: Do not change the default behavior (1000/500). Do not change the summary output format.
  References: src/agent_guidance_mcp/token_analytics.py:26-33 (__init__), token_analytics.py:62-63 (trim logic), src/agent_guidance_mcp/token_config.py:9-56 (TokenOptimizationConfig dataclass), token_config.py:59-77 (load_config_from_env)
  Acceptance criteria: Create TokenTracker(max_records=10, trim_to=5). Call record() 15 times. Assert len(records) <= 5. Default behavior unchanged. Env var override works.
  QA scenarios: Happy: default 1000/500 unchanged. Config: custom values respected. Evidence: .omo/evidence/task-14-fix-all-audit-issues.md
  Commit: Y | refactor(token_analytics): make record cap configurable

- [ ] 15. Handle missing CSV files gracefully in `ui_ux.py`
  What to do: `_search_csv()` at line 527-546 calls `_load_csv(filepath)` which opens the file without try/except. If a CSV data file is missing (partial install, corrupted deployment), it raises FileNotFoundError unhandled → tool crashes.
  MUST DO: In `_search_csv()`, wrap the `rows = _load_csv(filepath)` call in try/except (FileNotFoundError, OSError). On failure, return `[]` (empty list). This is safe because all callers check `if not filepath.is_file(): return []` already on line 530-531, but the race condition between `is_file()` and `open()` can still trigger. Also add the guard to `_apply_reasoning()` line 671-672 which calls `_load_csv(reasoning_file)` without an `is_file()` guard.
  MUST NOT DO: Do not log warnings (the empty result is sufficient signal). Do not change the return type.
  References: src/agent_guidance_mcp/ui_ux.py:527-546 (_search_csv), ui_ux.py:549-551 (_load_csv), ui_ux.py:661-697 (_apply_reasoning)
  Acceptance criteria: Temporarily rename a CSV data file. Call search_ui_ux_guidance — returns empty results, not an exception. Call generate_ui_ux_design_system — returns default values gracefully.
  QA scenarios: Happy: existing CSV search unchanged. Failure: missing CSV returns empty results. Evidence: .omo/evidence/task-15-fix-all-audit-issues.md
  Commit: Y | fix(ui_ux): handle missing CSV files gracefully

### Wave 5 — Test Coverage (parallel, 3 todos)

- [ ] 16. Add tests for catalog building and error handling
  What to do: Test catalog construction, entry lookup, read operations, and the new error-handling behavior from Task 2.
  MUST DO: Create `tests/test_catalog.py` with: (1) test_catalog_builds_from_temp_dir — create temp dirs with skill/docs/agent-guidance structure, verify catalog.entries count, manifest entry_count, by_identifier lookup. (2) test_catalog_skips_unreadable_file — corrupted .md file skipped, stderr has warning, valid files still present. (3) test_catalog_get_entry_missing — KeyError raised with helpful message. (4) test_catalog_read_entry — returns file content. Use pytest tmp_path fixture.
  MUST NOT DO: Do not modify existing test files. Do not depend on real skills directory — use tmp_path with synthetic files.
  References: src/agent_guidance_mcp/catalog.py (full module), tests/test_project_context.py (existing test patterns to follow)
  Acceptance criteria: `python -m pytest tests/test_catalog.py -v` — all 4 tests pass.
  QA scenarios: Happy: catalog builds correctly. Failure: missing/unreadable entries handled. Evidence: .omo/evidence/task-16-fix-all-audit-issues.md
  Commit: Y | test: add catalog construction and error handling tests

- [ ] 17. Add tests for guidance(), task_pipeline(), and workflow_prompt()
  What to do: Test the MCP handler dispatch layer and the task_pipeline orchestration.
  MUST DO: Create `tests/test_pipelines.py` that builds a StandardsCatalog from tmp_path synthetic data and tests: (1) guidance list — returns entries filtered by kind/category. (2) guidance get — returns entry dict, include_content adds content field, missing identifier returns error dict. (3) guidance search — returns ranked results with snippets. (4) guidance recommend — returns recommendations with reasons. (5) guidance unsupported operation — returns error with supported_operations. (6) task_pipeline — returns recommendations + project_tree, validates structure. (7) task_pipeline with UI task — includes ui_ux key. (8) guidance dependency cycle — test from Task 1, ensure no crash, cycle warnings present. (9) workflow_prompt valid mode — returns non-empty string. (10) workflow_prompt invalid mode — returns "unsupported" string. Use monkeypatch for catalog.read_path in workflow tests.
  MUST NOT DO: Do not test ui_ux CSV data (that's covered in Task 18). Do not actually call MCP server — test the pipeline functions directly.
  References: src/agent_guidance_mcp/pipelines.py (full module), src/agent_guidance_mcp/server.py:206-254 (workflow_prompt flow)
  Acceptance criteria: `python -m pytest tests/test_pipelines.py -v` — all 10 tests pass.
  QA scenarios: Happy: all operations return expected structure. Failure: invalid ops return errors. Evidence: .omo/evidence/task-17-fix-all-audit-issues.md
  Commit: Y | test: add pipeline dispatch and workflow prompt tests

- [ ] 18. Add tests for ui_ux, response_optimizer, and token_analytics
  What to do: Test UI/UX search, token optimization pipeline, and token tracking.
  MUST DO: Create `tests/test_ui_ux.py` with: (1) test_search_ui_ux_by_domain — uses real CSV data from bundled skills, searches "minimalist design", returns results with expected keys. (2) test_search_ui_ux_by_stack — search with stack="react", returns stack results. (3) test_search_ui_ux_missing_csv — monkeypatch _load_csv to raise FileNotFoundError, returns empty results. (4) test_design_system_generation — calls generate_ui_ux_design_system, returns markdown string with expected sections. (5) test_design_system_ascii_format — output_format="ascii" returns ASCII format. Create `tests/test_token.py` with: (6) test_estimate_tokens — verify chars/4 rounding. (7) test_token_tracker_record_and_summary — record 3 events, verify summary totals. (8) test_token_tracker_disabled — record returns None. (9) test_token_tracker_custom_caps — task 14 configurable caps respected. (10) test_optimize_response_type_guard — mixed-type list from task 4 handled.
  MUST NOT DO: Do not depend on network or external services. Use real bundled CSV data for ui_ux tests (it's in the repo).
  References: src/agent_guidance_mcp/ui_ux.py, src/agent_guidance_mcp/response_optimizer.py, src/agent_guidance_mcp/token_analytics.py
  Acceptance criteria: `python -m pytest tests/test_ui_ux.py tests/test_token.py -v` — all 10 tests pass.
  QA scenarios: Happy: all functions return expected data. Failure: missing data handled. Evidence: .omo/evidence/task-18-fix-all-audit-issues.md
  Commit: Y | test: add ui_ux, token optimizer, and analytics tests

## Final verification wave
> Runs in parallel after ALL todos. ALL must APPROVE. Surface results and wait for the user's explicit okay before declaring complete.
- [ ] F1. Plan compliance audit — every todo status verified, evidence files exist, no skipped items
- [ ] F2. Full test suite — `python -m pytest tests/ -v` passes all 4 original + all new tests (expected 22+ tests total)
- [ ] F3. Catalog build from real corpus — `python -c "from agent_guidance_mcp.catalog import build_catalog; c = build_catalog(); print(c.manifest()['entry_count'])"` succeeds
- [ ] F4. Import surface check — `python -c "from agent_guidance_mcp import *"` succeeds, no dead imports
- [ ] F5. Dependency resolution with cycle — verify fix programmatically through test 17

## Commit strategy
One commit per wave (5 total), squashed from todo-level commits:
1. `fix: prevent crashes in dependency resolution, catalog build, and workflow prompts` (W1: T1-3)
2. `fix: add type guard, pin mcp dep, remove dead code` (W2: T4-6)
3. `refactor: unify skip-lists, cache BM25, tighten root discovery, expose version` (W3: T7-10)
4. `fix: clamp limits, add health tool, cleanup imports, configurable tracking, CSV guards` (W4: T11-15)
5. `test: add comprehensive test coverage for catalog, pipelines, ui_ux, and token modules` (W5: T16-18)

## Success criteria
- All 16 audit findings resolved with evidence
- Zero regression: existing 4 tests pass
- New test coverage: 22+ tests covering catalog, pipelines, ui_ux, tokens
- Server starts without crashing on corrupted/missing files
- Dependency cycles produce warnings, not stack overflows
- All tool parameters validated at boundaries
- Version and health endpoints exposed
- Dead code removed, imports cleaned
