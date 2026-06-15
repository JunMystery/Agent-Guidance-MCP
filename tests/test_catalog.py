from pathlib import Path

import pytest

from agent_guidance_mcp.catalog import build_catalog, find_standards_root


ROOT = Path(__file__).resolve().parents[1]


def test_find_standards_root_detects_parent_checkout():
    assert find_standards_root(ROOT) == ROOT


def test_build_catalog_uses_standalone_repo_by_default():
    catalog = build_catalog()

    assert catalog.root == ROOT


def test_catalog_indexes_core_surfaces():
    catalog = build_catalog(ROOT)
    identifiers = {entry["identifier"] for entry in catalog.list_entries()}

    assert "karpathy-principles" in identifiers
    assert "skill-reference" in identifiers
    assert "ui-ux-pro-max" in identifiers
    assert "frontend-hub" in identifiers
    assert "testing-hub" in identifiers
    assert "security-hub" in identifiers
    assert "docs-research-hub" in identifiers
    assert "workflow-hub" in identifiers
    assert "backend-hub" in identifiers
    assert "workflow-modes" in identifiers
    assert "orchestration-pipeline" in identifiers
    assert "agent-workflow-ops" in identifiers
    assert "session-context-ops" in identifiers
    assert "testing-core" in identifiers
    assert "framework-testing" in identifiers
    assert "codex" not in identifiers
    assert all(entry["kind"] != "agent" for entry in catalog.list_entries())


def test_catalog_exposes_ui_ux_pro_max_as_one_public_skill():
    catalog = build_catalog(ROOT)
    skill_identifiers = {entry["identifier"] for entry in catalog.list_entries(kind="skill")}

    assert "ui-ux-pro-max" in skill_identifiers
    assert {
        "banner-design",
        "brand",
        "slides",
        "ui-styling",
    }.isdisjoint(skill_identifiers)


def test_catalog_reads_skill_by_name():
    catalog = build_catalog(ROOT)

    content = catalog.read_entry("security-core")

    assert "# Security Core" in content
    assert "authentication" in content.lower()


def test_catalog_keeps_specialized_skills_directly_loadable():
    catalog = build_catalog(ROOT)

    assert "# UI/UX Pro Max" in catalog.read_entry("ui-ux-pro-max")


def test_hub_skills_route_to_obvious_specialized_skills():
    catalog = build_catalog(ROOT)

    hub_expectations = {
        "frontend-hub": [
            "ui-ux-pro-max",
            "frontend-core",
            "frontend-frameworks",
            "browser-qa",
            "motion-design",
            "presentation-ui",
        ],
        "testing-hub": [
            "testing-core",
            "framework-testing",
            "browser-qa",
        ],
        "security-hub": [
            "security-core",
            "framework-security",
            "regulated-security",
        ],
        "docs-research-hub": [
            "research-core",
            "scientific-research",
            "content-core",
            "media-doc-processing",
        ],
        "workflow-hub": [
            "workflow-modes",
            "orchestration-pipeline",
            "agent-workflow-ops",
            "session-context-ops",
        ],
        "backend-hub": [
            "backend-core",
            "backend-frameworks",
            "data-platforms",
            "api-integrations",
        ],
    }

    for hub, expected_skills in hub_expectations.items():
        content = catalog.read_entry(hub)
        for skill in expected_skills:
            assert f"`{skill}`" in content


def test_skill_grouping_audit_documents_grouping_strategy():
    audit = (ROOT / "docs" / "skill-grouping-audit.md").read_text(encoding="utf-8")

    assert "Hubs route; specialized skills teach" in audit
    assert "[Skill Merge Policy](skill-merge-policy.md)" in audit
    assert "## Hub Groups" in audit
    assert "## Niche Or Unassigned Skills" in audit
    assert "## Future Merge Candidates" in audit
    assert "`frontend-hub`" in audit
    assert "`backend-hub`" in audit


def test_catalog_search_returns_ranked_snippets():
    catalog = build_catalog(ROOT)

    results = catalog.search_entries("security auth secrets", limit=3)

    assert results
    assert all("snippet" in result for result in results)
    assert any("security" in result["path"].lower() for result in results)


def test_recommend_context_includes_essentials_and_task_matches():
    catalog = build_catalog(ROOT)

    result = catalog.recommend_context("Build a secure API with tests", limit=6)
    paths = [item["path"] for item in result["recommendations"]]

    assert "karpathy/principles.md" in paths
    assert "SKILL-REFERENCE.md" in paths
    assert any("security" in path.lower() for path in paths)
    assert any("test" in path.lower() or "api" in path.lower() for path in paths)


def test_recommend_context_prefers_frontend_hub_for_interface_tasks():
    catalog = build_catalog(ROOT)

    result = catalog.recommend_context("Build a SaaS dashboard UI", limit=8)
    identifiers = [item["identifier"] for item in result["recommendations"]]

    assert "frontend-hub" in identifiers
    assert identifiers.index("frontend-hub") <= 3


def test_recommend_context_prefers_domain_hubs():
    catalog = build_catalog(ROOT)

    cases = [
        ("Write pytest unit tests", "testing-hub"),
        ("Add Playwright e2e regression coverage", "testing-hub"),
        ("Review auth token security", "security-hub"),
        ("Check HIPAA compliance and XSS risk", "security-hub"),
        ("Write documentation from research notes", "docs-research-hub"),
        ("Research PubMed sources for an article", "docs-research-hub"),
        ("Plan workflow orchestration for a feature", "workflow-hub"),
        ("Restore session recap and parallel agent plan", "workflow-hub"),
        ("Build REST API endpoint backed by a database", "backend-hub"),
        ("Implement FastAPI service with Postgres and Redis", "backend-hub"),
    ]

    for task, expected_identifier in cases:
        result = catalog.recommend_context(task, limit=8)
        identifiers = [item["identifier"] for item in result["recommendations"]]
        assert expected_identifier in identifiers
        assert identifiers.index(expected_identifier) <= 3




def test_recommend_context_prefers_frontend_hub_for_react_dashboard_ui():
    catalog = build_catalog(ROOT)

    result = catalog.recommend_context("build React dashboard UI", limit=8)
    identifiers = [item["identifier"] for item in result["recommendations"]]

    assert "frontend-hub" in identifiers
    assert identifiers.index("frontend-hub") <= 3




def test_recommend_context_prefers_backend_hub_for_fastapi_postgres():
    catalog = build_catalog(ROOT)

    result = catalog.recommend_context("build FastAPI endpoint with Postgres", limit=8)
    identifiers = [item["identifier"] for item in result["recommendations"]]

    assert "backend-hub" in identifiers
    assert identifiers.index("backend-hub") <= 3




def test_recommend_context_prefers_security_hub_for_auth_token_security():
    catalog = build_catalog(ROOT)

    result = catalog.recommend_context("review auth token security", limit=8)
    identifiers = [item["identifier"] for item in result["recommendations"]]

    assert "security-hub" in identifiers
    assert identifiers.index("security-hub") <= 3




def test_recommend_context_prefers_docs_research_hub_for_pubmed_sources():
    catalog = build_catalog(ROOT)

    result = catalog.recommend_context("research PubMed sources for an article", limit=8)
    identifiers = [item["identifier"] for item in result["recommendations"]]

    assert "docs-research-hub" in identifiers
    assert identifiers.index("docs-research-hub") <= 3


def test_missing_entry_raises_key_error():
    catalog = build_catalog(ROOT)

    with pytest.raises(KeyError):
        catalog.read_entry("does-not-exist")


def test_read_bounded_text_handles_invalid_utf8():
    import os
    import tempfile
    from pathlib import Path
    from agent_guidance_mcp.project_scan import read_bounded_text

    fd, path_str = tempfile.mkstemp()
    try:
        os.write(fd, b"Hello \xff World")
        os.close(fd)

        content, truncated = read_bounded_text(Path(path_str), 100)
        assert content is not None
        assert "Hello" in content
        assert "World" in content
        assert "\ufffd" in content
        assert truncated is False
    finally:
        try:
            os.remove(path_str)
        except OSError:
            pass