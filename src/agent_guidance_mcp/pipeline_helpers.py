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
    
    # Track modification times of any common project manifest files
    manifests = [
        "package.json", "pyproject.toml", "requirements.txt", "Cargo.toml", "Gemfile",
        "pubspec.yaml", "go.mod", "composer.json", "build.gradle", "build.gradle.kts",
        "pom.xml", "Podfile", "Package.swift"
    ]
    max_mtime = base_path.stat().st_mtime
    for manifest in manifests:
        p = base_path / manifest
        if p.is_file():
            try:
                max_mtime = max(max_mtime, p.stat().st_mtime)
            except OSError:
                pass
                
    cache_key = (key, max_mtime)
    if cache_key in _FRAMEWORK_CACHE:
        val = _FRAMEWORK_CACHE.pop(cache_key)
        _FRAMEWORK_CACHE[cache_key] = val
        return list(val)
    
    while len(_FRAMEWORK_CACHE) >= _FRAMEWORK_CACHE_MAX:
        _FRAMEWORK_CACHE.popitem(last=False)
    
    detected: list[str] = []
    
    # 1. Javascript/Node (package.json)
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
        except (OSError, json.JSONDecodeError):
            pass

    # 2. Python (pyproject.toml / requirements.txt)
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

    # 3. Rust (Cargo.toml)
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

    # 4. Ruby (Gemfile)
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

    # 5. Flutter/Dart (pubspec.yaml)
    pubspec = base_path / "pubspec.yaml"
    if pubspec.is_file():
        try:
            content = pubspec.read_text(encoding="utf-8").lower()
            detected.append("dart")
            if "flutter" in content:
                detected.append("flutter")
        except OSError:
            pass

    # 6. Go (go.mod)
    go_mod = base_path / "go.mod"
    if go_mod.is_file():
        try:
            content = go_mod.read_text(encoding="utf-8").lower()
            detected.append("go")
            detected.append("golang")
            if "gin-gonic" in content or "github.com/gin-gonic" in content:
                detected.append("gin")
        except OSError:
            pass

    # 7. PHP (composer.json)
    composer = base_path / "composer.json"
    if composer.is_file():
        try:
            with open(composer, "r", encoding="utf-8") as f:
                data = json.load(f)
            reqs = data.get("require", {}) or {}
            detected.append("php")
            if "laravel/framework" in reqs:
                detected.append("laravel")
            elif "symfony/framework-bundle" in reqs or "symfony/symfony" in reqs:
                detected.append("symfony")
        except (OSError, json.JSONDecodeError):
            pass

    # 8. JVM (Java/Kotlin) (build.gradle / build.gradle.kts / pom.xml)
    gradle = base_path / "build.gradle"
    gradle_kts = base_path / "build.gradle.kts"
    pom = base_path / "pom.xml"
    jvm_content = ""
    for path in (gradle, gradle_kts, pom):
        if path.is_file():
            try:
                jvm_content += path.read_text(encoding="utf-8").lower()
            except OSError:
                pass
    if jvm_content:
        detected.append("java")
        if "kotlin" in jvm_content:
            detected.append("kotlin")
        if "spring-boot" in jvm_content or "springboot" in jvm_content:
            detected.append("springboot")
        if "com.android.tools" in jvm_content or "android" in jvm_content:
            detected.append("android")

    # 9. iOS/Swift (Podfile / Package.swift / xcodeproj check)
    podfile = base_path / "Podfile"
    pkg_swift = base_path / "Package.swift"
    has_xcodeproj = any(base_path.glob("*.xcodeproj"))
    if podfile.is_file() or pkg_swift.is_file() or has_xcodeproj:
        detected.append("swift")
        detected.append("ios")
        if pkg_swift.is_file():
            try:
                content = pkg_swift.read_text(encoding="utf-8").lower()
                if "swiftui" in content:
                    detected.append("swiftui")
            except OSError:
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


def _detect_dependency_cycles(catalog: object, start_identifier: str) -> list[str]:
    """Detect dependency cycles starting from start_identifier via DFS."""
    visited: set[str] = set()
    on_stack: set[str] = set()
    cycles: list[str] = []

    def _dfs(identifier: str) -> None:
        if identifier in on_stack:
            cycles.append(identifier)
            return
        if identifier in visited:
            return
        visited.add(identifier)
        on_stack.add(identifier)
        try:
            entry = catalog.get_entry(identifier)
            for dep in entry.dependencies:
                _dfs(dep)
        except KeyError:
            pass
        on_stack.discard(identifier)

    _dfs(start_identifier)
    return cycles
