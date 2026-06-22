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
            
            # Recursive dependency injection with topological sorting
            if entry.dependencies:
                deps_dict: dict[str, dict[str, object]] = {}
                resolved: set[str] = {entry.identifier}
                order: list[str] = []

                def visit(dep_id: str) -> None:
                    if dep_id in resolved:
                        return
                    try:
                        dep_entry = catalog.get_entry(dep_id)
                    except KeyError:
                        return
                    resolved.add(dep_id)
                    for child_id in dep_entry.dependencies:
                        visit(child_id)
                    order.append(dep_id)
                    
                    dep_dict_entry = dep_entry.to_dict()
                    dep_dict_entry["content"] = catalog.read_entry(dep_entry.identifier, config=config)
                    deps_dict[dep_id] = dep_dict_entry

                for dep_id in entry.dependencies:
                    visit(dep_id)

                if deps_dict:
                    result["resolved_dependencies"] = deps_dict
                    result["dependency_execution_order"] = order
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


def _detect_frameworks(project_path: str) -> list[str]:
    import json
    from pathlib import Path
    
    detected = []
    base_path = Path(project_path)
    
    # 1. Node/JS frameworks via package.json
    pkg_json = base_path / "package.json"
    if pkg_json.is_file():
        try:
            with open(pkg_json, "r", encoding="utf-8") as f:
                data = json.load(f)
            deps = data.get("dependencies", {}) or {}
            dev_deps = data.get("devDependencies", {}) or {}
            all_deps = {**deps, **dev_deps}
            
            js_frameworks = {
                "react": "react",
                "next": "nextjs",
                "vue": "vue",
                "nuxt": "nuxt",
                "svelte": "svelte",
                "angular": "angular",
                "express": "express",
                "nestjs": "nestjs",
                "vite": "vite",
                "tailwindcss": "tailwindcss",
            }
            for dep_key, tag in js_frameworks.items():
                if dep_key in all_deps or any(dep_key in str(k) for k in all_deps):
                    detected.append(tag)
        except Exception:
            pass

    # 2. Python frameworks via pyproject.toml, requirements.txt
    pyproject = base_path / "pyproject.toml"
    req_txt = base_path / "requirements.txt"
    py_content = ""
    if pyproject.is_file():
        try:
            py_content += pyproject.read_text(encoding="utf-8")
        except Exception:
            pass
    if req_txt.is_file():
        try:
            py_content += req_txt.read_text(encoding="utf-8")
        except Exception:
            pass
            
    if py_content:
        py_frameworks = {
            "django": "django",
            "fastapi": "fastapi",
            "flask": "flask",
            "pytest": "pytest",
            "numpy": "numpy",
            "torch": "pytorch",
        }
        py_content_lower = py_content.lower()
        for dep_key, tag in py_frameworks.items():
            if dep_key in py_content_lower:
                detected.append(tag)

    # 3. Rust frameworks via Cargo.toml
    cargo_toml = base_path / "Cargo.toml"
    if cargo_toml.is_file():
        try:
            content = cargo_toml.read_text(encoding="utf-8").lower()
            rust_frameworks = {
                "tokio": "tokio",
                "serde": "serde",
                "axum": "axum",
                "actix": "actix",
            }
            for dep_key, tag in rust_frameworks.items():
                if dep_key in content:
                    detected.append(tag)
        except Exception:
            pass

    # 4. Ruby frameworks via Gemfile
    gemfile = base_path / "Gemfile"
    if gemfile.is_file():
        try:
            content = gemfile.read_text(encoding="utf-8").lower()
            if "rails" in content:
                detected.append("rails")
            if "sinatra" in content:
                detected.append("sinatra")
        except Exception:
            pass

    return list(dict.fromkeys(detected))

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
    
    detected_tags = _detect_frameworks(project_path)
    ecosystem_str = " ".join(detected_tags)
    weighted_task = f"{focus} {ecosystem_str} {task}".strip()
    recommendations_payload = catalog.recommend_context(task=weighted_task, limit=limit)
    
    result: dict[str, object] = {
        "task": task,
        "focus": focus,
        "recommendations": recommendations_payload,
    }

    # Dynamic Intent Routing: Auto-detect code query if none provided
    active_code_query = code_query
    if not active_code_query:
        active_code_query = extract_code_terms(task)

    if include_tree:
        result["project_tree"] = project_context_helpers.get_project_tree(
            project_path=project_path,
            max_depth=project_context_helpers.DEFAULT_MAX_DEPTH,
        )

    if active_code_query:
        result["code_search"] = project_context_helpers.search_project_code(
            project_path=project_path,
            query=active_code_query,
            limit=min(max(1, limit), 20),
        )

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
    lifecycle_order = [
        "spec-driven-development",
        "planning-and-task-breakdown",
        "intent-driven-development",
        "api-design",
        "frontend-hub",
        "backend-hub",
        "incremental-implementation",
        "test-driven-development",
        "framework-testing",
        "browser-qa",
        "code-review-and-quality",
        "shipping-and-launch",
    ]
    recs = recommendations_payload.get("recommendations", [])
    skills_to_chain = [r["identifier"] for r in recs if r.get("kind") == "skill"]
    
    def lifecycle_sort_key(skill_id: str) -> int:
        try:
            return lifecycle_order.index(skill_id)
        except ValueError:
            return len(lifecycle_order)
            
    sorted_skills = sorted(skills_to_chain, key=lifecycle_sort_key)
    if sorted_skills:
        result["execution_sequence"] = sorted_skills

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
    from .utils import record_savings
    record_savings(tracker, tool_name, operation, original, optimized)

