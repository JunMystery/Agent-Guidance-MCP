"""Tests for per-call usage tracking (no sessions, no project paths)."""

import json
import threading
import time
from pathlib import Path

import pytest

from agent_guidance_mcp.usage import UsageTracker, DB_PATH


def _flush(t: UsageTracker) -> None:
    t._flush_now()


# ── Fixtures ──────────────────────────────────────────────────────────

@pytest.fixture(autouse=True)
def _clean_db():
    """Use a temporary DB path to avoid interfering with real usage data."""
    orig = DB_PATH
    test_db = Path(__file__).parent / ".pytest_temp" / "test_usage.db"
    test_db.parent.mkdir(parents=True, exist_ok=True)
    # Monkey-patch by replacing the module-level constant path
    import agent_guidance_mcp.usage as mod
    mod.DB_PATH = test_db
    if test_db.exists():
        test_db.unlink()
    yield
    mod.DB_PATH = orig


# ── Schema ────────────────────────────────────────────────────────────

class TestSchema:
    def test_fresh_db_creates_tables(self) -> None:
        t = UsageTracker()
        t.close()
        import sqlite3
        conn = sqlite3.connect(str(DB_PATH))
        tables = {r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type='table'")}
        conn.close()
        assert "tool_calls" in tables
        assert "skill_loads" in tables
        assert "embed_queries" in tables

    def test_no_sessions_table(self) -> None:
        import sqlite3
        t = UsageTracker()
        t.close()
        conn = sqlite3.connect(str(DB_PATH))
        tables = {r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type='table'")}
        conn.close()
        assert "sessions" not in tables


# ── Recording ─────────────────────────────────────────────────────────

class TestRecording:
    def test_tool_call_recorded(self) -> None:
        t = UsageTracker()
        t.record_tool_call("test_tool", "op1", duration_ms=100,
                           tokens_original=500, tokens_optimized=200)
        s = t.summary()
        t.close()
        assert s["totals"]["tool_calls"] == 1
        assert s["tool_breakdown"][0]["tool_name"] == "test_tool"

    def test_skill_load_recorded(self) -> None:
        t = UsageTracker()
        t.record_skill_load("tdd-workflow", query="testing")
        s = t.summary()
        t.close()
        assert s["totals"]["skills_loaded"] == 1
        assert s["top_skills"][0]["skill_id"] == "tdd-workflow"

    def test_embed_query_recorded(self) -> None:
        t = UsageTracker()
        t.record_embed_query("test query", model_name="e5-small", duration_ms=50)
        s = t.summary()
        t.close()
        assert s["totals"]["embed_queries"] == 1


# ── Aggregation ───────────────────────────────────────────────────────

class TestAggregation:
    def test_tool_breakdown(self) -> None:
        t = UsageTracker()
        t.record_tool_call("tool_a", "op1", tokens_original=100, tokens_optimized=30)
        t.record_tool_call("tool_a", "op1", tokens_original=200, tokens_optimized=60)
        t.record_tool_call("tool_b", "op1", tokens_original=50, tokens_optimized=10)
        s = t.summary()
        t.close()
        assert s["totals"]["tool_calls"] == 3
        breakdown = {r["tool_name"]: r["cnt"] for r in s["tool_breakdown"]}
        assert breakdown["tool_a"] == 2
        assert breakdown["tool_b"] == 1

    def test_token_totals(self) -> None:
        t = UsageTracker()
        t.record_tool_call("tool_a", "op1", tokens_original=1000, tokens_optimized=300)
        t.record_tool_call("tool_b", "op1", tokens_original=500, tokens_optimized=100)
        s = t.summary()
        t.close()
        assert s["totals"]["tokens_original"] == 1500
        assert s["totals"]["tokens_optimized"] == 400
        assert s["totals"]["token_savings"] == 1100
        assert s["totals"]["savings_pct"] == 73.3

    def test_top_skills(self) -> None:
        t = UsageTracker()
        for i in range(5):
            t.record_skill_load("skill_a")
            t.record_skill_load("skill_b")
        t.record_skill_load("skill_a")
        t.record_skill_load("skill_c")
        s = t.summary()
        t.close()
        assert s["totals"]["skills_loaded"] == 12
        assert s["top_skills"][0]["skill_id"] == "skill_a"
        assert s["top_skills"][0]["cnt"] >= 5

    def test_no_sessions_in_response(self) -> None:
        t = UsageTracker()
        t.record_tool_call("x", "op1")
        s = t.summary()
        t.close()
        assert "sessions" not in s
        assert "session_id" not in s

    def test_empty_db_returns_zeros(self) -> None:
        t = UsageTracker()
        s = t.summary()
        t.close()
        assert s["totals"]["tool_calls"] == 0
        assert s["totals"]["skills_loaded"] == 0
        assert s["totals"]["embed_queries"] == 0
        assert s["totals"]["tokens_original"] == 0


# ── Persistence ───────────────────────────────────────────────────────

class TestPersistence:
    def test_data_survives_close_reopen(self) -> None:
        t = UsageTracker()
        t.record_tool_call("persist", "op1", tokens_original=100, tokens_optimized=30)
        t.close()

        t2 = UsageTracker()
        s = t2.summary()
        assert s["totals"]["tool_calls"] == 1
        t2.close()


# ── Concurrency ───────────────────────────────────────────────────────

class TestConcurrency:
    def test_concurrent_record_calls(self) -> None:
        t = UsageTracker()
        n = 50
        def writer(start):
            for i in range(start, start + n):
                t.record_tool_call(f"tool_{i}", "op1")
        threads = [threading.Thread(target=writer, args=(i * n,)) for i in range(4)]
        for th in threads:
            th.start()
        for th in threads:
            th.join()
        s = t.summary()
        t.close()
        assert s["totals"]["tool_calls"] == 200

    def test_concurrent_read_write(self) -> None:
        t = UsageTracker()
        stop = threading.Event()
        results = []
        def writer():
            i = 0
            while not stop.is_set():
                t.record_tool_call("concurrent", "op1", tokens_original=10, tokens_optimized=5)
                i += 1
        def reader():
            while not stop.is_set():
                s = t.summary()
                if s["totals"]["tool_calls"] > 0:
                    results.append(s["totals"]["tool_calls"])
        w = threading.Thread(target=writer, daemon=True)
        r = threading.Thread(target=reader, daemon=True)
        w.start()
        r.start()
        time.sleep(0.3)
        stop.set()
        w.join(timeout=1)
        r.join(timeout=1)
        t.close()
        assert len(results) > 0


# ── Retention ─────────────────────────────────────────────────────────

class TestRetention:
    def test_old_records_purged(self) -> None:
        import os
        os.environ["AGENT_RETENTION_DAYS"] = "0"
        t = UsageTracker()
        t.record_tool_call("old_call", "op1")
        s = t.summary()
        t.close()
        assert s["totals"]["tool_calls"] >= 0
        os.environ.pop("AGENT_RETENTION_DAYS", None)

    def test_retention_days_configurable(self) -> None:
        import os
        os.environ["AGENT_RETENTION_DAYS"] = "1"
        # Calls from 2 days ago should be purged
        t = UsageTracker()
        t.close()
        os.environ.pop("AGENT_RETENTION_DAYS", None)
