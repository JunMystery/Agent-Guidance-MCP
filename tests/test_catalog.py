from agent_guidance_mcp.catalog import build_catalog


def test_search_uses_content_cache(tmp_path):
    _setup_standards_root(tmp_path)
    (tmp_path / "skills").mkdir()
    (tmp_path / "skills" / "cache-skill").mkdir()
    (tmp_path / "skills" / "cache-skill" / "SKILL.md").write_text(
        "---\nname: cache-skill\ndescription: Cache test\n---\n\n# Cache Skill\nUniqueKeywordXYZ123.",
        encoding="utf-8",
    )
    catalog = build_catalog(str(tmp_path))

    results1 = catalog.search_entries("UniqueKeywordXYZ123")
    assert len(results1) > 0

    results2 = catalog.search_entries("UniqueKeywordXYZ123")
    assert len(results2) > 0
    assert results1[0]["identifier"] == results2[0]["identifier"]


def _setup_standards_root(tmp_path):
    """Create minimal standards root so is_standards_root() passes."""
    (tmp_path / "karpathy").mkdir()
    (tmp_path / "karpathy" / "principles.md").write_text("# Principles", encoding="utf-8")
    (tmp_path / "SKILL-REFERENCE.md").write_text("# Skill Reference", encoding="utf-8")
    (tmp_path / "agent-guidance").mkdir()
    (tmp_path / "agent-guidance" / "INDEX.md").write_text("# Index", encoding="utf-8")


def test_catalog_builds_from_temp_dir(tmp_path):
    _setup_standards_root(tmp_path)
    (tmp_path / "karpathy" / "principles.md").write_text("# Principles\n\nContent.", encoding="utf-8")
    (tmp_path / "skills").mkdir()
    (tmp_path / "skills" / "test-skill").mkdir()
    (tmp_path / "skills" / "test-skill" / "SKILL.md").write_text(
        "---\nname: test-skill\ndescription: A test skill\n---\n\n# Test Skill\nBody.",
        encoding="utf-8",
    )
    (tmp_path / "docs").mkdir()
    (tmp_path / "docs" / "test-doc.md").write_text("# Test Doc\nContent.", encoding="utf-8")
    (tmp_path / "agent-guidance" / "principles").mkdir()
    (tmp_path / "agent-guidance" / "principles" / "test-standard.md").write_text(
        "# Test Standard\nContent.", encoding="utf-8"
    )

    catalog = build_catalog(str(tmp_path))
    manifest = catalog.manifest()

    assert manifest["entry_count"] >= 5
    kinds = manifest["kinds"]
    assert "skill" in kinds
    assert "principle" in kinds
    assert "doc" in kinds
    assert "standard" in kinds

    entry = catalog.get_entry("test-skill")
    assert entry.title == "Test Skill"
    assert entry.kind == "skill"


def test_catalog_skips_unreadable_file(tmp_path, capsys):
    _setup_standards_root(tmp_path)
    (tmp_path / "skills").mkdir()
    (tmp_path / "skills" / "broken-skill").mkdir()
    (tmp_path / "skills" / "broken-skill" / "SKILL.md").write_bytes(b"\x00\x01\x02\x03\xff\xfe")

    catalog = build_catalog(str(tmp_path))

    captured = capsys.readouterr()
    assert "skipping unreadable file" in captured.err
    assert "broken-skill" in captured.err

    with __import__("pytest").raises(KeyError):
        catalog.get_entry("broken-skill")

    entry = catalog.get_entry("karpathy-principles")
    assert entry.title == "Principles"


def test_catalog_get_entry_missing(tmp_path):
    _setup_standards_root(tmp_path)

    catalog = build_catalog(str(tmp_path))

    with __import__("pytest").raises(KeyError, match="nonexistent"):
        catalog.get_entry("nonexistent")


def test_catalog_read_entry(tmp_path):
    _setup_standards_root(tmp_path)
    (tmp_path / "skills").mkdir()
    (tmp_path / "skills" / "reader-skill").mkdir()
    (tmp_path / "skills" / "reader-skill" / "SKILL.md").write_text(
        "---\nname: reader-skill\ndescription: Reads content\n---\n\n# Reader Skill\nExpected body text here.",
        encoding="utf-8",
    )

    catalog = build_catalog(str(tmp_path))
    content = catalog.read_entry("reader-skill")

    assert "Expected body text here" in content
