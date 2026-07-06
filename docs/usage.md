# Usage Guide

[Back to README](../README.md)

Use this MCP server to give AI agents standards guidance, skill references, workflow prompts, and bounded access to project code context.

## Verify With MCP Inspector

After installation, launch the MCP Inspector:

```bash
npx @modelcontextprotocol/inspector .venv/bin/python -m agent_guidance_mcp
```

Open the printed URL, usually `http://localhost:5173`, and inspect the registered tools, prompts, and resources.

## Recommended Agent Workflow

At the start of a coding session:

1. Call `task_pipeline(task, project_path)` to load relevant standards, skill recommendations, and an initial project tree.
2. For large refactors, upgrades, audits, or unfamiliar code, also use `project_context(operation="search", project_path=..., query=...)` and `project_context(operation="snapshot", project_path=...)` when a reusable overview is useful.
3. Before editing any file, inspect the current target file with `project_context(operation="read", project_path=..., relative_path=...)` or an equivalent file-read tool.
4. Use `ui_ux(operation=...)` for frontend, design-system, branding, landing page, dashboard, or slide guidance.
5. Run the smallest relevant verification command after changes.

Avoid repeated broad scans during the same session unless the project changed significantly.

## Example: Standards Context

```json
{
  "task": "Build a secure API endpoint with tests",
  "project_path": "/absolute/path/to/project",
  "limit": 6
}
```

Use `task_pipeline` for the normal first call. Use `guidance(operation="recommend", query=...)` when you only need catalog recommendations.

## Example: Project Code Context

Inspect project structure:

```json
{
  "operation": "tree",
  "project_path": "/absolute/path/to/project",
  "max_depth": 3
}
```

Search for a feature or symbol:

```json
{
  "operation": "search",
  "project_path": "/absolute/path/to/project",
  "query": "refresh token auth",
  "limit": 10
}
```

Read the current source file before editing:

```json
{
  "operation": "read",
  "project_path": "/absolute/path/to/project",
  "relative_path": "src/auth/token_service.py",
  "start_line": 1,
  "max_lines": 160
}
```

## Example: Workflow Prompt

Use `workflow_prompt(mode, subject, target)` when the client exposes MCP prompts.

For example, `workflow_prompt(mode="plan", subject="Build billing export")` loads the planning workflow capsule and appends the subject.

## Token Guidance

Prefer narrow calls:

- Use `max_depth=3` or `max_depth=4` for initial tree scans.
- Use `limit=10` or `limit=20` for search.
- Use `max_lines=120` to `200` for file reads unless a broader range is necessary.
- Avoid exporting full snapshots for small one-file tasks.

See [Project Context Tools](reference/project-context-tools.md) for details on snapshot freshness and token cost.

## Related Docs

- [MCP Surface](reference/mcp-surface.md)
- [Project Context Tools](reference/project-context-tools.md)
- [Development Guide](development.md)
