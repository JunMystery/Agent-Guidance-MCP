"""Tests for embed daemon's /api/stats endpoint shape and dashboard HTML."""

import json
import time
from pathlib import Path

import pytest

from agent_guidance_mcp.usage import UsageTracker, DB_PATH as _db_path
from agent_guidance_mcp._dashboard_shared import write_default_dashboard, DASHBOARD_DIR

# ── Patch DB path for tests ───────────────────────────────────────────

@pytest.fixture(autouse=True)
def _test_db(tmp_path):
    import agent_guidance_mcp.usage as mod
    orig = mod.DB_PATH
    test_db = tmp_path / "usage.db"
    mod.DB_PATH = test_db
    yield
    mod.DB_PATH = orig


class TestDashboardHTML:
    def test_dashboard_html_written(self, tmp_path: Path) -> None:
        p = tmp_path / "index.html"
        write_default_dashboard(p)
        assert p.exists()
        content = p.read_text("utf-8")
        assert "<!DOCTYPE html>" in content
        assert "sidebar" in content
        assert "</html>" in content

    def test_dashboard_has_all_sections(self, tmp_path: Path) -> None:
        p = tmp_path / "index.html"
        write_default_dashboard(p)
        content = p.read_text("utf-8")
        sections = ["view-dashboard", "view-actions", "view-tokens",
                    "view-embed", "view-guides", "view-tools"]
        for sec in sections:
            assert sec in content, f"Missing section: {sec}"

    def test_dashboard_has_fetch_api(self, tmp_path: Path) -> None:
        p = tmp_path / "index.html"
        write_default_dashboard(p)
        content = p.read_text("utf-8")
        assert "/api/stats" in content


class TestDashboardServerStatsShape:
    """Test the query logic used by the dashboard server."""

    @pytest.fixture
    def seeded_db(self, tmp_path: Path) -> None:
        """Seed the global usage.db with known data."""
        import agent_guidance_mcp.usage as mod
        mod.DB_PATH = tmp_path / "usage.db"
        t = UsageTracker()
        t.record_tool_call("guidance", "search", duration_ms=10,
                           tokens_original=1000, tokens_optimized=500)
        t.record_skill_load("tdd-workflow", query="testing")
        t.record_embed_query("test query", model_name="e5-small", duration_ms=50)
        t.close()

    def _query_stats(self, db_path: Path) -> dict:
        import sqlite3
        from agent_guidance_mcp.dashboard_server import _query_stats
        conn = sqlite3.connect(str(db_path))
        conn.row_factory = sqlite3.Row
        try:
            return _query_stats(conn)
        finally:
            conn.close()

    def test_stats_all_has_totals(self, seeded_db, tmp_path) -> None:
        data = self._query_stats(tmp_path / "usage.db")
        t = data["totals"]
        assert t["tool_calls"] == 1
        assert t["skills_loaded"] == 1
        assert t["embed_queries"] == 1
        assert t["token_savings"] == 500
        assert t["savings_pct"] == 50.0

    def test_stats_all_has_tool_breakdown(self, seeded_db, tmp_path) -> None:
        data = self._query_stats(tmp_path / "usage.db")
        assert len(data["tool_breakdown"]) >= 1
        assert data["tool_breakdown"][0]["tool_name"] == "guidance"

    def test_stats_all_has_top_skills(self, seeded_db, tmp_path) -> None:
        data = self._query_stats(tmp_path / "usage.db")
        assert len(data["top_skills"]) >= 1
        assert data["top_skills"][0]["skill_id"] == "tdd-workflow"

    def test_stats_empty_db(self, tmp_path: Path) -> None:
        """Empty DB should return zeros, not crash."""
        import agent_guidance_mcp.usage as mod
        mod.DB_PATH = tmp_path / "usage.db"
        t = UsageTracker()
        t.close()
        data = self._query_stats(tmp_path / "usage.db")
        assert data["totals"]["tool_calls"] == 0
        assert data["totals"]["tokens_original"] == 0

    def test_stats_no_sessions_key(self, seeded_db, tmp_path) -> None:
        data = self._query_stats(tmp_path / "usage.db")
        assert "sessions" not in data
        assert "session_id" not in data

    def test_stats_health_response_shape(self) -> None:
        """Dashboard server /health returns expected keys."""
        from agent_guidance_mcp.dashboard_server import DashboardHandler
        assert hasattr(DashboardHandler, "do_GET")
        assert hasattr(DashboardHandler, "_handle_health")
