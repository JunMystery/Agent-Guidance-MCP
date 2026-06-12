"""Bounded project code context helpers for MCP agents."""

from __future__ import annotations

import json
from datetime import datetime, timezone

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


def export_project_snapshot(
    project_path: str = ".",
    output_path: str = DEFAULT_SNAPSHOT_PATH,
    max_file_bytes: int = DEFAULT_MAX_FILE_BYTES,
    max_total_bytes: int = DEFAULT_MAX_TOTAL_BYTES,
) -> dict[str, object]:
    """Write a bounded JSON snapshot of source files and return its manifest."""
    root = resolve_project_root(project_path)
    output = resolve_inside_project(root, output_path)
    output_relative = output.relative_to(root).as_posix()
    max_file_bytes = max(1, max_file_bytes)
    max_total_bytes = max(1, max_total_bytes)

    tree = build_project_tree(root, DEFAULT_MAX_DEPTH, excluded_paths={output_relative})
    files: list[dict[str, object]] = []
    total_content_bytes = 0

    for path in iter_project_files(root, excluded_paths={output_relative}):
        if total_content_bytes >= max_total_bytes:
            break

        remaining_bytes = max_total_bytes - total_content_bytes
        content, truncated = read_bounded_text(path, min(max_file_bytes, remaining_bytes))
        if content is None:
            continue

        total_content_bytes += len(content.encode("utf-8"))
        files.append(
            {
                "path": relative_path(root, path),
                "language_hint": language_hint(path),
                "size_bytes": path.stat().st_size,
                "truncated": truncated,
                "content": content,
            }
        )

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
    root = resolve_project_root(project_path)
    return build_project_tree(root, max(1, max_depth), excluded_paths={DEFAULT_SNAPSHOT_PATH})


def read_project_file(
    project_path: str = ".",
    relative_path_value: str = "",
    start_line: int = 1,
    max_lines: int = DEFAULT_MAX_READ_LINES,
) -> dict[str, object]:
    """Read a bounded line range from one text file inside a project."""
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

    end_line = start_line + len(selected) - 1 if selected else start_line - 1
    return {
        "project_root": str(root),
        "path": relative_path(root, path),
        "start_line": start_line,
        "end_line": end_line,
        "truncated": truncated,
        "content": "\n".join(selected),
    }


def search_project_code(
    project_path: str = ".", query: str = "", limit: int = 20
) -> dict[str, object]:
    """Search bounded text content in source files and return ranked snippets."""
    root = resolve_project_root(project_path)
    terms = tokenize(query)
    limit = max(1, min(limit, 100))
    if not terms:
        return {"project_root": str(root), "query": query, "matches": []}

    matches: list[tuple[int, dict[str, object]]] = []
    for path in iter_project_files(root, excluded_paths={DEFAULT_SNAPSHOT_PATH}):
        content, _ = read_bounded_text(path, DEFAULT_MAX_FILE_BYTES)
        if content is None:
            continue

        haystack = f"{relative_path(root, path)}\n{content}".lower()
        score = sum(haystack.count(term) for term in terms)
        if score == 0:
            continue

        line_number, snippet = first_matching_line(content, terms)
        matches.append(
            (
                score,
                {
                    "path": relative_path(root, path),
                    "language_hint": language_hint(path),
                    "score": score,
                    "line": line_number,
                    "snippet": snippet,
                },
            )
        )

    matches.sort(key=lambda item: (-item[0], str(item[1]["path"])))
    return {
        "project_root": str(root),
        "query": query,
        "matches": [item for _, item in matches[:limit]],
    }
