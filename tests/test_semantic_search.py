import unittest
from pathlib import Path
from agent_guidance_mcp.embeddings import cosine_similarity, get_embedding, load_precomputed_embeddings
from agent_guidance_mcp.catalog import build_catalog, StandardsCatalog

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

if __name__ == "__main__":
    unittest.main()
