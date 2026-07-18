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

GUIDANCE_OPERATIONS = ("list", "get", "search", "recommend", "reason", "docs", "feedback", "workflow", "precode", "verify")
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
    next_workflow_mode,
    PRECODE_CATEGORY_QUERIES,
    infer_verification_kind,
    _is_codegen_task,
    infer_codegen_plan,
)
from .response_optimizer import optimize_markdown

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
    rating: int = 0,
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
                    from .server import get_usage
                    _usage = get_usage()
                    if _usage is not None:
                        for sub_id in resolved:
                            _usage.record_skill_load(sub_id, project_path=None)

            cycles = _detect_dependency_cycles(catalog, entry.identifier)
            if cycles:
                result["dependency_cycles_detected"] = cycles
        return result

    if operation_key == "search":
        if not query:
            return _missing_argument("query", operation_key)
        results = catalog.search_entries(query=query, limit=limit, kind=kind)
        if not results:
            return {
                "success": False,
                "message": f"No skills or standards found matching query: '{query}'",
                "suggestions": ["Try broader terms", "Filter by category or kind", "Run list operation to view all"]
            }
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
        if not query:
            return _missing_argument("query", operation_key)
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

    if operation_key == "feedback":
        if not identifier:
            return _missing_argument("identifier", operation_key)
        from .server import get_usage
        usage = get_usage()
        if usage is None:
            return {"success": False, "error": "Usage tracking not started."}
        usage.record_feedback(identifier, rating, query or None)
        return {
            "success": True,
            "skill_id": identifier,
            "rating": max(1, min(5, int(rating))),
            "message": "Feedback recorded — future recommendations will learn from it.",
        }

    if operation_key == "workflow":
        mode = (identifier or query or "plan")
        return workflow_mode(catalog, mode=mode, subject=query or "", target="", config=config)

    if operation_key == "precode":
        if not query:
            return _missing_argument("query", operation_key)
        return precode_check(catalog, task=query, config=config)

    if operation_key == "verify":
        if not query:
            return _missing_argument("query", operation_key)
        return verify(catalog, changes=query, config=config)

    # Fallback: "recommend" operation (the only remaining unhandled op)
    if not query:
        return _missing_argument("query", operation_key)

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

    def _project_error(exc: Exception, details: dict[str, object] | None = None) -> dict[str, object]:
        return {
            "success": False,
            "error": type(exc).__name__,
            "message": str(exc),
            "operation": operation_key,
            **({"details": details} if details else {})
        }

    if operation_key == "tree":
        return project_context_helpers.get_project_tree(
            project_path=project_path, max_depth=max_depth
        )

    if operation_key == "search":
        if not query:
            return _missing_argument("query", operation_key)
        try:
            return project_context_helpers.search_project_code(
                project_path=project_path, query=query, limit=limit
            )
        except (ValueError, FileNotFoundError, NotADirectoryError) as exc:
            return _project_error(exc, {"project_path": project_path})

    if operation_key == "read":
        if not relative_path:
            return _missing_argument("relative_path", operation_key)
        try:
            return project_context_helpers.read_project_file(
                project_path=project_path,
                relative_path_value=relative_path,
                start_line=start_line,
                max_lines=max_lines,
                config=config,
                tracker=tracker,
            )
        except (ValueError, FileNotFoundError, NotADirectoryError) as exc:
            return _project_error(exc, {"relative_path": relative_path})

    if operation_key == "symbols":
        if not relative_path:
            return _missing_argument("relative_path", operation_key)
        try:
            return project_context_helpers.extract_project_symbols(
                project_path=project_path,
                relative_path_value=relative_path,
                config=config,
                tracker=tracker,
            )
        except (ValueError, FileNotFoundError, NotADirectoryError) as exc:
            return _project_error(exc, {"relative_path": relative_path})

    if operation_key == "references":
        if not query:
            return _missing_argument("query", operation_key)
        try:
            return project_context_helpers.find_project_references(
                project_path=project_path,
                symbol_name=query,
                limit=limit,
                config=config,
                tracker=tracker,
            )
        except (ValueError, FileNotFoundError, NotADirectoryError) as exc:
            return _project_error(exc, {"symbol_name": query})

    if operation_key == "structure":
        if not relative_path:
            return _missing_argument("relative_path", operation_key)
        try:
            return project_context_helpers.get_project_file_structure(
                project_path=project_path,
                relative_path_value=relative_path,
                config=config,
                tracker=tracker,
            )
        except (ValueError, FileNotFoundError, NotADirectoryError) as exc:
            return _project_error(exc, {"relative_path": relative_path})

    if operation_key == "callers":
        if not query:
            return _missing_argument("query", operation_key)
        try:
            return project_context_helpers.get_project_callers(
                project_path=project_path,
                symbol_id=query,
                config=config,
                tracker=tracker,
            )
        except (ValueError, FileNotFoundError, NotADirectoryError) as exc:
            return _project_error(exc, {"symbol_id": query})

    if operation_key == "callees":
        if not query:
            return _missing_argument("query", operation_key)
        try:
            return project_context_helpers.get_project_callees(
                project_path=project_path,
                symbol_id=query,
                config=config,
                tracker=tracker,
            )
        except (ValueError, FileNotFoundError, NotADirectoryError) as exc:
            return _project_error(exc, {"symbol_id": query})

    if operation_key == "diff":
        try:
            return project_context_helpers.get_project_diff(
                project_path=project_path,
                config=config,
                tracker=tracker,
            )
        except (ValueError, FileNotFoundError, NotADirectoryError) as exc:
            return _project_error(exc, {"project_path": project_path})

    try:
        return project_context_helpers.export_project_snapshot(
            project_path=project_path,
            output_path=output_path,
            max_file_bytes=max_file_bytes,
            max_total_bytes=max_total_bytes,
            config=config,
            tracker=tracker,
        )
    except (PermissionError, OSError, ValueError, FileNotFoundError, NotADirectoryError) as exc:
        return {
            "success": False,
            "error": type(exc).__name__,
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
    tracker: TokenTracker | None = None,
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

    result: dict[str, object]
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
        if isinstance(data, dict) and data.get("success") is False:
            result = data
        else:
            result = {"success": True, "session": data}
    elif operation_key == "load":
        data = load_session(project_path=validated_root)
        if data and not data.get("_corrupt"):
            result = {"success": True, "session_active": True, "session": data}
        elif data and data.get("_corrupt"):
            result = {
                "success": False,
                "error": "SESSION_CORRUPT",
                "message": data.get("error", "Session file unreadable"),
            }
        else:
            result = {"success": True, "session_active": False, "message": "No active session found."}
    else:  # clear
        cleared = clear_session(project_path=validated_root)
        result = {"success": cleared}
    _record_savings(tracker, "session_continuity", operation_key, result, result, project_path=project_path)
    return result


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

    # Codegen Scaffolding: If task signals code-creation intent, attach a plan
    if _is_codegen_task(f"{task} {focus} {active_code_query or ''}"):
        try:
            codegen_plan = infer_codegen_plan(
                catalog=catalog,
                task=task,
                frameworks=detected_tags,
                skills=sorted_skills,
            )
            result["codegen_plan"] = codegen_plan
        except Exception:
            pass

    optimized = optimize_response(
        result, max_content_tokens=config.task_pipeline_max_tokens, config=config
    )
    _record_savings(tracker, "task_pipeline", "task_pipeline", result, optimized, project_path=project_path)
    return optimized


def auto_context(
    catalog: StandardsCatalog,
    task: str = "",
    project_path: str = ".",
    config: TokenOptimizationConfig | None = None,
) -> dict[str, object]:
    """Lightweight context enrichment for gate auto-pass. Runs framework
    detection + essential skills (no tree/code search)."""
    config = config or load_config_from_env()
    try:
        frameworks = _detect_frameworks(project_path)
    except Exception:
        frameworks = []
    ecosystem_str = " ".join(frameworks)
    weighted_task = f"{task} {ecosystem_str}".strip() if ecosystem_str else task

    try:
        context = catalog.recommend_context(
            task=weighted_task or "general development",
            limit=5,
            include_content=False,
            config=config,
        )
    except Exception as e:
        context = {"error": str(e), "recommendations": []}

    return {
        "task": task or "auto-detected",
        "frameworks": frameworks,
        "context": context,
    }


def workflow_mode(
    catalog: StandardsCatalog,
    mode: str = "plan",
    subject: str = "",
    target: str = "",
    config: TokenOptimizationConfig | None = None,
) -> dict[str, object]:
    """Load a workflow mode with enriched context and next-step suggestion."""
    config = config or load_config_from_env()
    mode_key = mode.lower().replace("-", "_")

    from .server import WORKFLOW_MODE_MAP  # lazy import — safe at call time

    if mode_key not in WORKFLOW_MODE_MAP:
        supported = ", ".join(sorted(WORKFLOW_MODE_MAP))
        return {
            "success": False,
            "error": f"Unsupported workflow mode: {mode}",
            "supported": supported,
        }

    try:
        raw_content = catalog.read_path(WORKFLOW_MODE_MAP[mode_key])
    except Exception as exc:
        return {"success": False, "error": f"Workflow '{mode}' could not be loaded: {exc}"}

    if config.enabled:
        content = optimize_markdown(
            raw_content,
            max_tokens=config.workflow_max_tokens,
            config=config,
        )
    else:
        content = raw_content

    result: dict[str, object] = {
        "mode": mode_key,
        "content": content,
        "suggested_next": next_workflow_mode(mode_key),
    }
    if subject:
        result["subject"] = subject
    if target:
        result["target"] = target

    return result


def precode_check(
    catalog: StandardsCatalog,
    task: str,
    paths: str = "",
    config: TokenOptimizationConfig | None = None,
) -> dict[str, object]:
    """Return a structured checklist for code-writing readiness.

    Searches the catalog for relevant coding conventions, security patterns,
    testing patterns, architecture guidelines, and deployment rules based
    on the task and detected frameworks.
    """
    config = config or load_config_from_env()
    try:
        frameworks = _detect_frameworks(".")
    except Exception:
        frameworks = []

    weighted_task = f"{task} {' '.join(frameworks)}".strip()

    checklist: dict[str, list[dict[str, object]]] = {}
    for category, query in PRECODE_CATEGORY_QUERIES.items():
        try:
            results = catalog.search_entries(query, limit=3, kind="skill")
            if results:
                checklist[category] = [
                    {"identifier": r["identifier"], "title": r.get("title", ""),
                     "description": r.get("description", "")}
                    for r in results
                ]
        except Exception:
            checklist[category] = []

    return {
        "task": task,
        "frameworks": frameworks,
        "checklist": checklist,
        "total_checks": sum(len(v) for v in checklist.values()),
    }


def verify(
    catalog: StandardsCatalog,
    changes: str,
    kind: str | None = None,
    config: TokenOptimizationConfig | None = None,
) -> dict[str, object]:
    """Return verification steps after code changes.

    Infers verification kind from changed files (test / review / security /
    audit / deploy) and loads relevant patterns from the catalog.
    """
    config = config or load_config_from_env()
    verification_kind = infer_verification_kind(changes, kind)

    query_map = {
        "test": "testing tdd verification",
        "review": "code review quality patterns",
        "security": "security audit review",
        "audit": "audit review checklist health",
        "deploy": "deployment ci cd patterns",
    }
    search_query = query_map.get(verification_kind, "review patterns")

    try:
        skill_results = catalog.search_entries(search_query, limit=4, kind="skill")
        doc_results = catalog.search_entries(search_query, limit=3, kind="doc")
    except Exception:
        skill_results = []
        doc_results = []

    skills_list = [
        {"identifier": r["identifier"], "title": r.get("title", ""),
         "description": r.get("description", "")}
        for r in skill_results
    ]
    docs_list = [
        {"identifier": r["identifier"], "title": r.get("title", ""),
         "description": r.get("description", "")}
        for r in doc_results
    ]

    next_mode = next_workflow_mode(verification_kind)

    return {
        "kind": verification_kind,
        "changes": changes,
        "patterns": skills_list,
        "references": docs_list,
        "suggested_next": next_mode,
        "suggested_workflow": f"workflow(mode='{verification_kind}')" if verification_kind in (
            "test", "review", "audit", "deploy"
        ) else None,
    }
