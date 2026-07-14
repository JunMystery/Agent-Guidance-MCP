"""Tests for Context7 library identifier normalization in docs.py."""

from agent_guidance_mcp.docs import CONTEXT7_ID_PATTERN, normalize_identifier


def test_context7_id_pattern():
    assert CONTEXT7_ID_PATTERN.match("/expressjs/express")
    assert CONTEXT7_ID_PATTERN.match("/anthropics/skills")
    assert not CONTEXT7_ID_PATTERN.match("express")
    assert not CONTEXT7_ID_PATTERN.match("expressjs/express")


def test_normalize_passthrough_valid_id():
    resolved, error = normalize_identifier("/expressjs/express", "sign")
    assert resolved == "/expressjs/express"
    assert error is None


def test_normalize_unresolvable_name_returns_hint(monkeypatch):
    import agent_guidance_mcp.docs as docs

    monkeypatch.setattr(docs, "_resolve_library_id", lambda name, query, key: (None, "no match"))

    resolved, error = normalize_identifier("express", "sign")
    assert resolved == "express"
    assert error is not None
    assert "/org/project" in error
    assert "guidance(operation='search'" in error
