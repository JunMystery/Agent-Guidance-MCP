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

CODEGEN_TERMS = {
    "add",
    "create",
    "implement",
    "build",
    "write",
    "develop",
    "generate",
    "scaffold",
    "new",
    "feature",
    "endpoint",
    "api",
    "function",
    "class",
    "module",
    "service",
    "component",
    "handler",
    "middleware",
    "route",
    "controller",
    "auth",
    "login",
    "crud",
    "fix",
    "patch",
    "refactor",
}

NEXT_WORKFLOW_MODE: dict[str, str] = {
    "init": "plan",
    "plan": "design",
    "design": "visualize",
    "visualize": "code",
    "code": "test",
    "test": "review",
    "review": "deploy",
    "deploy": "audit",
    "run": "debug",
    "debug": "refactor",
    "refactor": "test",
    "audit": "rollback",
    "rollback": "recap",
    "brainstorm": "plan",
}

def next_workflow_mode(mode: str) -> str | None:
    return NEXT_WORKFLOW_MODE.get(mode)


def _is_codegen_task(value: str) -> bool:
    """Heuristic: task signals code-creation/editing intent."""
    terms = set()
    for t in value.split():
        cleaned = t.strip(".,:;()[]{}").lower()
        terms.add(cleaned)
        terms.update(cleaned.split("-"))
    return bool(terms & CODEGEN_TERMS)

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
        "success": False,
        "error": "UNSUPPORTED_OPERATION",
        "message": f"Unsupported operation: {operation}",
        "details": {
            "operation": operation,
            "supported_operations": list(supported),
        },
    }

def _missing_argument(argument: str, operation: str) -> dict[str, Any]:
    return {
        "success": False,
        "error": "MISSING_ARGUMENT",
        "message": f"{argument} is required for operation '{operation}'.",
        "details": {
            "required_argument": argument,
            "operation": operation,
        },
    }

def _record_savings(
    tracker: TokenTracker | None,
    tool_name: str,
    operation: str,
    original: object,
    optimized: object,
    project_path: str | None = None,
) -> None:
    from .utils import record_savings
    record_savings(tracker, tool_name, operation, original, optimized)

    from .usage import get_usage
    usage = get_usage()
    if usage is not None:
        from .response_optimizer import estimate_tokens
        orig_str = original if isinstance(original, str) else str(original)
        opt_str = optimized if isinstance(optimized, str) else str(optimized)
        tok_orig = estimate_tokens(orig_str)
        tok_opt = estimate_tokens(opt_str)
        usage.record_tool_call(
            tool_name, operation,
            tokens_original=tok_orig, tokens_optimized=tok_opt,
            project_path=project_path,
        )

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


VERIFICATION_KINDS = ("test", "review", "security", "audit", "deploy")

VERIFICATION_KIND_EXTENSIONS: dict[str, str] = {
    ".test.js": "test",
    ".spec.js": "test",
    ".test.ts": "test",
    ".spec.ts": "test",
    "test_": "test",
    "_test.": "test",
    ".py": "review",
    ".js": "review",
    ".ts": "review",
    ".tsx": "review",
    ".jsx": "review",
    ".java": "review",
    ".rs": "review",
    ".go": "review",
    ".rb": "review",
    ".php": "review",
    ".kt": "review",
    ".swift": "review",
    ".rs": "review",
    "Dockerfile": "deploy",
    "docker-compose": "deploy",
    ".yaml": "audit",
    ".yml": "audit",
    ".json": "audit",
    ".toml": "audit",
}

PRECODE_CATEGORY_QUERIES: dict[str, str] = {
    "coding_conventions": "coding standards conventions patterns",
    "security": "security checklist review",
    "testing": "testing patterns tdd",
    "architecture": "architecture design patterns",
    "deployment": "deployment deployment ci cd",
}


def infer_verification_kind(changes: str, kind: str | None = None) -> str:
    """Infer the verification kind from changed file paths or explicit kind."""
    if kind and kind in VERIFICATION_KINDS:
        return kind
    changes_lower = changes.lower()
    for pattern, vkind in VERIFICATION_KIND_EXTENSIONS.items():
        if pattern.lower() in changes_lower:
            return vkind
    return "review"


def infer_codegen_plan(
    catalog: object,
    task: str,
    frameworks: list[str],
    skills: list[str],
) -> dict[str, object]:
    """Build a lightweight implementation plan for a code-creation task.

    Returns ordered phases (spec → implement → test → verify → ship) with
    the matched skills attached to each phase. Frameworks seed suggested
    libraries; skills seed recommended patterns.
    """
    ecosystem = " ".join(frameworks)
    weighted = f"{task} {ecosystem}".strip()

    plan_phases: list[dict[str, object]] = [
        {"phase": "spec", "goal": "Clarify requirements and interface contract",
         "skills": _pick_skills(skills, "spec")},
        {"phase": "implement", "goal": "Write the minimal working code",
         "skills": _pick_skills(skills, "implement")},
        {"phase": "test", "goal": "Add tests, run the suite",
         "skills": _pick_skills(skills, "test")},
        {"phase": "verify", "goal": "Lint, review, security pass",
         "skills": _pick_skills(skills, "verify")},
        {"phase": "ship", "goal": "Document + commit + open PR",
         "skills": _pick_skills(skills, "ship")},
    ]

    suggestions: list[str] = []
    if frameworks:
        suggestions.append(f"Ecosystem detected: {', '.join(frameworks)} — prefer native stdlib before adding deps")
    if skills:
        suggestions.append(f"Load skills via guidance(operation='get', identifier='<id>', include_content=True): {', '.join(skills[:3])}")
    suggestions.append("Run guidance(operation='precode', query=task) before editing; run guidance(operation='verify', query=changes) after")
    suggestions.append("Before any file edits: call workflow_gate(action='status') "
                       "to verify stage is 'Build' with plan_approved=true.")

    return {
        "is_codegen": True,
        "task": task,
        "frameworks": frameworks,
        "phases": plan_phases,
        "suggestions": suggestions,
        "next_tool": "guidance(operation='precode')",
    }


def _pick_skills(skills: list[str], phase: str) -> list[str]:
    """Attach a subset of skills to a lifecycle phase by keyword match."""
    phase_keywords = {
        "spec": ("spec", "plan", "api-design", "intent"),
        "implement": ("frontend", "backend", "incremental", "tdd"),
        "test": ("tdd", "verification", "test"),
        "verify": ("review", "quality", "browser", "audit"),
        "ship": ("shipping", "launch"),
    }
    kws = phase_keywords.get(phase, ())
    matched = [s for s in skills if any(k in s for k in kws)]
    return matched[:3]
