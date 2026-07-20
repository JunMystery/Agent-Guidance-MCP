"""Persistent project tree cache in SQLite.

Stored in .agent-context/tree-cache.db per project.
Lazy cleanup: stale entries (>7 days) removed on first write.
"""

import json
import sqlite3
import threading
import time
from pathlib import Path


_TREE_CACHE_RELPATH = ".agent-context/tree-cache.db"
_PERSIST_LOCK = threading.Lock()
_CLEANUP_MAX_AGE_DAYS = 7

# Track which roots have been lazily cleaned this session
_cleaned_roots: set[str] = set()

_SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS tree_cache (
    cache_key TEXT PRIMARY KEY,
    root_path TEXT NOT NULL,
    root_mtime REAL NOT NULL,
    git_index_mtime REAL NOT NULL,
    data TEXT NOT NULL,
    cached_at REAL NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_tree_cache_root ON tree_cache(root_path);
"""


def _db_path(root: Path) -> Path:
    return root / _TREE_CACHE_RELPATH


def _get_conn(root: Path) -> sqlite3.Connection:
    db = _db_path(root)
    db.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(db))
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA synchronous=NORMAL")
    conn.executescript(_SCHEMA_SQL)
    return conn


def _cache_key(root: Path, max_depth: int) -> str:
    return f"{root}\0{max_depth}"


def _load_all(root: Path) -> dict[str, tuple[float, float, float, dict]]:
    result: dict[str, tuple[float, float, float, dict]] = {}
    try:
        conn = _get_conn(root)
        cursor = conn.execute(
            "SELECT cache_key, root_mtime, git_index_mtime, data FROM tree_cache"
        )
        for row in cursor:
            data = json.loads(row[3])
            result[row[0]] = (row[1], row[2], data)
        conn.close()
    except Exception:
        pass
    return result


def load_tree_cache(
    root: Path,
) -> dict[str, tuple[float, float, float, dict]]:
    """Load all cache entries for a project root from SQLite.

    Returns dict keyed by cache_key string (e.g. "/path\0depth"),
    values are (root_mtime, git_index_mtime, data_dict).
    """
    return _load_all(root)


def save_tree_cache(
    root: Path,
    cache_key: str,
    root_mtime: float,
    git_index_mtime: float,
    data: dict,
) -> None:
    """Upsert a single tree cache entry to SQLite (best-effort)."""
    with _PERSIST_LOCK:
        try:
            conn = _get_conn(root)

            root_str = str(root)
            if root_str not in _cleaned_roots:
                cutoff = time.time() - (_CLEANUP_MAX_AGE_DAYS * 86400)
                conn.execute("DELETE FROM tree_cache WHERE cached_at < ?", (cutoff,))
                _cleaned_roots.add(root_str)

            conn.execute(
                """INSERT OR REPLACE INTO tree_cache
                   (cache_key, root_path, root_mtime, git_index_mtime, data, cached_at)
                   VALUES (?, ?, ?, ?, ?, ?)""",
                (
                    cache_key,
                    str(root),
                    root_mtime,
                    git_index_mtime,
                    json.dumps(data),
                    time.time(),
                ),
            )
            conn.commit()
            conn.close()
        except Exception:
            pass


def delete_tree_cache(root: Path, cache_key: str | None = None) -> None:
    """Delete tree cache entries for a project root.

    If cache_key is None, deletes all entries for that root.
    """
    with _PERSIST_LOCK:
        try:
            conn = _get_conn(root)
            if cache_key:
                conn.execute(
                    "DELETE FROM tree_cache WHERE cache_key = ?", (cache_key,)
                )
            else:
                conn.execute(
                    "DELETE FROM tree_cache WHERE root_path = ?", (str(root),)
                )
            conn.commit()
            conn.close()
        except Exception:
            pass


def cleanup_stale_cache(root: Path) -> None:
    """Delete tree cache entries older than CLEANUP_MAX_AGE_DAYS."""
    with _PERSIST_LOCK:
        try:
            conn = _get_conn(root)
            cutoff = time.time() - (_CLEANUP_MAX_AGE_DAYS * 86400)
            conn.execute("DELETE FROM tree_cache WHERE cached_at < ?", (cutoff,))
            conn.commit()
            conn.close()
        except Exception:
            pass
