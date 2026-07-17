# Audit: MCP Not Called After Subagent Spawn

## Summary

After the IDE/CLI spawns a subagent, the MCP server stops responding to gated tool
calls. The root cause is a **one-shot sentinel file** combined with **per-process
priority gate state** — when the MCP server restarts during subagent lifecycle,
the gate locks permanently.

---

## Finding 1: Priority Gate State is Per-Process, Perishable

**File:** `src/agent_guidance_mcp/server.py:83`

```python
_priority_gate_passed: bool = False  # line 83 — module-level, resets on every import
```

The `_priority_gate_passed` flag is a Python module-level global in `server.py`.
Once `task_pipeline` calls `priority_gate_pass()`, the flag is `True` for the
lifetime of that Python process.

**Problem:** If the MCP server process is killed and restarted (e.g., IDE/CLI
manages MCP subprocess lifecycle per-agent-session, or a crash triggers restart),
the new process imports `server.py` fresh — `_priority_gate_passed` starts as
`False` again. No mechanism persists this flag across restarts beyond the
single-use sentinel file.

### Likely Trigger

When the IDE/CLI spawns a subagent, it may:

- Kill and restart the MCP server subprocess (isolation boundary)
- Spawn a new agent process that connects to a new MCP server
- Trigger a session boundary that terminates the old MCP server

This causes `_priority_gate_passed` to reset. The sentinel file is the only
bridge, but it has a critical flaw (Finding 2).

---

## Finding 2: Sentinel File is One-Shot, Cleared After First Read

**File:** `src/agent_guidance_mcp/server.py:133-238`, lines 466-468

**Flow:**

```
1. --session-start hook runs:
   run_session_start() → priority_gate_pass() + _gate_sentinel_write(path)
   → Writes ~/.agent-guidance/.gate_passed

2. MCP server starts:
   create_server() → _gate_sentinel_check(deploy_root)
   → Reads sentinel, sets _priority_gate_passed = True
   → _gate_sentinel_clear()  ← DELETES the sentinel file (line 468)

3. Subagent spawn triggers server restart:
   New process starts → _priority_gate_passed = False
   → _gate_sentinel_check() returns False (file was deleted)
   → Gate stays locked → all gated tools return PRIORITY_REQUIRED
```

**Verdict:** The sentinel is a one-shot bootstrap. After the initial server
startup clears it, any subsequent server restart has no way to recover the gate
state.

---

## Finding 3: Auto-Context Hijacks the Tool Call

**File:** `src/agent_guidance_mcp/server.py:170-188`

When `priority_gate_check()` detects the gate hasn't been passed AND the caller
provided `catalog` and `tool_name`, it auto-runs `auto_context()` and returns
a dict with `auto_context: True` — **instead of executing the actual requested
tool operation**.

```python
ctx = _p.auto_context(...)
_priority_gate_passed = True
return {
    "success": True,
    "auto_context": True,
    "message": f"Auto-loaded context for: {task or 'your task'}",
    **ctx,
}
```

**Problem:** The LLM asked for `guidance(operation="get", identifier="humanizer")`
but receives auto-context instead. The auto-context response format differs from
the expected tool response. This can:

- Confuse the LLM about what the MCP tool actually returns
- Make the LLM think the tool is unreliable
- Gradually reduce the LLM's willingness to call MCP tools

Additionally, if `auto_context()` raises an exception, the gate stays locked
even though a gated tool was the first call — forcing a hard `PRIORITY_REQUIRED`
error.

---

## Finding 4: Mixed Return Types Break LLM Expectations

**File:** `src/agent_guidance_mcp/server.py:600-640`

The `guidance` tool declares:
```python
def guidance(...) -> dict[str, object] | list[dict[str, object]]:
```

But returns `dict[str, object]` when the gate blocks, even for operations that
normally return `list[dict]` (e.g., `operation="list"` or `operation="search"`).
The LLM receives a dict where it expects a list, which can cause:

- Schema validation failures in the LLM's output parser
- Tool selection degradation over time
- Confusing error handling

---

## Finding 5: No Gate Persistence Hook on Subagent Boundary

When a subagent finishes and returns control to the main agent, there is no
mechanism to:

1. Verify the MCP server is still running
2. Re-pass the priority gate if the server restarted
3. Re-establish the sentinel file if needed

`priority_gate_reset()` exists (`server.py:201`) but is only used in tests
(no tests actually exist for it — grep shows zero callers outside its
definition).

---

## Finding 6: Zero Test Coverage for Gate Mechanism

**Directory:** `tests/`

- No test file for `server.py` exists
- `test_pipelines.py` does not test gate interactions
- `priority_gate_check`, `priority_gate_pass`, `priority_gate_reset`,
  `_gate_sentinel_write`, `_gate_sentinel_check`, `_gate_sentinel_clear`,
  and `auto_context` all have zero test coverage

---

## Recommended Fixes

### Fix 1: Don't Clear the Sentinel (or Re-write Periodically)

In `create_server()` (line 466-468), keep the sentinel file alive instead of
deleting it. Optionally tag it with an expiry timestamp.

```python
# Instead of clearing, keep it for the session lifetime
# _gate_sentinel_clear()  ← REMOVE THIS
# Add:
_gate_sentinel_touch()  # update timestamp, don't delete
```

Or add a periodic refresh: `run_session_start` should be callable mid-session
and re-write the sentinel.

### Fix 2: Heartbeat / Re-Activation on Tool Call

In `priority_gate_check()`, add a fallback: if `_priority_gate_passed` is `False`
and no sentinel exists, check if the server has been running > N seconds (heuristic:
the gate should have been passed by now), and if a prior `task_pipeline` was
recorded in the usage DB (`usage.db`), auto-pass the gate.

### Fix 3: Add `--re-gate` CLI Flag

Add a `--re-gate` flag to the CLI that re-writes the sentinel file and passes
the gate, callable from a post-subagent hook:

```bash
agent-guidance-mcp --re-gate --project-path "$PWD"
```

This can be wired into the IDE/CLI's subagent lifecycle hook (if available).

### Fix 4: Expose Gate State as a Resource

Add an MCP resource `agent-guidance-mcp://system/gate` that exposes gate status
(`passed: true/false`) and a `re-pass` method. The IDE/CLI or main agent can
check this after subagent return.

### Fix 5: Add Tests

Add `tests/test_server_gate.py` covering:
- `priority_gate_pass` / `priority_gate_check` round-trip
- `_gate_sentinel_write` / `_gate_sentinel_check` / `_gate_sentinel_clear`
- Server restart simulation (multi-process sentinel recovery)
- Auto-context does NOT fire when gate is already passed
- Auto-context error does not leave gate permanently locked

---

## Files Examined

| File | Lines | Relevance |
|------|-------|-----------|
| `src/agent_guidance_mcp/server.py` | 1-1074 | Priority gate, sentinel, handlers |
| `src/agent_guidance_mcp/__main__.py` | 1-176 | CLI entry points |
| `src/agent_guidance_mcp/pipelines.py` | 592-622 | `auto_context()` |
| `hooks/session-start.sh` | 1-59 | Session start hook |
| `hooks/hooks.json` | 1-14 | Hook registration |
| `opencode.json` | 1-16 | MCP configuration |
| `docs/ARCHITECTURE.md` | full | Architecture docs |
