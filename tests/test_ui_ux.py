from agent_guidance_mcp.paths import find_standards_root
from agent_guidance_mcp.ui_ux import (
    search_ui_ux_guidance,
    generate_ui_ux_design_system,
    clear_bm25_cache,
    _load_csv,
)
from agent_guidance_mcp.ui_ux import _load_csv as ui_ux_load_csv


ROOT = find_standards_root()


def test_search_ui_ux_by_domain():
    result = search_ui_ux_guidance(root=ROOT, query="minimalist design", domain="style", limit=3)
    assert "domain" in result
    assert result["domain"] == "style"
    assert "results" in result
    assert isinstance(result["results"], list)
    assert len(result["results"]) > 0
    assert "Style Category" in result["results"][0]


def test_search_ui_ux_by_stack():
    result = search_ui_ux_guidance(root=ROOT, query="useState performance", stack="react", limit=3)
    assert "stack" in result
    assert result["stack"] == "react"
    assert "results" in result
    assert isinstance(result["results"], list)


def test_search_ui_ux_missing_csv(monkeypatch):
    def _raise(*args, **kwargs):
        raise FileNotFoundError("simulated missing CSV")

    monkeypatch.setattr("agent_guidance_mcp.ui_ux._load_csv", _raise)
    clear_bm25_cache()
    result = search_ui_ux_guidance(root=ROOT, query="test", domain="style")
    assert result["results"] == []


def test_design_system_generation():
    content = generate_ui_ux_design_system(
        root=ROOT, query="SaaS dashboard", project_name="TestApp", output_format="markdown"
    )
    assert isinstance(content, str)
    assert "## Design System: TestApp" in content
    assert "### Pattern" in content
    assert "### Style" in content
    assert "### Colors" in content
    assert "### Typography" in content


def test_design_system_ascii_format():
    content = generate_ui_ux_design_system(
        root=ROOT, query="SaaS dashboard", project_name="TestApp", output_format="ascii"
    )
    assert isinstance(content, str)
    assert "DESIGN SYSTEM:" in content
    assert "## Design System:" not in content
