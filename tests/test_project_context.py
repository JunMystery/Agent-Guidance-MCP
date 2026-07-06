import json
from pathlib import Path

import pytest

from agent_guidance_mcp.project_context import (
    export_project_snapshot,
    get_project_tree,
    read_project_file,
    search_project_code,
)


def test_snapshot_rejects_non_agent_context_path(tmp_path):
    project = make_sample_project(tmp_path)
    with __import__("pytest").raises(ValueError, match=".agent-context/"):
        export_project_snapshot(str(project), output_path="src/main.py")


def test_snapshot_accepts_agent_context_subpath(tmp_path):
    project = make_sample_project(tmp_path)
    (project / ".agent-context").mkdir(exist_ok=True)
    manifest = export_project_snapshot(str(project), output_path=".agent-context/custom.json")
    assert manifest["output_path"] == ".agent-context/custom.json"


def test_tree_missing_directory():
    result = get_project_tree("/nonexistent/path/to/nowhere")
    assert "error" in result
    assert "project_path" in result


def make_sample_project(tmp_path: Path) -> Path:
    project = tmp_path / "sample-project"
    (project / "src").mkdir(parents=True)
    (project / "node_modules").mkdir()
    (project / ".pytest_cache").mkdir()
    (project / ".agent-context").mkdir()

    (project / "README.md").write_text("# Sample\n\nNeedle in docs.\n", encoding="utf-8")
    (project / "src" / "app.py").write_text(
        "def hello():\n"
        "    value = 'needle from source'\n"
        "    return value\n",
        encoding="utf-8",
    )
    (project / "node_modules" / "ignored.js").write_text(
        "const ignored = 'needle';\n", encoding="utf-8"
    )
    (project / ".pytest_cache" / "ignored.txt").write_text("needle\n", encoding="utf-8")
    (project / ".agent-context" / "code-snapshot.json").write_text("{}", encoding="utf-8")
    (project / "image.png").write_bytes(b"\x89PNG\r\n\x1a\n\x00\x00")
    return project


def test_project_tree_skips_ignored_binary_and_snapshot_files(tmp_path):
    project = make_sample_project(tmp_path)

    tree = get_project_tree(str(project), max_depth=4)
    entries = {entry["path"]: entry for entry in tree["tree"]}

    assert "src/app.py" in entries
    assert entries["src/app.py"]["language_hint"] == "python"
    assert "node_modules/ignored.js" not in entries
    assert ".pytest_cache/ignored.txt" not in entries
    assert ".agent-context/code-snapshot.json" not in entries
    assert "image.png" not in entries


def test_read_project_file_bounds_lines_and_rejects_path_escape(tmp_path):
    project = make_sample_project(tmp_path)

    result = read_project_file(str(project), "src/app.py", start_line=1, max_lines=1)

    assert result["path"] == "src/app.py"
    assert result["start_line"] == 1
    assert result["end_line"] == 1
    assert result["truncated"] is True
    assert result["content"] == "def hello():"

    with pytest.raises(ValueError):
        read_project_file(str(project), "../outside.py")


def test_search_project_code_returns_ranked_snippets_without_ignored_files(tmp_path):
    project = make_sample_project(tmp_path)

    result = search_project_code(str(project), "needle", limit=10)
    matches = result["matches"]
    paths = [match["path"] for match in matches]

    assert "src/app.py" in paths
    assert "README.md" in paths
    assert "node_modules/ignored.js" not in paths
    assert ".pytest_cache/ignored.txt" not in paths
    assert any("needle from source" in match["snippet"] for match in matches)


def test_export_project_snapshot_writes_bounded_json(tmp_path):
    project = make_sample_project(tmp_path)

    manifest = export_project_snapshot(
        str(project), max_file_bytes=12, max_total_bytes=1_000
    )

    snapshot_path = project / ".agent-context" / "code-snapshot.json"
    data = json.loads(snapshot_path.read_text(encoding="utf-8"))
    files = {entry["path"]: entry for entry in data["files"]}
    tree_paths = {entry["path"] for entry in data["tree"]}

    assert manifest["output_path"] == ".agent-context/code-snapshot.json"
    assert data["project_root"] == str(project.resolve())
    assert data["limits"] == {"max_file_bytes": 12, "max_total_bytes": 1_000}
    assert "src/app.py" in files
    assert files["src/app.py"]["truncated"] is True
    assert "content" in files["src/app.py"]
    assert ".agent-context/code-snapshot.json" not in tree_paths
