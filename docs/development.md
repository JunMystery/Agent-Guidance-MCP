# Development Guide

[Back to README](../README.md)

This project is a small Python package that exposes Agent Guidance MCP over MCP, backed by the bundled agent guidance corpus.

## Setup

Install the package in editable mode with dev dependencies:

```bash
python -m venv .venv
.venv/bin/pip install -e ".[dev]"
```

On Windows:

```bash
python -m venv .venv
.venv\Scripts\pip install -e ".[dev]"
```

## Source-Only Execution

To run and debug the project directly from the local source directory without installing it globally (ensuring edits are used instantly):

```bash
PYTHONPATH=src python3 -m agent_guidance_mcp --dashboard
```

This works for all commands. Replace `agent-guidance-mcp` with `PYTHONPATH=src python3 -m agent_guidance_mcp`.

## Test

Run the test suite:

```bash
python -m pytest
```

If the system Python does not have `pytest`, use the repository virtual environment:

```bash
.venv/bin/python -m pytest
```

Run a whitespace check before committing:

```bash
git diff --check
```

## Project Structure

```text
Agent-Guidance-MCP/
├── agent-guidance/          # Core standards corpus
├── docs/                        # Maintainer and user documentation
├── karpathy/                    # Karpathy framework references
├── scripts/                     # Installer, launchers, docs generators
├── skills/                      # On-demand skill capsules
├── src/agent_guidance_mcp/  # Python package source
├── tests/                       # Pytest suite
├── PROJECT-STANDARDS.md         # Project-specific agent standards
├── pyproject.toml               # Python package metadata
├── README.md                    # Compact landing page
└── SKILL-REFERENCE.md           # Skill category reference
```

## Core Source Files

- `server.py`: FastMCP registration and MCP surface declarations.
- `catalog.py`: standards catalog indexing, search, and recommendations.
- `paths.py`: standards root discovery and safe corpus path resolution.
- `text.py`: text normalization, snippet, and keyword helpers.
- `agent-guidance-mcp_project_context.py`: public project-context tool helpers.
- `project_scan.py`: project-context traversal and filtering internals.
- `__main__.py`: command-line module launcher.

## Documentation Notes

- Keep `README.md` compact and link to detailed docs.
- Keep generated documentation such as `docs/SKILLS_OVERVIEW.md` managed by its generator.
- Add new user-facing reference docs under `docs/`.
- Use relative Markdown links so GitHub and IDE previews can open files directly.

## Packaging Notes

The wheel includes:

- `SKILL-REFERENCE.md`
- `docs/`
- `karpathy/`
- `skills/`
- `agent-guidance/`

These paths are configured in `pyproject.toml`.

## Version Bump

Update these files when releasing a new version:

| File | Line | Action |
|---|---|---|
| `pyproject.toml` | 7 | Set `version = "X.Y.Z"` |
| `src/agent_guidance_mcp/__init__.py` | 3 | Set `__version__ = "X.Y.Z"` |
| `src/agent_guidance_mcp/dashboard_src/package.json` | 3 | Set `"version": "X.Y.Z"` |

Files that auto-follow via `from . import __version__` (no manual change):
- `server.py`, `dashboard_server.py`, `__main__.py`, `updater.py`

Procedure: `pyproject.toml` → `__init__.py` → `package.json`.

## Related Docs

- [Installation](installation.md)
- [Client Setup](setup/client-configuration.md)
- [MCP Surface](reference/mcp-surface.md)
