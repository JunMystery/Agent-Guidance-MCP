"""Helper functions, cache configurations, and sort functions extracted from pipelines.py."""

import json
from collections import OrderedDict
from pathlib import Path
from typing import Any
from .token_analytics import TokenTracker

_FRAMEWORK_CACHE_MAX = 10
_FRAMEWORK_CACHE: OrderedDict[tuple[str, float], list[str]] = OrderedDict()

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

LIFECYCLE_ORDER = [
    "spec-driven-development",
    "planning-and-task-breakdown",
    "intent-driven-development",
    "api-design",
    "frontend-patterns",
    "backend-patterns",
    "incremental-implementation",
    "tdd-workflow",
    "verification-loop",
    "browser-qa",
    "code-review-and-quality",
    "shipping-and-launch",
]

def lifecycle_sort_key(skill_id: str) -> int:
    try:
        return LIFECYCLE_ORDER.index(skill_id)
    except ValueError:
        return len(LIFECYCLE_ORDER)

def _is_ui_task(value: str) -> bool:
    terms = set()
    for t in value.split():
        cleaned = t.strip(".,:;()[]{}").lower()
        terms.add(cleaned)
        terms.update(cleaned.split("-"))
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

def _detect_frameworks(project_path: str) -> list[str]:
    from .project_scan import resolve_project_root
    
    base_path = resolve_project_root(project_path)
    key = str(base_path.resolve())
    
    pkg_json = base_path / "package.json"
    mtime = pkg_json.stat().st_mtime if pkg_json.is_file() else base_path.stat().st_mtime
    cache_key = (key, mtime)
    if cache_key in _FRAMEWORK_CACHE:
        val = _FRAMEWORK_CACHE.pop(cache_key)
        _FRAMEWORK_CACHE[cache_key] = val
        return list(val)
    
    while len(_FRAMEWORK_CACHE) >= _FRAMEWORK_CACHE_MAX:
        _FRAMEWORK_CACHE.popitem(last=False)
    
    detected: list[str] = []
    
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
        except (OSError, json.JSONDecodeError):
            pass

    pyproject = base_path / "pyproject.toml"
    req_txt = base_path / "requirements.txt"
    py_content = ""
    if pyproject.is_file():
        try:
            py_content += pyproject.read_text(encoding="utf-8")
        except (OSError, json.JSONDecodeError):
            pass
    if req_txt.is_file():
        try:
            py_content += req_txt.read_text(encoding="utf-8")
        except (OSError, json.JSONDecodeError):
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
        except (OSError, json.JSONDecodeError):
            pass

    gemfile = base_path / "Gemfile"
    if gemfile.is_file():
        try:
            content = gemfile.read_text(encoding="utf-8").lower()
            if "rails" in content:
                detected.append("rails")
            if "sinatra" in content:
                detected.append("sinatra")
        except (OSError, json.JSONDecodeError):
            pass

    result = list(dict.fromkeys(detected))
    _FRAMEWORK_CACHE[cache_key] = list(result)
    return result


def _wrap_response(
    data: dict[str, object] | list[dict[str, object]],
    tool: str = "",
    operation: str = "",
    backend: str = "python",
    warnings: list[str] | None = None,
    error: str | None = None,
) -> dict[str, object]:
    """Wrap tool output in a standard response envelope."""
    result: dict[str, object] = {
        "data": data,
        "metadata": {
            "tool": tool,
            "operation": operation,
            "backend": backend,
        },
        "error": error,
    }
    if warnings:
        result["warnings"] = warnings
    return result
