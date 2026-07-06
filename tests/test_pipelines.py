from agent_guidance_mcp import pipelines
from agent_guidance_mcp.catalog import build_catalog
from agent_guidance_mcp.server import WORKFLOW_MODE_MAP
from agent_guidance_mcp.text import parse_frontmatter


def _make_catalog(tmp_path):
    (tmp_path / "karpathy").mkdir()
    (tmp_path / "karpathy" / "principles.md").write_text("# Principles\nCore principles here.", encoding="utf-8")
    (tmp_path / "SKILL-REFERENCE.md").write_text("# Skill Reference", encoding="utf-8")
    (tmp_path / "agent-guidance").mkdir()
    (tmp_path / "agent-guidance" / "INDEX.md").write_text("# Index", encoding="utf-8")
    (tmp_path / "agent-guidance" / "principles").mkdir()
    (tmp_path / "agent-guidance" / "principles" / "test.md").write_text("# Standard\nContent.", encoding="utf-8")
    (tmp_path / "docs").mkdir()
    (tmp_path / "docs" / "api.md").write_text("# API Design\nREST API patterns.", encoding="utf-8")
    (tmp_path / "skills").mkdir()
    (tmp_path / "skills" / "api-design").mkdir()
    (tmp_path / "skills" / "api-design" / "SKILL.md").write_text(
        "---\nname: api-design\ndescription: API design patterns\n---\n\n# API Design\nREST API patterns and best practices.",
        encoding="utf-8",
    )
    return build_catalog(str(tmp_path))


def test_guidance_list(tmp_path):
    catalog = _make_catalog(tmp_path)
    result = pipelines.guidance(catalog=catalog, operation="list")
    assert isinstance(result, dict)
    assert result["operation"] == "list"
    entries = result["entries"]
    assert isinstance(entries, list)
    assert len(entries) > 0
    assert all("identifier" in r and "kind" in r for r in entries)

    skills_only = pipelines.guidance(catalog=catalog, operation="list", kind="principle")
    assert all(r["kind"] == "principle" for r in skills_only["entries"])


def test_guidance_get(tmp_path):
    catalog = _make_catalog(tmp_path)
    result = pipelines.guidance(
        catalog=catalog, operation="get", identifier="karpathy-principles", include_content=True
    )
    assert isinstance(result, dict)
    assert result["identifier"] == "karpathy-principles"
    assert "content" in result
    assert "Core principles here" in str(result["content"]) or "Principles" in str(result["content"])


def test_guidance_get_missing(tmp_path):
    catalog = _make_catalog(tmp_path)
    result = pipelines.guidance(catalog=catalog, operation="get", identifier="nonexistent")
    assert isinstance(result, dict)
    assert "error" in result
    assert "nonexistent" in str(result["error"])


def test_guidance_search(tmp_path):
    catalog = _make_catalog(tmp_path)
    result = pipelines.guidance(catalog=catalog, operation="search", query="principles")
    assert isinstance(result, list)
    assert len(result) > 0
    assert all("score" in r and "snippet" in r for r in result)


def test_guidance_recommend(tmp_path):
    catalog = _make_catalog(tmp_path)
    result = pipelines.guidance(catalog=catalog, operation="recommend", query="build a new API")
    assert isinstance(result, dict)
    assert "task" in result
    assert "keywords" in result
    assert "recommendations" in result
    assert len(result["recommendations"]) > 0


def test_guidance_unsupported(tmp_path):
    catalog = _make_catalog(tmp_path)
    result = pipelines.guidance(catalog=catalog, operation="invalid_op")
    assert isinstance(result, dict)
    assert "error" in result
    assert "Unsupported" in str(result["error"])
    assert "supported_operations" in result


def test_task_pipeline_structure(tmp_path):
    catalog = _make_catalog(tmp_path)
    result = pipelines.task_pipeline(catalog=catalog, task="fix the login bug")
    assert isinstance(result, dict)
    assert result["task"] == "fix the login bug"
    assert "recommendations" in result
    assert "project_tree" in result


def test_task_pipeline_with_ui(tmp_path):
    catalog = _make_catalog(tmp_path)
    result = pipelines.task_pipeline(
        catalog=catalog, task="redesign the landing page with new colors"
    )
    assert "ui_ux" in result


def test_guidance_dependency_cycle(tmp_path):
    (tmp_path / "karpathy").mkdir()
    (tmp_path / "karpathy" / "principles.md").write_text("# Principles", encoding="utf-8")
    (tmp_path / "SKILL-REFERENCE.md").write_text("# Skill Reference", encoding="utf-8")
    (tmp_path / "agent-guidance").mkdir()
    (tmp_path / "agent-guidance" / "INDEX.md").write_text("# Index", encoding="utf-8")
    (tmp_path / "skills").mkdir()
    (tmp_path / "skills" / "cycle-a").mkdir()
    (tmp_path / "skills" / "cycle-a" / "SKILL.md").write_text(
        "---\nname: cycle-a\ndescription: Skill A\ndependencies: [cycle-b]\n---\n\n# Skill A\nContent A.",
        encoding="utf-8",
    )
    (tmp_path / "skills" / "cycle-b").mkdir()
    (tmp_path / "skills" / "cycle-b" / "SKILL.md").write_text(
        "---\nname: cycle-b\ndescription: Skill B\ndependencies: [cycle-a]\n---\n\n# Skill B\nContent B.",
        encoding="utf-8",
    )

    catalog = build_catalog(str(tmp_path))
    result = pipelines.guidance(
        catalog=catalog, operation="get", identifier="cycle-a", include_content=True
    )
    assert isinstance(result, dict)
    assert "dependency_cycles_detected" in result
    cycles = result["dependency_cycles_detected"]
    assert "cycle-a" in cycles or "cycle-b" in cycles


def test_workflow_prompt_invalid_mode():
    assert "nonexistent_mode" not in WORKFLOW_MODE_MAP
    assert "plan" in WORKFLOW_MODE_MAP
    assert "code" in WORKFLOW_MODE_MAP
    assert len(WORKFLOW_MODE_MAP) == 20


def test_task_pipeline_truncates_long_task(tmp_path):
    catalog = _make_catalog(tmp_path)
    long_task = "fix " + "the bug " * 5000
    result = pipelines.task_pipeline(catalog=catalog, task=long_task)
    assert len(result["task"]) <= 10000


def test_parse_frontmatter_bom():
    content = "\ufeff---\nkey: value\n---\n"
    data = parse_frontmatter(content)
    assert data["key"] == "value"


def test_parse_frontmatter_trailing_space():
    content = "--- \nkey: value\n---\n"
    data = parse_frontmatter(content)
    assert data["key"] == "value"


def test_parse_frontmatter_quoted_list():
    content = '---\nitems: ["a, b", "c"]\n---\n'
    data = parse_frontmatter(content)
    assert data["items"] == ["a, b", "c"]


def test_task_pipeline_exception_safety(tmp_path, monkeypatch):
    catalog = _make_catalog(tmp_path)
    
    def mock_get_project_tree(*args, **kwargs):
        raise RuntimeError("Simulated project tree error")
        
    monkeypatch.setattr(pipelines.project_context_helpers, "get_project_tree", mock_get_project_tree)
    
    result = pipelines.task_pipeline(catalog=catalog, task="fix the login bug", project_path=str(tmp_path))
    assert isinstance(result, dict)
    assert "project_tree" in result
    assert "error" in result["project_tree"]
    assert "Simulated project tree error" in result["project_tree"]["error"]
