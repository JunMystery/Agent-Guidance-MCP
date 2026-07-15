"""Bounded project code context helpers for MCP agents."""


import json
from datetime import datetime, timezone
from pathlib import Path

from .response_optimizer import (
    TokenBudget,
    estimate_tokens,
    optimize_snapshot_content,
    optimize_source_content,
)
from .symbols import extract_symbols, find_references, get_file_structure
from .token_analytics import TokenTracker
from .token_config import TokenOptimizationConfig, load_config_from_env
from .token_filter import FilterLevel
from .content_compressor import is_binary_file, is_likely_binary
from .database import CodeGraphDatabase
from .project_scan import (
    DEFAULT_MAX_DEPTH,
    DEFAULT_MAX_FILE_BYTES,
    DEFAULT_MAX_READ_LINES,
    DEFAULT_MAX_TOTAL_BYTES,
    DEFAULT_SNAPSHOT_PATH,
    build_project_tree,
    ensure_project_file_allowed,
    first_matching_line,
    iter_project_files,
    language_hint,
    read_bounded_text,
    relative_path,
    resolve_inside_project,
    resolve_project_root,
    tokenize,
)

from .project_codegraph import (
    _get_db,
    extract_project_symbols,
    find_project_references,
    get_project_file_structure,
    get_project_callers,
    get_project_callees,
)


def export_project_snapshot(
    project_path: str = ".",
    output_path: str = DEFAULT_SNAPSHOT_PATH,
    max_file_bytes: int = DEFAULT_MAX_FILE_BYTES,
    max_total_bytes: int = DEFAULT_MAX_TOTAL_BYTES,
    config: TokenOptimizationConfig | None = None,
    tracker: TokenTracker | None = None,
) -> dict[str, object]:
    """Write a bounded JSON snapshot of source files and return its manifest."""
    config = config or load_config_from_env()
    root = resolve_project_root(project_path)
    output = resolve_inside_project(root, output_path)
    output_relative = output.relative_to(root).as_posix()
    if not output_relative.startswith(".agent-context/"):
        raise ValueError(
            f"output_path must be within .agent-context/ directory, got {output_relative!r}"
        )
    max_file_bytes = max(1, max_file_bytes)
    max_total_bytes = max(1, max_total_bytes)

    tree = build_project_tree(root, DEFAULT_MAX_DEPTH, excluded_paths={output_relative})
    file_paths = list(iter_project_files(root, excluded_paths={output_relative}))

    def _read_file(path):
        content, truncated = read_bounded_text(path, max_file_bytes)
        if content is None:
            return None
        return {
            "path": relative_path(root, path),
            "language_hint": language_hint(path),
            "size_bytes": path.stat().st_size,
            "truncated": truncated,
            "content": content,
            "content_bytes": len(content.encode("utf-8")),
        }

    from .parallel import parallel_map

    raw_results = parallel_map(_read_file, file_paths)

    files: list[dict[str, object]] = []
    total_content_bytes = 0
    for entry in raw_results:
        if total_content_bytes >= max_total_bytes:
            break
        content_bytes = entry.pop("content_bytes")
        if total_content_bytes + content_bytes > max_total_bytes:
            remaining = max_total_bytes - total_content_bytes
            if remaining <= 0:
                break
            entry["content"] = entry["content"][:remaining]
            entry["truncated"] = True
            content_bytes = remaining
        total_content_bytes += content_bytes
        files.append(entry)

    raw_files = files
    if config.enabled:
        files = optimize_snapshot_content(
            files, max_total_tokens=config.snapshot_total_max_tokens, config=config
        )
        _record_savings(tracker, "project_context", "snapshot", raw_files, files)

    snapshot = {
        "project_root": str(root),
        "generated_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "limits": {
            "max_file_bytes": max_file_bytes,
            "max_total_bytes": max_total_bytes,
        },
        "tree": tree["tree"],
        "files": files,
    }

    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(snapshot, indent=2, sort_keys=True), encoding="utf-8")

    return {
        "project_root": str(root),
        "output_path": output_relative,
        "file_count": len(files),
        "tree_entry_count": len(tree["tree"]),
        "content_bytes": total_content_bytes,
        "limits": snapshot["limits"],
    }


def get_project_tree(
    project_path: str = ".", max_depth: int = DEFAULT_MAX_DEPTH
) -> dict[str, object]:
    """Return a bounded source tree for a project."""
    try:
        root = resolve_project_root(project_path)
    except (NotADirectoryError, FileNotFoundError) as e:
        return {
            "success": False,
            "error": "INVALID_PATH",
            "message": str(e),
            "details": {"project_path": project_path}
        }
    return build_project_tree(root, max(1, max_depth), excluded_paths={DEFAULT_SNAPSHOT_PATH})


def read_project_file(
    project_path: str = ".",
    relative_path_value: str = "",
    start_line: int = 1,
    max_lines: int = DEFAULT_MAX_READ_LINES,
    config: TokenOptimizationConfig | None = None,
    tracker: TokenTracker | None = None,
) -> dict[str, object]:
    """Read a bounded line range from one text file inside a project."""
    config = config or load_config_from_env()
    if not relative_path_value:
        raise ValueError("relative_path is required.")

    root = resolve_project_root(project_path)
    path = resolve_inside_project(root, relative_path_value)
    ensure_project_file_allowed(root, path)

    start_line = max(1, start_line)
    max_lines = max(1, max_lines)
    selected: list[str] = []
    truncated = False

    with path.open("r", encoding="utf-8", errors="replace") as file:
        for line_number, line in enumerate(file, start=1):
            if line_number < start_line:
                continue
            if len(selected) >= max_lines:
                truncated = True
                break
            selected.append(line.rstrip("\n"))

    end_line = start_line + len(selected) - 1 if selected else min(start_line - 1, line_number)
    content = "\n".join(selected)
    if is_binary_file(path) or is_likely_binary(content):
        optimized = content
        original_tokens = estimate_tokens(content)
        token_stats = {
            "original_tokens": original_tokens,
            "optimized_tokens": original_tokens,
            "savings_pct": 0,
            "binary": True,
        }
    elif config.enabled:
        optimized, token_stats = optimize_source_content(
            content, language_hint(path), FilterLevel.MINIMAL, config=config
        )
        _record_savings(tracker, "project_context", "read", content, optimized)
    else:
        optimized = content
        original_tokens = estimate_tokens(content)
        token_stats = {
            "original_tokens": original_tokens,
            "optimized_tokens": original_tokens,
            "savings_pct": 0,
        }

    return {
        "project_root": str(root),
        "path": relative_path(root, path),
        "start_line": start_line,
        "end_line": end_line,
        "truncated": truncated,
        "content": optimized,
        "token_stats": token_stats,
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



def search_project_code(
    project_path: str = ".", query: str = "", limit: int = 20
) -> dict[str, object]:
    """Search bounded text content in source files and return ranked snippets."""
    root = resolve_project_root(project_path)
    limit = max(1, min(limit, 100))
    if not query:
        return {"project_root": str(root), "query": query, "matches": []}

    # Try SQLite FTS5 first
    db = _get_db(root)
    try:
        results = db.search_symbols(query, limit=limit)
        if results:
            matches = []
            for row in results:
                matches.append({
                    "path": row["file_path"],
                    "language_hint": language_hint(root / row["file_path"]),
                    "score": 100,  # FTS5 matches get generic high score
                    "line": row["start_line"],
                    "snippet": row["signature"] or row["name"],
                })
            return {"project_root": str(root), "query": query, "matches": matches}
    except Exception:
        pass
    finally:
        db.close()

    # ── 3-tier fallback: docs → structural → general code ─────────────────
    terms = tokenize(query)
    if not terms:
        return {"project_root": str(root), "query": query, "matches": []}

    all_files = list(iter_project_files(root, excluded_paths={DEFAULT_SNAPSHOT_PATH}))

    def _tier_files(patterns):
        matched = []
        for f in all_files:
            rel = relative_path(root, f).replace("\\", "/")
            if any(rel.startswith(p) or rel == p or f"/{p}" in rel for p in patterns):
                matched.append(f)
        return matched

    # Tier 1: high-signal docs and manifests
    doc_tier = _tier_files({
        "README.md", "ARCHITECTURE.md", "CONTRIBUTING.md", "CHANGELOG.md",
        "docs/", "documentation/", "adr/", "decisions/",
        "pyproject.toml", "package.json", "Cargo.toml", "go.mod",
        "setup.py", "setup.cfg", "Makefile",
    })
    # Tier 2: structural and config files
    config_tier = _tier_files({
        "tsconfig.json", "Dockerfile", "docker-compose",
        ".github/workflows/", ".gitlab-ci.yml",
        "main.py", "index.ts", "main.go", "lib.rs",
        "cmd/", "app/", "src/", "internal/",
        "tests/", "test/", "__tests__/",
    })
    config_tier = [f for f in config_tier if f not in doc_tier]
    # Tier 3: everything else, capped
    general_tier = [f for f in all_files if f not in doc_tier and f not in config_tier][:300]

    def _scan_file(path):
        content, _ = read_bounded_text(path, DEFAULT_MAX_FILE_BYTES)
        if content is None:
            return None
        haystack = f"{relative_path(root, path)}\n{content}".lower()
        score = sum(haystack.count(term) for term in terms)
        if score == 0:
            return None
        line_number, snippet = first_matching_line(content, terms)
        return (
            score,
            {
                "path": relative_path(root, path),
                "language_hint": language_hint(path),
                "score": score,
                "line": line_number,
                "snippet": snippet,
            },
        )

    from .parallel import parallel_map

    matches = parallel_map(_scan_file, doc_tier + config_tier + general_tier)
    matches.sort(key=lambda item: (-item[0], str(item[1]["path"])))
    return {
        "project_root": str(root),
        "query": query,
        "matches": [item for _, item in matches[:limit]],
    }


def get_project_diff(
    project_path: str = ".",
    config: TokenOptimizationConfig | None = None,
    tracker: TokenTracker | None = None,
) -> dict[str, object]:
    """Retrieve git diff (staged and unstaged) in the project workspace, token-optimized."""
    import subprocess
    root = resolve_project_root(project_path)
    config = config or load_config_from_env()

    try:
        # Get diff of both staged and unstaged changes
        res = subprocess.run(
            ["git", "--no-pager", "diff", "HEAD"],
            cwd=str(root),
            capture_output=True,
            text=True,
            timeout=5,
        )
        diff_text = res.stdout or ""
        if not diff_text:
            # Fallback to unstaged diff
            res2 = subprocess.run(
                ["git", "--no-pager", "diff"],
                cwd=str(root),
                capture_output=True,
                text=True,
                timeout=5,
            )
            diff_text = res2.stdout or ""
    except Exception as e:
        return {
            "success": False,
            "error": "COMMAND_FAILED",
            "message": f"Failed to run git diff: {e}",
            "details": {"project_root": str(root)}
        }

    original_len = len(diff_text)
    if not diff_text.strip():
        return {
            "project_root": str(root),
            "diff": "No changes detected.",
            "original_length": 0,
            "optimized_length": 0,
        }

    # Bounded diff
    if config.enabled:
        optimized, _ = optimize_source_content(diff_text, "diff", config=config)
    else:
        optimized = diff_text

    _record_savings(tracker, "project_context", "diff", diff_text, optimized)
    return {
        "project_root": str(root),
        "diff": optimized,
        "original_length": original_len,
        "optimized_length": len(optimized),
    }



