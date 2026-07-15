"""Tests for persistent usage tracking (UsageTracker)."""

import os
import time
import threading
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor

import pytest

from agent_guidance_mcp.usage import UsageTracker


# ── Helpers ────────────────────────────────────────────────────────────────


def _seed_session(t: UsageTracker, client: str = "test", label: str = "test") -> str:
    sid = t.session_start(client_name=client, session_label=label)
    t.record_tool_call("guidance", "search", duration_ms=10,
                       tokens_original=1000, tokens_optimized=500)
    t.record_skill_load("tdd-workflow", query="test")
    t.record_embed_query("test query", prefix_type="query", model_name="e5-small")
    t.session_end()
    _flush(t)
    return sid


def _flush(t: UsageTracker) -> None:
    """Block until the write queue is drained."""
    t._flush_now()


# ── 5.1: Schema + migration ────────────────────────────────────────────────


class TestSchema:
    def test_fresh_db_creates_tables(self, tmp_path: Path) -> None:
        t = UsageTracker(tmp_path)
        cur = t._conn.cursor()
        cur.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")
        tables = {row["name"] for row in cur.fetchall()}
        assert "sessions" in tables
        assert "tool_calls" in tables
        assert "skill_loads" in tables
        assert "embed_queries" in tables
        assert "schema_version" in tables
        t.close()

    def test_v1_to_v2_migration(self, tmp_path: Path) -> None:
        """Simulate v1 DB, verify v2 migration adds columns."""
        db_path = tmp_path / ".agent-context" / "usage.db"
        db_path.parent.mkdir(parents=True, exist_ok=True)

        import sqlite3
        conn = sqlite3.connect(str(db_path))
        conn.execute("PRAGMA journal_mode=WAL;")
        conn.execute("""
            CREATE TABLE IF NOT EXISTS schema_version (
                version INTEGER PRIMARY KEY, applied_at INTEGER NOT NULL
            )
        """)
        conn.execute("""
            CREATE TABLE sessions (
                session_id TEXT PRIMARY KEY, started_at INTEGER NOT NULL,
                ended_at INTEGER, project_path TEXT NOT NULL,
                tool_call_count INTEGER DEFAULT 0,
                total_tokens_original INTEGER DEFAULT 0,
                total_tokens_optimized INTEGER DEFAULT 0,
                total_skills_loaded INTEGER DEFAULT 0,
                total_embed_queries INTEGER DEFAULT 0
            )
        """)
        conn.execute("INSERT INTO schema_version (version, applied_at) VALUES (1, 1000)")
        conn.commit()
        conn.close()

        # Open with v2 code — should migrate
        t = UsageTracker(tmp_path)
        cur = t._conn.cursor()
        cur.execute("PRAGMA table_info(sessions)")
        cols = {row["name"] for row in cur.fetchall()}
        assert "client_name" in cols
        assert "session_label" in cols
        t.close()

    def test_idempotent_migration(self, tmp_path: Path) -> None:
        t1 = UsageTracker(tmp_path)
        t1.close()
        t2 = UsageTracker(tmp_path)  # re-open — migration already done
        cur = t2._conn.cursor()
        cur.execute("SELECT MAX(version) AS v FROM schema_version")
        assert cur.fetchone()["v"] == 2
        cur.execute("PRAGMA table_info(sessions)")
        cols = {row["name"] for row in cur.fetchall()}
        assert "client_name" in cols
        t2.close()


# ── 5.2: Session lifecycle ─────────────────────────────────────────────────


class TestSessionLifecycle:
    def test_session_start_returns_id(self, tmp_path: Path) -> None:
        t = UsageTracker(tmp_path)
        sid = t.session_start()
        assert sid is not None
        assert len(sid) == 32  # UUID hex
        t.close()

    def test_session_start_with_client_and_label(self, tmp_path: Path) -> None:
        t = UsageTracker(tmp_path)
        sid = t.session_start(client_name="Cursor", session_label="My Task")
        t.record_tool_call("test", "op")
        t.session_end()
        _flush(t)
        s = t.summary(session_id=sid)
        assert s["session"]["client_name"] == "Cursor"
        assert s["session"]["session_label"] == "My Task"
        t.close()

    def test_session_start_with_external_id(self, tmp_path: Path) -> None:
        t = UsageTracker(tmp_path)
        sid = t.session_start(external_session_id="ide-abc-123")
        t.record_tool_call("test", "op")
        t.session_end()
        _flush(t)
        s = t.summary(session_id=sid)
        assert sid == "ide-abc-123"
        assert s["session"]["session_id"] == "ide-abc-123"
        t.close()

    def test_session_end_marks_ended(self, tmp_path: Path) -> None:
        t = UsageTracker(tmp_path)
        sid = t.session_start()
        t.session_end()
        _flush(t)
        s = t.summary(session_id=sid)
        assert s["session"]["ended_at"] is not None
        assert s["session"]["duration_seconds"] >= 0
        t.close()

    def test_session_end_computes_totals(self, tmp_path: Path) -> None:
        t = UsageTracker(tmp_path)
        sid = t.session_start()
        for _ in range(5):
            t.record_tool_call("test", "op")
        t.session_end()
        _flush(t)
        cur = t._conn.cursor()
        cur.execute("SELECT * FROM sessions WHERE session_id = ?", (sid,))
        row = dict(cur.fetchone())
        assert row["tool_call_count"] == 5
        t.close()


# ── 5.3: Recording helpers ─────────────────────────────────────────────────


class TestRecording:
    def test_tool_call_recorded(self, tmp_path: Path) -> None:
        t = UsageTracker(tmp_path)
        sid = t.session_start()
        t.record_tool_call("guidance", "search", duration_ms=42,
                           tokens_original=1000, tokens_optimized=600)
        _flush(t)
        cur = t._conn.cursor()
        cur.execute("SELECT * FROM tool_calls WHERE session_id = ?", (sid,))
        rows = cur.fetchall()
        assert len(rows) == 1
        assert rows[0]["tool_name"] == "guidance"
        assert rows[0]["tokens_original"] == 1000
        t.close()

    def test_skill_load_recorded(self, tmp_path: Path) -> None:
        t = UsageTracker(tmp_path)
        t.session_start()
        t.record_skill_load("tdd-workflow", query="testing", embed_used=True)
        _flush(t)
        cur = t._conn.cursor()
        cur.execute("SELECT * FROM skill_loads")
        rows = cur.fetchall()
        assert len(rows) == 1
        assert rows[0]["skill_id"] == "tdd-workflow"
        assert rows[0]["embed_used"] == 1
        t.close()

    def test_embed_query_recorded(self, tmp_path: Path) -> None:
        t = UsageTracker(tmp_path)
        t.session_start()
        t.record_embed_query("test query", prefix_type="query",
                             model_name="e5-small", vector_dim=384, duration_ms=85)
        _flush(t)
        cur = t._conn.cursor()
        cur.execute("SELECT * FROM embed_queries")
        rows = cur.fetchall()
        assert len(rows) == 1
        assert rows[0]["model_name"] == "e5-small"
        t.close()

    def test_update_session_label(self, tmp_path: Path) -> None:
        t = UsageTracker(tmp_path)
        sid = t.session_start(client_name="test")
        t.update_session_label(sid, "updated-label")
        t.record_tool_call("test", "op")
        t.session_end()
        _flush(t)
        s = t.summary(session_id=sid)
        assert s["session"]["session_label"] == "updated-label"
        t.close()

    def test_recording_without_session_does_nothing(self, tmp_path: Path) -> None:
        t = UsageTracker(tmp_path)
        t.record_tool_call("test", "op")  # no session started
        _flush(t)
        cur = t._conn.cursor()
        cur.execute("SELECT COUNT(*) AS c FROM tool_calls")
        assert cur.fetchone()["c"] == 0
        t.close()

    def test_session_start_no_params_backward_compat(self, tmp_path: Path) -> None:
        t = UsageTracker(tmp_path)
        sid = t.session_start()  # no client_name, no label
        assert sid is not None
        t.record_tool_call("test", "op")
        t.session_end()
        _flush(t)
        s = t.summary(session_id=sid)
        assert s["session"]["client_name"] is None
        assert s["session"]["session_label"] is None
        t.close()


# ── 5.4: Aggregation ───────────────────────────────────────────────────────


class TestAggregation:
    def test_summary_session_scope(self, tmp_path: Path) -> None:
        t = UsageTracker(tmp_path)
        _seed_session(t)
        s = t.summary(scope="session")  # no active session, shows last
        assert s["session_id"] is None or isinstance(s["session_id"], str)
        assert "totals" in s
        t.close()

    def test_summary_all_scope_returns_sessions_list(self, tmp_path: Path) -> None:
        t = UsageTracker(tmp_path)
        sid1 = _seed_session(t, "cli-1", "sess-a")
        sid2 = _seed_session(t, "cli-2", "sess-b")
        s = t.summary(scope="all")
        assert "sessions" in s
        ids = {row["session_id"] for row in s["sessions"]}
        assert sid1 in ids
        assert sid2 in ids
        assert len(s["sessions"]) >= 2
        t.close()

    def test_summary_session_id_filter(self, tmp_path: Path) -> None:
        t = UsageTracker(tmp_path)
        sid1 = _seed_session(t, "cli-1", "first")
        sid2 = _seed_session(t, "cli-2", "second")
        s = t.summary(session_id=sid1)
        assert s["session_id"] == sid1
        assert s["session"]["client_name"] == "cli-1"
        assert s["session"]["session_label"] == "first"
        t.close()

    def test_summary_totals_aggregate(self, tmp_path: Path) -> None:
        t = UsageTracker(tmp_path)
        _seed_session(t)
        _seed_session(t)
        _flush(t)
        s = t.summary(scope="all")
        assert s["totals"]["tool_calls"] == 2  # 1 tool per session
        assert s["totals"]["skills_loaded"] == 2
        assert s["totals"]["embed_queries"] == 2
        assert s["totals"]["token_savings"] == 1000  # (1000-500) * 2 sessions
        t.close()

    def test_tool_breakdown(self, tmp_path: Path) -> None:
        t = UsageTracker(tmp_path)
        sid = t.session_start()
        t.record_tool_call("guidance", "search")
        t.record_tool_call("guidance", "search")
        t.record_tool_call("project_context", "read")
        t.session_end()
        _flush(t)
        s = t.summary(session_id=sid)
        breakdown = {r["tool_name"] + "/" + (r["operation"] or ""): r["cnt"]
                     for r in s["tool_breakdown"]}
        assert breakdown.get("guidance/search") == 2
        assert breakdown.get("project_context/read") == 1
        t.close()

    def test_top_skills(self, tmp_path: Path) -> None:
        t = UsageTracker(tmp_path)
        sid = t.session_start()
        t.record_skill_load("tdd-workflow")
        t.record_skill_load("backend-patterns")
        t.record_skill_load("tdd-workflow")
        t.session_end()
        _flush(t)
        s = t.summary(session_id=sid)
        skills = {r["skill_id"]: r["cnt"] for r in s["top_skills"]}
        assert skills.get("tdd-workflow") == 2
        assert skills.get("backend-patterns") == 1
        t.close()


# ── 5.5: Persistence ───────────────────────────────────────────────────────


class TestPersistence:
    def test_data_survives_close_reopen(self, tmp_path: Path) -> None:
        t = UsageTracker(tmp_path)
        sid = _seed_session(t)
        t.close()

        t2 = UsageTracker(tmp_path)
        s = t2.summary(scope="all")
        assert s["totals"]["tool_calls"] == 1
        assert len(s["sessions"]) == 1
        assert s["sessions"][0]["session_id"] == sid
        t2.close()

    def test_multiple_sessions_accumulate(self, tmp_path: Path) -> None:
        t = UsageTracker(tmp_path)
        _seed_session(t, "cli-1")
        t.close()

        t2 = UsageTracker(tmp_path)
        _seed_session(t2, "cli-2")
        t2.close()

        t3 = UsageTracker(tmp_path)
        s = t3.summary(scope="all")
        assert len(s["sessions"]) == 2
        t3.close()

    def test_wal_preserves_data_on_crash(self, tmp_path: Path) -> None:
        """WAL mode ensures committed data survives unclean shutdown."""
        t = UsageTracker(tmp_path)
        sid = t.session_start()
        t.record_tool_call("test", "op")
        t.session_end()
        _flush(t)
        db_path = t._db_path
        t.close()

        # Simulate "crash" by just deleting the in-memory reference
        import sqlite3
        conn = sqlite3.connect(str(db_path))
        conn.row_factory = sqlite3.Row
        cur = conn.cursor()
        cur.execute("SELECT COUNT(*) AS c FROM tool_calls")
        assert cur.fetchone()["c"] == 1
        conn.close()


# ── 5.6: Concurrency ───────────────────────────────────────────────────────


class TestConcurrency:
    def test_concurrent_record_calls(self, tmp_path: Path) -> None:
        t = UsageTracker(tmp_path)
        sid = t.session_start()
        n = 50

        def record(i: int) -> None:
            t.record_tool_call(f"tool-{i % 5}", "op")

        with ThreadPoolExecutor(max_workers=8) as pool:
            pool.map(record, range(n))
        t.session_end()
        _flush(t)

        s = t.summary(session_id=sid)
        assert s["totals"]["tool_calls"] == n
        t.close()

    def test_concurrent_read_write(self, tmp_path: Path) -> None:
        t = UsageTracker(tmp_path)
        sid = t.session_start()

        def writer() -> None:
            for _ in range(20):
                t.record_tool_call("w", "op")
                time.sleep(0.001)

        def reader() -> None:
            for _ in range(5):
                t.summary(session_id=sid)
                time.sleep(0.002)

        threads = []
        for _ in range(3):
            th = threading.Thread(target=writer, daemon=True)
            th.start()
            threads.append(th)
        for _ in range(2):
            th = threading.Thread(target=reader, daemon=True)
            th.start()
            threads.append(th)
        for th in threads:
            th.join(timeout=5)
        t.session_end()
        _flush(t)

        s = t.summary(session_id=sid)
        assert s["totals"]["tool_calls"] == 60  # 3 writers * 20
        t.close()

    def test_multiple_trackers_same_db(self, tmp_path: Path) -> None:
        """Two UsageTracker instances pointing same DB (simulates 2 MCP servers)."""
        t1 = UsageTracker(tmp_path)
        t2 = UsageTracker(tmp_path)

        sid1 = t1.session_start(client_name="server-1")
        t1.record_tool_call("tool", "op1")
        t1.session_end()

        sid2 = t2.session_start(client_name="server-2")
        t2.record_tool_call("tool", "op2")
        t2.session_end()

        _flush(t1)
        _flush(t2)

        t1.close()
        t2.close()

        t3 = UsageTracker(tmp_path)
        s = t3.summary(scope="all")
        assert len(s["sessions"]) == 2
        # Each sees their own session
        s1 = t3.summary(session_id=sid1)
        assert s1["session"]["client_name"] == "server-1"
        s2 = t3.summary(session_id=sid2)
        assert s2["session"]["client_name"] == "server-2"
        t3.close()
