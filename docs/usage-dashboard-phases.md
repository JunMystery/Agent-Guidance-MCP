# Usage Dashboard — Implementation Phases

**Derived from:** `docs/usage-dashboard-plan.md`  
**Status:** Draft — phases ordered by dependency + risk

---

## Phase 0: Schema v2 + session identity

**Goal:** `usage.py` has client_name + session_label columns, session_id filter in summary().  
**Files:** `src/agent_guidance_mcp/usage.py`, `src/agent_guidance_mcp/server.py`  
**Dependencies:** None  
**Est:** ~65 LOC  
**Risk:** Low — pure SQL, existing pattern

### Tasks

| # | Task | Exit criteria |
|---|------|--------------|
| 0.1 | `usage.py` _init_db() v2 migration: add `client_name`, `session_label` columns | ALTER TABLE runs, old DBs upgrade clean |
| 0.2 | `usage.py` session_start(client_name, session_label) param | Old callers without params still work |
| 0.3 | `usage.py` update_session_label(session_id, label) method | Label persists in DB, survives reopen |
| 0.4 | `usage.py` summary(scope, session_id) filter | `summary(session_id="abc")` returns single-session totals |
| 0.5 | `usage.py` summary(scope="all") returns `sessions` list | Array with client_name, label, duration per row |
| 0.6 | `server.py` create_server() reads `AGENT_CLIENT_NAME` env → session_start() | env var appears in usage_report() |
| 0.7 | `server.py` task_pipeline() calls update_session_label(sid, task) | First task_pipeline task appears as session_label |

### Verify

```bash
python3 -m pytest tests/ -x -q && \
PYTHONPATH=src python3 -c "
from agent_guidance_mcp.usage import UsageTracker
t = UsageTracker('/tmp/test-phase0')
sid = t.session_start(client_name='test-cli', session_label='test-label')
t.record_tool_call('task_pipeline', 'run', duration_ms=10)
t.update_session_label(sid, 'my task')
s = t.summary(scope='session')
assert s['session']['client_name'] == 'test-cli'
assert s['session']['session_label'] == 'my task'
assert s['totals']['tool_calls'] == 1
s2 = t.summary(scope='all')
assert len(s2['sessions']) == 1
t.close()
print('Phase 0 OK')
"
```

### Blocking next phase

Phase 1 depends on: 0.4 (summary session_id filter) + 0.5 (sessions list).

---

## Phase 1: Embed daemon API + Dashboard skeleton

**Goal:** `GET /api/stats?session_id=` works. Dashboard loads in browser with sidebar + router.  
**Files:** `src/agent_guidance_mcp/embed_daemon.py`, `~/.agent-guidance/dashboard/index.html`  
**Dependencies:** Phase 0.4, 0.5  
**Est:** ~60 LOC backend + ~100 LOC HTML skeleton  
**Risk:** Medium — HTML first JS app, no frameworks

### Tasks

| # | Task | Exit criteria |
|---|------|--------------|
| 1.1 | `embed_daemon.py` `/api/stats` accept `session_id` param | `?session_id=abc` returns single-session data |
| 1.2 | `embed_daemon.py` `/api/stats` without session_id returns `sessions` list | Dropdown can populate |
| 1.3 | Create `~/.agent-guidance/dashboard/index.html` | File exists, opens in browser |
| 1.4 | HTML sidebar with 6 nav items + click router | Click switches view, correct section shown |
| 1.5 | HTML fetch daemon.json → discover port → fetch `/api/stats` | Console shows data loaded, no CORS errors |
| 1.6 | Session selector `<select>` populated from `sessions` list | Dropdown shows client_name - label (time ago) |
| 1.7 | Dashboard view shows session summary + top 5 tools | Cards render with real data |
| 1.8 | Dark/light mode via `prefers-color-scheme` | Switch OS theme, dashboard follows |

### Key decisions

- Port discovery: `fetch('/daemon.json')` NOT hardcoded
- Fallback if daemon.json missing: show error message, not blank page
- session selector onChange → re-fetch with session_id → re-render all views

### Verify

```bash
# Start daemon, fetch stats, check HTML loads
agent-guidance-mcp --embed-daemon &
sleep 2
PORT=$(cat ~/.agent-guidance/daemon.json | python3 -c "import json,sys; print(json.load(sys.stdin)['port'])")
curl -s "http://127.0.0.1:$PORT/api/stats?project_path=$(pwd)" | python3 -m json.tool
# Open in browser: http://127.0.0.1:$PORT
```

### Blocking next phase

Phase 2 depends on: 1.1 (session_id filter on API), 1.6 (session selector working).

---

## Phase 2: Actions Log + Token Savings views

**Goal:** Two interactive views fully functional. Actions log polls live. Token savings shows per-session + lifetime.  
**Files:** `~/.agent-guidance/dashboard/index.html`  
**Dependencies:** Phase 1  
**Est:** ~120 LOC  
**Risk:** Medium — timer-based DOM updates, formatting

### Tasks

| # | Task | Exit criteria |
|---|------|--------------|
| 2.1 | Actions Log table: tool, operation, count, orig tokens, opt tokens, savings % | Columns render from API data |
| 2.2 | Live polling: fetch `/api/stats` every 5s, update table rows | DOM updates without flicker |
| 2.3 | Token Savings view: session bar (orig vs opt side-by-side) | Two colored bars per session |
| 2.4 | Token Savings view: lifetime totals row | Cumulative below session bars |
| 2.5 | Token Savings view: savings percentage badge | "61.3%" green badge |
| 2.6 | Throttle: pause polling when tab hidden (Page Visibility API) | No fetches when backgrounded |

### Verify

- Switch to Actions Log → see table with data → wait 5s → see updated timestamps
- Switch tab to background → confirm no network activity (DevTools Network tab)
- Switch to Token Savings → see bars with correct proportions

### Blocking next phase

Phase 3 depends on: no hard dependency, can run parallel.

---

## Phase 3: Embed Status + Quick Guides + MCP Tools views

**Goal:** Remaining 3 views populated. Embed status live. Guides and tools are static but clean.  
**Files:** `~/.agent-guidance/dashboard/index.html`  
**Dependencies:** Phase 1 (skeleton exists), no dependency on Phase 2  
**Est:** ~80 LOC  
**Risk:** Low — mostly static content

### Tasks

| # | Task | Exit criteria |
|---|------|--------------|
| 3.1 | Embed Status view: `GET /health` → model_loaded badge, active clients count | Green/red dot, number shown |
| 3.2 | Embed Status view: total embed queries from `/api/stats` | Number matches DB count |
| 3.3 | Quick Guides view: 4 cards (task_pipeline → guidance → project_context → tools) | Each card has title, 1-line desc, copyable code |
| 3.4 | MCP Tools view: table with columns (Tool, Gate, Description, Operations) | Matches README tool surface |
| 3.5 | Responsive: sidebar collapses to hamburger on <768px | Mobile-friendly layout |

### Verify

- Click Embed Status → see model status
- Click Quick Guides → code blocks readable, copy button works
- Click MCP Tools → table scrollable, matches docs
- Resize browser to 600px → sidebar becomes hamburger

---

## Phase 4: CLI flags + Hook scripts

**Goal:** `--client-name` and `--session-label` flags work. Hook scripts auto-detect IDE.  
**Files:** `src/agent_guidance_mcp/__main__.py`, `hooks/session-start.sh`, `hooks/session-start-test.sh`  
**Dependencies:** Phase 0.6, 0.7  
**Parallel with:** Phase 1 (no code overlap)  
**Est:** ~15 LOC  
**Risk:** Low

### Tasks

| # | Task | Exit criteria |
|---|------|--------------|
| 4.1 | `__main__.py` add `--client-name` arg → passed to create_server() | CLI flag overrides env var |
| 4.2 | `__main__.py` add `--session-label` arg → passed to create_server() | Label persists in DB |
| 4.3 | `hooks/session-start.sh` set `AGENT_CLIENT_NAME` based on caller context | Hook exports correct name |
| 4.4 | `hooks/session-start-test.sh` same | Test hook behaves identically |

### Verify

```bash
AGENT_CLIENT_NAME="Cursor" agent-guidance-mcp &
# ... check usage_report() shows client_name="Cursor"
```

---

## Phase 5: Tests

**Goal:** `usage.py` fully tested. `/api/stats` shape validated.  
**Files:** `tests/test_usage.py`, `tests/test_embed_daemon.py`  
**Dependencies:** Phase 0, Phase 1.1  
**Parallel with:** Phase 2, 3, 4  
**Est:** ~160 LOC  
**Risk:** Low

### Tasks

| # | Task | Exit criteria |
|---|------|--------------|
| 5.1 | test_usage.py: schema creation + migration v1→v2 | Both versions tested |
| 5.2 | test_usage.py: session start/end lifecycle | started_at < ended_at, totals computed |
| 5.3 | test_usage.py: tool call / skill load / embed recording | All 3 tables populated correctly |
| 5.4 | test_usage.py: aggregation (session + all + session_id filter) | Numbers match expected |
| 5.5 | test_usage.py: persistence (close + reopen) | Data survives between instances |
| 5.6 | test_usage.py: concurrent read/write | Threads don't corrupt DB |
| 5.7 | test_embed_daemon.py: `/api/stats` returns valid JSON with expected keys | Response shape matches schema |

---

## Phase 6: Review + Polish

**Goal:** All code reviewed. Anti-pattern checklist passed. Dashboard iterated.  
**Files:** All  
**Dependencies:** Phase 0-5 complete  
**Est:** review session  
**Risk:** Low

### Tasks

| # | Task | Exit criteria |
|---|------|--------------|
| 6.1 | Run anti-pattern checklist (plan Appendix D.7) | 8 items all pass |
| 6.2 | Run code-review-and-quality skill on all changed files | No critical findings |
| 6.3 | Dashboard UX review: loading states, error states, empty states | All states handled |
| 6.4 | Manual smoke test: full lifecycle (daemon start → use tools → check stats → dashboard) | End-to-end works |
| 6.5 | Update README with usage_report() and dashboard docs | Documented |
| 6.6 | git commit all phases with descriptive messages | Clean history |

---

## Dependency graph

```
Phase 0 (schema v2)
  ├──► Phase 1 (API + skeleton) ──► Phase 2 (actions + tokens)
  │                                └──► Phase 3 (embed + guides + tools)
  │
  └──► Phase 4 (CLI + hooks)
       Phase 5 (tests) ──► can start after Phase 0 + 1.1
                          ──► parallel with Phase 2, 3, 4

All ──► Phase 6 (review)
```

## Summary

| Phase | What | Files | LOC | Risk | Time |
|-------|------|-------|-----|------|------|
| 0 | Schema v2 + identity | 2 | 65 | Low | 1 session |
| 1 | API + Dashboard skeleton | 2 | 160 | Med | 1-2 sessions |
| 2 | Actions + Token views | 1 | 120 | Med | 1 session |
| 3 | Embed + Guides + Tools views | 1 | 80 | Low | 1 session |
| 4 | CLI flags + Hook scripts | 3 | 15 | Low | 0.5 session |
| 5 | Tests | 1 | 160 | Low | 1 session |
| 6 | Review + Polish | all | — | Low | 1 session |
| | **Total** | ~10 | ~600 | | 6-8 sessions |

## Plan Mutations Log

| Date | Phase | Change | Reason | Impact |
|------|-------|--------|--------|--------|
| Jul 15 | 1 | Standalone `--dashboard` server created | User didn't want to run embed daemon just for stats | Replaces embed daemon as primary dashboard server |
| Jul 15 | 1 | `AGENT_SESSION_LABEL` env var added | Needed for `--session-label` flag without changing create_server signature | server.py reads env, not param |
| Jul 15 | 3 | `_ensure_daemon()` retries 5 times before fallback | User requested always try daemon first, only fallback after 5 retries | embeddings.py logic redesigned |
| Jul 15 | 3 | `agent-guidance-mcp_guidance(search)` records embed queries in usage.db | User noticed model loads but queries not logged | Added record_embed_query in server.py guidance handler |
| Jul 15 | 6 | Exponential polling backoff added | Anti-pattern review found constant 5s poll on error | pollBackoff doubles to 30s max |
| Jul 15 | 6 | Error banner added to dashboard | No visual feedback when API unreachable | error-banner div + show/hide logic |
