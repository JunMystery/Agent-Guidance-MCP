# MCP Surface Reference

[Back to README](../README.md)

Complete reference for every public MCP tool, resource, and prompt exposed by the Agent Guidance MCP server.

---

## Tools (10)

All tools except `agent-guidance-mcp_health_check`, `agent-guidance-mcp_diagnose`, `agent-guidance-mcp_token_stats`, `agent-guidance-mcp_usage_report`, and `agent-guidance-mcp_require_edit_approval` require `agent-guidance-mcp_task_pipeline` to be called first. Gated tools return `PRIORITY_REQUIRED` if called before `agent-guidance-mcp_task_pipeline`.

### 1. `agent-guidance-mcp_task_pipeline` -- Call First (unlocks gate)

One-stop context preparation. Returns standards recommendations, project tree, code search, and optional UI/UX guidance in a single optimized call. Uses parallel execution internally.

```
task_pipeline(
    task: str,                         # required — description of work
    project_path: str = ".",           # project root
    focus: str = "general",            # "general" | "frontend" | "backend"
    code_query: str | None = None,     # search override (auto-detected if omitted)
    include_tree: bool = True,         # include directory tree
    include_ui: bool = True,           # attach UI/UX guidance when task signals UI
    limit: int = 8,                    # max recommendations
) -> dict
```

**Returns:**
- `task`, `focus` — echoed inputs
- `recommendations` — skill/standard recommendations with reasons
- `project_tree` — bounded directory tree (if `include_tree=True`)
- `code_search` — ranked code matches (if auto-detected or provided query)
- `agent-guidance-mcp_ui_ux` — UI/UX guidance (if UI intent detected and `include_ui=True`)
- `execution_sequence` — recommended skills sorted by lifecycle order

**Example:**
```
task_pipeline(task="Add JWT auth to Express API", focus="backend")
```

---

### 2. `agent-guidance-mcp_guidance` -- Standards & Skill Catalog

Standards catalog and skill lookup. 185 entries available on-demand. Supports 10 operations (the workflow/precode/verify/feedback tools were consolidated into `guidance` operations).

```
guidance(
    operation: str,                    # required — list|get|search|recommend|reason|docs|workflow|precode|verify|feedback
    query: str | None = None,          # search/recommend/reason/docs/precode/verify query
    identifier: str | None = None,     # skill/document ID for "get"; library name for "docs"; mode for "workflow"; skill_id for "feedback"
    category: str | None = None,       # filter by category
    kind: str | None = None,           # filter by kind (skill, doc, principle, etc.)
    limit: int = 10,                   # max results
    include_content: bool = False,     # include full body for "get"
    rating: int = 0,                   # 1-5 rating for "feedback"
) -> dict | list[dict]
```

#### Operations

| Operation | Required Args | Description |
|---|---|---|
| `list` | -- | List all catalog entries (filterable by `category`, `kind`) |
| `get` | `identifier` | Load a specific skill/document. Set `include_content=True` for full body. Detects dependency cycles. |
| `search` | `query` | Full-text search across catalog. Returns ranked results with scores + snippets. |
| `recommend` | `query` | Auto-recommend skills/standards for a task (keyword + TASK_ANCHORS matching) |
| `reason` | `query` | Structured reasoning framework. Classifies task into: `decision`, `bug`, `architecture`, `security`, `performance`, `general`. Returns framework template, key questions, and skill URIs. |
| `docs` | `query`, `identifier` | Live library/API documentation via Context7. `identifier` is the library name (e.g. `"react"`, `"nextjs"`, `"express"`). |
| `workflow` | `identifier` (mode) | Load a workflow mode with enriched context and next-step suggestion. Replaces the deprecated `workflow`/`workflow_prompt` tools. |
| `precode` | `query` (task) | Structured pre-code checklist (conventions, security, testing, arch, deploy). Replaces the deprecated `precode_check` tool. |
| `verify` | `query` (changes) | Post-change verification steps; infers test/review/security/audit/deploy. Replaces the deprecated `verify` tool. |
| `feedback` | `identifier`, `rating` | Record a 1-5 skill rating to boost future recommendations. Replaces the deprecated `feedback` tool. |

**Examples:**
```
guidance(operation="search", query="humanizer writing")
guidance(operation="get", identifier="humanizer", include_content=True)
guidance(operation="reason", query="should I use microservices vs monolith")
guidance(operation="docs", query="jsonwebtoken sign options", identifier="node-jsonwebtoken")
```

**Loading skills on-demand:** The built-in `skill` tool only lists a few external skills. Use `agent-guidance-mcp_guidance(operation="get", identifier="skill-name", include_content=True)` to load any of the 185 Agent Guidance skills.

---

### 3. `agent-guidance-mcp_project_context` -- Bounded File Operations

Read, search, and explore project files with built-in token budgets. Supports 10 operations.

```
project_context(
    operation: str,                    # required — see operations below
    project_path: str = ".",
    query: str | None = None,          # search query / symbol name / symbol ID
    relative_path: str | None = None,  # file path for read/symbols/structure
    start_line: int = 1,               # line offset for read
    max_lines: int = 300,              # max lines to read
    max_depth: int = 8,                # directory tree depth
    output_path: str = ".agent-context/code-snapshot.json",
    max_file_bytes: int = 200000,      # per-file cap for snapshot
    max_total_bytes: int = 2000000,    # total cap for snapshot
    limit: int = 20,                   # max search/reference results
) -> dict
```

#### Operations

| Operation | Required Args | Description |
|---|---|---|
| `tree` | -- | Directory tree with file metadata (path, type, language_hint, size_bytes) |
| `search` | `query` | Codebase text search with 3-tier fallback: FTS5 (SQLite full-text) → docs/manifests → structural/config files → general code (capped 300). |
| `read` | `relative_path` | Bounded file read (300 line cap). Path traversal protected. |
| `snapshot` | -- | Export bounded JSON snapshot to `.agent-context/`. Must be within `.agent-context/` directory. |
| `symbols` | `relative_path` | Extract classes, functions, methods from a file. Tree-sitter AST (7 langs) or regex fallback (13 langs). |
| `references` | `query` | Find all usages of a symbol name across the codebase. |
| `structure` | `relative_path` | Hierarchical file overview: classes with nested methods, standalone functions. |
| `callers` | `query` | Get all callers of a symbol (from SQLite CodeGraph DB). `query` is the fully-qualified symbol ID. |
| `callees` | `query` | Get all callees of a symbol (from SQLite CodeGraph DB). |
| `diff` | -- | Git diff of workspace changes (staged + unstaged). Token-optimized. |
| `architecture` | -- | Detailed project architecture mapping (tech stack, modules, core hubs). |

**Examples:**
```
project_context(operation="read", relative_path="src/auth.js", max_lines=160)
project_context(operation="search", query="JWT middleware")
project_context(operation="symbols", relative_path="src/server.py")
project_context(operation="references", query="build_catalog")
project_context(operation="structure", relative_path="src/parallel.py")
project_context(operation="callers", query="src/parallel.py::parallel_map::1")
project_context(operation="diff")
```

---

### 4. `agent-guidance-mcp_ui_ux` -- Design Guidance

UI/UX Pro Max design guidance. Supports 3 operations.

```
ui_ux(
    operation: str,                    # required — search|design_system|slides
    query: str,                        # required — search query
    domain: str | None = None,         # style|color|chart|landing|product|ux|typography|icons|react|web
    stack: str | None = None,          # react|nextjs|vue|svelte|astro|etc.
    project_name: str | None = None,   # project name for design_system
    output_format: str = "markdown",   # "markdown" | "ascii"
    limit: int = 3,                    # max results
) -> dict
```

#### Operations

| Operation | Description |
|---|---|
| `search` | Search UI/UX guidance by domain and stack |
| `design_system` | Generate full design system (colors, typography, patterns, style) |
| `slides` | Search slide/presentation guidance |

**Examples:**
```
ui_ux(operation="search", query="minimalist dashboard design", domain="style")
ui_ux(operation="design_system", query="SaaS landing page", project_name="MyApp")
ui_ux(operation="slides", query="pitch deck", domain="landing")
```

---

### 5. `agent-guidance-mcp_session_continuity` -- Task State Persistence

Persist or recover task session state for continuity across interruptions.

```
session_continuity(
    operation: str,                    # required — save|load|clear
    project_path: str = ".",
    task: str | None = None,           # required for save
    checklist: list[dict] | None = None,  # [{"title": "...", "status": "todo"|"done"}]
    current_step_index: int = 0,
    metadata: dict | None = None,      # optional context variables
) -> dict
```

| Operation | Description |
|---|---|
| `save` | Save task + checklist to `.agent-context/session.json` (atomic write via tempfile + rename) |
| `load` | Load persisted session state. Returns `session_active: True/False`. |
| `clear` | Delete session file |

---

### 6. `agent-guidance-mcp_workflow_gate` -- Stage Enforcement

Manage and validate the active workflow stage. Supports 3 actions.

```
workflow_gate(
    action: str,                       # required — status|check|set_stage
    project_path: str = ".",
    user_message: str | None = None,   # required for check — user's approval text
    target_stage: str | None = None,   # required for set_stage — valid target
) -> dict
```

| Action | Description |
|---|---|
| `status` | View current stage, plan approval status, fix attempts |
| `check` | Parse user message for approval keywords ("proceed", "ok", "do it", etc.) |
| `set_stage` | Transition to a new stage (validates rules + circuit breaker) |

**Stage lifecycle:** `Context → Plan → Ask_Revise → Build → Test_Recheck → Fix → Proposal`
Transition to `Build` requires `plan_approved=true`. The circuit breaker resets to `Ask_Revise` after 3 failed fix attempts.

---

### 7. `agent-guidance-mcp_require_edit_approval` -- Edit Permission Gate

Final gate check before any write/edit/bash operation. Returns error unless workflow stage is `Build` with `plan_approved=true`.

```
require_edit_approval(
    project_path: str = ".",
) -> dict
```

**Returns:** `{success, allowed, stage, plan_approved}` — blocked calls include a `resolution` field with steps to unblock.

---

### 8. `agent-guidance-mcp_usage_report` -- Usage Statistics

```
usage_report(scope: str = "session") -> dict
```

Returns persistent usage statistics: tool calls, skill loads, embed queries, token savings per session or lifetime. Data stored in `.agent-context/usage.db`.

| Param | Default | Description |
|-------|---------|-------------|
| `scope` | `"session"` | `"session"` for active session, `"all"` for lifetime |

Example response:
```json
{
  "scope": "all",
  "sessions": [{"client_name": "OpenCode", "session_label": "Phase 1", "duration_seconds": 7200}],
  "totals": {"tool_calls": 187, "token_savings": 3800, "savings_pct": 61.3},
  "tool_breakdown": [{"tool_name": "guidance", "operation": "search", "cnt": 42}]
}
```

View the dashboard in a browser: `agent-guidance-mcp --dashboard`

---

### 9. `agent-guidance-mcp_token_stats` -- Session Statistics

```
token_stats() -> dict
```

Returns token optimization statistics: `total_calls`, `total_original_tokens`, `total_optimized_tokens`, `total_saved_tokens`, `overall_savings_pct`, `recent_records`.

---

### 10. `agent-guidance-mcp_health_check` -- Server Status

```
health_check() -> dict
```

Returns `status`, `server`, `version`, `entries` (catalog entry count).

---

### 11. `agent-guidance-mcp_diagnose` -- Self-Diagnostics

```
diagnose() -> dict
```

Comprehensive diagnostics across 7 subsystems:

| Key | Contents |
|---|---|
| `system` | OS, Python version, PID, project root |
| `tree_sitter` | Installed status, supported languages (python, javascript, typescript, go, rust, java, csharp) |
| `database` | CodeGraph DB path, exists, size, files_indexed, symbols_indexed, call_edges_indexed, status |
| `context7_api` | DNS resolution, IP, TCP connection status |
| `watcher` | DB exists, DB size |
| `catalog` | Entry count, categories |

---

## Resources (7)

| URI | MIME | Description |
|---|---|---|
| `standards://manifest` | `application/json` | Full manifest: entry_count, kinds, categories, all entries with identifiers/paths/URIs |
| `standards://version` | `application/json` | `{"server": "agent-guidance-mcp", "version": "1.0.6", "mcp_protocol": "2024-11-05"}` |
| `standards://document/{identifier}` | `text/markdown` | Standards document content by slug (token-optimized) |
| `standards://skill/{name}` | `text/markdown` | On-demand skill capsule by name (token-optimized) |
| `agent-guidance-mcp://system/priority` | `text/markdown` | Priority gate instructions — returned by `PRIORITY_REQUIRED` errors |
| `agent-guidance-mcp://system/gate` | `application/json` | Priority gate status: passed + sentinel present |
| `agent-guidance-mcp://system/edit-allowed` | `application/json` | Edit permission check based on workflow stage |

---

## Workflow access

Workflow modes are accessed through two separate tools:

**Content mode** — `agent-guidance-mcp_guidance(operation="workflow", identifier="<mode>")` loads workflow instructions for a given phase. The previous standalone `workflow` / `workflow_prompt` tools were consolidated into `guidance`. Supported modes:

| Mode | Description |
|---|---|
| `init` | Project initialization |
| `plan` | Planning workflow (default) |
| `design` | Design phase |
| `visualize` | Visualization |
| `code` | Implementation |
| `run` | Execution |
| `test` | Testing |
| `deploy` | Deployment |
| `debug` | Debugging |
| `refactor` | Refactoring |
| `audit` | Audit |
| `rollback` | Rollback |
| `recap` | Recap |
| `review` | Code review |
| `next` | Next steps |
| `help` | Help |
| `readme` | README generation |
| `customize` | Customization |
| `brainstorm` | Brainstorming |
| `save_brain` | Save brainstorm output |

**Stage management** — `agent-guidance-mcp_workflow_gate(action="status"|"check"|"set_stage")` manages the 7-stage workflow lifecycle (`Context → Plan → Ask_Revise → Build → Test_Recheck → Fix → Proposal`). See section 6 for full documentation.

---

## Internal Subsystems (12)

These modules power the MCP tools but are not directly callable via the MCP protocol.

| Subsystem | Module | Role |
|---|---|---|
| **CodeGraph Database** | `database.py` | SQLite FTS5 symbol index. Tables: `files`, `symbols`, `call_edges`, `symbols_fts` (virtual). WAL mode, thread-safe. |
| **Indexer** | `indexer.py` | Incremental workspace scanner. Parallel file parsing with `parallel_map`. Thread-safe DB access via `threading.Lock`. Detects file changes via mtime + content hash. |
| **Watcher** | `watcher.py` | Background daemon thread. Polls for file changes at configurable interval (`AGENT_WATCHER_INTERVAL`). Debounced, batched reference resolution. |
| **Symbol Extractor** | `symbols.py` | Tree-sitter AST parsing (7 languages: Python, JS, TS, Go, Rust, Java, C#) with regex fallback (13 languages: + Ruby, PHP, Kotlin, Swift, C, C++). Graceful degradation when tree-sitter not installed. |
| **Parallel Engine** | `parallel.py` | `ThreadPoolExecutor` helpers: `parallel_map` (order-preserving, None-filtering), `parallel_filter_map` (keep/discard), `parallel_run` (named concurrent tasks with exception isolation). |
| **Reasoning Engine** | `reasoning.py` | 6 framework templates (decision/bug/architecture/security/performance/general). Keyword classifier maps task text to framework type. Returns framework markdown, key questions, skill URIs. |
