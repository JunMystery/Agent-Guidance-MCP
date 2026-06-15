from pathlib import Path

from agent_guidance_mcp.catalog import build_catalog
from agent_guidance_mcp import server
from agent_guidance_mcp.server import register_handlers


ROOT = Path(__file__).resolve().parents[1]
FORBIDDEN_BRANDING = ("a" + "wf", "anti" + "gravity")


class FakeMCP:
    def __init__(self):
        self.resources = {}
        self.tools = {}
        self.prompts = {}

    def resource(self, uri, mime_type=None):
        def decorator(func):
            self.resources[uri] = {"func": func, "mime_type": mime_type}
            return func

        return decorator

    def tool(self):
        def decorator(func):
            self.tools[func.__name__] = func
            return func

        return decorator

    def prompt(self):
        def decorator(func):
            self.prompts[func.__name__] = func
            return func

        return decorator


class FakeFastMCP(FakeMCP):
    def __init__(self, name, **kwargs):
        super().__init__()
        self.name = name
        self.kwargs = kwargs


def test_manifest_resource_payload_is_json_text():
    catalog = build_catalog(ROOT)

    payload = catalog.manifest_json()

    assert '"name": "AI Agent Coding Standards"' in payload
    assert '"entries": [' in payload


def test_prompt_recommendation_has_loadable_paths():
    catalog = build_catalog(ROOT)

    recommendation = catalog.recommend_context("Review generated code for security", limit=5)

    for item in recommendation["recommendations"]:
        assert (ROOT / item["path"]).is_file()


def test_register_handlers_exposes_expected_mcp_contract():
    catalog = build_catalog(ROOT)
    mcp = FakeMCP()

    register_handlers(mcp, catalog)

    assert set(mcp.resources) == {
        "standards://manifest",
        "standards://document/{identifier}",
        "standards://skill/{name}",
    }
    assert set(mcp.tools) == {
        "task_pipeline",
        "guidance",
        "project_context",
        "ui_ux",
    }
    assert set(mcp.prompts) == {"workflow_prompt"}

    document = mcp.resources["standards://document/{identifier}"]["func"]("karpathy-principles")
    skill = mcp.resources["standards://skill/{name}"]["func"]("security-core")
    recommendations = mcp.tools["guidance"](
        operation="recommend", query="Build a secure API with tests", limit=6
    )
    ui_guidance = mcp.tools["ui_ux"](
        operation="search", query="saas dashboard", domain="product", limit=1
    )
    design_system = mcp.tools["ui_ux"](
        operation="design_system", query="saas dashboard", project_name="Acme"
    )
    slide_guidance = mcp.tools["ui_ux"](operation="slides", query="investor pitch", limit=1)
    project_tree = mcp.tools["project_context"](
        operation="tree", project_path=str(ROOT), max_depth=1
    )
    pipeline = mcp.tools["task_pipeline"](
        task="Build a SaaS dashboard UI", project_path=str(ROOT), code_query="FastMCP", limit=6
    )
    prompt = mcp.prompts["workflow_prompt"](mode="code", subject="Build a secure API with tests")

    assert "# Karpathy Coding Principles" in document
    assert "# Security Core" in skill
    assert any("security" in item["path"].lower() for item in recommendations["recommendations"])
    assert ui_guidance["count"] == 1
    assert "SaaS" in str(ui_guidance["results"])
    assert "## Design System: Acme" in design_system["content"]
    assert slide_guidance["count"] == 1
    assert "pitch" in str(slide_guidance["results"]).lower()
    assert any(entry["path"] == "README.md" for entry in project_tree["tree"])
    assert "ui_ux" in pipeline
    assert "code_search" in pipeline
    assert "Subject: Build a secure API with tests" in prompt


def test_mcp_prompt_docs_and_catalog_metadata_do_not_expose_legacy_branding():
    catalog = build_catalog(ROOT)
    mcp = FakeMCP()

    register_handlers(mcp, catalog)

    prompt_docs = "\n".join(func.__doc__ or "" for func in mcp.prompts.values()).lower()
    catalog_metadata = "\n".join(
        " ".join(
            [
                entry["identifier"],
                entry["title"],
                entry["path"],
                entry["kind"],
                entry["category"],
                entry["description"],
            ]
        )
        for entry in catalog.list_entries()
    ).lower()

    for forbidden in FORBIDDEN_BRANDING:
        assert forbidden not in prompt_docs
        assert forbidden not in catalog_metadata


def test_create_server_initialization(monkeypatch):
    monkeypatch.setattr(server, "FastMCP", FakeFastMCP)

    mcp = server.create_server(ROOT)

    assert mcp.name == "Agent Guidance MCP"
    assert mcp.kwargs["json_response"] is True


def test_workflow_prompt_can_be_called_without_arguments():
    catalog = build_catalog(ROOT)
    mcp = FakeMCP()
    register_handlers(mcp, catalog)

    assert mcp.prompts["workflow_prompt"]() is not None
    assert "# WORKFLOW: /plan" in mcp.prompts["workflow_prompt"](mode="plan")
    assert "# Deprecated: use `workflow-modes`" not in mcp.prompts["workflow_prompt"](
        mode="plan"
    )
    for mode in ["next", "help", "readme", "customize", "brainstorm", "save_brain"]:
        assert "# Deprecated:" not in mcp.prompts["workflow_prompt"](mode=mode)
    assert "Unsupported workflow mode" in mcp.prompts["workflow_prompt"](mode="unknown")


def test_grouped_tool_operations_return_useful_payloads(tmp_path):
    catalog = build_catalog(ROOT)
    mcp = FakeMCP()
    register_handlers(mcp, catalog)
    snapshot_project = tmp_path / "project"
    snapshot_project.mkdir()
    (snapshot_project / "app.py").write_text("print('hello')\n", encoding="utf-8")

    listed = mcp.tools["guidance"](operation="list", kind="skill", limit=3)
    entry = mcp.tools["guidance"](
        operation="get", identifier="frontend-hub", include_content=True
    )
    workflow_modes = mcp.tools["guidance"](
        operation="get", identifier="workflow-modes", include_content=True
    )
    framework_testing = mcp.tools["guidance"](
        operation="get", identifier="framework-testing", include_content=True
    )
    searched = mcp.tools["guidance"](operation="search", query="security auth", limit=2)
    framework_search = mcp.tools["guidance"](
        operation="search", query="Python testing pytest fixtures", kind="skill", limit=5
    )
    tree = mcp.tools["project_context"](operation="tree", project_path=str(ROOT), max_depth=1)
    read = mcp.tools["project_context"](
        operation="read", project_path=str(ROOT), relative_path="README.md", max_lines=5
    )
    code_search = mcp.tools["project_context"](
        operation="search", project_path=str(ROOT), query="FastMCP", limit=2
    )
    snapshot = mcp.tools["project_context"](
        operation="snapshot",
        project_path=str(snapshot_project),
        output_path=".agent-context/test-snapshot.json",
        max_total_bytes=1000,
    )
    invalid = mcp.tools["guidance"](operation="nope")

    assert listed
    assert "# Frontend Hub" in entry["content"]
    assert "# Workflow Modes" in workflow_modes["content"]
    assert "# Framework Testing" in framework_testing["content"]
    assert searched
    assert any(
        result["identifier"] == "framework-testing"
        for result in framework_search
    )
    assert tree["tree"]
    assert "Agent Guidance MCP" in read["content"]
    assert code_search["matches"]
    assert snapshot["file_count"] >= 1
    assert invalid["supported_operations"] == ["list", "get", "search", "recommend"]
