"""Project source scanning internals."""


import os
import re
from pathlib import Path
from typing import Iterable

from .constants import PROJECT_IGNORED_PARTS

DEFAULT_SNAPSHOT_PATH = ".agent-context/code-snapshot.json"
DEFAULT_MAX_FILE_BYTES = 200_000
DEFAULT_MAX_TOTAL_BYTES = 2_000_000
DEFAULT_MAX_DEPTH = 8
DEFAULT_MAX_READ_LINES = 300

BINARY_SUFFIXES = set(
    """
    .7z .avi .class .db .dll .dylib .exe .gif .gz .ico .jar .jpeg .jpg
    .mov .mp3 .mp4 .otf .pdf .png .pyc .pyo .so .sqlite .sqlite3 .tar
    .tgz .ttf .wasm .wav .webp .woff .woff2 .xz .zip
    """.split()
)

LANGUAGE_HINTS = {
    ".c": "c",
    ".cc": "cpp",
    ".cpp": "cpp",
    ".cs": "csharp",
    ".css": "css",
    ".go": "go",
    ".html": "html",
    ".java": "java",
    ".js": "javascript",
    ".jsx": "javascript",
    ".json": "json",
    ".kt": "kotlin",
    ".md": "markdown",
    ".mdc": "markdown",
    ".php": "php",
    ".py": "python",
    ".rs": "rust",
    ".sh": "shell",
    ".sql": "sql",
    ".swift": "swift",
    ".toml": "toml",
    ".ts": "typescript",
    ".tsx": "typescript",
    ".txt": "text",
    ".vue": "vue",
    ".xml": "xml",
    ".yaml": "yaml",
    ".yml": "yaml",
}


def build_project_tree(
    root: Path, max_depth: int, excluded_paths: Iterable[str] | None = None
) -> dict[str, object]:
    entries: list[dict[str, object]] = []
    excluded = normalize_excluded_paths(excluded_paths)

    for dirpath_text, dirnames, filenames in os.walk(root):
        dirpath = Path(dirpath_text)
        kept_dirnames: list[str] = []
        for dirname in sorted(dirnames):
            directory = dirpath / dirname
            rel = relative_path(root, directory)
            if directory.is_symlink() or should_skip_relative_path(rel, excluded):
                continue
            if path_depth(rel) > max_depth:
                continue
            entries.append({"path": rel, "type": "directory"})
            if path_depth(rel) < max_depth:
                kept_dirnames.append(dirname)
        dirnames[:] = kept_dirnames

        for filename in sorted(filenames):
            path = dirpath / filename
            if path.is_symlink() or not path.is_file():
                continue
            rel = relative_path(root, path)
            if path_depth(rel) > max_depth:
                continue
            if should_skip_relative_path(rel, excluded) or is_binary_file(path):
                continue
            entries.append(
                {
                    "path": rel,
                    "type": "file",
                    "language_hint": language_hint(path),
                    "size_bytes": path.stat().st_size,
                }
            )

    entries.sort(key=lambda entry: (str(entry["path"]).count("/"), str(entry["path"])))
    return {"project_root": str(root), "max_depth": max_depth, "tree": entries}


def iter_project_files(
    root: Path,
    max_depth: int | None = None,
    excluded_paths: Iterable[str] | None = None,
) -> Iterable[Path]:
    excluded = normalize_excluded_paths(excluded_paths)
    for dirpath_text, dirnames, filenames in os.walk(root):
        dirpath = Path(dirpath_text)
        kept_dirnames: list[str] = []
        for dirname in sorted(dirnames):
            directory = dirpath / dirname
            rel = relative_path(root, directory)
            if directory.is_symlink() or should_skip_relative_path(rel, excluded):
                continue
            if max_depth is not None and path_depth(rel) >= max_depth:
                continue
            kept_dirnames.append(dirname)
        dirnames[:] = kept_dirnames

        for filename in sorted(filenames):
            path = dirpath / filename
            if path.is_symlink() or not path.is_file():
                continue
            rel = relative_path(root, path)
            if max_depth is not None and path_depth(rel) > max_depth:
                continue
            if should_skip_relative_path(rel, excluded) or is_binary_file(path):
                continue
            yield path


_SYSTEM_DIR_PARTS = frozenset({"etc", "proc", "sys", "var", "Windows", "System32", ".ssh", ".gnupg", ".config", "dev", "boot", "root"})
_SENSITIVE_PATHS = frozenset({"/etc", "/proc", "/sys", "/dev", "/boot", "/root", "/tmp"})


def _is_project_path_allowed(root: Path) -> bool:
    allowed = os.environ.get("AGENT_PROJECT_ALLOWED_ROOTS", "").strip()
    if allowed:
        allowed_paths = [Path(p.strip()).expanduser().resolve() for p in allowed.split(",") if p.strip()]
        for allowed_root in allowed_paths:
            try:
                root.relative_to(allowed_root)
                return True
            except ValueError:
                continue
        return False
    resolved = root.resolve()
    parts = set(resolved.parts)
    if parts & _SYSTEM_DIR_PARTS and not any(p.startswith("home") or p.startswith("Users") for p in parts):
        return False
    if str(resolved) in _SENSITIVE_PATHS or any(str(resolved).startswith(p + "/") for p in _SENSITIVE_PATHS):
        return False
    return True


def resolve_project_root(project_path: str) -> Path:
    if project_path == "." and os.environ.get("AGENT_PROJECT_ROOT"):
        project_path = os.environ["AGENT_PROJECT_ROOT"]
    root = Path(project_path).expanduser().resolve()
    if not root.is_dir():
        raise NotADirectoryError(f"Project path is not a directory: {project_path!r}")
    if not _is_project_path_allowed(root):
        raise ValueError(f"Project path is not allowed: {project_path!r}. Set AGENT_PROJECT_ALLOWED_ROOTS to whitelist directories.")
    return root


def resolve_inside_project(root: Path, path_value: str) -> Path:
    path = Path(path_value).expanduser()
    if ".." in path.parts:
        raise ValueError(f"Path traversal blocked: {path_value!r}")
    resolved = path.resolve() if path.is_absolute() else (root / path).resolve()
    try:
        resolved.relative_to(root)
    except ValueError as exc:
        raise ValueError(f"Path escapes project root: {path_value!r}") from exc
    return resolved


def ensure_project_file_allowed(root: Path, path: Path) -> None:
    rel = relative_path(root, path)
    if should_skip_relative_path(rel, {DEFAULT_SNAPSHOT_PATH}):
        raise ValueError(f"Path is ignored by project context scanner: {rel}")
    if not path.is_file():
        raise FileNotFoundError(rel)


def read_bounded_text(path: Path, max_bytes: int) -> tuple[str | None, bool]:
    if path.suffix.lower() in BINARY_SUFFIXES:
        return None, False
    size = path.stat().st_size
    with path.open("rb") as file:
        data = file.read(max_bytes + 1)
    if looks_binary(data):
        return None, False

    truncated = size > max_bytes
    if len(data) > max_bytes:
        data = data[:max_bytes]

    try:
        return data.decode("utf-8", errors="replace"), truncated
    except Exception:
        return None, False


def is_binary_file(path: Path) -> bool:
    if path.suffix.lower() in BINARY_SUFFIXES:
        return True
    try:
        with path.open("rb") as file:
            return looks_binary(file.read(4096))
    except (PermissionError, OSError):
        return True


def looks_binary(data: bytes) -> bool:
    return b"\x00" in data


def should_skip_relative_path(relative: str, excluded_paths: set[str]) -> bool:
    parts = Path(relative).parts
    return any(part in PROJECT_IGNORED_PARTS for part in parts) or relative in excluded_paths


def normalize_excluded_paths(excluded_paths: Iterable[str] | None) -> set[str]:
    if excluded_paths is None:
        return set()
    return {Path(path).as_posix().strip("/") for path in excluded_paths}


def language_hint(path: Path) -> str:
    return LANGUAGE_HINTS.get(
        path.suffix.lower(), path.suffix.lower().lstrip(".") or "text"
    )


def relative_path(root: Path, path: Path) -> str:
    return path.relative_to(root).as_posix()


def path_depth(relative: str) -> int:
    return len(Path(relative).parts)


def tokenize(query: str) -> list[str]:
    from .text import tokenize as text_tokenize
    return text_tokenize(query, min_length=1)



def first_matching_line(content: str, terms: list[str]) -> tuple[int, str]:
    for line_number, line in enumerate(content.splitlines(), start=1):
        if any(term in line.lower() for term in terms):
            return line_number, line.strip()[:300]
    return 0, ""
