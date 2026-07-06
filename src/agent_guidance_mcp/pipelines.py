"""Grouped MCP pipeline dispatchers."""


import json
from typing import Any

from . import project_context as project_context_helpers
from . import ui_ux as ui_ux_helpers
from . import docs as docs_helpers
from .catalog import StandardsCatalog
from .response_optimizer import estimate_tokens, optimize_response
from .token_analytics import TokenTracker
from .token_config import TokenOptimizationConfig, load_config_from_env

GUIDANCE_OPERATIONS = ("list", "get", "search", "recommend", "reason", "docs")
PROJECT_CONTEXT_OPERATIONS = ("tree", "search", "read", "snapshot", "symbols", "references", "structure", "callers", "callees", "diff")
UI_UX_OPERATIONS = ("search", "design_system", "slides")

from .pipeline_helpers import (
    _detect_frameworks,
    _is_ui_task,
    _unsupported_operation,
    _missing_argument,
    _record_savings,
    _wrap_response,
    lifecycle_sort_key,
)

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
) -> dict[str, object]:
    """Dispatch standards catalog guidance operations."""
    if operation is None:
        return _missing_argument("operation", "guidance")
    config = config or load_config_from_env()
    operation_key = operation.lower()
    if operation_key not in GUIDANCE_OPERATIONS:
        return _unsupported_operation(operation, GUIDANCE_OPERATIONS)

    limit = max(1, min(limit, 100))

    if operation_key == "list":
        return {"operation": "list", "entries": catalog.list_entries(category=category, kind=kind)}

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

    if operation_key == "reason":
        result = catalog.recommend_reasoning_framework(task=query)
        optimized = optimize_response(result, config=config)
        _record_savings(tracker, "guidance", operation_key, result, optimized)
        return optimized

    if operation_key == "docs":
        if not query:
            return _missing_argument("query", operation_key)
        if not identifier:
            return _missing_argument("identifier", operation_key)
        return docs_helpers.query_library_docs(
            library_name=identifier,
            query=query,
            config=config,
            tracker=tracker,
        )

    return optimize_response(
        catalog.recommend_context(task=query, limit=limit), config=config
    )


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
    if operation is None:
        return _missing_argument("operation", "project_context")
    config = config or load_config_from_env()
    operation_key = operation.lower()
    if operation_key not in PROJECT_CONTEXT_OPERATIONS:
        return _unsupported_operation(operation, PROJECT_CONTEXT_OPERATIONS)

    limit = max(1, min(limit, 100))

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

    if operation_key == "symbols":
        if not relative_path:
            return _missing_argument("relative_path", operation_key)
        return project_context_helpers.extract_project_symbols(
            project_path=project_path,
            relative_path_value=relative_path,
            config=config,
            tracker=tracker,
        )

    if operation_key == "references":
        if not query:
            return _missing_argument("query", operation_key)
        return project_context_helpers.find_project_references(
            project_path=project_path,
            symbol_name=query,
            limit=limit,
            config=config,
            tracker=tracker,
        )

    if operation_key == "structure":
        if not relative_path:
            return _missing_argument("relative_path", operation_key)
        return project_context_helpers.get_project_file_structure(
            project_path=project_path,
            relative_path_value=relative_path,
            config=config,
            tracker=tracker,
        )

    if operation_key == "callers":
        if not query:
            return _missing_argument("query", operation_key)
        return project_context_helpers.get_project_callers(
            project_path=project_path,
            symbol_id=query,
            config=config,
            tracker=tracker,
        )

    if operation_key == "callees":
        if not query:
            return _missing_argument("query", operation_key)
        return project_context_helpers.get_project_callees(
            project_path=project_path,
            symbol_id=query,
            config=config,
            tracker=tracker,
        )

    if operation_key == "diff":
        return project_context_helpers.get_project_diff(
            project_path=project_path,
            config=config,
            tracker=tracker,
        )

    try:
        return project_context_helpers.export_project_snapshot(
            project_path=project_path,
            output_path=output_path,
            max_file_bytes=max_file_bytes,
            max_total_bytes=max_total_bytes,
            config=config,
            tracker=tracker,
        )
    except (PermissionError, OSError) as exc:
        return {"error": f"Failed to write snapshot: {exc}", "output_path": output_path}


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
    if operation is None:
        return _missing_argument("operation", "ui_ux")
    config = config or load_config_from_env()
    operation_key = operation.lower()
    if operation_key not in UI_UX_OPERATIONS:
        return _unsupported_operation(operation, UI_UX_OPERATIONS)

    limit = max(1, min(limit, 100))

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
    except (ValueError, FileNotFoundError, KeyError) as exc:
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
    """Prepare task recommendations, project context, and optional UI guidance in one call."""
    from .text import extract_code_terms
    config = config or load_config_from_env()
    limit = max(1, min(limit, 100))
    task = task[:10000]
    
    try:
        detected_tags = _detect_frameworks(project_path)
    except (FileNotFoundError, NotADirectoryError, PermissionError):
        detected_tags = []
    ecosystem_str = " ".join(detected_tags)
    weighted_task = f"{focus} {ecosystem_str} {task}".strip()

    # Dynamic Intent Routing: Auto-detect code query if none provided
    active_code_query = code_query
    if not active_code_query:
        active_code_query = extract_code_terms(task)

    from .parallel import parallel_run

    concurrent_tasks: dict[str, object] = {
        "recommendations": lambda: catalog.recommend_context(task=weighted_task, limit=limit),
    }
    if include_tree:
        concurrent_tasks["project_tree"] = lambda: project_context_helpers.get_project_tree(
            project_path=project_path,
            max_depth=project_context_helpers.DEFAULT_MAX_DEPTH,
        )
    if active_code_query:
        concurrent_tasks["code_search"] = lambda: project_context_helpers.search_project_code(
            project_path=project_path,
            query=active_code_query,
            limit=min(max(1, limit), 20),
        )

    concurrent_results = parallel_run(concurrent_tasks)

    recommendations = concurrent_results.get("recommendations", {})
    if not isinstance(recommendations, dict):
        recommendations = {"error": str(recommendations), "recommendations": []}

    result: dict[str, object] = {
        "task": task,
        "focus": focus,
        "recommendations": recommendations,
    }
    if "project_tree" in concurrent_results:
        result["project_tree"] = concurrent_results["project_tree"]
    if "code_search" in concurrent_results:
        result["code_search"] = concurrent_results["code_search"]

    # Dynamic Intent Routing: Check UI signals in prompt and code query
    ui_search_text = " ".join([task, focus, active_code_query or ""])
    if include_ui and _is_ui_task(ui_search_text):
        result["ui_ux"] = {
            "skill": "ui-ux-pro-max",
            "guidance": ui_ux_helpers.search_ui_ux_guidance(
                root=catalog.root,
                query=task,
                limit=min(max(1, limit), 3),
            ),
        }

    # Execution Chaining: Sort recommended skills in lifecycle order
    if isinstance(recommendations, dict):
        recs = recommendations.get("recommendations", [])
    else:
        recs = []
    skills_to_chain = [r["identifier"] for r in recs if r.get("kind") == "skill"]
    
    sorted_skills = sorted(skills_to_chain, key=lifecycle_sort_key)
    if sorted_skills:
        result["execution_sequence"] = sorted_skills

    optimized = optimize_response(
        result, max_content_tokens=config.task_pipeline_max_tokens, config=config
    )
    _record_savings(tracker, "task_pipeline", "task_pipeline", result, optimized)
    return optimized
