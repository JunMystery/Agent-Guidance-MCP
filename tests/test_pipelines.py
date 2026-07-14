import time

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


def test_infer_task_keywords_lemma_variations():
    from agent_guidance_mcp.text import infer_task_keywords
    
    # "testing" should trigger "tests"
    kw_testing = infer_task_keywords("run testing suite")
    assert "tests" in kw_testing
    
    # "authentication" should trigger "security"
    kw_auth = infer_task_keywords("perform authentication check")
    assert "security" in kw_auth
    
    # "accessible" should trigger "accessibility"
    kw_access = infer_task_keywords("make dashboard accessible")
    assert "accessibility" in kw_access
    
    # "databases" should trigger "backend"
    kw_db = infer_task_keywords("query databases")
    assert "backend" in kw_db


def test_detect_frameworks_extended(tmp_path):
    from agent_guidance_mcp.pipeline_helpers import _detect_frameworks
    
    # 1. Test Flutter detection
    flutter_dir = tmp_path / "flutter_proj"
    flutter_dir.mkdir()
    (flutter_dir / "pubspec.yaml").write_text("name: my_app\ndependencies:\n  flutter:\n    sdk: flutter", encoding="utf-8")
    tags = _detect_frameworks(str(flutter_dir))
    assert "flutter" in tags
    assert "dart" in tags

    # 2. Test Go/Gin detection
    go_dir = tmp_path / "go_proj"
    go_dir.mkdir()
    (go_dir / "go.mod").write_text("module my_go_app\nrequire github.com/gin-gonic/gin v1.7.0", encoding="utf-8")
    tags = _detect_frameworks(str(go_dir))
    assert "go" in tags
    assert "golang" in tags
    assert "gin" in tags

    # 3. Test PHP/Laravel detection
    php_dir = tmp_path / "php_proj"
    php_dir.mkdir()
    (php_dir / "composer.json").write_text('{"require": {"laravel/framework": "^9.0"}}', encoding="utf-8")
    tags = _detect_frameworks(str(php_dir))
    assert "php" in tags
    assert "laravel" in tags

    # 4. Test JVM/Android/SpringBoot detection
    jvm_dir = tmp_path / "jvm_proj"
    jvm_dir.mkdir()
    (jvm_dir / "build.gradle.kts").write_text('dependencies {\n    implementation("org.springframework.boot:spring-boot-starter-web")\n    implementation("org.jetbrains.kotlin:kotlin-stdlib")\n}', encoding="utf-8")
    tags = _detect_frameworks(str(jvm_dir))
    assert "java" in tags
    assert "kotlin" in tags
    assert "springboot" in tags


def test_guidance_resolve_dependencies(tmp_path):
    (tmp_path / "karpathy").mkdir()
    (tmp_path / "karpathy" / "principles.md").write_text("# Principles", encoding="utf-8")
    (tmp_path / "SKILL-REFERENCE.md").write_text("# Skill Reference", encoding="utf-8")
    (tmp_path / "agent-guidance").mkdir()
    (tmp_path / "agent-guidance" / "INDEX.md").write_text("# Index", encoding="utf-8")
    (tmp_path / "skills").mkdir()
    
    # create skill A depending on skill B
    (tmp_path / "skills" / "skill-a").mkdir()
    (tmp_path / "skills" / "skill-a" / "SKILL.md").write_text(
        "---\nname: skill-a\ndescription: Skill A\ndependencies: [skill-b]\n---\n\n# Skill A\nContent of A.",
        encoding="utf-8",
    )
    # create skill B depending on nothing
    (tmp_path / "skills" / "skill-b").mkdir()
    (tmp_path / "skills" / "skill-b" / "SKILL.md").write_text(
        "---\nname: skill-b\ndescription: Skill B\n---\n\n# Skill B\nContent of B.",
        encoding="utf-8",
    )

    catalog = build_catalog(str(tmp_path))
    result = pipelines.guidance(
        catalog=catalog, operation="get", identifier="skill-a", include_content=True, resolve_dependencies=True
    )
    assert isinstance(result, dict)
    assert "resolved_dependencies" in result
    assert "skill-b" in result["resolved_dependencies"]
    assert "Content of B" in result["resolved_dependencies"]["skill-b"]


def test_task_pipeline_includes_recommendations_content(tmp_path):
    catalog = _make_catalog(tmp_path)
    result = pipelines.task_pipeline(catalog=catalog, task="design the landing page with new colors", include_tree=False)
    assert isinstance(result, dict)
    recs = result["recommendations"]["recommendations"]
    assert len(recs) > 0
    # Top matching entries should contain content (at least 2 should load)
    has_content = [r for r in recs if "content" in r]
    assert len(has_content) >= 2
    assert len(has_content[0]["content"]) > 0


def test_session_continuity_roundtrip(tmp_path):
    checklist = [{"title": "step 1", "status": "done"}, {"title": "step 2", "status": "todo"}]
    saved = pipelines.session_continuity(
        operation="save",
        project_path=str(tmp_path),
        task="build the thing",
        checklist=checklist,
        current_step_index=1,
    )
    assert saved["success"] is True
    assert saved["session"]["task"] == "build the thing"

    loaded = pipelines.session_continuity(operation="load", project_path=str(tmp_path))
    assert loaded["success"] is True
    assert loaded["session_active"] is True
    assert loaded["session"]["task"] == "build the thing"
    assert loaded["session"]["checklist"] == checklist

    cleared = pipelines.session_continuity(operation="clear", project_path=str(tmp_path))
    assert cleared["success"] is True

    reloaded = pipelines.session_continuity(operation="load", project_path=str(tmp_path))
    assert reloaded["session_active"] is False


def test_session_continuity_invalid_operation(tmp_path):
    result = pipelines.session_continuity(operation="explode", project_path=str(tmp_path))
    assert "error" in result
    assert "Unsupported" in str(result["error"])
    assert "supported_operations" in result
    assert "save" in result["supported_operations"]


def test_session_continuity_save_requires_task(tmp_path):
    result = pipelines.session_continuity(operation="save", project_path=str(tmp_path))
    assert result["success"] is False
    assert "task" in str(result["error"])


def test_task_pipeline_timeout_warning(tmp_path, monkeypatch):
    import time as _time

    catalog = _make_catalog(tmp_path)

    def slow_tree(*args, **kwargs):
        time.sleep(1.0)
        return {"tree": []}

    def slow_search(*args, **kwargs):
        time.sleep(1.0)
        return {"matches": []}

    monkeypatch.setattr(pipelines.project_context_helpers, "get_project_tree", slow_tree)
    monkeypatch.setattr(pipelines.project_context_helpers, "search_project_code", slow_search)

    result = pipelines.task_pipeline(
        catalog=catalog,
        task="fix the login bug",
        project_path=str(tmp_path),
        timeout=0.05,
    )
    assert isinstance(result, dict)
    assert "warning" in result
    assert "timeout" in result["warning"].lower()


def test_parallel_run_timeout_isolation():
    from agent_guidance_mcp.parallel import parallel_run

    def slow():
        time.sleep(1.0)
        return "done"

    def fast():
        return "fast"

    results = parallel_run(
        {"slow": slow, "fast": fast},
        timeout=0.05,
    )
    assert isinstance(results["slow"], TimeoutError)
    assert results["fast"] == "fast"
