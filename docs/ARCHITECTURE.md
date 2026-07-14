# Architecture

[Back to README](../README.md)

## Overview

Agent Guidance MCP is a Python MCP server that gives AI coding agents standards guidance, skill references, workflow prompts, and bounded project code context. It enforces a priority gate so `task_pipeline` is always called before gated tools.

---

## Module Map

```
src/agent_guidance_mcp/
├── __init__.py         # Package version, public API exports
├── __main__.py         # CLI entry: --setup, --update, --session-start, server
├── server.py           # FastMCP registration, priority gate, sentinel, run_session_start
├── catalog.py          # StandardsCatalog: indexing, search, recommendations
├── pipelines.py        # Tool dispatchers: task_pipeline, guidance, project_context, ui_ux
├── pipeline_helpers.py # Shared helpers: framework detection, lifecycle sort, response wrapping
│
├── project_context.py  # Tool handlers: tree, search, read, snapshot, symbols, diff
├── project_scan.py     # os.walk traversal, file filtering, ignore lists
├── project_codegraph.py# CodeGraph semantic indexing integration
│
├── embeddings.py       # SentenceTransformer model (intfloat/multilingual-e5-small) lazy load
├── semantic_search.py  # Hybrid search: keyword + vector cosine similarity
├── reasoning.py        # 6 framework templates (decision, bug, architecture, security, perf)
│
├── setup.py            # Post-install: IDE registration, rule/skill deployment, uninstall
├── updater.py          # Skill repo download, commit-SHA skip, model pre-download
├── deploy_rules.py     # Auto-deploy rules/skills to workspace on server start
│
├── response_optimizer.py   # 8-stage token optimization pipeline
├── token_analytics.py      # Token savings tracking
├── token_config.py         # Token optimization config from env vars
├── token_filter.py         # Filter levels: minimal, balanced, aggressive
├── content_compressor.py   # Language-aware source truncation
│
├── parallel.py         # ThreadPoolExecutor helpers: parallel_map, parallel_run
├── text.py             # Tokenization, code term extraction, text normalization
├── paths.py            # Standards root discovery, safe path resolution
├── symbols.py          # Tree-sitter AST extraction with regex fallback
├── database.py         # SQLite FTS5 index for CodeGraph
├── indexer.py          # Incremental workspace indexer
├── watcher.py          # Background file watcher daemon
├── diagnostics.py      # Self-diagnostics: system, tree-sitter, DB, Context7
├── session.py          # Session continuity persistence
├── ui_ux.py            # UI/UX Pro Max design guidance
├── docs.py             # Context7 live documentation search
├── utils.py            # Misc helpers
├── constants.py        # PROJECT_IGNORED_PARTS, TASK_ANCHORS, etc.
└── deploy_rules.py     # AGENTS.md / SKILL.md deployment to workspace
```

---

## Enforcement Architecture

### Priority Gate (3 layers)

```
Session startup
  └─ Layer 1: Session-start hook
       hooks/session-start.sh → agent-guidance-mcp --session-start
       → Writes ~/.agent-guidance/.gate_passed sentinel
       → Injects project context JSON into AI conversation

MCP server starts
  └─ Layer 2: create_server() reads sentinel
       → _gate_sentinel_check(deploy_root) validates project path
       → Sets _priority_gate_passed = True, clears sentinel file
       → Bridges hook process and server process

Tool call
  └─ Layer 3: priority_gate_check(project_path)
       → Checks _priority_gate_passed (in-memory flag)
       → Fallback: _gate_sentinel_check(project_path) validates sentinel
       → If both fail: returns PRIORITY_REQUIRED error
```

### Tool Gate Status

| Tool | Built-in | Behavior |
|---|---|---|
| `task_pipeline` | ✅ | **Unlocks** gate via `priority_gate_pass()` |
| `guidance` | ✅ | Gated — blocked before `task_pipeline` |
| `project_context` | ✅ | Gated — blocked before `task_pipeline` |
| `ui_ux` | ✅ | Gated — blocked before `task_pipeline` |
| `session_continuity` | ✅ | Gated — blocked before `task_pipeline` |
| `workflow_prompt` (prompt) | ✅ | Gated — blocked before `task_pipeline` |
| `health_check`, `diagnose`, `token_stats` | ✅ | Whitelisted — always open |

---

## Key Flows

### Installation Flow

```
install.sh / install.ps1
  ├─ Install uv (Python toolchain)
  ├─ Install agent-guidance-mcp via uv tool
  ├─ agent-guidance-mcp --setup
  │   ├─ Register MCP client in IDE configs (Claude, Cursor, VS Code, etc.)
  │   ├─ Deploy AGENT_RULES_BLOCK to global AGENTS.md and workspace rule files
  │   └─ Deploy agent-guidance/SKILL.md to all skill directories
  └─ agent-guidance-mcp --update
      ├─ Pre-download embedding model (cached, skip if present)
      ├─ For each 3rd-party repo: query GitHub API for latest commit SHA
      │   ├─ SHA matches cache AND target dir exists → skip download
      │   └─ Otherwise → git clone / zip download → extract → save SHA
      └─ Save update state to ~/.agent-guidance/.update-state.json
```

### Session-Start Flow

```
CLI agent starts
  └─ hooks/session-start.sh (Claude Code)
       ├─ agent-guidance-mcp --session-start --project-path $PWD
       │   ├─ Build catalog
       │   ├─ priority_gate_pass() + _gate_sentinel_write()
       │   ├─ Run task_pipeline for default context
       │   └─ Output JSON: {priority, message}
       └─ JSON injected into AI conversation (project context visible)

Non-hook clients (OpenCode, Gemini, etc.)
  └─ Gate is locked on startup
  └─ Agent must call task_pipeline first (enforced by PRIORITY_REQUIRED error)
```

### Tool Call Flow

```
AI calls gated tool (guidance, project_context, etc.)
  ├─ handler() → priority_gate_check(catalog.root)
  │   ├─ _priority_gate_passed? → pass
  │   └─ _gate_sentinel_check(root)? → pass + clear sentinel
  │       └─ None → return PRIORITY_REQUIRED
  └─ pass → execute pipeline → return result
```

### Search Flow (3-tier fallback)

```
project_context(operation="search", query="...")
  ├─ FTS5 (SQLite full-text index) → resolves ~90% of queries
  │   └─ Empty/no results →
  ├─ Tier 1: Documentation + manifests (README, ARCHITECTURE, pyproject.toml, etc.)
  │   └─ Empty →
  ├─ Tier 2: Structural + config (Dockerfile, main.py, tsconfig, tests/, src/)
  │   └─ Empty →
  └─ Tier 3: General code files (capped at 300, parallel scan)
      └─ Return ranked matches
```

### Update Flow

```
agent-guidance-mcp --update
  ├─ Pre-download embedding model (SentenceTransformer)
  ├─ For each UPDATER_REPOS key (ecc, ui_ux, anthropic, owasp, system_design):
  │   ├─ Fetch latest commit SHA from GitHub API
  │   ├─ If cached SHA matches AND target dir exists: skip
  │   └─ Else: git clone / download → extract → save new SHA
  └─ Save state to ~/.agent-guidance/.update-state.json
```

---

## Deploy & Uninstall

```
--setup
  ├─ configure_mcp_clients() → register in IDE configs (Claude, Gemini, Cursor, VS Code, Continue)
  ├─ configure_opencode() → register in opencode.json (global + local)
  ├─ configure_codex() → register in .codex/config.toml
  ├─ configure_global_rules() → append AGENT_RULES_BLOCK to AGENTS.md / CLAUDE.md
  ├─ configure_workspace_rules() → append tagged block to .cursorrules, .clinerules, etc.
  └─ configure_skills_enforcer() → write SKILL.md to skill dirs

--uninstall
  ├─ remove_mcp_clients() → delete from all IDE configs
  ├─ remove_opencode_and_codex() → delete from opencode.json + .codex/config.toml
  ├─ remove_global_rules() → strip tagged block from AGENTS.md / CLAUDE.md, delete skill dirs
  └─ remove_workspace_rules() → strip tagged block from .cursorrules, .clinerules, etc.
```

All rule/skill sections use HTML-comment tags (`<!-- agent-guidance:start -->` / `<!-- agent-guidance:end -->`) for reliable find-and-replace by Python.

---

## Configuration

### Environment Variables

| Variable | Purpose |
|---|---|
| `AGENT_AUTO_UPDATE_INTERVAL` | Auto-update frequency: `weekly` (default) or `monthly` |
| `AGENT_GUIDANCE_ROOT` | Custom standards corpus path |
| `AGENT_PROJECT_ROOT` | Override project root for context tools |
| `AGENT_PROJECT_ALLOWED_ROOTS` | Whitelist directories for security |
| `AGENT_WATCHER_ENABLED` | Enable/disable CodeGraph file watcher |
| `AGENT_WATCHER_INTERVAL` | Watcher poll interval (seconds) |

### CLI Flags

| Flag | Action |
|---|---|
| `--setup` | Register MCP server in all IDE clients |
| `--update` | Download skills + LLM model(s) |
| `--auto-update` | Check schedule and update if needed (exits cleanly) |
| `--session-start` | Auto-pass gate, inject project context (used by hook) |
| `--uninstall` | Remove all registrations, rules, and skill folders |
| `--project-path` | Project root for `--session-start` |

---

## 3rd-Party Updates

Five repositories managed by `updater.py`:

| Key | Repository | Update check |
|---|---|---|
| `ecc` | `affaan-m/ECC` (main) | Commit SHA |
| `ui_ux` | `nextlevelbuilder/ui-ux-pro-max-skill` (main) | Commit SHA |
| `anthropic` | `anthropics/skills` (main) | Commit SHA |
| `owasp` | `OWASP/CheatSheetSeries` (master) | Commit SHA |
| `system_design` | `donnemartin/system-design-primer` (master) | Commit SHA |

Updates skip when target directory exists AND cached commit SHA matches the latest on GitHub. State is persisted in `~/.agent-guidance/.update-state.json`.

---

## Related

- [MCP Surface](reference/mcp-surface.md) — full tool/resource/prompt reference
- [Development Guide](development.md) — tests, project structure, maintainer
- [Installation](installation.md) — automatic and manual setup
- [README](../README.md) — project overview
