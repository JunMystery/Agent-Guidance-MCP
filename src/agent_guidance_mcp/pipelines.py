"""Grouped MCP pipeline dispatchers."""

from __future__ import annotations

import json
from typing import Any

from . import project_context as project_context_helpers
from . import ui_ux as ui_ux_helpers
from .catalog import StandardsCatalog
from .response_optimizer import estimate_tokens, optimize_response
from .token_analytics import TokenTracker
from .token_config import TokenOptimizationConfig, load_config_from_env

GUIDANCE_OPERATIONS = ("list", "get", "search", "recommend")
PROJECT_CONTEXT_OPERATIONS = ("tree", "search", "read", "snapshot")
UI_UX_OPERATIONS = ("search", "design_system", "slides")

UI_TASK_TERMS = {
    "a11y",
    "accessibility",
    "brand",
    "branding",
    "color",
    "component",
    "components",
    "dashboard",
    "design",
    "frontend",
    "landing",
    "slides",
    "typography",
    "ui",
    "ux",
    "visual",
}


def guidance(
    catalog: StandardsCatalog,
    operation: str,
    query: str | None = None,
    identifier: str | None = None,
    category: str | None = None,
    kind: str | None = None,
    limit: int = 10,
    include_content: bool = False,
    config: TokenOptimizationConfig | None = None,
    tracker: TokenTracker | None = None,
) -> dict[str, object] | list[dict[str, object]]:
    """Dispatch standards catalog guidance operations."""
    config = config or load_config_from_env()
    operation_key = operation.lower()
    if operation_key not in GUIDANCE_OPERATIONS:
        return _unsupported_operation(operation, GUIDANCE_OPERATIONS)

    if operation_key == "list":
        return catalog.list_entries(category=category, kind=kind)

    if operation_key == "get":
        if not identifier:
            return _missing_argument("identifier", operation_key)
        try:
            entry = catalog.get_entry(identifier)
        except KeyError as exc:
            return {"error": str(exc), "identifier": identifier}
        result: dict[str, object] = entry.to_dict()
        if include_content:
            raw_content = catalog.read_entry(entry.identifier, optimize=False)
            result["content"] = catalog.read_entry(entry.identifier, config=config)
            _record_savings(tracker, "guidance", operation_key, raw_content, str(result["content"]))
        return result

    if not query:
        return _missing_argument("query", operation_key)

    if operation_key == "search":
        results = catalog.search_entries(query=query, limit=limit, kind=kind)
        optimized = optimize_response({"results": results}, config=config)
        _record_savings(tracker, "guidance", operation_key, results, optimized["results"])
        return optimized["results"]  # type: ignore[return-value]

    return catalog.recommend_context(task=query, limit=limit)


def project_context(
    operation: str,
    project_path: str = ".",
    query: str | None = None,
    relative_path: str | None = None,
    start_line: int = 1,
    max_lines: int = project_context_helpers.DEFAULT_MAX_READ_LINES,
    max_depth: int = project_context_helpers.DEFAULT_MAX_DEPTH,
    output_path: str = project_context_helpers.DEFAULT_SNAPSHOT_PATH,
    max_file_bytes: int = project_context_helpers.DEFAULT_MAX_FILE_BYTES,
    max_total_bytes: int = project_context_helpers.DEFAULT_MAX_TOTAL_BYTES,
    limit: int = 20,
    config: TokenOptimizationConfig | None = None,
    tracker: TokenTracker | None = None,
) -> dict[str, object]:
    """Dispatch bounded project-context operations."""
    config = config or load_config_from_env()
    operation_key = operation.lower()
    if operation_key not in PROJECT_CONTEXT_OPERATIONS:
        return _unsupported_operation(operation, PROJECT_CONTEXT_OPERATIONS)

    if operation_key == "tree":
        return project_context_helpers.get_project_tree(
            project_path=project_path, max_depth=max_depth
        )

    if operation_key == "search":
        if not query:
            return _missing_argument("query", operation_key)
        return project_context_helpers.search_project_code(
            project_path=project_path, query=query, limit=limit
        )

    if operation_key == "read":
        if not relative_path:
            return _missing_argument("relative_path", operation_key)
        return project_context_helpers.read_project_file(
            project_path=project_path,
            relative_path_value=relative_path,
            start_line=start_line,
            max_lines=max_lines,
            config=config,
            tracker=tracker,
        )

    return project_context_helpers.export_project_snapshot(
        project_path=project_path,
        output_path=output_path,
        max_file_bytes=max_file_bytes,
        max_total_bytes=max_total_bytes,
        config=config,
        tracker=tracker,
    )


def ui_ux(
    catalog: StandardsCatalog,
    operation: str,
    query: str,
    domain: str | None = None,
    stack: str | None = None,
    project_name: str | None = None,
    output_format: str = "markdown",
    limit: int = 3,
    config: TokenOptimizationConfig | None = None,
    tracker: TokenTracker | None = None,
) -> dict[str, object]:
    """Dispatch UI/UX Pro Max operations."""
    config = config or load_config_from_env()
    operation_key = operation.lower()
    if operation_key not in UI_UX_OPERATIONS:
        return _unsupported_operation(operation, UI_UX_OPERATIONS)
    if not query:
        return _missing_argument("query", operation_key)

    if operation_key == "search":
        result = ui_ux_helpers.search_ui_ux_guidance(
            root=catalog.root,
            query=query,
            domain=domain,
            stack=stack,
            limit=limit,
        )
        optimized = optimize_response(result, config=config)
        _record_savings(tracker, "ui_ux", operation_key, result, optimized)
        return optimized

    if operation_key == "slides":
        result = ui_ux_helpers.search_slide_guidance(
            root=catalog.root,
            query=query,
            domain=domain,
            limit=limit,
        )
        optimized = optimize_response(result, config=config)
        _record_savings(tracker, "ui_ux", operation_key, result, optimized)
        return optimized

    try:
        content = ui_ux_helpers.generate_ui_ux_design_system(
            root=catalog.root,
            query=query,
            project_name=project_name,
            output_format=output_format,
        )
    except ValueError as exc:
        return {"error": str(exc), "supported_formats": ["markdown", "ascii"]}
    result = {
        "operation": operation_key,
        "query": query,
        "project_name": project_name,
        "output_format": output_format,
        "content": content,
    }
    optimized = optimize_response(result, config=config)
    _record_savings(tracker, "ui_ux", operation_key, result, optimized)
    return optimized


def task_pipeline(
    catalog: StandardsCatalog,
    task: str,
    project_path: str = ".",
    focus: str = "general",
    code_query: str | None = None,
    include_tree: bool = True,
    include_ui: bool = True,
    limit: int = 8,
    config: TokenOptimizationConfig | None = None,
    tracker: TokenTracker | None = None,
) -> dict[str, object]:
    """Prepare one-call task context with recommendations and optional project/UI context."""
    config = config or load_config_from_env()
    weighted_task = f"{focus} {task}".strip()
    result: dict[str, object] = {
        "task": task,
        "focus": focus,
        "recommendations": catalog.recommend_context(task=weighted_task, limit=limit),
    }

    if include_tree:
        result["project_tree"] = project_context_helpers.get_project_tree(
            project_path=project_path,
            max_depth=project_context_helpers.DEFAULT_MAX_DEPTH,
        )

    if code_query:
        result["code_search"] = project_context_helpers.search_project_code(
            project_path=project_path,
            query=code_query,
            limit=min(max(1, limit), 20),
        )

    if include_ui and _is_ui_task(" ".join([task, focus, code_query or ""])):
        result["ui_ux"] = {
            "skill": "ui-ux-pro-max",
            "guidance": ui_ux_helpers.search_ui_ux_guidance(
                root=catalog.root,
                query=task,
                limit=min(max(1, limit), 3),
            ),
        }

    optimized = optimize_response(
        result, max_content_tokens=config.task_pipeline_max_tokens, config=config
    )
    _record_savings(tracker, "task_pipeline", "task_pipeline", result, optimized)
    return optimized


def _is_ui_task(value: str) -> bool:
    terms = {term.strip(".,:;()[]{}").lower() for term in value.split()}
    return bool(terms & UI_TASK_TERMS)


def _unsupported_operation(operation: str, supported: tuple[str, ...]) -> dict[str, object]:
    return {
        "error": f"Unsupported operation: {operation}",
        "supported_operations": list(supported),
    }


def _missing_argument(argument: str, operation: str) -> dict[str, Any]:
    return {
        "error": f"{argument} is required for operation '{operation}'.",
        "required_argument": argument,
        "operation": operation,
    }


def _record_savings(
    tracker: TokenTracker | None,
    tool_name: str,
    operation: str,
    original: object,
    optimized: object,
) -> None:
    if tracker is None:
        return
    original_text = original if isinstance(original, str) else json.dumps(original, default=str)
    optimized_text = optimized if isinstance(optimized, str) else json.dumps(optimized, default=str)
    tracker.record(
        tool_name=tool_name,
        operation=operation,
        original_tokens=estimate_tokens(original_text),
        optimized_tokens=estimate_tokens(optimized_text),
    )
