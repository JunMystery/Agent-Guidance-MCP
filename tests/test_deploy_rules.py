"""Tests for deploy_rules module — auto-deployment of rules and skills."""

import os
from pathlib import Path

from agent_guidance_mcp.deploy_rules import (
    ENFORCER_SKILL_CONTENT,
    MARKER,
    RULE_FILE_NAMES,
    SKILL_TARGETS,
    _atomic_append,
    _has_marker,
    _has_project_markers,
    deploy_project_rules,
)


# ── _has_project_markers ─────────────────────────────────────────────────────

def test_has_project_markers_dot_git(tmp_path):
    (tmp_path / ".git").mkdir()
    assert _has_project_markers(tmp_path) is True


def test_has_project_markers_pyproject(tmp_path):
    (tmp_path / "pyproject.toml").write_text("")
    assert _has_project_markers(tmp_path) is True


def test_has_project_markers_none(tmp_path):
    assert _has_project_markers(tmp_path) is False


# ── _has_marker ─────────────────────────────────────────────────────────────

def test_has_marker_present():
    assert _has_marker(f"some text\n{MARKER}\nmore text") is True


def test_has_marker_absent():
    assert _has_marker("random content without the marker") is False


def test_has_marker_empty():
    assert _has_marker("") is False


# ── _atomic_append ──────────────────────────────────────────────────────────

def test_atomic_append_creates_new_file(tmp_path):
    path = tmp_path / ".cursorrules"
    written = _atomic_append(path, "## Test Block\n\ncontent\n")
    assert written is True
    assert path.exists()
    content = path.read_text(encoding="utf-8")
    assert "## Test Block" in content
    assert "content" in content


def test_atomic_append_appends_to_existing(tmp_path):
    path = tmp_path / "AGENTS.md"
    path.write_text("# My Project Rules\n\nSome user content.\n", encoding="utf-8")
    written = _atomic_append(path, "## New Guidance Block\n\nAdd this.\n")
    assert written is True
    content = path.read_text(encoding="utf-8")
    assert content.startswith("# My Project Rules")
    assert "## New Guidance Block" in content
    assert "Add this." in content


def test_atomic_append_skips_when_marker_present(tmp_path):
    path = tmp_path / ".cursorrules"
    path.write_text(f"# Existing\n\n{MARKER}\n\nMore stuff.\n", encoding="utf-8")
    written = _atomic_append(path, "## Should Not Append\n")
    assert written is False
    # Content MUST be unchanged
    content = path.read_text(encoding="utf-8")
    assert "## Should Not Append" not in content
    assert MARKER in content


def test_atomic_append_marker_in_first_file_already(tmp_path):
    """If marker is already in a file that also has existing AGENT_RULES_BLOCK content, skip."""
    path = tmp_path / ".clinerules"
    path.write_text(f"# User rules\n\n{MARKER}\n\n### Six Mandatory Rules\n\n1. Rule one\n", encoding="utf-8")
    written = _atomic_append(path, "## Extra\n")
    assert written is False
    assert path.read_text(encoding="utf-8").count(MARKER) == 1


# ── deploy_project_rules ────────────────────────────────────────────────────

def test_deploy_project_rules_no_markers_returns_early(tmp_path):
    """No .git / pyproject.toml → should return empty results."""
    result = deploy_project_rules(root=tmp_path)
    assert result["root"] == str(tmp_path)
    assert result["rules"] == {}
    assert result["skills"] == {}
    assert any("No project markers" in n for n in result.get("notes", []))


def test_deploy_project_rules_creates_rules_and_skills(tmp_path):
    (tmp_path / ".git").mkdir()
    result = deploy_project_rules(root=tmp_path)
    assert result["root"] == str(tmp_path)
    assert result["errors"] == []

    # Every rule file should have been created
    for name in RULE_FILE_NAMES:
        status = result["rules"].get(name, "")
        assert status == "created", f"Expected {name} to be created, got {status!r}"
        file_path = tmp_path / name
        assert file_path.exists(), f"Missing {name}"
        content = file_path.read_text(encoding="utf-8")
        assert MARKER in content, f"{name} missing marker"

    # Every skill should have been created
    for rel_path in SKILL_TARGETS:
        status = result["skills"].get(rel_path, "")
        assert status == "created", f"Expected {rel_path} to be created, got {status!r}"
        skill_file = tmp_path / rel_path
        assert skill_file.exists(), f"Missing {rel_path}"
        content = skill_file.read_text(encoding="utf-8")
        assert "name: agent-guidance" in content


def test_deploy_project_rules_skips_existing_content(tmp_path):
    """If rules files already have the marker, they should be skipped."""
    (tmp_path / ".git").mkdir()

    # Pre-populate one rule file with the marker
    (tmp_path / ".cursorrules").write_text(
        f"# My user rules\n\n{MARKER}\n\n### Six Mandatory Rules\n\nAlready here.\n",
        encoding="utf-8",
    )
    # Pre-populate one skill file
    skill_path = tmp_path / ".agents" / "skills" / "agent-guidance" / "SKILL.md"
    skill_path.parent.mkdir(parents=True, exist_ok=True)
    skill_path.write_text("name: agent-guidance\ncustom: true\n", encoding="utf-8")

    result = deploy_project_rules(root=tmp_path)
    assert result["errors"] == []

    # .cursorrules should be skipped (marker already present)
    assert result["rules"][".cursorrules"] == "skipped (already present)"
    # User content in .cursorrules must be untouched
    cursor_content = (tmp_path / ".cursorrules").read_text(encoding="utf-8")
    assert cursor_content.startswith("# My user rules"), "User content was overwritten!"

    # skill should be skipped
    assert result["skills"][".agents/skills/agent-guidance/SKILL.md"] == "skipped (already exists)"
    # User skill content must be untouched
    assert skill_path.read_text(encoding="utf-8") == "name: agent-guidance\ncustom: true\n"


def test_deploy_project_rules_never_overwrites_user_content(tmp_path):
    """Existing user-only content (without marker) should have block appended, never replaced."""
    (tmp_path / ".git").mkdir()
    user_content = "# My custom agent rules\n\nBe concise. Write tests.\n"
    (tmp_path / "AGENTS.md").write_text(user_content, encoding="utf-8")

    result = deploy_project_rules(root=tmp_path)
    assert result["rules"]["AGENTS.md"] == "appended"

    full_content = (tmp_path / "AGENTS.md").read_text(encoding="utf-8")
    assert full_content.startswith(user_content), "User content at top was lost!"
    assert MARKER in full_content, "Marker should be appended"


def test_deploy_project_rules_env_disable(tmp_path):
    """AGENT_DEPLOY_RULES=0 should skip deployment entirely."""
    (tmp_path / ".git").mkdir()
    os.environ["AGENT_DEPLOY_RULES"] = "0"
    try:
        result = deploy_project_rules(root=tmp_path)
        assert result["rules"] == {}
        assert result["skills"] == {}
        assert any("Disabled" in n for n in result.get("notes", []))
    finally:
        os.environ.pop("AGENT_DEPLOY_RULES", None)


def test_deploy_project_rules_env_skip_list(tmp_path):
    """AGENT_DEPLOY_RULES_SKIP should skip specific files."""
    (tmp_path / ".git").mkdir()
    os.environ["AGENT_DEPLOY_RULES_SKIP"] = ".cursorrules, AGENTS.md"
    try:
        result = deploy_project_rules(root=tmp_path)
        assert result["rules"][".cursorrules"] == "skipped (via AGENT_DEPLOY_RULES_SKIP)"
        assert result["rules"]["AGENTS.md"] == "skipped (via AGENT_DEPLOY_RULES_SKIP)"
        # Other rules should still be created
        assert result["rules"][".clinerules"] == "created"
    finally:
        os.environ.pop("AGENT_DEPLOY_RULES_SKIP", None)


def test_deploy_project_rules_with_root_none(tmp_path):
    """When root=None, should auto-detect from cwd."""
    (tmp_path / ".git").mkdir()
    original_cwd = Path.cwd()
    os.chdir(tmp_path)
    try:
        result = deploy_project_rules(root=None)
        assert result["root"] is not None
        assert result["rules"] != {}
    finally:
        os.chdir(original_cwd)
