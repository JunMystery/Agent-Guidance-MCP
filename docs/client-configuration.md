# Client Configuration

[Back to README](../README.md)

This server is designed for MCP clients that launch tools over Stdio. Configure clients to run the package module from the repository virtual environment.

## VS Code And GitHub Copilot

The repository includes a workspace MCP settings file under `.vscode/mcp.json`.

When you open this repository in VS Code with GitHub Copilot installed:

1. Run the installer (`python scripts/install-mcp.py`) to create `.venv` and automatically configure both `.vscode/mcp.json` and your global VS Code user config (`mcp.json`).
2. Open the repository folder in VS Code.
3. Let VS Code detect the MCP server from `.vscode/mcp.json`.
4. Trust the server when prompted.
5. Use the tools and prompts from Copilot Chat.

By default, running the installer script automatically configures `.vscode/mcp.json` with the correct path for your platform:

On Windows:
```json
"command": "${workspaceFolder}/.venv/Scripts/python.exe"
```

On Linux/macOS:
```json
"command": "${workspaceFolder}/.venv/bin/python"
```

## Generic MCP Client Config

Use this structure for Claude Desktop, Cursor, and other MCP-compatible clients.

Linux/macOS:

```json
{
  "mcpServers": {
    "agent-guidance-mcp": {
      "command": "/absolute/path/to/repo/.venv/bin/python",
      "args": ["-m", "agent_guidance_mcp"],
      "env": { "PYTHONPATH": "/absolute/path/to/repo/src" }
    }
  }
}
```

Windows:

```json
{
  "mcpServers": {
    "agent-guidance-mcp": {
      "command": "C:\\absolute\\path\\to\\repo\\.venv\\Scripts\\python.exe",
      "args": ["-m", "agent_guidance_mcp"],
      "env": { "PYTHONPATH": "C:\\absolute\\path\\to\\repo\\src" }
    }
  }
}
```

## Client Notes

- Claude Desktop typically uses a global MCP config file.
- Cursor can use a native MCP config or extension-specific MCP settings.
- Gemini-compatible tools can use a JSON MCP config under the user's Gemini configuration directory.
- Codex can use an MCP server entry in `~/.codex/config.toml` (global) and `.codex/config.toml` (project-local).

The bundled `scripts/install-mcp.py` attempts to configure several common clients automatically.

## Environment Variables

You can customize the MCP server behavior, including path configuration and token optimization thresholds, using environment variables:

### Core Configuration

| Variable | Default | Description |
|---|---|---|
| `PYTHONPATH` | *(required)* | Path to `src/` directory so the `agent_guidance_mcp` package can be found |
| `AGENT_GUIDANCE_ROOT` | auto | Override path to standards corpus when it is outside this repo workspace |

```json
"env": {
  "PYTHONPATH": "/path/to/repo/src",
  "AGENT_GUIDANCE_ROOT": "/path/to/Agent-Guidance"
}
```

### Token Optimization & Compression

Configure these variables in your MCP client's `"env"` settings block (e.g. inside `mcp.json` or `config.json`):

| Variable | Default | Description |
|---|---|---|
| `AGENT_GUIDANCE_TOKEN_OPT` | `1` | `0` = disable all optimization, compression & analytics |
| `AGENT_GUIDANCE_FILTER_LEVEL` | `minimal` | `none` / `minimal` / `aggressive` — comment/docstring stripping depth |
| `AGENT_GUIDANCE_DOC_MAX_TOKENS` | `8000` | Max token cap for standard documents |
| `AGENT_GUIDANCE_SKILL_MAX_TOKENS` | `8000` | Max token cap for skill guides |
| `AGENT_GUIDANCE_TRACK_SAVINGS` | `1` | `0` = disable session-level token analytics |

**`AGENT_GUIDANCE_FILTER_LEVEL` details:**

| Value | Effect |
|---|---|
| `none` | No code filter or compression |
| `minimal` (default) | Strips block headers and whitespace, preserves inline comments |
| `aggressive` | Strips all docstrings and comments for maximum compression |

### CLI Arguments

Pass these in the `"args"` array. They take precedence over environment variables.

| Flag | Effect |
|---|---|
| `--root <path>` | Override standards corpus path (overrides `AGENT_GUIDANCE_ROOT`) |
| `--no-optimize` | Disable all token optimization & tracking |

```json
"args": ["-m", "agent_guidance_mcp", "--root", "/custom/path", "--no-optimize"]
```

### Programmatic-Only Configuration

These `TokenOptimizationConfig` fields in `src/agent_guidance_mcp/token_config.py` are not exposed via environment variables — modify the source to change them.

| Field | Default | Description |
|---|---|---|
| `workflow_max_tokens` | `8000` | Max token cap for workflow prompts |
| `source_file_max_tokens` | `3000` | Max tokens per source file |
| `snapshot_total_max_tokens` | `50000` | Total token budget for project snapshots |
| `snapshot_per_file_max_tokens` | `2000` | Per-file token cap in snapshots |
| `task_pipeline_max_tokens` | `12000` | Max token cap for `task_pipeline` output |
| `guidance_content_max_tokens` | `4000` | Max token cap for guidance response content |
| `strip_comments` | `true` | Strip comments during optimization |
| `collapse_whitespace` | `true` | Collapse redundant whitespace |
| `deduplicate_lines` | `true` | Deduplicate repeated lines |
| `strip_html_comments` | `true` | Strip `<!-- -->` HTML comments |
| `strip_badge_images` | `true` | Strip shield.io badge images |

### Predefined Profiles

Available programmatically via `TokenOptimizationConfig`:

| Profile | Effect |
|---|---|
| `TokenOptimizationConfig.disabled()` | `enabled=False`, `track_savings=False` — disables all optimization and tracking |
| `TokenOptimizationConfig.aggressive()` | `source_filter_level="aggressive"`, budgets halved |

### Project Context

Project-context tools should receive an explicit `project_path` argument. Avoid relying on the MCP process current working directory when scanning a user project.

## Related Docs

- [Installation](installation.md)
- [Usage Guide](usage.md)
- [MCP Surface Reference](mcp-surface.md)
