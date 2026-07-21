# Multi-IDE / Multi-CLI Usage

Agent Guidance MCP runs as a subprocess managed by each IDE or CLI tool. When you use multiple IDEs simultaneously, each one spawns its own MCP server process — but the **embedding model is shared** via a local HTTP daemon.

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

When the IDE starts, it spawns the command as a child process. This is **stdio transport** — the IDE and MCP server communicate over stdin/stdout pipes.

The embedding model is not loaded per-process. Instead, a cross-process **embed daemon** serves all MCP processes:

```
VS Code         → MCP process A ──┐
Cursor          → MCP process B ──┼──► embed_daemon (127.0.0.1)
Claude Desktop  → MCP process C ──┘     │
                                    [SentenceTransformer]
                                    intfloat/multilingual-e5-small
```

## Memory Impact

| IDEs open | MCP processes | Model instances | Total RAM (model only) |
|---|---|---|---|
| 1 | 1 | 1 (daemon) | 466 MB |
| 2 | 2 | 1 (daemon) | 466 MB |
| 3 | 3 | 1 (daemon) | 466 MB |
| 4 | 4 | 1 (daemon) | 466 MB |

The daemon is spawned lazily on the first call to `agent-guidance-mcp_guidance(operation="search")` across any IDE. If you never use semantic search, the model never loads and the cost is just the base server process (~30 MB per IDE).

### How the daemon works

| Layer | Mechanism |
|---|---|
| **Daemon spawn** | First MCP process needing embeddings acquires `~/.agent-guidance/daemon.lock` (fcntl flock) and spawns the daemon subprocess |
| **Service discovery** | Daemon writes `~/.agent-guidance/daemon.json` with its port and PID |
| **Client connection** | All MCP processes POST to `http://127.0.0.1:<port>/embed` |
| **Health checks** | Daemon exposes `GET /health` echoing its PID + `embed_ready`; clients detect stale manifests |
| **Client registration** | Each MCP process calls `POST /register` with its PID; daemon background-reaps dead clients |
| **Auto-shutdown** | Daemon exits after 600s idle or when all clients disconnect (30s grace) |

### Fallback (daemon unavailable)

If the daemon cannot start (lock contention, `AGENT_EMBEDDING_DAEMON=0`, or under pytest), each MCP process falls back to a **process-local singleton** — each loads its own 466 MB model. This is transparent to the caller.

## Which Tools Trigger Model Load

| Tool | Daemon started? | Notes |
|---|---|---|
| `agent-guidance-mcp_task_pipeline` | No | Uses precomputed embeddings JSON |
| `agent-guidance-mcp_guidance(operation="search")` | **Yes** | First call spawns daemon, subsequent calls reuse |
| `agent-guidance-mcp_guidance(operation="list\|get\|recommend")` | No | Catalog metadata only |
| `agent-guidance-mcp_guidance(operation="docs")` | No | Context7 API, no model needed |
| `agent-guidance-mcp_project_context` (all ops) | No | File system operations |
| `agent-guidance-mcp_session_continuity` | No | JSON state, no model |
| `agent-guidance-mcp_workflow_gate` | No | Stage management, no model |
| `agent-guidance-mcp_health_check / diagnose` | No | Server info |

## SSE Mode (Not Yet Implemented)

The current server uses **stdio transport only**. A future SSE (Server-Sent Events) transport mode would allow a single long-running MCP daemon process to serve multiple IDE/CLI clients — sharing not just the embed model but also the MCP server state:

```
Current (stdio):                Future (SSE):
VS Code ──→ MCP(A)             VS Code ──┐
Cursor  ──→ MCP(B)             Cursor  ──┤──→ MCP Daemon
Claude  ──→ MCP(C)             Claude  ──┘
```

**Benefits:**
- Single MCP process (not just single model)
- Single codegraph index (shared across IDEs)
- No duplicate rule/skill deployment

**Cost:**
- You manage the daemon lifecycle (systemd/launchd/auto-start)
- HTTP round-trip latency vs direct pipe
- One process crash takes down all IDEs

**Implementation not started.** The embed daemon already solves the model-sharing problem; SSE would solve the MCP state-sharing problem. If this is a priority for your workflow, see the [GitHub Issues](https://github.com/JunMystery/Agent-Guidance-MCP/issues) or contribute.

## Recommendations

| Setup | Recommendation |
|---|---|
| Single IDE, 16+ GB RAM | No action needed — default stdio mode |
| 2+ IDEs, 16+ GB RAM | Daemon already shares one model — no extra RAM cost |
| 2+ IDEs, 8-16 GB RAM | Daemon keeps model at 466 MB regardless of IDE count |
| 8 GB or less | Daemon still shares, but close unused IDEs to free MCP process memory (~30 MB each) |
