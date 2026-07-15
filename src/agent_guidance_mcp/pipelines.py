"""Grouped MCP pipeline dispatchers."""


import json
from typing import Any, cast

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
    _detect_dependency_cycles,
    _is_ui_task,
    _unsupported_operation,
    _missing_argument,
    _record_savings,
    _wrap_response,
    lifecycle_sort_key,
)

SESSION_CONTINUITY_OPERATIONS = ("save", "load", "clear")

def guidance(
    catalog: StandardsCatalog,
    operation: str,
    query: str | None = None,
    identifier: str | None = None,
    category: str | None = None,
    kind: str | None = None,
    limit: int = 10,
    include_content: bool = False,
    resolve_dependencies: bool = False,
    config: TokenOptimizationConfig | None = None,
    tracker: TokenTracker | None = None,
) -> dict[str, object] | list[dict[str, object]]:
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
            return {
                "success": False,
                "error": "NOT_FOUND",
                "message": str(exc),
                "details": {"identifier": identifier}
            }
        result: dict[str, object] = entry.to_dict()
        if include_content:
            raw_content = catalog.read_entry(entry.identifier, optimize=False)
            result["content"] = catalog.read_entry(entry.identifier, config=config)
            _record_savings(tracker, "guidance", operation_key, raw_content, str(result["content"]))
            
            # Resolve transitive dependencies if requested
            if resolve_dependencies:
                resolved: dict[str, str] = {}
                def _resolve(dep_id: str) -> None:
                    if dep_id == entry.identifier or dep_id in resolved:
                        return
                    try:
                        dep_entry = catalog.get_entry(dep_id)
                        dep_content = catalog.read_entry(dep_id, config=config)
                        resolved[dep_id] = dep_content
                        for sub_dep in dep_entry.dependencies:
                            _resolve(sub_dep)
                    except KeyError:
                        pass
                for dep in entry.dependencies:
                    _resolve(dep)
                if resolved:
                    result["resolved_dependencies"] = resolved

            cycles = _detect_dependency_cycles(catalog, entry.identifier)
            if cycles:
                result["dependency_cycles_detected"] = cycles
        return result

    if not query:
        return _missing_argument("query", operation_key)

    if operation_key == "search":
        results = catalog.search_entries(query=query, limit=limit, kind=kind)
        try:
            from .llm_selector import LLMSelector
            selector = LLMSelector()
            candidate_list = [
                {"identifier": r["identifier"], "title": r.get("title", ""), "description": r.get("description", "")}
                for r in results
            ]
            llm_picks = set(selector.select(query, candidate_list, limit=3))
            if llm_picks:
                llm_boosted = [r for r in results if r["identifier"] in llm_picks]
                rest = [r for r in results if r["identifier"] not in llm_picks]
                results = llm_boosted + rest
        except Exception:
            pass
        optimized = optimize_response({"results": results}, config=config)
        _record_savings(tracker, "guidance", operation_key, results, optimized["results"])
        return cast(list[dict[str, object]], optimized["results"])

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
        return {
            "success": False,
            "error": "WRITE_FAILED",
            "message": f"Failed to write snapshot: {exc}",
            "details": {"output_path": output_path}
        }


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
        return {
            "success": False,
            "error": "GENERATION_FAILED",
            "message": str(exc),
            "details": {"supported_formats": ["markdown", "ascii"]}
        }
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


def session_continuity(
    operation: str,
    project_path: str = ".",
    task: str | None = None,
    checklist: list[dict] | None = None,
    current_step_index: int = 0,
    metadata: dict | None = None,
) -> dict[str, object]:
    """Persist or recover task session state for continuity."""
    if operation is None:
        return _missing_argument("operation", "session_continuity")
    operation_key = operation.lower()
    if operation_key not in SESSION_CONTINUITY_OPERATIONS:
        return _unsupported_operation(operation, SESSION_CONTINUITY_OPERATIONS)

    from .session import save_session, load_session, clear_session
    from .project_scan import resolve_project_root

    try:
        validated_root = str(resolve_project_root(project_path))
    except Exception as e:
        return {
            "success": False,
            "error": "INVALID_PATH",
            "message": f"Invalid project_path: {e}",
            "details": {"project_path": project_path}
        }

    if operation_key == "save":
        if not task:
            return {
                "success": False,
                "error": "MISSING_ARGUMENT",
                "message": "task is required for save operation",
                "details": {"argument": "task"}
            }
        data = save_session(
            project_path=validated_root,
            task=task,
            checklist=checklist or [],
            current_step_index=current_step_index,
            metadata=metadata,
        )
        return {"success": True, "session": data}
    elif operation_key == "load":
        data = load_session(project_path=validated_root)
        if data:
            return {"success": True, "session_active": True, "session": data}
        return {"success": True, "session_active": False, "message": "No active session found."}
    else:  # clear
        cleared = clear_session(project_path=validated_root)
        return {"success": cleared}


def task_pipeline(
    catalog: StandardsCatalog,
    task: str,
    project_path: str = ".",
    focus: str = "general",
    code_query: str | None = None,
    include_tree: bool = True,
    include_ui: bool = True,
    limit: int = 8,
    timeout: float | None = 30.0,
    config: TokenOptimizationConfig | None = None,
    tracker: TokenTracker | None = None,
) -> dict[str, object]:
    """Prepare task recommendations, project context, and optional UI guidance in one call."""
    from .text import extract_code_terms
    config = config or load_config_from_env()

    # Ensure local skills embedded sequentially before thread pool to avoid
    # subprocess/pytorch deadlocks inside parallel workers.
    catalog._ensure_local_skills_embedded()

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
        "recommendations": lambda: catalog.recommend_context(
            task=weighted_task, limit=limit, include_content=True, config=config
        ),
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

    concurrent_results = parallel_run(concurrent_tasks, timeout=timeout)

    timed_out = [k for k, v in concurrent_results.items() if isinstance(v, TimeoutError)]
    recommendations = concurrent_results.get("recommendations", {})
    if not isinstance(recommendations, dict) or isinstance(recommendations, Exception):
        recommendations = {"error": str(recommendations), "recommendations": []}

    result: dict[str, object] = {
        "task": task,
        "focus": focus,
        "recommendations": recommendations,
    }
    if timed_out:
        result["warning"] = f"timeout on: {', '.join(timed_out)}"
    if "project_tree" in concurrent_results:
        tree_res = concurrent_results["project_tree"]
        if isinstance(tree_res, TimeoutError):
            result["project_tree"] = {"error": f"Project tree timed out after {timeout}s", "tree": []}
        elif isinstance(tree_res, Exception):
            result["project_tree"] = {"error": f"Failed to build project tree: {tree_res}"}
        else:
            result["project_tree"] = tree_res
    if "code_search" in concurrent_results:
        search_res = concurrent_results["code_search"]
        if isinstance(search_res, TimeoutError):
            result["code_search"] = {"error": f"Code search timed out after {timeout}s", "matches": []}
        elif isinstance(search_res, Exception):
            result["code_search"] = {"error": f"Failed to perform code search: {search_res}", "matches": []}
        else:
            result["code_search"] = search_res

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
