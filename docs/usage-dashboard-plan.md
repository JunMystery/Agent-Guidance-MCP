# Usage Dashboard — Implementation Plan

## Overview

Persistent MCP usage tracking backed by SQLite, served via embed daemon HTTP interface, rendered as single-page dashboard HTML. Tracks tool calls, skill loads, embed queries, token savings — per session, per client.

---

## 1. Backend: `src/agent_guidance_mcp/usage.py`

**Status: DONE** (v1 created, needs v2 schema update)

### Schema (v2)

```sql
CREATE TABLE sessions (
    session_id      TEXT PRIMARY KEY,
    client_name     TEXT,               -- "Claude Code", "OpenCode", etc.
    session_label   TEXT,               -- first task_pipeline task or --session-label
    started_at      INTEGER NOT NULL,
    ended_at        INTEGER,
    project_path    TEXT NOT NULL,
    tool_call_count INTEGER DEFAULT 0,
    total_tokens_original INTEGER DEFAULT 0,
    total_tokens_optimized INTEGER DEFAULT 0,
    total_skills_loaded INTEGER DEFAULT 0,
    total_embed_queries INTEGER DEFAULT 0
);

CREATE TABLE tool_calls (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id      TEXT NOT NULL,
    tool_name       TEXT NOT NULL,
    operation       TEXT,
    started_at      INTEGER NOT NULL,
    duration_ms     INTEGER DEFAULT 0,
    tokens_original INTEGER,
    tokens_optimized INTEGER
);

CREATE TABLE skill_loads (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id      TEXT NOT NULL,
    skill_id        TEXT NOT NULL,
    query           TEXT,
    search_term     TEXT,
    embed_used      INTEGER DEFAULT 0,
    loaded_at       INTEGER NOT NULL
);

CREATE TABLE embed_queries (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id      TEXT NOT NULL,
    query_text      TEXT NOT NULL,
    prefix_type     TEXT,
    model_name      TEXT,
    vector_dim      INTEGER,
    duration_ms     INTEGER DEFAULT 0,
    result_count    INTEGER DEFAULT 0,
    queried_at      INTEGER NOT NULL
);
```

### API: `UsageTracker`

| Method | Description |
|--------|-------------|
| `__init__(project_root)` | Init SQLite DB, start background flusher thread |
| `session_start(client_name=None, session_label=None)` | Insert new session row. Returns session_id |
| `session_end()` | Mark current session ended, aggregate totals |
| `update_session_label(session_id, label)` | Set label (called after first task_pipeline) |
| `record_tool_call(tool_name, operation, duration_ms, tokens_original, tokens_optimized)` | Append one tool call |
| `record_skill_load(skill_id, query, search_term, embed_used)` | Append one skill load |
| `record_embed_query(query_text, prefix_type, model_name, vector_dim, duration_ms, result_count)` | Append one embed query |
| `summary(scope="session", session_id=None)` | Return aggregated stats dict |
| `close()` | Flush + close DB |

### `summary()` output shape

```python
{
    "scope": "session" | "all",
    "session_id": "abc..." or None,
    "session": { ... single session row ... },  # only if scope=session
    "sessions": [ {session rows}, ... ],        # only if scope=all
    "totals": {
        "tool_calls": int,
        "skills_loaded": int,
        "embed_queries": int,
        "tokens_original": int,
        "tokens_optimized": int,
        "token_savings": int,
        "savings_pct": float,
    },
    "tool_breakdown": [
        {"tool_name": str, "operation": str, "cnt": int,
         "tok_orig": int, "tok_opt": int},
    ],
    "top_skills": [ {"skill_id": str, "cnt": int}, ... ],
}
```

**When `session_id` param passed to summary():** filter tool_breakdown and top_skills to that session only.
**When `scope="all"`:** return `sessions` list + lifetime totals.

### Background flusher

- Queue-based, daemon thread, drains every 2s or on shutdown
- Batch-commits up to 100 items per cycle
- `_flush_now()` blocks on join before reads

---

## 2. Wiring: `src/agent_guidance_mcp/server.py`

**Status: DONE** (basic wiring, needs client_name + session_label)

### Globals

```python
_global_usage: UsageTracker | None = None
```

### New functions

| Function | Purpose |
|----------|---------|
| `get_usage()` | Return global UsageTracker |
| `set_usage(usage)` | Set global UsageTracker |
| `_now_ms()` | Monotonic time helper |
| `_track_usage(tool_name, operation, t0)` | Record tool call with duration |

### `create_server()` changes

```python
# After catalog build, before MCP creation
_global_usage = UsageTracker(project_root)
client_name = os.environ.get("AGENT_CLIENT_NAME", None)
_global_usage.session_start(client_name=client_name)

import atexit
atexit.register(_close_usage)
```

### Tool handlers — all wired

| Tool | Tracking |
|------|----------|
| `agent-guidance-mcp_task_pipeline()` | `_track_usage("task_pipeline", "run")` + `usage.update_session_label(sid, task)` |
| `agent-guidance-mcp_guidance()` | `_track_usage("guidance", operation)` + `usage.record_skill_load()` on `get` |
| `agent-guidance-mcp_project_context()` | `_track_usage("project_context", operation)` |
| `agent-guidance-mcp_ui_ux()` | `_track_usage("ui_ux", operation)` |
| `agent-guidance-mcp_session_continuity()` | `_track_usage("session_continuity", operation)` |
| `agent-guidance-mcp_guidance(operation="workflow")` | `usage.record_tool_call("guidance", "workflow")` |
| `standards://skill/{name}` resource | `usage.record_skill_load(name)` |

### New MCP tool: `agent-guidance-mcp_usage_report()`

```python
@mcp.tool()
def usage_report(scope: str = "session", session_id: str | None = None) -> dict:
```

---

## 3. Embed Daemon HTTP API: `src/agent_guidance_mcp/embed_daemon.py`

**Status: DONE** (basic route, needs session_id filter)

### Endpoints

| Route | Method | Params | Returns |
|-------|--------|--------|---------|
| `/api/stats` | GET | `project_path`, `session_id` | Aggregated stats dict |
| `/health` | GET | none | `{status, model_loaded, clients}` |

### Implementation

```python
@app.get("/api/stats")
def stats(project_path: str | None = None, session_id: str | None = None) -> dict:
    # Read usage.db at project_path
    tracker = UsageTracker(project_path)
    try:
        return tracker.summary(scope="all" if not session_id else "session",
                               session_id=session_id)
    finally:
        tracker.close()
```

---

## 4. Session Identity

### Identity chain (priority order)

| Priority | Source | Example |
|----------|--------|---------|
| 1 | `--client-name` CLI flag | `agent-guidance-mcp --client-name "Claude Code"` |
| 2 | `AGENT_CLIENT_NAME` env var | Set by hook or shell |
| 3 | Auto-detect | `TERM_PROGRAM`, `VSCODE_INJECTION`, `OPENCODE_VERSION` |

### session_label population

| Source | How |
|--------|-----|
| `--session-label` flag | Explicit |
| `agent-guidance-mcp_task_pipeline(task)` first call | Auto-capture via `update_session_label(sid, task)` |
| Fallback | `client_name + formatted timestamp` |

### Display format

```
Client Name - "Session Label" (3h ago) [active]
Client Name - "Session Label" (yesterday)
```

---

## 5. HTML Dashboard: `~/.agent-guidance/dashboard/index.html`

**Status: TODO**

### Layout

```
┌──────────────────┬──────────────────────────────────────────────┐
│ SIDEBAR          │ MAIN VIEW                                    │
│ ───────          │                                              │
│ ○ Dashboard      │  ┌─ Session Selector ───────────────────┐   │
│ ○ Actions Log    │  │ ▼ Claude Code - "Add JWT"  (active)  │   │
│ ○ Token Savings  │  │   OpenCode - "Fix DB"     (2h ago)   │   │
│ ○ Embed Status   │  │   Cursor - Jul 12         (3d ago)   │   │
│ ○ Quick Guides   │  └──────────────────────────────────────┘   │
│ ○ MCP Tools      │                                              │
│                  │  [Content selected session]                  │
│ ──────────       │  No selection: master list all sessions      │
│ project: /foo    │                                              │
│ port: 54732      │                                              │
└──────────────────┴──────────────────────────────────────────────┘
```

### Sections (sidebar → view)

| Sidebar Item | Main View Content |
|-------------|-------------------|
| Dashboard | Session summary card, top 5 tools, embed status badge, quick stats row |
| Actions Log | Table: timestamp, tool, operation, duration, tokens, savings %. Poll every 5s |
| Token Savings | Per-session bar chart + lifetime cumulative. Orig vs optimized breakdown |
| Embed Status | Model loaded, active clients, total embed queries count |
| Quick Guides | 4-step workflow cards (task_pipeline → guidance → project_context → tools) |
| MCP Tools | Table: tool name, gate status, description, operations |

### Tech choices

- Single file: `index.html`
- Zero dependencies (no React, build step, CDN)
- CSS: System font stack, CSS grid/flexbox, `prefers-color-scheme` dark/light
- JS: Vanilla, `fetch()` polling `/api/stats` every 5s + `/health`
- Session selector: `<select>` populated from `sessions` list in `/api/stats?scope=all`
- Router: Click handler hides/shows sections via class toggle

### Data flow

```javascript
// On load
const data = await fetch(`/api/stats?project_path=${path}&scope=all`);
data.sessions.forEach(s => addOption(s.client_name, s.session_label, s.session_id));

// On session select
const detail = await fetch(`/api/stats?project_path=${path}&session_id=${id}`);
renderDashboard(detail);
renderActions(detail);
renderTokens(detail);

// Embed status (separate call)
const health = await fetch(`http://127.0.0.1:${port}/health`);
renderEmbedStatus(health);

// Poll every 5s (if session selected)
setInterval(async () => {
  const data = await fetch(`/api/stats?project_path=${path}&session_id=${id}`);
  updateActionsLive(data.tool_breakdown);
}, 5000);
```

---

## 6. CLI Flag Changes: `src/agent_guidance_mcp/__main__.py`

**Status: TODO**

| Flag | Type | Purpose |
|------|------|---------|
| `--client-name` | `str` | Human-readable client/IDE name |
| `--session-label` | `str` | Human-readable session label |

### Hook scripts update

- `hooks/session-start.sh`: Set `AGENT_CLIENT_NAME` based on calling context
- `hooks/session-start-test.sh`: Same

---

## 7. File Summary

| File | Action | Priority |
|------|--------|----------|
| `src/agent_guidance_mcp/usage.py` | Update schema v2, add `client_name`/`session_label`, `update_session_label()`, `summary(session_id)` filter | HIGH |
| `src/agent_guidance_mcp/server.py` | Pass `client_name` to `session_start()`, auto-label from `agent-guidance-mcp_task_pipeline` | HIGH |
| `src/agent_guidance_mcp/embed_daemon.py` | Accept `session_id` param, return `sessions` list | HIGH |
| `src/agent_guidance_mcp/__main__.py` | Add `--client-name`, `--session-label` flags | MED |
| `~/.agent-guidance/dashboard/index.html` | Create dashboard (sidebar + 6 views) | HIGH |
| `hooks/session-start.sh` | Set `AGENT_CLIENT_NAME` | MED |
| `src/agent_guidance_mcp/__init__.py` | No changes needed | - |
| `tests/test_*.py` | No changes needed | - |

---

## Migration from v1 schema

```python
# usage.py _init_db()
if current_version < 2:
    cur.execute("ALTER TABLE sessions ADD COLUMN client_name TEXT")
    cur.execute("ALTER TABLE sessions ADD COLUMN session_label TEXT")
    cur.execute("INSERT INTO schema_version (version, applied_at) VALUES (2, ?)",
                (int(time.time()),))
```

---

## Appendix A: Upgrades from Project Planning Skills

Three project-planning skills reviewed against plan. Below: gaps found + proposed upgrades.

### A.1 Blueprint Skill ("Construction Plan Generator")

| Gap | Upgrade |
|-----|---------|
| No rollback strategy | Add `usage.py` v2 → v1 downgrade script. If dashboard breaks on v2 schema, rollback restores production |
| No error recovery flow | Add handling for: corrupt `usage.db`, flusher thread crash (restart), concurrent writes from 2 MCP servers same project |
| No step handoff context | Each step below gets a context brief: "copy this block, give to fresh agent, they can execute cold" |
| No adversarial review gate | Each milestone gets a review step before "DONE". Reviewer checks: schema matches docs, no data loss, tests pass |
| No risk register | Document risks and mitigations: `project_path` not writable → fallback to `~/.agent-guidance/usage.db`. Daemon port conflict → auto-retry with port+1. DB locked → busy_timeout=5000 |

### A.2 Planning & Task Breakdown Skill

| Gap | Upgrade |
|-----|---------|
| No parallel lanes identified | `usage.py` v2 migration **parallel** with dashboard HTML skeleton. Backend + frontend can be built same time if schema contract frozen |
| No acceptance criteria per task | Each task below gets explicit "Done when" clause |
| No dependency graph | `embed_daemon.py` `/api/stats` blocks HTML until API returns `sessions` list. `usage.py` v2 blocks everything else. Rest is parallel |
| No sizing estimates | Estimated LOC per file added below. Flags `index.html` as risk (250+ lines) |

### A.3 Code Review & Quality Skill

| Gap | Upgrade |
|-----|---------|
| No security review | `usage.py` stores raw `query_text` and `search_term` from user input — SQL injection risk via skill name? Mitigation: `sqlite3` param queries (already done), no raw string interpolation |
| No performance budget | Background flusher thread per `UsageTracker` instance. If 2 MCP servers point same project → 2 flushers, 2 write queues, no corruption (WAL) but overhead. Document this limit |
| No maintainability gate | `usage.py` at ~253 LOC. v2 + `update_session_label` + `summary(session_id)` filter pushes to ~320. Still under 400. Re-assess if >400 |
| No concurrency audit | Current: 1 Queue + 1 flusher + 1 Connection sharing via SQLite WAL. Safe. If concurrent `summary()` reads while flusher writes: `_flush_now()` ensures consistency. Document this in code comment |
| No testgap analysis | `usage.py` has zero tests. Plan must include: `tests/test_usage.py` with schema creation, session lifecycle, tool call recording, aggregation, persistence, concurrent read/write |

---

## Appendix B: Revised Task Breakdown (with Acceptance Criteria)

### Phase 1: Schema v2 + session identity (HIGH)

**Parallel: B1 + B2**

#### B1. `usage.py` schema v2 migration

- Context: `docs/usage-dashboard-plan.md` §1, §4. Edit `usage.py` `_init_db()`. Add v2 migration block. Add `client_name`, `session_label` columns. Add `update_session_label(session_id, label)` method. Update `session_start(client_name=None, session_label=None)` signature. Update `summary()` to accept `session_id` filter and return `sessions` list.
- **Done when**: `summary(scope="all")["sessions"]` returns list with `client_name`, `session_label`, `duration_seconds`. Old sessions get NULL client_name (shown as "unknown").
- Est: ~50 LOC

#### B2. `server.py` client_name + auto-label

- Context: `docs/usage-dashboard-plan.md` §2. In `create_server()`, read `AGENT_CLIENT_NAME` env and pass to `session_start()`. In `agent-guidance-mcp_task_pipeline()` handler, after first call call `usage.update_session_label(sid, task)`.
- **Done when**: `agent-guidance-mcp_usage_report()` shows `client_name` from env, `session_label` = first `agent-guidance-mcp_task_pipeline` task string.
- Est: ~15 LOC

### Phase 2: API + Dashboard (HIGH)

**Blocked on: Phase 1 complete (schema contract frozen)**

#### C1. `embed_daemon.py` `/api/stats` enhanced

- Context: `docs/usage-dashboard-plan.md` §3. Accept `session_id` query param. When present, call `tracker.summary(session_id=session_id)`. When absent, return `scope="all"` with `sessions` list.
- **Done when**: `GET /api/stats?project_path=...&session_id=abc` returns single-session detail. `GET /api/stats?project_path=...` returns `sessions` array.
- Est: ~10 LOC

#### C2. Dashboard HTML

- Context: `docs/usage-dashboard-plan.md` §5. Single file at `~/.agent-guidance/dashboard/index.html`. Sidebar + 6 views. Session selector dropdown populated from `/api/stats`. Vanilla JS, no deps.
- **Done when**: Opens in browser without errors. Clicking session selector refreshes all views. `/health` status shown. Actions table polls every 5s. Dark/light mode works.
- Est: ~300 LOC — highest risk, split into sections

### Phase 3: CLI + Hooks (MED)

**Parallel: D1 + D2**

#### D1. `__main__.py` flags

- Context: `docs/usage-dashboard-plan.md` §6. Add `--client-name` and `--session-label` arguments. Pass through to `create_server()`.
- **Done when**: `agent-guidance-mcp --client-name "Claude Code"` stores that name in `sessions.client_name`.
- Est: ~10 LOC

#### D2. `hooks/session-start.sh` update

- Context: Detect calling IDE context. Set `AGENT_CLIENT_NAME` before `--session-start` call.
- **Done when**: `AGENT_CLIENT_NAME` is set to "Cursor" / "Claude Code" / "OpenCode" when hook fires.
- Est: ~5 LOC

### Phase 4: Testing (MED)

**Blocked on: Phase 1 + 2 complete**

#### E1. `tests/test_usage.py`

- Test: schema creation, session start/end lifecycle, tool call recording, skill load recording, embed query recording, aggregation (session + all), persistence (close + reopen), concurrent read/write.
- **Done when**: All tests pass, coverage >90% for `usage.py`.
- Est: ~120 LOC

#### E2. `tests/test_dashboard.py` (optional)

- Test: `/api/stats` endpoint returns valid JSON with expected shape. Use `TestClient` from FastAPI.
- **Done when**: embed_daemon's stats endpoint responds 200 with valid schema.
- Est: ~40 LOC

### Phase 5: Review

#### F1. Adversarial review

- Run `code-review-and-quality` skill against all changed files. Verify: no SQL injection, no data loss on migration, no thread safety holes, dashboard works without daemon running.
- **Done when**: Review passes all axes.
- Est: review session

---

## Appendix C: Risk Register

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|------------|
| Corrupt `usage.db` | Low | Lose usage history | WAL mode prevents corruption. `PRAGMA integrity_check` on startup optional |
| 2 MCP servers same project_path | Medium | Double session records, 2 flushers | Sessions keyed by UUID, no conflict. Overhead: 2 bg threads. Acceptable |
| Daemon port conflict | Low | Daemon fails to start | Auto-bind port 0 (already implemented). OS assigns free port |
| `project_path` not writable | Low | Can't create `.agent-context/` | `session_start()` catches `OSError`. No crash, just no tracking |
| Memory from unbounded queue | Low | Queue full, producer blocks | `_MAX_QUEUE_SIZE = 5000`, producer blocks not drops (backpressure). 5000 records ~2MB RAM |
| Dashboard fetches wrong port | Medium | Blank page | Read `~/.agent-guidance/daemon.json` for port, not hardcoded. Show explicit error if file missing |

---

## Appendix D: Additional Upgrades (Round 2)

From deeper read of Blueprint, Planning-and-Task-Breakdown, and Strategic Compact skills.

### D.1 Cold-start context briefs per step

Each step in our plan gets a **standalone context block** so a fresh agent (or human) can execute it without reading the full plan. Pattern:

```markdown
## Step: [name]

**Context:** We're building usage tracking. Previous steps created the SQLite schema
and wrote session lifecycle code. This step: [specific thing].

**Entry state:** `usage.py` has `session_start()` and `session_end()` but no `session_label` column.

**Files you need to read before editing:**
- `src/agent_guidance_mcp/usage.py` (lines 1-253)
- `docs/usage-dashboard-plan.md` §4 (session identity design)

**Commands to verify success:**
```bash
PYTHONPATH=src python3 -c "
from agent_guidance_mcp.usage import UsageTracker
t = UsageTracker('.')
sid = t.session_start(client_name='test', session_label='cold-test')
t.update_session_label(sid, 'cold-start verify')
s = t.summary(scope='all')
assert any(s['client_name'] == 'test' for s in s['sessions'])
print('OK')
t.close()
"
```

**Exit criteria:** [list of 3-5 verifiable conditions]
```

This is already partially present in Appendix B. Round 2 upgrade: **every step in B gets a "Files to read" and "Verify" block.**

### D.2 Vertical slicing (Planning & Breakdown §3)

Current plan slices **horizontally** (all backend → all API → all HTML). Suggested **vertical slice** per deliverable:

| Horizontal (current) | Vertical (better) | Why |
|---------------------|-------------------|-----|
| Phase 1: Schema v2 | Slice 1: Full "session label" feature | Backend schema + API + HTML view = demonstrable at end of Slice 1 |
| Phase 2: API | Slice 2: session selector dropdown | Backend `sessions` list + API filter + HTML dropdown = ship |
| Phase 3: HTML all views | Slice 3-7: One view per deliverable | Each view testable, reviewable, shippable independently |

**Recommendation:** Stay horizontal (simpler for solo dev, less context-switching) but add **mini-checkpoints** after each HTML view slice.

### D.3 Anti-pattern catalog (Blueprint §4)

Blueprint ships an anti-pattern library. Checking our plan against it:

| Anti-pattern | In our plan? | Fix |
|-------------|-------------|-----|
| "One big step" | HTML at ~300 LOC | Split into sections: skeleton (sidebar + router), session selector + dashboard, actions log, remaining 4 views |
| "No rollback at all" | Rollback not designed | Add `revert_v2_schema()` to `usage.py`, document in `_init_db()` |
| "Hidden dependencies" | HTML depends on `/api/stats` | Already documented in Phase 2 blocker comment |
| "No failure mode doc" | Partially in Risk Register | Add explicit "What breaks if:" per component |
| "Tests as an afterthought" | Phase 4 | Promote test_usage.py to Phase 1.5 (blocking v2 merge) |
| "Context loss between phases" | Real risk across 5 phases | Add Strategic Compact recommendation at each Phase boundary |

### D.4 Checkpoint protocol (Planning & Breakdown §4)

After each Phase in Appendix B, add explicit checkpoint:

```markdown
## ◆ Checkpoint: Phase N complete

- [ ] `python3 -m pytest tests/ -x -q` passes
- [ ] `PYTHONPATH=src python3 -c "from agent_guidance_mcp.usage import UsageTracker; ..."` smoke test passes
- [ ] No `.agent-context/usage.db` corruption (sqlite3 integrity_check)
- [ ] git commit with message format: `phase-N: <summary>`
- [ ] Summary of decisions made this phase written to top of plan file
```

### D.5 Plan mutation protocol (Blueprint)

If during implementation we discover the plan needs to change:

1. **Log the deviation** in the plan file under a "Plan Mutations" section
2. **Assess impact:** does this change the schema contract? Block a downstream step?
3. **Update dependency graph** if edges changed
4. **Re-verify** all downstream steps' exit criteria still hold

```markdown
## Plan Mutations Log

| Date | Step | Change | Reason | Impact |
|------|------|--------|--------|--------|
| TBD | B2 | [what changed] | [why] | [which steps affected] |
```

### D.6 Strategic context preservation (Strategic Compact)

Context pressure will build across 5 phases. Add compact guidance at phase boundaries:

| Transition | Compact? | What survives | What to write first |
|-----------|----------|-------------|-------------------|
| Phase 1→2 | Yes | Schema in Git, plan file | Compact, keep plan file reference |
| Phase 2→3 | Maybe | API contract in code | Compact if >100 tool calls |
| Phase 3→4 | Yes | HTML file on disk | Compact, keep daemon.json port |
| Phase 4→5 | No | Review checklist context | Don't compact mid-review |

### D.7 Anti-pattern checklist (for F1 Adversarial Review)

From Blueprint's anti-pattern catalog, review checklist extension:

```markdown
## Anti-pattern Check (add to F1 review)

- [ ] No task >300 LOC (HTML exception at ~300, confirm no creep)
- [ ] No schema change without migration (v2 has migration)
- [ ] No hardcoded ports or paths in HTML (reads from daemon.json)
- [ ] No polling without backoff (5s is aggressive — add exponential backoff?)
- [ ] No data loss on crash (WAL mode, atomic writes — verify)
- [ ] No single point of failure (daemon dies → dashboard shows error, not hang)
- [ ] No credentials in plan file (none found)
- [ ] No implicit state (session_id stored in URL hash? localStorage? verify)
```

### D.8 Updated vertical priority ranking

Applying Blueprint's "fail fast" principle to our risk analysis:

| Slice | Risk Score | Why | Priority |
|-------|-----------|-----|----------|
| `usage.py` v2 + `summary(session_id)` | Low | Pure SQL, well-understood pattern | **1** |
| `embed_daemon.py` `/api/stats` + session_id | Low | 10 LOC, read-only | **2** |
| Dashboard skeleton (sidebar + router + fetch) | Medium | Dependency on daemon port, cross-origin? | **3** |
| Session selector dropdown | Medium | Depends on `sessions` list shape from API | **4** |
| Actions log table | High | Live polling, sort, format — most complex view | **5** |
| Token savings chart | High | Need CSS bar rendering without library | **6** |
| Remaining 4 views | Low-Med | Mostly static content | **7** |
| `__main__.py` flags | Low | Simple argparse additions | **8** |
| Hook scripts update | Low | 5 LOC | **9** |
| `test_usage.py` | Low | 120 LOC, standard pattern | **10** |


