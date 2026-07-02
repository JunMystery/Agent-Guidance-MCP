---
slug: fix-deep-audit-issues
status: awaiting-approval
intent: clear
review_required: false
pending-action: write .omo/plans/fix-deep-audit-issues.md
approach: Fix all 12 deep-audit findings across 4 waves, minimal surgical changes, verify with existing + new tests
---

# Draft: fix-deep-audit-issues

## Findings (cited)
12 findings from deep audit. Key locations:
- pipelines.py:286-345 (bare except:pass × 5)
- project_context.py:94 (snapshot overwrite risk)
- server.py:98 (unbounded task string)
- text.py:219 (fragile frontmatter parsing)
- catalog.py:171 (per-search disk I/O)
- pipelines.py:249-347 (per-call framework detection)
- response_optimizer.py:151-180 (no recursion guard)
- project_scan.py:131-137 (crash on missing dir)
- pipelines.py:50 (inconsistent return types)
- project_context.py:115-127 (raises instead of error dict)

## Decisions
1. Content cache: store content in CatalogEntry with lazy-load via `_content` field, invalidated on config change
2. Framework cache: cache by project_path with mtime check on package.json — single source of truth
3. Snapshot restriction: only allow output_path starting with `.agent-context/`
4. Return consistency: wrap list results, use error dicts for all operations
5. Keep existing test suite passing throughout

## Scope IN
All 12 deep-audit findings. 3 security, 2 code quality, 2 perf, 3 consistency, 2 edge case.

## Scope OUT
- No architectural rewrites
- No new dependencies
- No changes to bundled content or CSV data
