# Project Context Tools

[Back to README](../README.md)

The `project_context` grouped tool gives AI agents a bounded, repeatable way to inspect a project before editing code. It is intentionally lightweight: no database, no GraphRAG, no UI, and no LLM calls.

## Why These Tools Exist

Agents often waste tokens by reading unrelated files or guessing the project structure. These tools encourage a narrower workflow:

1. Inspect the tree.
2. Search for relevant files.
3. Read the current target file.
4. Export a snapshot only when reusable context is useful.

The tools skip common dependency/cache folders, binary files, and generated snapshot output.

## Agent Instruction Policy

At the start of each coding session, call `task_pipeline(task, project_path)`. It includes recommendations and can include the bounded project tree.

For large refactors, upgrades, audits, or unfamiliar code, also use `project_context(operation="search", project_path=..., query=...)` and `project_context(operation="snapshot", project_path=...)` when a reusable overview is useful.

Before editing any file, inspect the current target file with `project_context(operation="read", project_path=..., relative_path=...)` or an equivalent file-read tool.

Avoid repeated broad scans during the same session unless the project changed significantly.

## `project_context(operation="tree")`

Returns a bounded source tree for a project.

Example:

```json
{
  "operation": "tree",
  "project_path": "/absolute/path/to/project",
  "max_depth": 3
}
```

Use this at the beginning of a coding session or when entering an unfamiliar repository.

The result includes entries with:

- `path`
- `type`
- `language_hint` for files
- `size_bytes` for files

## `project_context(operation="search")`

Searches source files and returns ranked snippets.

Example:

```json
{
  "operation": "search",
  "project_path": "/absolute/path/to/project",
  "query": "auth refresh token",
  "limit": 10
}
```

Use this to find relevant symbols, feature names, error messages, endpoints, or configuration keys.

The result includes:

- `path`
- `language_hint`
- `score`
- `line`
- `snippet`

## `project_context(operation="read")`

Reads a bounded range from one text file inside the project.

Example:

```json
{
  "operation": "read",
  "project_path": "/absolute/path/to/project",
  "relative_path": "src/auth/token_service.py",
  "start_line": 1,
  "max_lines": 160
}
```

Use this immediately before editing a file. It validates that the requested file stays inside the project root.

## `project_context(operation="snapshot")`

Writes a bounded JSON snapshot to the project.

Example:

```json
{
  "operation": "snapshot",
  "project_path": "/absolute/path/to/project"
}
```

Default output:

```text
.agent-context/code-snapshot.json
```

The snapshot contains:

- `project_root`
- `generated_at`
- `limits`
- `tree`
- `files`

Each file entry includes:

- `path`
- `language_hint`
- `size_bytes`
- `truncated`
- `content`

## Snapshot Freshness

Treat snapshots as cached overview context, not the source of truth.

Before editing a file, the agent should still use `project_context(operation="read", ...)` or an equivalent current file-read tool. This avoids making changes from stale snapshot content.

Use `project_context(operation="snapshot", ...)` when:

- onboarding into a larger project,
- preparing an audit,
- handing context to another agent,
- working across multiple related tasks,
- summarizing a project for later retrieval.

Avoid exporting snapshots for every small prompt.

## Token Guidance

Recommended defaults:

```json
{
  "max_depth": 3,
  "limit": 10,
  "max_lines": 120
}
```

Use larger values only when the task requires it.

`project_context(operation="snapshot", ...)` has byte limits:

```json
{
  "max_file_bytes": 200000,
  "max_total_bytes": 2000000
}
```

These limits protect the agent context window, but a snapshot can still be much larger than a targeted search/read workflow.

## Safety Rules

- Pass an explicit absolute `project_path` whenever possible.
- Do not rely on the MCP process current working directory for multi-project workflows.
- Do not edit code based only on snapshot content.
- Prefer `project_context(operation="search", ...)` and `project_context(operation="read", ...)` for focused task work.

## Related Docs

- [Usage Guide](usage.md)
- [MCP Surface Reference](mcp-surface.md)
- [Repo Map For Agents](repo-map-for-agents.md)
