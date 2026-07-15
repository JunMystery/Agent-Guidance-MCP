import os
import sqlite3
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from agent_guidance_mcp.embeddings import cosine_similarity, get_embedding, load_precomputed_embeddings
from agent_guidance_mcp.catalog import build_catalog, StandardsCatalog, CatalogEntry
from agent_guidance_mcp import usage as usage_mod


class TestSemanticSearch(unittest.TestCase):
    def test_cosine_similarity(self):
        # Orthogonal vectors
        v1 = [1.0, 0.0, 0.0]
        v2 = [0.0, 1.0, 0.0]
        self.assertAlmostEqual(cosine_similarity(v1, v2), 0.0)

        # Identical vectors
        self.assertAlmostEqual(cosine_similarity(v1, v1), 1.0)

        # Opposite vectors
        v3 = [-1.0, 0.0, 0.0]
        self.assertAlmostEqual(cosine_similarity(v1, v3), -1.0)

    def test_precomputed_embeddings_exist(self):
        embeddings = load_precomputed_embeddings()
        self.assertTrue(len(embeddings) > 0)
        self.assertIn("context-budget", embeddings)

    def test_catalog_semantic_search(self):
        # Build catalog
        catalog = build_catalog()

        # Try a semantic search query for context budget
        results = catalog.search_entries(query="reducing context size budget limit", limit=5, kind="skill")
        self.assertTrue(len(results) > 0)

        # Verify that context-budget is in the results and has a high ranking
        top_identifiers = [r["identifier"] for r in results]
        self.assertIn("context-budget", top_identifiers)

    def test_local_workspace_skills_indexing(self):
        catalog = build_catalog()
        # Verify that the workspace-local skill (.agents/skills/agent-guidance/SKILL.md) is indexed
        self.assertTrue(any(e.identifier == "agent-guidance" for e in catalog.entries))

        # Find the entry and check category and kind
        local_entry = next(e for e in catalog.entries if e.identifier == "agent-guidance")
        self.assertEqual(local_entry.kind, "skill")
        self.assertEqual(local_entry.category, "skills")

        # Verify that it is loaded with dynamic embeddings
        self.assertIn("agent-guidance", catalog.skills_embeddings)

    # ── F6: dimension guard ────────────────────────────────────────────────

    def test_cosine_dimension_guard(self):
        # Mismatched dimensions must not raise and must degrade to 0.0.
        self.assertEqual(cosine_similarity([1.0, 0.0], [1.0, 0.0, 0.0]), 0.0)
        self.assertEqual(cosine_similarity([1.0, 0.0, 0.0], [1.0]), 0.0)

    # ── F1: negative semantic must not suppress keyword matches ────────────

    def test_search_negative_semantic_not_suppressed(self):
        entries = [
            CatalogEntry(
                identifier="jwt-auth",
                title="JWT auth middleware",
                path="skills/jwt-auth/SKILL.md",
                kind="skill",
                category="security",
                description="JWT authentication middleware",
            ),
        ]
        catalog = StandardsCatalog(Path("/tmp"), entries)
        # Query vector and entry vector are opposite -> cosine == -1.
        q_vec = [1.0, 0.0, 0.0, 0.0]
        catalog.skills_embeddings = {"jwt-auth": [-1.0, 0.0, 0.0, 0.0]}
        with mock.patch("agent_guidance_mcp.catalog.get_embedding", return_value=q_vec):
            results = catalog.search_entries("jwt authentication middleware", limit=5, kind="skill")
        self.assertIn("jwt-auth", [r["identifier"] for r in results])

    # ── F3: word-boundary keyword matching (no false substring positives) ──

    def test_search_word_boundary_no_false_positive(self):
        entries = [
            CatalogEntry(
                identifier="rapid-thing",
                title="Rapid prototyping tool",
                path="skills/rapid-thing/SKILL.md",
                kind="skill",
                category="frontend",
                description="rapid prototyping",
            ),
            CatalogEntry(
                identifier="api-design",
                title="API design guide",
                path="skills/api-design/SKILL.md",
                kind="skill",
                category="backend",
                description="api design",
            ),
        ]
        catalog = StandardsCatalog(Path("/tmp"), entries)
        catalog.skills_embeddings = {}
        # Disable semantic so the test isolates keyword matching only.
        with mock.patch("agent_guidance_mcp.catalog.get_embedding", return_value=None):
            results = catalog.search_entries("api", limit=10, kind="skill")
        ids = [r["identifier"] for r in results]
        self.assertIn("api-design", ids)
        self.assertNotIn("rapid-thing", ids)

    # ── F2/F5: persistence + hash round-trip ──────────────────────────────

    def test_embeddings_persist_roundtrip(self):
        tmp = tempfile.NamedTemporaryFile(suffix=".json", delete=False)
        tmp.close()
        os.unlink(tmp.name)
        from agent_guidance_mcp import embeddings as emb_mod
        try:
            with mock.patch.object(emb_mod, "_EMBEDDINGS_FILE", Path(tmp.name)):
                # Use realistic 384-dim e5 vectors (load guard rejects others).
                vec = [0.1] * 384
                self.assertTrue(emb_mod.save_embeddings({"foo": vec}, {"foo": "h123"}))
                vectors = emb_mod.load_precomputed_embeddings()
                hashes = emb_mod.load_embedding_hashes()
            self.assertEqual(vectors, {"foo": vec})
            self.assertEqual(hashes, {"foo": "h123"})
            self.assertNotIn("__meta__", vectors)
        finally:
            if os.path.exists(tmp.name):
                os.unlink(tmp.name)

    # ── F9: embed-query telemetry records prefix_type ─────────────────────

    def test_embed_query_prefix_type_recorded(self):
        tmp = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
        tmp.close()
        os.unlink(tmp.name)
        try:
            with mock.patch.object(usage_mod, "DB_PATH", Path(tmp.name)):
                tracker = usage_mod.UsageTracker()
                tracker.record_embed_query(
                    query_text="token budget", prefix_type="query", model_name="e5-small"
                )
                tracker.close()
            conn = sqlite3.connect(tmp.name)
            row = conn.execute(
                "SELECT prefix_type FROM embed_queries ORDER BY id DESC LIMIT 1"
            ).fetchone()
            conn.close()
            self.assertIsNotNone(row)
            self.assertEqual(row[0], "query")
        finally:
            if os.path.exists(tmp.name):
                os.unlink(tmp.name)


if __name__ == "__main__":
    unittest.main()
