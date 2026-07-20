"""Project source scanning internals."""


import os
import re
import time
import threading
from pathlib import Path
from typing import Iterable

from .constants import PROJECT_IGNORED_PARTS

DEFAULT_SNAPSHOT_PATH = ".agent-context/code-snapshot.json"
DEFAULT_MAX_FILE_BYTES = 200_000
DEFAULT_MAX_TOTAL_BYTES = 2_000_000
DEFAULT_MAX_DEPTH = 8
DEFAULT_MAX_READ_LINES = 300
DEFAULT_DETAIL_DEPTH = 3
DEFAULT_MAX_TREE_ENTRIES = 2000

# ── Tree cache ───────────────────────────────────────────────────────────────
# Key: (root_str, max_depth)
# Value: (monotonic_time, root_mtime, git_index_mtime, result)
_tree_cache: dict[tuple[str, int], tuple[float, float, float, dict]] = {}
_tree_cache_lock = threading.Lock()
_TREE_CACHE_TTL = 120  # seconds


def _root_mtime(root: Path) -> float:
    try:
        return root.stat().st_mtime
    except OSError:
        return 0.0


def _git_index_mtime(root: Path) -> float:
    """Check .git/index mtime — changes on any git add/commit/checkout."""
    try:
        return (root / ".git" / "index").stat().st_mtime
    except OSError:
        return 0.0


def invalidate_tree_cache(root: Path | None = None) -> None:
    """Clear tree cache. Called by watcher on file changes."""
    with _tree_cache_lock:
        if root is None:
            _tree_cache.clear()
        else:
            root_str = str(root)
            keys_to_remove = [k for k in _tree_cache if k[0] == root_str]
            for k in keys_to_remove:
                del _tree_cache[k]
    if root is not None:
        try:
            from .tree_cache import delete_tree_cache
            delete_tree_cache(root)
        except Exception:
            pass

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
    root: Path,
    max_depth: int,
    excluded_paths: Iterable[str] | None = None,
    detail_depth: int = DEFAULT_DETAIL_DEPTH,
    use_cache: bool = True,
    max_entries: int = DEFAULT_MAX_TREE_ENTRIES,
) -> dict[str, object]:
    """Build a progressive project tree using os.scandir.

    Depth 1 to detail_depth: full metadata (size_bytes, is_binary check).
    Depth detail_depth+1 to max_depth: light listing (suffix-only, shallow=True).
    Results are cached with TTL + root mtime + .git/index mtime invalidation.
    """
    # ponytail: no per-entry mtime tracking; rely on TTL + root + git index.
    # Upgrade path: add inotify/ReadDirectoryChanges watcher per-subtree.

    # ── Cache check ──────────────────────────────────────────────────────
    cache_key = (str(root), max_depth)
    if use_cache:
        with _tree_cache_lock:
            cached = _tree_cache.get(cache_key)
        if cached:
            ts, rmtime, gmtime, cached_result = cached
            if (time.monotonic() - ts < _TREE_CACHE_TTL
                    and _root_mtime(root) == rmtime
                    and _git_index_mtime(root) == gmtime):
                return cached_result

    # ── Persistent cache check (SQLite) ──────────────────────────────
    if use_cache:
        try:
            from .tree_cache import _cache_key as _pkey, load_tree_cache, save_tree_cache
            pkey = _pkey(root, max_depth)
            db_entries = load_tree_cache(root)
            if pkey in db_entries:
                db_rmtime, db_gmtime, db_data = db_entries[pkey]
                if (_root_mtime(root) == db_rmtime
                        and _git_index_mtime(root) == db_gmtime):
                    # Warm in-memory cache
                    with _tree_cache_lock:
                        _tree_cache[cache_key] = (
                            time.monotonic(), db_rmtime, db_gmtime, db_data,
                        )
                    return db_data
        except Exception:
            pass

    excluded = normalize_excluded_paths(excluded_paths)
    entries: list[dict[str, object]] = []
    capped = False

    def _walk(current: Path, depth: int) -> None:
        nonlocal capped
        if capped or depth > max_depth:
            return
        try:
            scan_iter = os.scandir(current)
        except (PermissionError, OSError):
            return

        dirs: list[os.DirEntry] = []
        files: list[os.DirEntry] = []
        with scan_iter:
            for entry in scan_iter:
                if entry.is_symlink():
                    continue
                try:
                    if entry.is_dir(follow_symlinks=False):
                        dirs.append(entry)
                    elif entry.is_file(follow_symlinks=False):
                        files.append(entry)
                except OSError:
                    continue

        # Deterministic order on both Linux and Windows
        dirs.sort(key=lambda e: e.name)
        files.sort(key=lambda e: e.name)

        for d in dirs:
            if len(entries) >= max_entries:
                capped = True
                return
            rel = relative_path(root, Path(d.path))
            if should_skip_relative_path(rel, excluded):
                continue
            entries.append({"path": rel, "type": "directory"})
            _walk(Path(d.path), depth + 1)

        for f in files:
            if len(entries) >= max_entries:
                capped = True
                return
            rel = relative_path(root, Path(f.path))
            if should_skip_relative_path(rel, excluded):
                continue
            suffix = Path(f.name).suffix.lower()
            fpath = Path(f.path)

            if depth <= detail_depth:
                # Full metadata — depth 1 to detail_depth
                if suffix in BINARY_SUFFIXES:
                    continue
                if is_binary_file(fpath):
                    continue
                try:
                    st = f.stat()
                except OSError:
                    continue
                entries.append({
                    "path": rel,
                    "type": "file",
                    "language_hint": language_hint(fpath),
                    "size_bytes": st.st_size,
                })
            else:
                # Shallow listing — depth detail_depth+1 to max_depth
                # No stat(), no is_binary_file() — suffix check only
                if suffix in BINARY_SUFFIXES:
                    continue
                entries.append({
                    "path": rel,
                    "type": "file",
                    "language_hint": language_hint(fpath),
                    "shallow": True,
                })

    _walk(root, 1)
    entries.sort(key=lambda e: (str(e["path"]).count("/"), str(e["path"])))

    result: dict[str, object] = {
        "project_root": str(root),
        "max_depth": max_depth,
        "detail_depth": detail_depth,
        "tree": entries,
    }
    if capped:
        result["warning"] = f"Tree capped at {max_entries} entries"
        result["capped"] = True

    # ── Cache populate ───────────────────────────────────────────────────
    if use_cache:
        with _tree_cache_lock:
            _tree_cache[cache_key] = (
                time.monotonic(),
                _root_mtime(root),
                _git_index_mtime(root),
                result,
            )
        # Persist to SQLite (best-effort)
        try:
            from .tree_cache import _cache_key as _pkey, save_tree_cache
            save_tree_cache(root, _pkey(root, max_depth), _root_mtime(root), _git_index_mtime(root), result)
        except Exception:
            pass
    return result


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


# ── Architecture doc probe ───────────────────────────────────────────────────
_ARCHITECTURE_PROBES = (
    "README.md", "ARCHITECTURE.md", "DESIGN.md", "CONTRIBUTING.md",
    "CHANGELOG.md", "PROJECT-MAP.md", "AGENTS.md", "CLAUDE.md",
    "pyproject.toml", "package.json", "Cargo.toml", "go.mod",
    "Makefile", "CMakeLists.txt",
)
_ARCHITECTURE_PROBE_DIRS = ("docs", "doc", "documentation", "adr", "decisions")


def probe_architecture_docs(root: Path) -> list[dict[str, object]]:
    """Instant probe for architecture/doc files. No tree walk."""
    found: list[dict[str, object]] = []
    for name in _ARCHITECTURE_PROBES:
        target = root / name
        try:
            if target.is_file():
                found.append({
                    "path": name,
                    "type": "file",
                    "size_bytes": target.stat().st_size,
                })
        except OSError:
            continue
    for name in _ARCHITECTURE_PROBE_DIRS:
        target = root / name
        try:
            if target.is_dir():
                found.append({"path": name, "type": "directory"})
        except OSError:
            continue
    return found


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
    # Default: only allow the current working directory and subdirectories.
    # Blocks access to other user dirs (~/Documents, ~/.ssh, etc.) by default.
    # User must set AGENT_PROJECT_ALLOWED_ROOTS to grant wider access.
    cwd = Path.cwd().resolve()
    try:
        root.relative_to(cwd)
        return True
    except ValueError:
        return False


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
