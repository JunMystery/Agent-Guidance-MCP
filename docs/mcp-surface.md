# MCP Surface Reference

[Back to README](../README.md)

This page lists the public MCP resources, grouped tools, and prompt exposed by the server.

## Resources

| Resource | Description |
|---|---|
| `standards://manifest` | JSON manifest for indexed standards, docs, skills, and root reference files. |
| `standards://version` | JSON object with server name, version, and MCP protocol version. |
| `standards://document/{identifier}` | Markdown content for a standards document by slug or identifier. |
| `standards://skill/{name}` | Markdown content for a local on-demand skill capsule by name. |

## Tools

| Tool | Description |
|---|---|
| `task_pipeline(task, project_path=".", focus="general", code_query=None, include_tree=True, include_ui=True, limit=8)` | Recommended first call. Returns standards recommendations, hub skill suggestions, a bounded project tree, optional code-search matches, and optional UI/UX guidance for frontend/design tasks. |
| `guidance(operation, query=None, identifier=None, category=None, kind=None, limit=10, include_content=False)` | Grouped standards catalog operations. |
| `project_context(operation, project_path=".", query=None, relative_path=None, start_line=1, max_lines=300, max_depth=3, output_path=".agent-context/code-snapshot.json", max_file_bytes=200000, max_total_bytes=2000000, limit=20)` | Grouped project tree, search, read, and snapshot operations. |
| `ui_ux(operation, query, domain=None, stack=None, project_name=None, output_format="markdown", limit=3)` | Grouped UI/UX Pro Max search, design-system, and slide guidance operations. |
| `token_stats()` | Return token optimization statistics for this session. No parameters. |
| `health_check()` | Return server health status and basic metadata. No parameters. |

## Tool Operations

`guidance` supports:

- `list`: replaces `list_entries(category, kind)`.
- `get`: replaces `get_entry(identifier)`.
- `search`: replaces `search_entries(query, limit, kind)`.
- `recommend`: replaces `recommend_context(task, limit)`.

`project_context` supports:

- `tree`: replaces `get_project_tree(project_path, max_depth)`.
- `search`: replaces `search_project_code(project_path, query, limit)`.
- `read`: replaces `read_project_file(project_path, relative_path, start_line, max_lines)`.
- `snapshot`: replaces `export_project_snapshot(project_path, output_path, max_file_bytes, max_total_bytes)`.

`ui_ux` supports:

- `search`: replaces `search_ui_ux_guidance(query, domain, stack, limit)`.
- `design_system`: replaces `generate_ui_ux_design_system(query, project_name, output_format)`.
- `slides`: replaces `search_slide_guidance(query, domain, limit)`.

Unsupported operations return an error payload with `supported_operations`.

## Prompt

| Prompt | Description |
|---|---|
| `workflow_prompt(mode="plan", subject="", target="")` | Loads one workflow prompt by mode. Supported modes: `init`, `plan`, `design`, `visualize`, `code`, `run`, `test`, `deploy`, `debug`, `refactor`, `audit`, `rollback`, `recap`, `review`. |

The individual workflow prompts are no longer public MCP prompts. Use `workflow_prompt` with the desired `mode`.

## Recommended Ordering

For most coding tasks, start with:

1. `task_pipeline(task, project_path, code_query=None)`
2. `project_context(operation="search", project_path=..., query=...)` when more code context is needed.
3. `project_context(operation="read", project_path=..., relative_path=...)` before editing a target file.
4. `ui_ux(operation="search" | "design_system" | "slides", query=...)` for frontend, brand, dashboard, landing page, or presentation work.
5. `health_check()` for server status verification.
6. `token_stats()` for session token optimization statistics.
7. Edit only the files needed.
8. Run targeted verification.

## Skill Recommendations

`task_pipeline` is the recommended first call. It auto-discovers relevant skills from the 168-skill catalog using task-keyword matching and TASK_ANCHORS. Individual skills are directly loadable by identifier via `guidance(operation="get", identifier=...)` or via the `standards://skill/{name}` resource.

## Related Docs

- [Usage Guide](usage.md)
- [Project Context Tools](project-context-tools.md)
- [Client Configuration](client-configuration.md)
