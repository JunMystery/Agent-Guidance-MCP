# Getting Started with Agent Guidance MCP

Agent Guidance MCP is a Python MCP server that gives AI coding agents standards guidance, skill references, workflow prompts, bounded project code context, and token optimization — all over Stdio transport.

## Quick Start

### 1. Install

```bash
curl -fsSL https://raw.githubusercontent.com/JunMystery/Agent-Guidance-MCP/main/scripts/install.sh | bash
```

See [Installation](installation.md) for manual setup.

### 2. Verify

Test the server with MCP Inspector:

```bash
DANGEROUSLY_OMIT_AUTH=true npx @modelcontextprotocol/inspector .venv/bin/python -m agent_guidance_mcp
```

### 3. Use in your workflow

Every session starts with a single call:

```
agent-guidance-mcp_task_pipeline(task="Describe what you're building", focus="backend"|"frontend"|"general")
```

This returns skill recommendations, project tree, and code search — all in one optimized call.

Then use the other tools as needed:

| Tool | When to call |
|---|---|
| `agent-guidance-mcp_guidance(operation="search", query=...)` | Find relevant skills and standards |
| `agent-guidance-mcp_project_context(operation="read", ...)` | Read a file before editing |
| `agent-guidance-mcp_workflow_gate(action="set_stage", ...)` | Manage workflow stage lifecycle |
| `agent-guidance-mcp_require_edit_approval(...)` | Verify stage permits edits before writing code |

## Key Concepts

### Priority Gate
`agent-guidance-mcp_task_pipeline` must be called before most tools. This ensures the agent always has project context before acting.

### Workflow Stages
The server enforces a 7-stage lifecycle: `Context → Plan → Ask_Revise → Build → Test_Recheck → Fix → Proposal`. Use `agent-guidance-mcp_workflow_gate` to manage transitions. Edits are only allowed in `Build` stage with `plan_approved=true`.

### Token Optimization
Every MCP response is filtered through an 8-stage pipeline that strips comments, collapses whitespace, and deduplicates output — saving 40-80% of tokens per call.

### Skill Catalog
185 on-demand skills covering backend, frontend, testing, security, DevOps, data, research, and 12+ language ecosystems. Loaded via `agent-guidance-mcp_guidance(operation="get", identifier="<name>")` — no context wasted on unused skills.

## Next Steps

- [Usage Guide](usage.md) — detailed workflow examples
- [MCP Surface](reference/mcp-surface.md) — all tools, resources, and prompts
- [Installation](installation.md) — manual setup and configuration
- [Architecture](ARCHITECTURE.md) — how the server works internally
