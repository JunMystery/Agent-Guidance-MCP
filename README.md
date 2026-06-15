# Agent Guidance MCP (v3.2.0)

[![Python Version](https://img.shields.io/badge/python-3.10%2B-blue)](https://www.python.org/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![MCP Version](https://img.shields.io/badge/mcp-%3E%3D1.0.0-green)](https://modelcontextprotocol.io/)
[![Tests](https://img.shields.io/badge/tests-passing-brightgreen)](#development)

MCP server serving AI agent guidance through the bundled guidance corpus, skill set, prompts, and bounded project-code context tools over **Stdio** transport.

![Agent Guidance MCP Architecture Flowchart](docs/images/architecture-flowchart.png)

## Installation

Automatic install:

```bash
python3 scripts/install-mcp.py        # Linux / macOS
python  scripts/install-mcp.py        # Windows
```

Manual install:

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
npx @modelcontextprotocol/inspector .venv/bin/python -m agent_guidance_mcp
```

Then call `task_pipeline(...)` to load task guidance and bounded project context before editing. See [Usage Guide](docs/usage.md) for practical workflows.

## Documentation

- [Installation](docs/installation.md) - automatic and manual setup.
- [Client Configuration](docs/client-configuration.md) - VS Code, GitHub Copilot, Claude Desktop, Cursor, Gemini-compatible config, and env vars.
- [Usage Guide](docs/usage.md) - quick checks, recommended agent workflows, and examples.
- [MCP Surface Reference](docs/mcp-surface.md) - all tools, prompts, and resources.
- [Project Context Tools](docs/project-context-tools.md) - grouped tree, search, file read, snapshot export, token guidance, and freshness rules.
- [Skill Grouping Audit](docs/skill-grouping-audit.md) - hub-first grouping map, unassigned skills, and future merge candidates.
- [Development Guide](docs/development.md) - tests, project structure, and maintainer notes.
- [Repo Map For Agents](docs/repo-map-for-agents.md) - existing repository orientation notes.
- [Rules Generation](docs/rules-generation.md) - existing rules-generation documentation.
- [Skills Overview](docs/SKILLS_OVERVIEW.md) - generated index of packaged skills.

## MCP Surface

Grouped tools:

- `task_pipeline(task, project_path, focus, code_query, include_tree, include_ui, limit)`
- `guidance(operation, query, identifier, category, kind, limit, include_content)`
- `project_context(operation, project_path, query, relative_path, start_line, max_lines, max_depth, output_path, max_file_bytes, max_total_bytes, limit)`
- `ui_ux(operation, query, domain, stack, project_name, output_format, limit)`

`task_pipeline` is the recommended first call. Skill recommendations prefer domain hubs first; load a hub first, then load deep skills only as needed. `ui_ux` is backed by the repo-owned `ui-ux-pro-max` skill and its internal references. `workflow_prompt(mode, subject, target)` replaces the individual workflow prompts. Full details are in [MCP Surface Reference](docs/mcp-surface.md).

## Development

```bash
python -m pytest
```

The test suite verifies catalog discovery, MCP handler registration, standards search, recommendation behavior, and project-context tooling. See [Development Guide](docs/development.md) for more detail.
