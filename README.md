# Agent Guidance MCP

![Status](https://img.shields.io/badge/status-stable-brightgreen)
[![Python Version](https://img.shields.io/badge/python-3.10%2B-blue)](https://www.python.org/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![MCP Version](https://img.shields.io/badge/mcp-%3E%3D1.0.0-green)](https://modelcontextprotocol.io/)
![GitHub license](https://img.shields.io/github/license/JunMystery/Agent-Guidance-MCP)
![GitHub repo size](https://img.shields.io/github/repo-size/JunMystery/Agent-Guidance-MCP)
[![Ko-fi](https://img.shields.io/badge/Ko--fi-F16061?logo=ko-fi&logoColor=white)](https://ko-fi.com/JunMystery)

MCP server serving AI agent guidance through a **168-skill catalog**, bundled guidance corpus, workflow prompts, and bounded project-code context tools over **Stdio** transport.

Skills are sourced from [Everything Claude Code (ECC) v2.0.0](https://github.com/affaan-m/ECC) and community contributions, covering backend, frontend, testing, security, DevOps, data, research, and 12+ language ecosystems.

![Agent Guidance MCP Architecture Flowchart](docs/images/architecture-flowchart.png)

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

*This requires no prior Python installation; the script will automatically bootstrap `uv` (a single-binary Python toolchain) to run the server if Python is not present.*

### Upgrading

**To update the server and refresh your IDE registrations:**
Simply rerun the installation command.

**To update the standards catalog & skills only (one line):**
```bash
agent-guidance-mcp --update
```

**To update the executable code package only:**
```bash
uv tool update agent-guidance-mcp
```

### Uninstalling

**Linux / macOS (Bash):**
```bash
curl -fsSL https://raw.githubusercontent.com/JunMystery/Agent-Guidance-MCP/main/scripts/uninstall.sh | bash
```

**Windows (CMD / PowerShell):**
```cmd
powershell -Command "irm https://raw.githubusercontent.com/JunMystery/Agent-Guidance-MCP/main/scripts/uninstall.ps1 | iex"
```

*This will automatically remove the server registration from all detected IDE client configurations, clean up the global rules in `AGENTS.md`, remove the database/skills directory (`~/.agent-guidance`), and uninstall the executable.*

### Manual / Local Developer Install

```bash
python -m venv .venv
.venv/bin/pip install -e ".[dev]"      # Linux / macOS
.venv\Scripts\pip install -e ".[dev]"  # Windows
```

Run the server module:

```bash
agent-guidance-mcp
.venv/bin/python -m agent_guidance_mcp          # Linux / macOS
.venv\Scripts\python.exe -m agent_guidance_mcp  # Windows
```

To point the server to a different standards corpus, set:

```bash
AGENT_GUIDANCE_ROOT=/path/to/Agent-Guidance
```

Platform notes and client-specific setup are covered in [Installation](docs/installation.md) and [Client Configuration](docs/client-configuration.md).

## Quick Start

Run the server through an MCP client, or verify it locally with MCP Inspector:

```bash
DANGEROUSLY_OMIT_AUTH=true npx @modelcontextprotocol/inspector .venv/bin/python -m agent_guidance_mcp
```

Then call `task_pipeline(...)` to load task guidance and bounded project context before editing. See [Usage Guide](docs/usage.md) for practical workflows.

## Documentation

- [Installation](docs/installation.md) - automatic and manual setup.
- [Client Configuration](docs/client-configuration.md) - VS Code, GitHub Copilot, Claude Desktop, Cursor, Gemini-compatible config, and env vars.
- [Usage Guide](docs/usage.md) - quick checks, recommended agent workflows, and examples.
- [MCP Surface Reference](docs/mcp-surface.md) - all tools, prompts, and resources.
- [Project Context Tools](docs/project-context-tools.md) - grouped tree, search, file read, snapshot export, token guidance, and freshness rules.
- [Integrated Repositories](docs/integrated-repositories.md) - third-party repos bundled, depended on, or running alongside.
- [Development Guide](docs/development.md) - tests, project structure, and maintainer notes.
- [Repo Map For Agents](docs/repo-map-for-agents.md) - existing repository orientation notes.
- [MCP Integrations Guide](agent-guidance/mcp-integrations/README.md) - SQLite caching, CodeGraph-like AST parsing, and Context7 docs details.

## MCP Surface

Tools:

- `task_pipeline(task, project_path, focus, code_query, include_tree, include_ui, limit)` — **Recommended first call.** Prepares task recommendations, project context, and optional UI guidance.
- `guidance(operation, query, identifier, category, kind, limit, include_content)` — Standards catalog operations: list, get, search, recommend, reason, and **docs** (live library docs via Context7).
- `project_context(operation, project_path, query, relative_path, start_line, max_lines, max_depth, output_path, max_file_bytes, max_total_bytes, limit)` — Bounded project context: tree, search, read, snapshot, **symbols**, **references**, **structure**, **callers**, and **callees** (local SQLite CodeGraph engine).
- `ui_ux(operation, query, domain, stack, project_name, output_format, limit)` — UI/UX Pro Max: search, design system, slides.
- `health_check()` — Server health status and metadata.
- `token_stats()` — Token optimization statistics for the session.

Resources:

- `standards://manifest` — Indexed standards manifest (JSON)
- `standards://skill/{name}` — On-demand skill capsule (Markdown)
- `standards://document/{identifier}` — Standards document by slug (Markdown)
- `standards://version` — Server version info (JSON)

Prompt:

- `workflow_prompt(mode, subject, target)` — Load a workflow prompt by mode (plan, test, deploy, debug, etc.)

## Development

```bash
python -m pytest
```

The test suite verifies catalog discovery, MCP handler registration, standards search, recommendation behavior, and project-context tooling. See [Development Guide](docs/development.md) for more detail.
