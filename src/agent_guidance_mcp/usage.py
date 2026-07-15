"""Persistent usage tracking for MCP tool calls, skill loads, and embed queries.

Stores append-only logs in SQLite under .agent-context/usage.db.
Designed for zero-overhead on the fast path via background writer.
"""
from __future__ import annotations

import json
import os
import sqlite3
import threading
import time
import uuid
from pathlib import Path
from queue import Queue, Empty
from typing import Any


DB_FILENAME = "usage.db"
_MAX_QUEUE_SIZE = 5000
_FLUSH_INTERVAL_S = 2.0


class _WriteOp:
    """Internal marker for queued write operations."""

    __slots__ = ("method", "args")

    def __init__(self, method: str, args: tuple) -> None:
        self.method = method
        self.args = args


class UsageTracker:
    """Persistent usage tracker backed by SQLite.

    Thread-safe.  Writes are offloaded to a background daemon thread via
    a Queue so the hot path (tool dispatch) never blocks on I/O.

    Typical usage
    -------------
    tracker = UsageTracker(project_root)
    sid = tracker.session_start()
    # ... tool calls ...
    tracker.record_tool_call("guidance", "search", elapsed_ms, orig_tok, opt_tok)
    tracker.record_skill_load("tdd-workflow", query="testing patterns")
    # ... on shutdown ...
    tracker.session_end()
    tracker.close()
    """

    def __init__(self, project_root: str | Path) -> None:
        self._project_root = Path(project_root).resolve()
        db_dir = self._project_root / ".agent-context"
        db_dir.mkdir(parents=True, exist_ok=True)
        self._db_path = db_dir / DB_FILENAME

        self._conn = sqlite3.connect(str(self._db_path), check_same_thread=False)
        self._conn.row_factory = sqlite3.Row
        self._init_db()

        self._queue: Queue = Queue(maxsize=_MAX_QUEUE_SIZE)
        self._session_id: str | None = None
        self._lock = threading.Lock()
        self._stop_event = threading.Event()
        self._flusher = threading.Thread(
            target=_flush_loop,
            args=(self._conn, self._queue, self._stop_event),
            name="usage-flusher",
            daemon=True,
        )
        self._flusher.start()

    # ── Schema ──────────────────────────────────────────────────────────

    def _init_db(self) -> None:
        cur = self._conn.cursor()
        cur.execute("PRAGMA journal_mode=WAL;")
        cur.execute("PRAGMA busy_timeout=3000;")
        cur.execute("PRAGMA synchronous=NORMAL;")

        cur.execute("""
            CREATE TABLE IF NOT EXISTS schema_version (
                version INTEGER PRIMARY KEY,
                applied_at INTEGER NOT NULL
            )
        """)

        # Only run migrations if schema_version is empty (fresh DB)
        row = cur.execute("SELECT MAX(version) AS v FROM schema_version").fetchone()
        current_version = row["v"] if row and row["v"] else 0

        if current_version < 1:
            cur.execute("""
                CREATE TABLE IF NOT EXISTS sessions (
                    session_id TEXT PRIMARY KEY,
                    started_at INTEGER NOT NULL,
                    ended_at INTEGER,
                    project_path TEXT NOT NULL,
                    tool_call_count INTEGER DEFAULT 0,
                    total_tokens_original INTEGER DEFAULT 0,
                    total_tokens_optimized INTEGER DEFAULT 0,
                    total_skills_loaded INTEGER DEFAULT 0,
                    total_embed_queries INTEGER DEFAULT 0
                )
            """)
            cur.execute("""
                CREATE TABLE IF NOT EXISTS tool_calls (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    session_id TEXT NOT NULL,
                    tool_name TEXT NOT NULL,
                    operation TEXT,
                    started_at INTEGER NOT NULL,
                    duration_ms INTEGER DEFAULT 0,
                    tokens_original INTEGER,
                    tokens_optimized INTEGER
                )
            """)
            cur.execute("""
                CREATE TABLE IF NOT EXISTS skill_loads (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    session_id TEXT NOT NULL,
                    skill_id TEXT NOT NULL,
                    query TEXT,
                    search_term TEXT,
                    embed_used INTEGER DEFAULT 0,
                    loaded_at INTEGER NOT NULL
                )
            """)
            cur.execute("""
                CREATE TABLE IF NOT EXISTS embed_queries (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    session_id TEXT NOT NULL,
                    query_text TEXT NOT NULL,
                    prefix_type TEXT,
                    model_name TEXT,
                    vector_dim INTEGER,
                    duration_ms INTEGER DEFAULT 0,
                    result_count INTEGER DEFAULT 0,
                    queried_at INTEGER NOT NULL
                )
            """)
            cur.execute("""
                CREATE INDEX IF NOT EXISTS idx_tool_calls_session
                    ON tool_calls(session_id)
            """)
            cur.execute("""
                CREATE INDEX IF NOT EXISTS idx_skill_loads_session
                    ON skill_loads(session_id)
            """)
            cur.execute("""
                CREATE INDEX IF NOT EXISTS idx_tool_calls_name
                    ON tool_calls(tool_name)
            """)
            cur.execute(
                "INSERT INTO schema_version (version, applied_at) VALUES (1, ?)",
                (int(time.time()),),
            )

        if current_version < 2:
            cur.execute("ALTER TABLE sessions ADD COLUMN client_name TEXT")
            cur.execute("ALTER TABLE sessions ADD COLUMN session_label TEXT")
            cur.execute(
                "INSERT INTO schema_version (version, applied_at) VALUES (2, ?)",
                (int(time.time()),),
            )

        self._conn.commit()

    # ── Session lifecycle ───────────────────────────────────────────────

    def session_start(
        self,
        project_path: str | None = None,
        client_name: str | None = None,
        session_label: str | None = None,
    ) -> str:
        """Start a new usage session.  Returns session_id (UUID)."""
        sid = uuid.uuid4().hex
        now = int(time.time())
        pp = project_path or str(self._project_root)
        self._queue.put(_WriteOp("session_start", (sid, now, pp, client_name, session_label)))
        self._session_id = sid
        return sid

    def session_end(self) -> None:
        """Mark current session as ended."""
        sid = self._session_id
        if sid is None:
            return
        now = int(time.time())
        self._queue.put(_WriteOp("session_end", (sid, now)))
        self._session_id = None

    def update_session_label(self, session_id: str | None = None, label: str | None = None) -> None:
        """Set or update the human-readable label for a session."""
        sid = session_id or self._current_session_id()
        if sid is None or label is None:
            return
        self._queue.put(_WriteOp("update_session_label", (sid, label)))

    # ── Recording helpers ───────────────────────────────────────────────

    def record_tool_call(
        self,
        tool_name: str,
        operation: str | None = None,
        duration_ms: int = 0,
        tokens_original: int | None = None,
        tokens_optimized: int | None = None,
    ) -> None:
        """Record one tool invocation."""
        sid = self._current_session_id()
        if sid is None:
            return
        now = int(time.time())
        self._queue.put(
            _WriteOp(
                "record_tool_call",
                (sid, tool_name, operation, now, duration_ms,
                 tokens_original, tokens_optimized),
            )
        )

    def record_skill_load(
        self,
        skill_id: str,
        query: str | None = None,
        search_term: str | None = None,
        embed_used: bool = False,
    ) -> None:
        """Record a skill being loaded via ``guidance(get)`` or search."""
        sid = self._current_session_id()
        if sid is None:
            return
        now = int(time.time())
        self._queue.put(
            _WriteOp(
                "record_skill_load",
                (sid, skill_id, query, search_term, int(embed_used), now),
            )
        )

    def record_embed_query(
        self,
        query_text: str,
        prefix_type: str | None = None,
        model_name: str | None = None,
        vector_dim: int = 0,
        duration_ms: int = 0,
        result_count: int = 0,
    ) -> None:
        """Record an embedding query."""
        sid = self._current_session_id()
        if sid is None:
            return
        now = int(time.time())
        self._queue.put(
            _WriteOp(
                "record_embed_query",
                (sid, query_text, prefix_type, model_name, vector_dim,
                 duration_ms, result_count, now),
            )
        )

    # ── Aggregation / summary ───────────────────────────────────────────

    def summary(self, scope: str = "session", session_id: str | None = None) -> dict[str, Any]:
        """Return an aggregated usage summary.

        Parameters
        ----------
        scope:
            ``"session"`` → current active session only.
            ``"all"``     → all recorded data (lifetime).
        session_id:
            If provided, filter tool_breakdown and top_skills to this session.
        """
        self._flush_now()
        sid = session_id or (self._session_id if scope == "session" else None)
        cur = self._conn.cursor()

        # ── session info ────────────────────────────────────────────────
        session_info: dict[str, Any] = {}
        sessions_list: list[dict[str, Any]] = []

        if scope == "all" and not session_id:
            cur.execute(
                "SELECT * FROM sessions ORDER BY started_at DESC"
            )
            for row in cur.fetchall():
                s = dict(row)
                if s.get("ended_at"):
                    s["duration_seconds"] = s["ended_at"] - s["started_at"]
                else:
                    s["duration_seconds"] = int(time.time()) - s["started_at"]
                sessions_list.append(s)

        if sid:
            cur.execute("SELECT * FROM sessions WHERE session_id = ?", (sid,))
            row = cur.fetchone()
            if row:
                session_info = dict(row)
                if session_info.get("ended_at"):
                    session_info["duration_seconds"] = (
                        session_info["ended_at"] - session_info["started_at"]
                    )
                else:
                    session_info["duration_seconds"] = int(time.time()) - session_info["started_at"]

        # ── tool call breakdown ──────────────────────────────────────────
        if sid:
            cur.execute(
                """SELECT tool_name, operation, COUNT(*) AS cnt,
                          COALESCE(SUM(tokens_original), 0) AS tok_orig,
                          COALESCE(SUM(tokens_optimized), 0) AS tok_opt
                   FROM tool_calls
                   WHERE session_id = ?
                   GROUP BY tool_name, operation
                   ORDER BY cnt DESC""",
                (sid,),
            )
        else:
            cur.execute(
                """SELECT tool_name, operation, COUNT(*) AS cnt,
                          COALESCE(SUM(tokens_original), 0) AS tok_orig,
                          COALESCE(SUM(tokens_optimized), 0) AS tok_opt
                   FROM tool_calls
                   GROUP BY tool_name, operation
                   ORDER BY cnt DESC"""
            )
        tool_breakdown = [dict(r) for r in cur.fetchall()]

        # ── top skill loads ──────────────────────────────────────────────
        if sid:
            cur.execute(
                """SELECT skill_id, COUNT(*) AS cnt
                   FROM skill_loads
                   WHERE session_id = ?
                   GROUP BY skill_id
                   ORDER BY cnt DESC
                   LIMIT 20""",
                (sid,),
            )
        else:
            cur.execute(
                """SELECT skill_id, COUNT(*) AS cnt
                   FROM skill_loads
                   GROUP BY skill_id
                   ORDER BY cnt DESC
                   LIMIT 20"""
            )
        top_skills = [dict(r) for r in cur.fetchall()]

        # ── totals ──────────────────────────────────────────────────────
        if sid:
            cur.execute(
                "SELECT COUNT(*) AS total FROM tool_calls WHERE session_id = ?", (sid,)
            )
            total_calls = cur.fetchone()["total"]
            cur.execute(
                "SELECT COUNT(*) AS total FROM skill_loads WHERE session_id = ?", (sid,)
            )
            total_skills_count = cur.fetchone()["total"]
            cur.execute(
                "SELECT COUNT(*) AS total FROM embed_queries WHERE session_id = ?", (sid,)
            )
            total_embeds = cur.fetchone()["total"]
        else:
            cur.execute("SELECT COUNT(*) AS total FROM tool_calls")
            total_calls = cur.fetchone()["total"]
            cur.execute("SELECT COUNT(*) AS total FROM skill_loads")
            total_skills_count = cur.fetchone()["total"]
            cur.execute("SELECT COUNT(*) AS total FROM embed_queries")
            total_embeds = cur.fetchone()["total"]

        tot_orig = sum(r.get("tok_orig", 0) for r in tool_breakdown)
        tot_opt = sum(r.get("tok_opt", 0) for r in tool_breakdown)
        token_savings = tot_orig - tot_opt
        savings_pct = round((token_savings / max(1, tot_orig)) * 100, 1)

        result: dict[str, Any] = {
            "scope": scope,
            "session_id": sid,
            "session": session_info,
            "totals": {
                "tool_calls": total_calls,
                "skills_loaded": total_skills_count,
                "embed_queries": total_embeds,
                "tokens_original": tot_orig,
                "tokens_optimized": tot_opt,
                "token_savings": token_savings,
                "savings_pct": savings_pct,
            },
            "tool_breakdown": tool_breakdown,
            "top_skills": top_skills,
        }

        if sessions_list:
            result["sessions"] = sessions_list

        return result

    # ── Internal helpers ────────────────────────────────────────────────

    def _current_session_id(self) -> str | None:
        with self._lock:
            return self._session_id

    def _flush_now(self) -> None:
        """Blocking drain of the write queue (used before reads)."""
        self._queue.join()

    # ── Lifecycle ──────────────────────────────────────────────────────

    def close(self) -> None:
        """Flush pending writes, stop the flusher thread, close DB."""
        self._stop_event.set()
        self._flush_now()
        self._conn.close()


# ── Background flusher ──────────────────────────────────────────────────


def _flush_loop(
    conn: sqlite3.Connection,
    queue: Queue,
    stop_event: threading.Event,
) -> None:
    """Daemon thread that drains the write queue into SQLite."""
    while True:
        try:
            op = queue.get(timeout=_FLUSH_INTERVAL_S)
        except Empty:
            if stop_event.is_set():
                break
            continue

        _execute_write(conn, op)
        queue.task_done()

        # Batch-drain remaining items to reduce commits
        drained = 0
        while drained < 100:
            try:
                op = queue.get_nowait()
                _execute_write(conn, op)
                queue.task_done()
                drained += 1
            except Empty:
                break

        conn.commit()


def _execute_write(conn: sqlite3.Connection, op: _WriteOp) -> None:
    """Execute a single queued write operation."""
    try:
        method = _WRITE_DISPATCH[op.method]
    except KeyError:
        return
    method(conn, *op.args)


def _w_session_start(
    conn: sqlite3.Connection, sid: str, now: int, pp: str,
    client_name: str | None = None, session_label: str | None = None,
) -> None:
    conn.execute(
        """INSERT INTO sessions (session_id, started_at, project_path, client_name, session_label)
           VALUES (?, ?, ?, ?, ?)""",
        (sid, now, pp, client_name, session_label),
    )


def _w_session_end(conn: sqlite3.Connection, sid: str, now: int) -> None:
    conn.execute(
        """UPDATE sessions
              SET ended_at = ?,
                  tool_call_count = (SELECT COUNT(*) FROM tool_calls WHERE session_id = ?),
                  total_tokens_original = (SELECT COALESCE(SUM(tokens_original), 0) FROM tool_calls WHERE session_id = ?),
                  total_tokens_optimized = (SELECT COALESCE(SUM(tokens_optimized), 0) FROM tool_calls WHERE session_id = ?),
                  total_skills_loaded = (SELECT COUNT(*) FROM skill_loads WHERE session_id = ?),
                  total_embed_queries = (SELECT COUNT(*) FROM embed_queries WHERE session_id = ?)
           WHERE session_id = ?""",
        (now, sid, sid, sid, sid, sid, sid),
    )


def _w_tool_call(
    conn: sqlite3.Connection,
    sid: str, tool: str, op: str | None, now: int,
    dur: int, tok_orig: int | None, tok_opt: int | None,
) -> None:
    conn.execute(
        """INSERT INTO tool_calls
               (session_id, tool_name, operation, started_at, duration_ms,
                tokens_original, tokens_optimized)
           VALUES (?, ?, ?, ?, ?, ?, ?)""",
        (sid, tool, op, now, dur, tok_orig, tok_opt),
    )


def _w_skill_load(
    conn: sqlite3.Connection,
    sid: str, skill_id: str, query: str | None,
    search_term: str | None, embed_used: int, now: int,
) -> None:
    conn.execute(
        """INSERT INTO skill_loads
               (session_id, skill_id, query, search_term, embed_used, loaded_at)
           VALUES (?, ?, ?, ?, ?, ?)""",
        (sid, skill_id, query, search_term, embed_used, now),
    )


def _w_update_session_label(conn: sqlite3.Connection, sid: str, label: str) -> None:
    conn.execute(
        "UPDATE sessions SET session_label = ? WHERE session_id = ?",
        (label, sid),
    )


def _w_embed_query(
    conn: sqlite3.Connection,
    sid: str, qtext: str, ptype: str | None,
    model: str | None, vdim: int, dur: int, rcnt: int, now: int,
) -> None:
    conn.execute(
        """INSERT INTO embed_queries
               (session_id, query_text, prefix_type, model_name, vector_dim,
                duration_ms, result_count, queried_at)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
        (sid, qtext, ptype, model, vdim, dur, rcnt, now),
    )


_WRITE_DISPATCH: dict[str, object] = {
    "session_start": _w_session_start,
    "session_end": _w_session_end,
    "record_tool_call": _w_tool_call,
    "record_skill_load": _w_skill_load,
    "record_embed_query": _w_embed_query,
    "update_session_label": _w_update_session_label,
}
