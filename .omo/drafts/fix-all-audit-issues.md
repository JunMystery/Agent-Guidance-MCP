---
slug: fix-all-audit-issues
status: awaiting-approval
intent: clear
review_required: false
pending-action: write .omo/plans/fix-all-audit-issues.md
approach: Fix all 16 audit findings across 5 parallel waves, minimal changes, verify with existing + new tests
---

# Draft: fix-all-audit-issues

## Components (topology ledger)
| id | outcome | status | evidence path |
|---|---|---|---|
| C1 | pipel | active | .omo/evidence/task-1-*.md |
| C2 | catalog | active | .omo/evidence/task-2-*.md |
| C3 | server | active | .omo/evidence/task-3-*.md |
| C4 | response_opt | active | .omo/evidence/task-4-*.md |
| C5 | pyproject | active | .omo/evidence/task-5-*.md |
| C6 | dead-dir | active | .omo/evidence/task-6-*.md |
| C7 | skip-lists | active | .omo/evidence/task-7-*.md |
| C8 | bm25-cache | active | .omo/evidence/task-8-*.md |
| C9 | paths-root | active | .omo/evidence/task-9-*.md |
| C10 | version | active | .omo/evidence/task-10-*.md |
| C11 | limit-val | active | .omo/evidence/task-11-*.md |
| C12 | health | active | .omo/evidence/task-12-*.md |
| C13 | future-imports | active | .omo/evidence/task-13-*.md |
| C14 | analytics-cfg | active | .omo/evidence/task-14-*.md |
| C15 | csv-guard | active | .omo/evidence/task-15-*.md |
| C16 | catalog-tests | active | .omo/evidence/task-16-*.md |
| C17 | guidance-tests | active | .omo/evidence/task-17-*.md |
| C18 | pipeline-tests | active | .omo/evidence/task-18-*.md |

## Open assumptions (announced defaults)
| assumption | adopted default | rationale | reversible? |
|---|---|---|---|
| Token estimation stays chars/4 | No tiktoken integration | Adds dependency; can revisit later | Yes |
| BM25 pre-build at catalog time | Build during build_catalog() | No async perf impact at startup | Yes |
| Health tool returns simple status dict | {"status": "ok", "version": "3.4.0"} | Standard MCP convention | Yes |
| Version exposed as resource | standards://version | Consistent with existing resource URIs | Yes |
| mcp upper bound | mcp>=1.0.0,<2.0.0 | Safe range for MCP SDK 1.x | Yes |

## Findings (cited - path:lines)
All 16 findings from prior audit — see audit report for full details. Key locations:
- pipelines.py:80-98 (cycle detection)
- catalog.py:270 (make_entry crash)
- server.py:237 (workflow_prompt crash)
- response_optimizer.py:171 (type guard)
- pyproject.toml:16 (loose mcp dep)
- src/ai_agent_standards_mcp/ (dead directory)
- constants.py:4 vs project_scan.py:16 (divergent skip lists)
- ui_ux.py:321-374 (BM25 per-query rebuild)
- paths.py:20-22 (overly broad parent search)
- server.py (no version exposed)
- pipelines.py:105 (no limit bounds)
- server.py (no health tool)
- *.py (unnecessary __future__ annotations)
- token_analytics.py:62 (magic number)
- ui_ux.py:527-531 (_search_csv no try/except on file open)

## Decisions (with rationale)
1. Fix critical crashes first (Wave 1) to unblock reliable testing
2. Bundle tests at end (Wave 5) so they verify all fixes
3. Keep token estimation as chars/4 — tiktoken adds a heavy dep for marginal gain
4. Unify skip-lists into constants.py — single source of truth
5. Pre-build BM25 in StandardsCatalog — avoid per-query rebuild overhead

## Scope IN
All 16 audit findings: 3 critical, 3 high, 5 medium, 4 low severity + new test coverage

## Scope OUT (Must NOT have)
- No architectural redesigns or new features beyond the listed fixes
- No tiktoken dependency
- No FastMCP version migration (stay on current MCP SDK 1.x)
- No changes to CSV data files under skills/ui-ux-pro-max/
- No changes to bundled content (skills, agent-guidance, karpathy docs)

## Open questions
None — all decisions resolved.

## Approval gate
status: awaiting-approval
Approach: 5 waves, 18 todos, all independent within each wave. Fix crashes first, then severity-ordered, tests last. Approve to write the full plan.
