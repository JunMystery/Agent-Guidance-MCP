import sqlite3
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from agent_guidance_mcp import usage as usage_mod
from agent_guidance_mcp import catalog as catalog_mod
from agent_guidance_mcp.catalog import build_catalog
from agent_guidance_mcp import server as server_mod


class TestModelTracking(unittest.TestCase):
    def _tmp_tracker(self):
        tmp = tempfile.mkdtemp()
        db = Path(tmp) / "usage.db"
        usage_mod.DB_PATH = db
        return usage_mod.UsageTracker(), db

    # ── F1: LLM (Qwen) query tracking ──────────────────────────────────

    def test_record_llm_query_writes_row(self):
        tracker, db = self._tmp_tracker()
        tracker.record_llm_query(
            query_text="add auth",
            model_name="Qwen/Qwen2.5-0.5B-Instruct",
            duration_ms=42,
            result_count=3,
        )
        tracker.close()
        conn = sqlite3.connect(str(db))
        rows = conn.execute(
            "SELECT query_text, model_name, duration_ms, result_count FROM llm_queries"
        ).fetchall()
        conn.close()
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0][0], "add auth")
        self.assertEqual(rows[0][1], "Qwen/Qwen2.5-0.5B-Instruct")
        self.assertEqual(rows[0][2], 42)
        self.assertEqual(rows[0][3], 3)

    def test_summary_includes_llm_queries(self):
        tracker, _ = self._tmp_tracker()
        tracker.record_llm_query(query_text="x", model_name="Qwen/Qwen2.5-0.5B-Instruct")
        summary = tracker.summary()
        tracker.close()
        self.assertEqual(summary["totals"]["llm_queries"], 1)

    # ── F5: embed_used flag persists on skill loads ────────────────────

    def test_skill_load_embed_used_flag(self):
        tracker, db = self._tmp_tracker()
        tracker.record_skill_load("context-budget", query="q", embed_used=True)
        tracker.close()
        conn = sqlite3.connect(str(db))
        rows = conn.execute("SELECT skill_id, embed_used FROM skill_loads").fetchall()
        conn.close()
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0][0], "context-budget")
        self.assertEqual(rows[0][1], 1)

    # ── F3/F4: embed query recorded only on real semantic success ──────

    def test_embed_query_recorded_only_on_semantic_success(self):
        tracker, db = self._tmp_tracker()
        catalog = build_catalog()
        with mock.patch.object(server_mod, "get_usage", return_value=tracker), \
             mock.patch.object(catalog_mod, "get_embedding", return_value=None):
            catalog.search_entries(query="rare term xyz", limit=5, kind="skill")
        tracker._flush_now()
        conn = sqlite3.connect(str(db))
        self.assertEqual(conn.execute("SELECT COUNT(*) FROM embed_queries").fetchone()[0], 0)

        with mock.patch.object(server_mod, "get_usage", return_value=tracker), \
             mock.patch.object(catalog_mod, "get_embedding", return_value=[0.1] * 384):
            catalog.search_entries(query="reducing context size budget limit", limit=5, kind="skill")
        tracker._flush_now()
        rows = conn.execute(
            "SELECT model_name, vector_dim, result_count FROM embed_queries"
        ).fetchall()
        conn.close()
        tracker.close()
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0][0], "intfloat/multilingual-e5-small")
        self.assertEqual(rows[0][1], 384)
        self.assertGreater(rows[0][2], 0)

    # ── F2/F5/F6: recommend picks counted as skill loads (embed_used) ──

    def test_record_recommend_skill_loads_helper(self):
        tracker, db = self._tmp_tracker()
        result = {
            "recommendations": [
                {"identifier": "api-design", "title": "API Design"},
                {"identifier": "security-review", "title": "Security Review"},
            ]
        }
        tracker.record_recommend_skill_loads(result, "add jwt auth")
        tracker._flush_now()
        conn = sqlite3.connect(str(db))
        rows = conn.execute("SELECT skill_id, embed_used FROM skill_loads").fetchall()
        conn.close()
        tracker.close()
        self.assertEqual({r[0] for r in rows}, {"api-design", "security-review"})
        self.assertTrue(all(r[1] == 1 for r in rows))

    def test_recommend_context_wiring(self):
        tracker, db = self._tmp_tracker()
        catalog = build_catalog()
        with mock.patch.object(catalog_mod, "get_embedding", return_value=[0.1] * 384):
            result = catalog.recommend_context(task="add jwt authentication", limit=5)
        tracker.record_recommend_skill_loads(result, "add jwt authentication")
        tracker._flush_now()
        conn = sqlite3.connect(str(db))
        rows = conn.execute("SELECT skill_id, embed_used FROM skill_loads").fetchall()
        conn.close()
        tracker.close()
        ids = {r[0] for r in rows}
        self.assertTrue(len(ids) > 0, "recommend should yield skill loads")
        self.assertTrue(all(r[1] == 1 for r in rows))


if __name__ == "__main__":
    unittest.main()
