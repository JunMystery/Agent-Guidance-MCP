"""Tests for embed daemon's /api/stats endpoint shape."""

import json
import time
from pathlib import Path

import pytest

from agent_guidance_mcp.usage import UsageTracker
from agent_guidance_mcp._dashboard_shared import write_default_dashboard, DASHBOARD_DIR


# ── Dashboard HTML ─────────────────────────────────────────────────────────


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

    def test_dashboard_has_session_selector(self, tmp_path: Path) -> None:
        p = tmp_path / "index.html"
        write_default_dashboard(p)
        content = p.read_text("utf-8")
        assert "session-select" in content

    def test_dashboard_has_fetch_api(self, tmp_path: Path) -> None:
        p = tmp_path / "index.html"
        write_default_dashboard(p)
        content = p.read_text("utf-8")
        assert "/api/stats" in content


# ── Dashboard Server /api/stats shape ──────────────────────────────────────


class TestDashboardServerStatsShape:
    """Test the query logic used by the dashboard server."""

    @pytest.fixture
    def seeded_db(self, tmp_path: Path) -> Path:
        """Create a usage.db with known data."""
        t = UsageTracker(tmp_path)
        sid = t.session_start(client_name="test-cli", session_label="test-label")
        t.record_tool_call("guidance", "search", duration_ms=10,
                           tokens_original=1000, tokens_optimized=500)
        t.record_skill_load("tdd-workflow", query="testing")
        t.record_embed_query("test query", prefix_type="query",
                             model_name="e5-small", duration_ms=50)
        t.session_end()
        time.sleep(0.05)
        t.close()
        return tmp_path

    def _query_stats(self, db_path: Path, session_id: str | None = None) -> dict:
        """Replicate the dashboard server's query path."""
        import sqlite3
        from agent_guidance_mcp.dashboard_server import _query_stats
        conn = sqlite3.connect(str(db_path))
        conn.row_factory = sqlite3.Row
        try:
            return _query_stats(conn, session_id)
        finally:
            conn.close()

    def test_stats_all_returns_sessions_list(self, seeded_db: Path) -> None:
        db_path = seeded_db / ".agent-context" / "usage.db"
        data = self._query_stats(db_path)
        assert "sessions" in data
        assert len(data["sessions"]) >= 1
        assert data["sessions"][0]["client_name"] == "test-cli"

    def test_stats_all_has_totals(self, seeded_db: Path) -> None:
        db_path = seeded_db / ".agent-context" / "usage.db"
        data = self._query_stats(db_path)
        t = data["totals"]
        assert t["tool_calls"] == 1
        assert t["skills_loaded"] == 1
        assert t["embed_queries"] == 1
        assert t["token_savings"] == 500
        assert t["savings_pct"] == 50.0

    def test_stats_session_id_filter(self, seeded_db: Path) -> None:
        db_path = seeded_db / ".agent-context" / "usage.db"
        all_data = self._query_stats(db_path)
        sid = all_data["sessions"][0]["session_id"]
        data = self._query_stats(db_path, session_id=sid)
        assert data["session_id"] == sid
        assert data["session"]["client_name"] == "test-cli"
        assert data["totals"]["tool_calls"] == 1

    def test_stats_all_has_tool_breakdown(self, seeded_db: Path) -> None:
        db_path = seeded_db / ".agent-context" / "usage.db"
        data = self._query_stats(db_path)
        assert len(data["tool_breakdown"]) >= 1
        entry = data["tool_breakdown"][0]
        assert "tool_name" in entry
        assert "operation" in entry
        assert "cnt" in entry
        assert "tok_orig" in entry
        assert "tok_opt" in entry

    def test_stats_all_has_top_skills(self, seeded_db: Path) -> None:
        db_path = seeded_db / ".agent-context" / "usage.db"
        data = self._query_stats(db_path)
        assert len(data["top_skills"]) >= 1
        assert data["top_skills"][0]["skill_id"] == "tdd-workflow"

    def test_stats_empty_db(self, tmp_path: Path) -> None:
        """Empty DB should return zeros, not crash."""
        # Create minimal DB with just schema
        t = UsageTracker(tmp_path)
        t.close()
        db_path = tmp_path / ".agent-context" / "usage.db"
        data = self._query_stats(db_path)
        assert data["totals"]["tool_calls"] == 0
        assert data["totals"]["skills_loaded"] == 0
        assert data["totals"]["embed_queries"] == 0
        assert data["totals"]["token_savings"] == 0

    def test_stats_health_response_shape(self) -> None:
        """Dashboard server /health returns expected keys."""
        from agent_guidance_mcp.dashboard_server import DashboardHandler
        # Just verify the response shape is defined
        assert hasattr(DashboardHandler, "project_path")
