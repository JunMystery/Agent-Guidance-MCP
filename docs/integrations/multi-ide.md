# Multi-IDE / Multi-CLI Usage

Agent Guidance MCP runs as a subprocess managed by each IDE or CLI tool. When you use multiple IDEs simultaneously, each one spawns its own server process — meaning the embedding model (466 MB) loads separately per process.

## How It Works

Each IDE registers `agent-guidance-mcp` in its MCP config:

```json
{
  "mcpServers": {
    "agent-guidance-mcp": {
      "command": "agent-guidance-mcp",
      "args": []
    }
  }
}
```

When the IDE starts, it spawns the command as a child process. This is **stdio transport** — the IDE and MCP server communicate over stdin/stdout pipes. Each IDE gets its **own process** with its **own memory space**.

## Memory Impact

| IDEs open | MCP processes | Model instances | Total RAM (model only) |
|---|---|---|---|
| 1 | 1 | 1 | 466 MB |
| 2 | 2 | 2 | 932 MB |
| 3 | 3 | 3 | 1.4 GB |
| 4 | 4 | 4 | 1.86 GB |

The model is loaded lazily on the first `agent-guidance-mcp_guidance(operation="search")` call. If you never use semantic search across all your IDEs, the model never loads and the cost is just the base server process (~30 MB).

## When It Matters

- **You use 2+ IDEs regularly** (e.g., VS Code for frontend + Cursor for backend + Claude Desktop for ad-hoc)
- **You run on memory-constrained hardware** (8-16 GB)
- **You frequently use semantic search** (`agent-guidance-mcp_guidance(search)`) in all IDEs

## When It Doesn't

- **Single IDE user** — one process, one model, no waste
- **You never use `agent-guidance-mcp_guidance(search)`** — model never loads
- **You only open one IDE at a time** — only one process exists
- **16+ GB RAM machine** — 466 MB overhead per additional IDE is negligible

## Which Tools Trigger Model Load

| Tool | Model loaded? | Notes |
|---|---|---|
| `agent-guidance-mcp_task_pipeline` | No | Uses precomputed embeddings JSON |
| `agent-guidance-mcp_guidance(operation="search")` | **Yes** | Loads on first call, cached in process memory |
| `agent-guidance-mcp_guidance(operation="list\|get\|recommend")` | No | Catalog metadata only |
| `agent-guidance-mcp_guidance(operation="docs")` | No | Context7 API, no model needed |
| `agent-guidance-mcp_project_context` (all ops) | No | File system operations |
| `agent-guidance-mcp_session_continuity` | No | JSON state, no model |
| `agent-guidance-mcp_health_check / diagnose` | No | Server info |

## SSE Mode (Not Yet Implemented)

The current server uses **stdio transport only**. A future SSE (Server-Sent Events) transport mode would allow a single long-running daemon process to serve multiple IDE/CLI clients:

```
Current (stdio):                Future (SSE):
VS Code ──→ MCP(A)             VS Code ──┐
Cursor  ──→ MCP(B)             Cursor  ──┤──→ MCP Daemon
Claude  ──→ MCP(C)             Claude  ──┘
```

**Benefits:**
- Single model instance (466 MB total, not N×)
- Single codegraph index (shared across IDEs)
- No duplicate rule/skill deployment

**Cost:**
- You manage the daemon lifecycle (systemd/launchd/auto-start)
- HTTP round-trip latency vs direct pipe
- One process crash takes down all IDEs

**Implementation not started.** If this is a priority for your workflow, see the [GitHub Issues](https://github.com/JunMystery/Agent-Guidance-MCP/issues) or contribute.

## Recommendations

| Setup | Recommendation |
|---|---|
| Single IDE, 16+ GB RAM | No action needed — default stdio mode |
| 2+ IDEs, 16+ GB RAM | Accept the overhead (~466 MB per extra IDE) or close unused IDEs |
| 2+ IDEs, 8-16 GB RAM | Avoid opening multiple IDEs simultaneously, or use one IDE for all work |
| 8 GB or less | Use one IDE at a time. Close other IDEs before opening another |
