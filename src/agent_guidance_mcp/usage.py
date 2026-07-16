"""Persistent per-call usage tracking for MCP tool calls, skill loads,
and embed queries. Append-only SQLite logs with 30-day retention.

No sessions. No project paths. One global DB at ~/.agent-guidance/usage.db.
Writes are offloaded to a background flusher thread.
"""
from __future__ import annotations

import os
import sqlite3
import threading
import time
import uuid
from pathlib import Path
from queue import Queue, Empty
from typing import Any


DB_DIR = Path.home() / ".agent-guidance"
DB_PATH = DB_DIR / "usage.db"
_MAX_QUEUE_SIZE = 5000
_FLUSH_INTERVAL_S = 2.0
_DEFAULT_RETENTION_DAYS = 30


class _WriteOp:
    __slots__ = ("method", "args")
    def __init__(self, method: str, args: tuple) -> None:
        self.method = method
        self.args = args


class UsageTracker:
    """Persistent per-call usage tracker backed by SQLite.

    Thread-safe. Writes offloaded to a background daemon thread.
    Retains records for AGENT_RETENTION_DAYS (default 30).
    """

    def __init__(self) -> None:
        DB_DIR.mkdir(parents=True, exist_ok=True)
        self._conn = sqlite3.connect(str(DB_PATH), check_same_thread=False)
        self._conn.row_factory = sqlite3.Row
        self._init_db()
        self._run_id = uuid.uuid4().hex

        self._queue: Queue = Queue(maxsize=_MAX_QUEUE_SIZE)
        self._stop_event = threading.Event()
        self._flusher = threading.Thread(
            target=_flush_loop,
            args=(self._conn, self._queue, self._stop_event),
            name="usage-flusher", daemon=True,
        )
        self._flusher.start()

    # ── Schema ──────────────────────────────────────────────────────────

    def _init_db(self) -> None:
        cur = self._conn.cursor()
        cur.execute("PRAGMA journal_mode=WAL;")
        cur.execute("PRAGMA busy_timeout=3000;")
        cur.execute("PRAGMA synchronous=NORMAL;")

        cur.execute("""
            CREATE TABLE IF NOT EXISTS tool_calls (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                tool_name TEXT NOT NULL,
                operation TEXT,
                started_at INTEGER NOT NULL,
                duration_ms INTEGER DEFAULT 0,
                tokens_original INTEGER,
                tokens_optimized INTEGER,
                project_path TEXT,
                run_id TEXT,
                error_message TEXT
            )
        """)
        cur.execute("""
            CREATE TABLE IF NOT EXISTS skill_loads (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                skill_id TEXT NOT NULL,
                query TEXT,
                search_term TEXT,
                embed_used INTEGER DEFAULT 0,
                loaded_at INTEGER NOT NULL,
                project_path TEXT,
                run_id TEXT
            )
        """)
        cur.execute("""
            CREATE TABLE IF NOT EXISTS embed_queries (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                query_text TEXT NOT NULL,
                prefix_type TEXT,
                model_name TEXT,
                vector_dim INTEGER,
                duration_ms INTEGER DEFAULT 0,
                result_count INTEGER DEFAULT 0,
                queried_at INTEGER NOT NULL,
                run_id TEXT
            )
        """)
        cur.execute("""
            CREATE TABLE IF NOT EXISTS llm_queries (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                query_text TEXT NOT NULL,
                model_name TEXT,
                duration_ms INTEGER DEFAULT 0,
                result_count INTEGER DEFAULT 0,
                queried_at INTEGER NOT NULL,
                run_id TEXT
            )
        """)
        cur.execute("""
            CREATE INDEX IF NOT EXISTS idx_tool_calls_name
                ON tool_calls(tool_name)
        """)
        cur.execute("""
            CREATE INDEX IF NOT EXISTS idx_tool_calls_started
                ON tool_calls(started_at)
        """)
        self._ensure_columns(cur)
        self._conn.commit()

        # Retention purge
        retention_raw = os.environ.get("AGENT_RETENTION_DAYS", str(_DEFAULT_RETENTION_DAYS))
        try:
            retention_days = int(retention_raw)
        except (ValueError, TypeError):
            retention_days = _DEFAULT_RETENTION_DAYS
        if retention_days > 0:
            cutoff = int(time.time()) - retention_days * 86400
            cur.execute("DELETE FROM tool_calls WHERE started_at < ?", (cutoff,))
            cur.execute("DELETE FROM skill_loads WHERE loaded_at < ?", (cutoff,))
            cur.execute("DELETE FROM embed_queries WHERE queried_at < ?", (cutoff,))
            cur.execute("DELETE FROM llm_queries WHERE queried_at < ?", (cutoff,))
            self._ensure_columns(cur)
        self._conn.commit()

    def _ensure_columns(self, cur) -> None:
        """Add attribution columns to existing DBs (no-op on fresh schemas)."""
        for table, col, coltype in (
            ("tool_calls", "project_path", "TEXT"),
            ("tool_calls", "run_id", "TEXT"),
            ("tool_calls", "error_message", "TEXT"),
            ("skill_loads", "project_path", "TEXT"),
            ("skill_loads", "run_id", "TEXT"),
            ("embed_queries", "run_id", "TEXT"),
            ("embed_queries", "status", "TEXT"),
        ):
            try:
                cur.execute(f"ALTER TABLE {table} ADD COLUMN {col} {coltype}")
            except sqlite3.OperationalError:
                pass  # column already present

    # ── Recording helpers ───────────────────────────────────────────────

    def record_tool_call(
        self,
        tool_name: str,
        operation: str | None = None,
        duration_ms: int = 0,
        tokens_original: int | None = None,
        tokens_optimized: int | None = None,
        project_path: str | None = None,
        error_message: str | None = None,
    ) -> None:
        """Record one tool invocation."""
        now = int(time.time())
        self._queue.put(
            _WriteOp("record_tool_call",
                     (tool_name, operation, now, duration_ms,
                      tokens_original, tokens_optimized, project_path, self._run_id,
                      error_message))
        )

    def record_skill_load(
        self,
        skill_id: str,
        query: str | None = None,
        search_term: str | None = None,
        embed_used: bool = False,
        project_path: str | None = None,
    ) -> None:
        """Record a skill load."""
        now = int(time.time())
        self._queue.put(
            _WriteOp("record_skill_load",
                     (skill_id, query, search_term, int(embed_used), now, project_path, self._run_id))
        )

    def record_recommend_skill_loads(
        self,
        result: object,
        query: str | None = None,
        project_path: str | None = None,
    ) -> None:
        """Record LLM-recommended skills as skill loads (embed_used=True) (F2/F5/F6).

        Each entry in result["recommendations"] is counted as a skill load so the
        dashboard "skills called" metric reflects actual usage. Bulk `search`
        hits are intentionally NOT counted to avoid inflating the metric with
        candidate lists. The e5 embed query for recommend is logged separately
        inside catalog.search_entries on semantic success.
        """
        recs = result.get("recommendations", []) if isinstance(result, dict) else []
        for rec in recs:
            rid = rec.get("identifier") if isinstance(rec, dict) else None
            if rid:
                self.record_skill_load(rid, query=query, embed_used=True, project_path=project_path)

    def record_embed_query(
        self,
        query_text: str,
        prefix_type: str | None = None,
        model_name: str | None = None,
        vector_dim: int = 0,
        duration_ms: int = 0,
        result_count: int = 0,
        status: str = "ok",
    ) -> None:
        """Record an embedding query. status="ok" for a real vector,
        "fallback" for a silent keyword-only degrade.
        """
        now = int(time.time())
        self._queue.put(
            _WriteOp("record_embed_query",
                     (query_text, prefix_type, model_name, vector_dim,
                      duration_ms, result_count, status, now, self._run_id))
        )

    def record_llm_query(
        self,
        query_text: str,
        model_name: str | None = None,
        duration_ms: int = 0,
        result_count: int = 0,
    ) -> None:
        """Record an LLM skill-selector query (e.g. Qwen2.5-0.5B-Instruct)."""
        now = int(time.time())
        self._queue.put(
            _WriteOp("record_llm_query",
                     (query_text, model_name, duration_ms, result_count, now, self._run_id))
        )

    # ── Aggregation / summary ───────────────────────────────────────────

    def summary(self) -> dict[str, Any]:
        """Return aggregated usage summary across all calls."""
        self._flush_now()
        cur = self._conn.cursor()

        cur.execute(
            """SELECT tool_name, operation, COUNT(*) AS cnt,
                      COALESCE(SUM(tokens_original), 0) AS tok_orig,
                      COALESCE(SUM(tokens_optimized), 0) AS tok_opt
               FROM tool_calls
               GROUP BY tool_name, operation
               ORDER BY cnt DESC"""
        )
        tool_breakdown = [dict(r) for r in cur.fetchall()]

        cur.execute(
            """SELECT skill_id, COUNT(*) AS cnt
               FROM skill_loads
               GROUP BY skill_id
               ORDER BY cnt DESC
               LIMIT 20"""
        )
        top_skills = [dict(r) for r in cur.fetchall()]

        cur.execute("SELECT COUNT(*) AS total FROM tool_calls")
        total_calls = cur.fetchone()["total"]
        cur.execute("SELECT COUNT(*) AS total FROM skill_loads")
        total_skills_count = cur.fetchone()["total"]
        cur.execute("SELECT COUNT(*) AS total FROM embed_queries")
        total_embeds = cur.fetchone()["total"]
        cur.execute(
            "SELECT COUNT(*) AS total FROM embed_queries WHERE status='fallback'"
        )
        total_embed_fallback = cur.fetchone()["total"]
        cur.execute("SELECT COUNT(*) AS total FROM llm_queries")
        total_llm = cur.fetchone()["total"]

        cur.execute(
            """SELECT id, queried_at, status, vector_dim, result_count
               FROM embed_queries ORDER BY queried_at DESC LIMIT 20"""
        )
        embed_recent = [dict(r) for r in cur.fetchall()]

        tot_orig = sum(r.get("tok_orig", 0) for r in tool_breakdown)
        tot_opt = sum(r.get("tok_opt", 0) for r in tool_breakdown)
        token_savings = tot_orig - tot_opt
        savings_pct = round((token_savings / max(1, tot_orig)) * 100, 1)

        return {
            "totals": {
                "tool_calls": total_calls,
                "skills_loaded": total_skills_count,
                "embed_queries": total_embeds,
                "embed_fallback": total_embed_fallback,
                "llm_queries": total_llm,
                "tokens_original": tot_orig,
                "tokens_optimized": tot_opt,
                "token_savings": token_savings,
                "savings_pct": savings_pct,
            },
            "tool_breakdown": tool_breakdown,
            "embed_recent": embed_recent,
            "top_skills": top_skills,
        }

    # ── Internal helpers ────────────────────────────────────────────────

    def _flush_now(self) -> None:
        self._queue.join()

    # ── Lifecycle ──────────────────────────────────────────────────────

    def close(self) -> None:
        self._stop_event.set()
        self._flush_now()
        self._conn.close()


# ── Background flusher ──────────────────────────────────────────────────


def _flush_loop(conn, queue, stop_event):
    while True:
        try:
            op = queue.get(timeout=_FLUSH_INTERVAL_S)
        except Empty:
            if stop_event.is_set():
                break
            continue
        _execute_write(conn, op)
        queue.task_done()
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


def _execute_write(conn, op):
    try:
        method = _WRITE_DISPATCH[op.method]
    except KeyError:
        return
    method(conn, *op.args)


def _w_tool_call(conn, tool, op, now, dur, tok_orig, tok_opt, proj, run_id, err):
    conn.execute(
        """INSERT INTO tool_calls
               (tool_name, operation, started_at, duration_ms,
                tokens_original, tokens_optimized, project_path, run_id, error_message)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (tool, op, now, dur, tok_orig, tok_opt, proj, run_id, err),
    )


def _w_skill_load(conn, skill_id, query, search_term, embed_used, now, proj, run_id):
    conn.execute(
        """INSERT INTO skill_loads
               (skill_id, query, search_term, embed_used, loaded_at, project_path, run_id)
           VALUES (?, ?, ?, ?, ?, ?, ?)""",
        (skill_id, query, search_term, embed_used, now, proj, run_id),
    )


def _w_embed_query(conn, qtext, ptype, model, vdim, dur, rcnt, status, now, run_id):
    conn.execute(
        """INSERT INTO embed_queries
                (query_text, prefix_type, model_name, vector_dim,
                 duration_ms, result_count, status, queried_at, run_id)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (qtext, ptype, model, vdim, dur, rcnt, status, now, run_id),
    )


def _w_llm_query(conn, qtext, model, dur, rcnt, now, run_id):
    conn.execute(
        """INSERT INTO llm_queries
                (query_text, model_name, duration_ms, result_count, queried_at, run_id)
           VALUES (?, ?, ?, ?, ?, ?)""",
        (qtext, model, dur, rcnt, now, run_id),
    )


_WRITE_DISPATCH: dict[str, object] = {
    "record_tool_call": _w_tool_call,
    "record_skill_load": _w_skill_load,
    "record_embed_query": _w_embed_query,
    "record_llm_query": _w_llm_query,
}
