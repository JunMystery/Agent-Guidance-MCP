# Agent Guidance MCP

![Status](https://img.shields.io/badge/status-stable-brightgreen)
[![Python Version](https://img.shields.io/badge/python-3.10%2B-blue)](https://www.python.org/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![MCP Version](https://img.shields.io/badge/mcp-%3E%3D1.0.0-green)](https://modelcontextprotocol.io/)
![GitHub license](https://img.shields.io/github/license/JunMystery/Agent-Guidance-MCP)
![GitHub repo size](https://img.shields.io/github/repo-size/JunMystery/Agent-Guidance-MCP)
[![Ko-fi](https://img.shields.io/badge/Ko--fi-F16061?logo=ko-fi&logoColor=white)](https://ko-fi.com/JunMystery)

<img src="docs/images/hero-banner.png" alt="Agent Guidance MCP">

MCP server serving AI agent guidance through a **185-skill catalog**, bundled guidance corpus, workflow prompts, bounded project-code context tools, and a **token optimization engine** — all over **Stdio** transport.

Skills are sourced from [Everything Claude Code (ECC) v2.0.0](https://github.com/affaan-m/ECC) and community contributions, covering backend, frontend, testing, security, DevOps, data, research, and 12+ language ecosystems.

---

## Installation

Install the Agent Guidance MCP server and configure all local IDE clients with a single command:

**Linux / macOS (Bash):**
```bash
curl -fsSL https://raw.githubusercontent.com/JunMystery/Agent-Guidance-MCP/main/scripts/install.sh | bash
```

**Windows (CMD / PowerShell):**
```cmd
powershell -Command "irm https://raw.githubusercontent.com/JunMystery/Agent-Guidance-MCP/main/scripts/install.ps1 | iex"
```

*No prior Python installation required — the script bootstraps `uv` (a single-binary Python toolchain) automatically.*

### Verify Installation

Test locally with MCP Inspector:

```bash
DANGEROUSLY_OMIT_AUTH=true npx @modelcontextprotocol/inspector .venv/bin/python -m agent_guidance_mcp
```

Then call `agent-guidance-mcp_task_pipeline(...)` to load guidance and bounded project context. See [Usage Guide](docs/usage.md) for workflows.

### Upgrading

**Server + IDE registrations:** rerun the install command above.

**Standards catalog & skills only:**
```bash
agent-guidance-mcp --update
```

**Executable package only:**
```bash
uv tool update agent-guidance-mcp
```

### Scheduled Auto-Update

```bash
agent-guidance-mcp --auto-update          # weekly (default)
agent-guidance-mcp --auto-update monthly  # monthly
```

Or via environment variable: `AGENT_AUTO_UPDATE_INTERVAL=weekly`

### Uninstalling

**Linux / macOS:**
```bash
curl -fsSL https://raw.githubusercontent.com/JunMystery/Agent-Guidance-MCP/main/scripts/install.sh | bash -s -- --uninstall
```

**Windows:**
```cmd
powershell -Command "irm https://raw.githubusercontent.com/JunMystery/Agent-Guidance-MCP/main/scripts/uninstall.ps1 | iex"
```

### Manual / Developer Install

```bash
python -m venv .venv
.venv/bin/pip install -e ".[dev]"      # Linux / macOS
.venv\Scripts\pip install -e ".[dev]"  # Windows
```

```bash
agent-guidance-mcp
.venv/bin/python -m agent_guidance_mcp          # Linux / macOS
.venv\Scripts\python.exe -m agent_guidance_mcp  # Windows
```

Custom corpus path:
```bash
AGENT_GUIDANCE_ROOT=/path/to/Agent-Guidance
```

Platform notes: [Installation](docs/installation.md) · [Client Setup](docs/setup/client-configuration.md)

---

## Supported IDEs

Works with any MCP-compatible client. Auto-configured by the installer:

| Claude Desktop / Claude Code | Cursor | VS Code (Copilot) |
| OpenCode / OMO | Gemini CLI | Windsurf |
| Cline / Roo-Code | Continue.dev | Antigravity |

---

## MCP Surface

<img src="docs/images/tool-surface.png" alt="MCP Tool Surface" width="50%">

### Tools

| Tool | Gate | Role | Key Operations |
|---|---|---|---|
| `agent-guidance-mcp_task_pipeline` | **Unlocks** | **Call first** — context prep | Recommendations + tree + search + UI + execution sequence |
| `agent-guidance-mcp_guidance` | Gated | Standards & skill catalog + workflow/precode/verify/feedback | `list`, `get`, `search`, `recommend`, `reason`, `docs` (Context7), `workflow`, `precode`, `verify`, `feedback` |
| `agent-guidance-mcp_project_context` | Gated | Project file ops + 3-tier search | `tree`, `search` (FTS5 docs config general), `read`, `symbols`, `references`, `structure`, `callers`, `callees`, `diff`, `snapshot` |
| `agent-guidance-mcp_ui_ux` | Gated | Design guidance | `search`, `design_system`, `slides` |
| `agent-guidance-mcp_session_continuity` | Gated | Task state persistence | `save`, `load`, `clear` |
| `agent-guidance-mcp_workflow_gate` | Gated | Stage enforcement | `status`, `check`, `set_stage` |
| `agent-guidance-mcp_require_edit_approval` | Not gated | Edit permission gate | `project_path` |
| `agent-guidance-mcp_usage_report` | Not gated | Usage statistics | `session`, `all` |
| `agent-guidance-mcp_health_check` / `agent-guidance-mcp_diagnose` / `agent-guidance-mcp_token_stats` | Whitelisted | Operational | Server status, self-diagnostics, token savings |

Gated tools return `PRIORITY_REQUIRED` if called before `agent-guidance-mcp_task_pipeline`. Whitelisted tools bypass the gate.

### Resources

| URI | Description |
|---|---|
| `standards://manifest` | Indexed standards manifest (JSON) |
| `standards://skill/{name}` | On-demand skill capsule (Markdown) |
| `standards://document/{identifier}` | Standards document by slug (Markdown) |
| `standards://version` | Server version info (JSON) |
| `agent-guidance-mcp://system/priority` | Priority gate instructions — returned by `PRIORITY_REQUIRED` errors |
| `agent-guidance-mcp://system/gate` | Priority gate status: passed + sentinel present (JSON) |
| `agent-guidance-mcp://system/edit-allowed` | Edit permission check based on workflow stage (JSON) |

### Workflow (consolidated into `guidance`)

`agent-guidance-mcp_guidance(operation="workflow", identifier="<mode>", query="<subject>")` — Load workflow by mode: plan, test, deploy, debug, etc. The previous `workflow` / `workflow_prompt` tools were merged into `guidance`.

For stage lifecycle management (`workflow_gate`), see the [Workflow Stage Enforcement](#workflow-stage-enforcement) section.

---

## Why Agent Guidance MCP

AI coding agents burn context fast. Every file read, every grep, every web search eats into the context window — and when it's gone, the agent forgets everything. Agent Guidance MCP solves this with four layers:

| Layer | What It Does | Your Gain |
|---|---|---|
| **Priority Enforcement** | `agent-guidance-mcp_task_pipeline` must be called before gated tools (guidance, project_context, ui_ux, session_continuity, workflow_gate). Session-start hook auto-passes gate. | Agent always has project context before acting. No more "forgot to call task_pipeline" |
| **Context Budgeting** | Caps file reads at 300 lines; smart-truncates source code preserving structure | Agent stays focused on relevant code, never drowns in noise |
| **Guidance Catalog** | 185 skills + coding standards + security rules served on-demand | Agent follows production patterns without you reminding it |
| **Token Optimization** | Strips comments, collapses whitespace, deduplicates output before it hits the LLM | **40–80% fewer tokens** per MCP response |

### What You Save

Measured on a typical 500-line React component refactor task:

<img src="docs/images/token-savings-chart.png" alt="Token Savings Comparison" width="65%">

```
                    Without MCP          With Agent Guidance MCP
                    ─────────────        ──────────────────────
Tool round-trips    12–18 calls          4–6 calls (task_pipeline consolidates)
Context used        ~45,000 tokens       ~12,000 tokens
File reads          8+ full reads        3 capped reads (300 lines ea.)
Standards lookup    Manual / guessed     Automatic via guidance()
Dead-ends           2–3 wrong searches   Zero (search-first discipline)
Time to first fix   ~4 minutes           ~45 seconds
```

### Token Optimization Pipeline

Every MCP response passes through an 8-stage filter before reaching your agent:

<img src="docs/images/token-pipeline.png" alt="Token Optimization Pipeline" width="40%">

```
Raw Response
  │
  ├─ Stage 1  ANSI strip          ── removes terminal color codes
  ├─ Stage 2  Regex replace       ── collapses noise patterns
  ├─ Stage 3  Match/short-circuit ── skips empty payloads
  ├─ Stage 4  Line filter         ── keep only relevant output lines
  ├─ Stage 5  Smart truncation    ── preserves imports, signatures, constants
  ├─ Stage 6  Head/tail keep      ── first + last N lines with omission marker
  ├─ Stage 7  Max lines cap       ── absolute ceiling
  └─ Stage 8  Empty guard         ── fallback message if everything filtered
  │
  ▼
Optimized Response (40–80% smaller)
```

### Semantic Skill Search & Local Workspace Skills

Agent Guidance MCP features a hybrid semantic search engine designed to dynamically load relevant skills based on intent and task context.

- **Pre-computed Embeddings**: The 185 global catalog skills have pre-computed embeddings mapped using the lightweight `intfloat/multilingual-e5-small` model. This ensures instant retrieval on startup.
- **Workspace-Local Skills**: The server automatically scans your project workspace for custom local skills defined in `.agents/skills/`, `.opencode/skills/`, or `.claude/skills/` directories, dynamically embeds them on startup, and merges them into the search index.
- **Hybrid Similarity Ranking**: `agent-guidance-mcp_guidance(operation="search")` blends traditional keyword matching with vector cosine similarity calculations to rank skills accurately, even when the task query contains no exact keyword overlaps (e.g., matching "reducing context size" to the `context-budget` skill).
- **Zero-Configuration Download**: The query embedding model is automatically downloaded on-demand when the server first runs, requiring zero manual setup or configuration.

---

## Priority Enforcement

Agent Guidance MCP ensures that `agent-guidance-mcp_task_pipeline` is always called before any gated tool, across all agents and IDEs.

### Three Enforcement Layers

```
Session starts
  │
  ├─ Layer 1: Session-start hook
  │    hooks/session-start.sh → agent-guidance-mcp --session-start
  │    → Writes ~/.agent-guidance/.gate_passed sentinel
  │    → Injects project context into conversation
  │
  ├─ Layer 2: Persistent sentinel file
  │    MCP server starts → reads sentinel → gate pre-passed
  │    Bridges hook process and server process
  │
  └─ Layer 3: In-process gate
       task_pipeline → priority_gate_pass() unlocks gate
       Gated tools → priority_gate_check() blocks if not passed
```

### Tool Gate Status

| Tool | Gate Behavior |
|---|---|
| `agent-guidance-mcp_task_pipeline` | **Unlocks gate** — call first to enable all gated tools |
| `agent-guidance-mcp_guidance`, `agent-guidance-mcp_project_context`, `agent-guidance-mcp_ui_ux`, `agent-guidance-mcp_session_continuity`, `agent-guidance-mcp_workflow_gate` | **Gated** — return `PRIORITY_REQUIRED` error if called before `agent-guidance-mcp_task_pipeline` |
| `agent-guidance-mcp_require_edit_approval`, `agent-guidance-mcp_usage_report` | **Not gated** — always callable, no priority check |
| `agent-guidance-mcp_health_check`, `agent-guidance-mcp_diagnose`, `agent-guidance-mcp_token_stats` | **Whitelisted** — always available, no gate check |

### Per-Phase Reset Rule

For each new work phase (plan → implement → test → review → refactor), re-call `agent-guidance-mcp_task_pipeline` with the phase goal. This refreshes skill recommendations, project context, and execution sequence for the new scope. The rule is deployed to all IDEs via `AGENTS.md` and `SKILL.md` files.

### Session-Start Hook

Every supported CLI agent fires a session-start hook that auto-calls `agent-guidance-mcp --session-start --project-path .`. This:

1. Builds the skill catalog
2. Passes the priority gate (writes sentinel file)
3. Runs `agent-guidance-mcp_task_pipeline` for default context
4. Returns a JSON payload injected into the conversation

The hook tries: installed binary → `python -m agent_guidance_mcp` → legacy meta-skill fallback.

### Tagged Section Deployment

Rule blocks and skill content are wrapped in HTML-comment tags (`<!-- agent-guidance:start -->` / `<!-- agent-guidance:end -->`). The `--setup` command uses these tags to find and replace sections across all IDE/CLI config files — no stale copies, no manual cleanup.

### Workflow Stage Enforcement

Beyond the priority gate, Agent Guidance MCP enforces a **7-stage workflow lifecycle** that gates file edits:
`Context → Plan → Ask_Revise → Build → Test_Recheck → Fix → Proposal`

| Stage | Edit allowed? | What gates block |
|---|---|---|
| `Context` | No | All tools except `task_pipeline`, `workflow_gate`, `session_continuity` |
| `Plan` | No | `diff` and `architecture` operations on `project_context` |
| `Ask_Revise` | No | Code reads (`read`, `search`, `symbols`, `references`, `structure`, `callers`, `callees`, `diff`) and `precode`/`verify` |
| `Build` | ✅ Yes (if approved) | All tools blocked if `plan_approved=false` |
| `Test_Recheck` | No | `precode` operation |
| `Fix` | ✅ Yes | Circuit breaker resets to `Ask_Revise` after 3 failed attempts |
| `Proposal` | No | `diff`, `structure`, `symbols` operations |

**Tools for stage management:**

| Tool/Resource | Purpose |
|---|---|
| `agent-guidance-mcp_workflow_gate(action="status")` | View current stage, plan approval, fix attempts |
| `agent-guidance-mcp_workflow_gate(action="check", user_message=...)` | Parse user approval from natural language ("proceed", "ok", "do it") |
| `agent-guidance-mcp_workflow_gate(action="set_stage", target_stage=...)` | Transition to a new stage (validates rules + circuit breaker) |
| `agent-guidance-mcp_require_edit_approval(project_path=...)` | Final gate check — returns error unless stage is `Build` + `plan_approved=true` |
| `agent-guidance-mcp://system/edit-allowed` | Read-only resource for low-friction permission check (JSON) |

**Circuit breaker**: If the agent fails to fix an issue 3 times (3 transitions to `Fix`), the stage automatically resets to `Ask_Revise` with `plan_approved=false`, forcing re-approval before any further edits.

The `require_edit_approval` tool and `agent-guidance-mcp://system/edit-allowed` resource together form the **edit gate** — callable by agents before any write/edit/bash to confirm the workflow stage permits edits.

---

## How It Works In Practice

### Scenario: "Add JWT authentication to my Express API"

**Step 1 — Agent calls `agent-guidance-mcp_task_pipeline` (ONE call)**

```
Agent: task_pipeline(task="Add JWT auth to Express API", focus="backend")
```

Returns in a single response:
- **Recommendations**: 8 relevant skills (api-design, security-review, backend-patterns, express-patterns...)
- **Project tree**: Directory structure of your Express project
- **Code search**: Pre-grepped results for "auth", "jwt", "token", "middleware"
- **Execution sequence**: Skills sorted in lifecycle order (spec → plan → build → test → review)

**Step 2 — Agent consults standards**

```
Agent: guidance(operation="search", query="JWT authentication middleware Express")
```

Returns: security-review skill, api-design patterns, OWASP auth cheatsheet — all pre-loaded, zero web search round-trips.

**Step 3 — Agent searches codebase using 3-tier fallback**

```
Agent: project_context(operation="search", query="JWT middleware auth")
```

Returns ranked results using a three-tier pipeline:
- **Tier 1**: Docs and manifests (README, ARCHITECTURE.md, pyproject.toml) — fast, high-signal
- **Tier 2**: Config, entry points, test dirs (Dockerfile, main.py, src/) — structural context
- **Tier 3**: General code files, capped at 300 — slowest, only reached if tiers 1–2 miss

FTS5 (SQLite full-text index) resolves ~90% of queries instantly, bypassing all three fallback tiers. The 3-tier fallback only fires when FTS5 is empty or the index isn't ready.

**Step 4 — Agent implements with live docs**

```
Agent: guidance(operation="docs", query="jsonwebtoken sign options", identifier="node-jsonwebtoken")
```

Returns: current `jsonwebtoken` API docs from Context7 — no hallucinated API calls.

**Result**: Agent writes production-grade JWT middleware in ~3 tool calls instead of 15+, with automatic security review awareness.

---

---

## Usage Dashboard

Agent Guidance MCP includes a lightweight usage dashboard to visualize tool calls, token savings, skill loads, and embed queries per session.

### Start the dashboard

```bash
# Standalone dashboard server (no ML model needed, pure stdlib)
agent-guidance-mcp --dashboard
# Dashboard: http://127.0.0.1:<port>/
```

### Automatically tracked data

| Data | Tracked via | Shown in dashboard |
|------|-------------|-------------------|
| Tool calls | Every `agent-guidance-mcp_task_pipeline`, `agent-guidance-mcp_guidance`, `agent-guidance-mcp_project_context`, `agent-guidance-mcp_ui_ux`, `agent-guidance-mcp_session_continuity` call | Actions Log view |
| Token savings | Per-tool origin vs optimized token counts | Token Savings view |
| Skill loads | `agent-guidance-mcp_guidance(get)`, `standards://skill/{name}` resource | Dashboard view |
| Embed queries | `agent-guidance-mcp_guidance(search)`, `agent-guidance-mcp_guidance(recommend)` | Embed Status view |
| Session identity | `AGENT_CLIENT_NAME` env var or `--client-name` flag | Session selector |

### Dashboard views

| View | Content |
|------|---------|
| Dashboard | Session summary cards, top skills list, embed status |
| Actions Log | Live-updating table of tool calls, polled every 5s |
| Token Savings | Per-session savings percentage + lifetime orig/opt/saved bars |
| Embed Status | Model loaded status, active clients (daemon mode), total embed queries |
| Quick Guides | 4-step workflow reference (task_pipeline → guidance → project_context → session_continuity) |
| MCP Tools | Complete tool reference with gate status and operations |

Data is persisted to `.agent-context/usage.db` in the project directory and survives server restarts.

---

## Environment Variables

| Variable | Purpose | Default |
|---|---|---|
| `AGENT_GUIDANCE_ROOT` | Custom standards corpus path | Bundled corpus |
| `AGENT_PROJECT_ROOT` | Override project root for context tools | `.` (cwd) |
| `AGENT_PROJECT_ALLOWED_ROOTS` | Whitelist directories for security | Project root only (set to expand) |
| `AGENT_EMBEDDING_DAEMON` | Disable embed daemon (forces in-process model) | `1` (enabled) |
| `AGENT_WATCHER_ENABLED` | Enable/disable CodeGraph file watcher | `true` |
| `AGENT_WATCHER_INTERVAL` | Watcher poll interval (seconds) | `30` |
| `AGENT_WATCHER_DEBOUNCE_MULTIPLIER` | Debounce multiplier after changes | `2.0` |
| `AGENT_WATCHER_REF_THRESHOLD` | Batch size before full reference resolve | `50` |
| `AGENT_AUTO_UPDATE_INTERVAL` | Auto-update schedule via env var | `weekly` |
| `--auto-update` / `--update` | CLI flags for manual update + model download | — |
| `--session-start` | CLI flag for session-start hook auto-activation | — |
| `--embed-daemon` | Start embedding daemon as foreground process | — |
| `--dashboard` | Start usage dashboard server | — |
| `--re-gate` | Re-pass priority gate for subagent recovery | — |
| `--no-optimize` | Disable token optimization and savings tracking | — |

For full tool documentation, response formats, and examples, see [MCP Surface](docs/reference/mcp-surface.md).

---

## Documentation

- [Getting Started](docs/getting-started.md) — first-time walkthrough.
- [Installation](docs/installation.md) — automatic and manual setup.
- [Usage Guide](docs/usage.md) — recommended agent workflows and examples.
- [Client Setup](docs/setup/client-configuration.md) — VS Code, Copilot, Cursor, Gemini, OpenCode, Windsurf, Antigravity.
- [MCP Surface](docs/reference/mcp-surface.md) — all tools, prompts, and resources.
- [Project Context Tools](docs/reference/project-context-tools.md) — tree, search, read, snapshot, symbols, references.
- [Skills Overview](docs/skills/SKILLS_OVERVIEW.md) — full catalog of 185+ skills.
- [Integrated Repositories](docs/integrations/integrated-repositories.md) — third-party repos in the codebase.
- [Multi-IDE Guide](docs/integrations/multi-ide.md) — memory usage, SSE mode, recommendations.
- [Development Guide](docs/development.md) — tests, project structure, maintainer notes.
- [MCP Integrations Guide](agent-guidance/mcp-integrations/README.md) — SQLite caching, CodeGraph, Context7 docs.

---

## Multi-IDE Usage

Each IDE/CLI spawns its own MCP server subprocess, but the **embedding model is shared** via a local HTTP daemon — one per user, one model load.

```
VS Code         → MCP process A ──┐
Cursor          → MCP process B ──┼──► embed_daemon (127.0.0.1)
Claude Desktop  → MCP process C ──┘     │
                                    [SentenceTransformer]
                                    intfloat/multilingual-e5-small
```

**Total RAM**: ~466 MB for the daemon, regardless of how many IDEs you open.

### How it works

| Layer | Mechanism |
|---|---|
| **Daemon spawn** | First MCP process needing embeddings acquires `~/.agent-guidance/daemon.lock` (fcntl flock on POSIX, msvcrt on Windows) and spawns the daemon subprocess |
| **Service discovery** | Daemon writes `~/.agent-guidance/daemon.json` with its port and PID on startup |
| **Client connection** | All MCP processes POST to `http://127.0.0.1:<port>/embed` for inference |
| **Health checks** | Daemon exposes `GET /health` echoing its PID + `embed_ready` flag; clients probe before reusing a manifest |
| **Client registration** | Each MCP process calls `POST /register` with its PID; daemon background-reaps dead clients |
| **Auto-shutdown** | Daemon exits after 600s idle or when all clients disconnect (30s grace) |

### Which tools trigger model load

The daemon is spawned lazily on the first call to any tool that needs embeddings, not only `guidance(search)`:

| Tool | Triggers daemon? |
|---|---|
| `agent-guidance-mcp_task_pipeline` | ❌ — uses precomputed `skills_embeddings.json` |
| `agent-guidance-mcp_guidance(operation="search")` | ✅ — first call spawns daemon, subsequent calls reuse |
| `agent-guidance-mcp_guidance(operation="list\|get\|recommend")` | ❌ — catalog only |
| `agent-guidance-mcp_project_context` | ❌ — file ops only |
| `agent-guidance-mcp_session_continuity` | ❌ — state only |
| `agent-guidance-mcp_health_check / diagnose / token_stats` | ❌ — server info |

On first call, the daemon loads the model in ~1 second. Subsequent calls are instant HTTP requests to the already-running daemon.

### Fallback (daemon unavailable)

If the daemon cannot start (lock contention, `AGENT_EMBEDDING_DAEMON=0`, or under pytest), each MCP process falls back to a **process-local singleton** — each loads its own 466 MB model. This is transparent to the caller.

### SSE mode (future)

Even with the shared embedding daemon, each MCP process still runs its own stdio server. Adding SSE transport (`--transport sse`) would allow all IDEs to share a single MCP daemon process. See [Multi-IDE Guide](docs/integrations/multi-ide.md) for details and current limitations.

---

## Development

```bash
python -m pytest
```

The test suite verifies catalog discovery, MCP handler registration, standards search, recommendation behavior, project-context tooling (18 tests), and priority + workflow gate enforcement (13 tests covering block/pass/reset/thread-safety/sentinel persistence/edit-approval). See [Development Guide](docs/development.md) for more detail.
