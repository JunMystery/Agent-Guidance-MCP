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
    assert "codebase-onboarding" in identifiers
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

    assert "# Deprecated: use `security-core`" in catalog.read_entry("security-review")
    assert "# UI/UX Pro Max" in catalog.read_entry("ui-ux-pro-max")
    assert "# Deprecated: use `framework-testing`" in catalog.read_entry("react-testing")
    assert "# Deprecated: use `backend-frameworks`" in catalog.read_entry("fastapi-patterns")


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


def test_skill_merge_policy_documents_phase_zero_guardrails():
    policy_path = ROOT / "docs" / "skill-merge-policy.md"
    phase_zero_path = ROOT / "mergin-plans" / "phase-0-policy-and-inventory.md"

    policy = policy_path.read_text(encoding="utf-8")
    phase_zero = phase_zero_path.read_text(encoding="utf-8")

    assert policy_path.is_file()
    assert "**Canonical skill**" in policy
    assert "**Shim skill**" in policy
    assert "**Absorbed skill**" in policy
    assert "**Merge manifest**" in policy
    assert "**Deprecation criteria**" in policy
    assert "# Deprecated: use `<canonical-skill>`" in policy
    assert (
        "This skill identifier is kept for compatibility. "
        "Load `<canonical-skill>` for the maintained workflow."
    ) in policy
    assert "../docs/skill-merge-policy.md" in phase_zero


def test_phase_one_workflow_merge_preserves_compatibility_shims_and_references():
    catalog = build_catalog(ROOT)
    identifiers = {entry["identifier"] for entry in catalog.list_entries(kind="skill")}

    assert {
        "workflow-modes",
        "orchestration-pipeline",
        "agent-workflow-ops",
        "session-context-ops",
    }.issubset(identifiers)

    shim_expectations = {
        "workflow-plan": "workflow-modes",
        "orch-pipeline": "orchestration-pipeline",
        "agentic-engineering": "agent-workflow-ops",
        "ck": "session-context-ops",
    }
    for old_identifier, canonical in shim_expectations.items():
        shim = catalog.read_entry(old_identifier)
        assert f"# Deprecated: use `{canonical}`" in shim
        assert (
            f"This skill identifier is kept for compatibility. "
            f"Load `{canonical}` for the maintained workflow."
        ) in shim

    reference_expectations = {
        "skills/workflow-modes/references/workflow-plan.md": "# WORKFLOW: /plan",
        "skills/orchestration-pipeline/references/orch-pipeline.md": "# Orchestrator Pipeline",
        "skills/agent-workflow-ops/references/agentic-engineering.md": "# Agentic Engineering",
        "skills/session-context-ops/references/ck.md": "# ck",
    }
    for path, expected_text in reference_expectations.items():
        assert expected_text in (ROOT / path).read_text(encoding="utf-8")

    manifest = (ROOT / "mergin-plans" / "phase-1-merge-manifest.md").read_text(
        encoding="utf-8"
    )
    assert "`workflow-plan` -> `skills/workflow-modes/references/workflow-plan.md`" in manifest


def test_phase_one_merge_manifest_entries_are_backed_by_files_and_shims():
    import re

    manifest = (ROOT / "mergin-plans" / "phase-1-merge-manifest.md").read_text(
        encoding="utf-8"
    )

    entries = re.findall(
        r"- `([^`]+)` -> `([^`]+)`; shim: `([^`]+)`",
        manifest,
    )

    assert entries
    for old_identifier, reference_path, shim_path in entries:
        reference = ROOT / reference_path
        shim = ROOT / shim_path

        assert reference.is_file(), reference_path
        assert shim.is_file(), shim_path
        assert "# Deprecated: use `" in shim.read_text(encoding="utf-8")
        reference_content = reference.read_text(encoding="utf-8")
        assert reference_content.strip()
        assert "# Deprecated: use `" not in reference_content


def test_phase_two_testing_merge_preserves_compatibility_shims_and_references():
    catalog = build_catalog(ROOT)
    identifiers = {entry["identifier"] for entry in catalog.list_entries(kind="skill")}

    assert {"testing-core", "framework-testing"}.issubset(identifiers)

    shim_expectations = {
        "tdd-workflow": "testing-core",
        "verification-loop": "testing-core",
        "react-testing": "framework-testing",
        "python-testing": "framework-testing",
        "django-tdd": "framework-testing",
        "springboot-verification": "framework-testing",
        "windows-desktop-e2e": "framework-testing",
    }
    for old_identifier, canonical in shim_expectations.items():
        shim = catalog.read_entry(old_identifier)
        assert f"# Deprecated: use `{canonical}`" in shim
        assert (
            f"This skill identifier is kept for compatibility. "
            f"Load `{canonical}` for the maintained workflow."
        ) in shim

    reference_expectations = {
        "skills/testing-core/references/tdd-workflow.md": "# Test-Driven Development Workflow",
        "skills/testing-core/references/verification-loop.md": "# Verification Loop",
        "skills/framework-testing/references/react-testing.md": "# React Testing",
        "skills/framework-testing/references/python-testing.md": "# Python Testing",
        "skills/framework-testing/references/django-tdd.md": "# Django Testing",
        "skills/framework-testing/references/windows-desktop-e2e.md": "# Windows Desktop E2E Testing",
    }
    for path, expected_text in reference_expectations.items():
        assert expected_text in (ROOT / path).read_text(encoding="utf-8")

    manifest = (ROOT / "mergin-plans" / "phase-2-merge-manifest.md").read_text(
        encoding="utf-8"
    )
    assert "`react-testing` -> `skills/framework-testing/references/react-testing.md`" in manifest


def test_phase_two_merge_manifest_entries_are_backed_by_files_and_shims():
    import re

    manifest = (ROOT / "mergin-plans" / "phase-2-merge-manifest.md").read_text(
        encoding="utf-8"
    )

    entries = re.findall(
        r"- `([^`]+)` -> `([^`]+)`; shim: `([^`]+)`",
        manifest,
    )

    assert entries
    for _old_identifier, reference_path, shim_path in entries:
        reference = ROOT / reference_path
        shim = ROOT / shim_path

        assert reference.is_file(), reference_path
        assert shim.is_file(), shim_path
        assert "# Deprecated: use `" in shim.read_text(encoding="utf-8")
        reference_content = reference.read_text(encoding="utf-8")
        assert reference_content.strip()
        assert "# Deprecated: use `" not in reference_content


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


def test_phase_three_frontend_merge_preserves_compatibility_shims_and_references():
    catalog = build_catalog(ROOT)
    identifiers = {entry["identifier"] for entry in catalog.list_entries(kind="skill")}

    assert {"frontend-core", "frontend-frameworks", "motion-design", "presentation-ui"}.issubset(identifiers)

    shim_expectations = {
        "frontend-patterns": "frontend-core",
        "frontend-design-direction": "frontend-core",
        "make-interfaces-feel-better": "frontend-core",
        "inherit-legacy-style": "frontend-core",
        "dashboard-builder": "frontend-core",
        "click-path-audit": "frontend-core",
        "react-patterns": "frontend-frameworks",
        "react-performance": "frontend-frameworks",
        "nextjs-turbopack": "frontend-frameworks",
        "vite-patterns": "frontend-frameworks",
        "nuxt4-patterns": "frontend-frameworks",
        "angular-developer": "frontend-frameworks",
        "ui-to-vue": "frontend-frameworks",
        "swiftui-patterns": "frontend-frameworks",
        "dart-flutter-patterns": "frontend-frameworks",
        "flutter-dart-code-review": "frontend-frameworks",
        "motion-foundations": "motion-design",
        "motion-patterns": "motion-design",
        "motion-advanced": "motion-design",
        "motion-ui": "motion-design",
        "frontend-slides": "presentation-ui",
        "remotion-video-creation": "media-doc-processing",
        "ui-demo": "presentation-ui",
    }
    for old_identifier, canonical in shim_expectations.items():
        shim = catalog.read_entry(old_identifier)
        assert f"# Deprecated: use `{canonical}`" in shim
        assert (
            f"This skill identifier is kept for compatibility. "
            f"Load `{canonical}` for the maintained workflow."
        ) in shim

    reference_expectations = {
        "skills/frontend-core/references/frontend-patterns.md": "# Frontend Development Patterns",
        "skills/frontend-frameworks/references/react-patterns.md": "# React Patterns",
        "skills/motion-design/references/motion-foundations.md": "# Motion Foundations",
        "skills/presentation-ui/references/frontend-slides.md": "# Frontend Slides",
    }
    for path, expected_text in reference_expectations.items():
        assert expected_text in (ROOT / path).read_text(encoding="utf-8")

    manifest = (ROOT / "mergin-plans" / "phase-3-merge-manifest.md").read_text(
        encoding="utf-8"
    )
    assert "`frontend-patterns` -> `skills/frontend-core/references/frontend-patterns.md`" in manifest


def test_phase_three_merge_manifest_entries_are_backed_by_files_and_shims():
    import re

    manifest = (ROOT / "mergin-plans" / "phase-3-merge-manifest.md").read_text(
        encoding="utf-8"
    )

    entries = re.findall(
        r"- `([^`]+)` -> `([^`]+)`; shim: `([^`]+)`",
        manifest,
    )

    assert entries
    for _old_identifier, reference_path, shim_path in entries:
        reference = ROOT / reference_path
        shim = ROOT / shim_path

        assert reference.is_file(), reference_path
        assert shim.is_file(), shim_path
        assert "# Deprecated: use `" in shim.read_text(encoding="utf-8")
        reference_content = reference.read_text(encoding="utf-8")
        assert reference_content.strip()
        assert "# Deprecated: use `" not in reference_content


def test_recommend_context_prefers_frontend_hub_for_react_dashboard_ui():
    catalog = build_catalog(ROOT)

    result = catalog.recommend_context("build React dashboard UI", limit=8)
    identifiers = [item["identifier"] for item in result["recommendations"]]

    assert "frontend-hub" in identifiers
    assert identifiers.index("frontend-hub") <= 3


def test_phase_four_backend_merge_preserves_compatibility_shims_and_references():
    catalog = build_catalog(ROOT)
    identifiers = {entry["identifier"] for entry in catalog.list_entries(kind="skill")}

    assert {"backend-core", "backend-frameworks", "data-platforms", "api-integrations"}.issubset(identifiers)

    shim_expectations = {
        "backend-patterns": "backend-core",
        "api-design": "backend-core",
        "error-handling": "backend-core",
        "hexagonal-architecture": "backend-core",
        "framework-onboarding": "backend-core",
        "deployment-patterns": "backend-core",
        "flox-environments": "backend-core",
        "fastapi-patterns": "backend-frameworks",
        "django-patterns": "backend-frameworks",
        "nestjs-patterns": "backend-frameworks",
        "laravel-patterns": "backend-frameworks",
        "springboot-patterns": "backend-frameworks",
        "quarkus-patterns": "backend-frameworks",
        "golang-patterns": "backend-frameworks",
        "rust-patterns": "backend-frameworks",
        "python-patterns": "backend-frameworks",
        "dotnet-patterns": "backend-frameworks",
        "kotlin-patterns": "backend-frameworks",
        "kotlin-ktor-patterns": "backend-frameworks",
        "perl-patterns": "backend-frameworks",
        "cpp-coding-standards": "backend-frameworks",
        "java-coding-standards": "backend-frameworks",
        "tinystruct-patterns": "backend-frameworks",
        "database-migrations": "data-platforms",
        "postgres-patterns": "data-platforms",
        "mysql-patterns": "data-platforms",
        "redis-patterns": "data-platforms",
        "prisma-patterns": "data-platforms",
        "clickhouse-io": "data-platforms",
        "data-throughput-accelerator": "data-platforms",
        "latency-critical-systems": "data-platforms",
        "content-hash-cache-pattern": "data-platforms",
        "api-connector-builder": "api-integrations",
        "mcp-server-patterns": "api-integrations",
        "x-api": "api-integrations",
        "nodejs-keccak256": "api-integrations",
        "agent-payment-x402": "api-integrations",
    }
    for old_identifier, canonical in shim_expectations.items():
        shim = catalog.read_entry(old_identifier)
        assert f"# Deprecated: use `{canonical}`" in shim
        assert (
            f"This skill identifier is kept for compatibility. "
            f"Load `{canonical}` for the maintained workflow."
        ) in shim

    reference_expectations = {
        "skills/backend-core/references/backend-patterns.md": "# Backend Development Patterns",
        "skills/backend-frameworks/references/fastapi-patterns.md": "# FastAPI Patterns",
        "skills/data-platforms/references/database-migrations.md": "# Database Migration Patterns",
        "skills/api-integrations/references/api-connector-builder.md": "# API Connector Builder",
    }
    for path, expected_text in reference_expectations.items():
        assert expected_text in (ROOT / path).read_text(encoding="utf-8")

    manifest = (ROOT / "mergin-plans" / "phase-4-merge-manifest.md").read_text(
        encoding="utf-8"
    )
    assert "`backend-patterns` -> `skills/backend-core/references/backend-patterns.md`" in manifest


def test_phase_four_merge_manifest_entries_are_backed_by_files_and_shims():
    import re

    manifest = (ROOT / "mergin-plans" / "phase-4-merge-manifest.md").read_text(
        encoding="utf-8"
    )

    entries = re.findall(
        r"- `([^`]+)` -> `([^`]+)`; shim: `([^`]+)`",
        manifest,
    )

    assert entries
    for _old_identifier, reference_path, shim_path in entries:
        reference = ROOT / reference_path
        shim = ROOT / shim_path

        assert reference.is_file(), reference_path
        assert shim.is_file(), shim_path
        assert "# Deprecated: use `" in shim.read_text(encoding="utf-8")
        reference_content = reference.read_text(encoding="utf-8")
        assert reference_content.strip()
        assert "# Deprecated: use `" not in reference_content


def test_recommend_context_prefers_backend_hub_for_fastapi_postgres():
    catalog = build_catalog(ROOT)

    result = catalog.recommend_context("build FastAPI endpoint with Postgres", limit=8)
    identifiers = [item["identifier"] for item in result["recommendations"]]

    assert "backend-hub" in identifiers
    assert identifiers.index("backend-hub") <= 3


def test_phase_five_security_merge_preserves_compatibility_shims_and_references():
    catalog = build_catalog(ROOT)
    identifiers = {entry["identifier"] for entry in catalog.list_entries(kind="skill")}

    assert {"security-core", "framework-security", "regulated-security"}.issubset(identifiers)

    shim_expectations = {
        "security-review": "security-core",
        "security-scan": "security-core",
        "security-bounty-hunter": "security-core",
        "safety-guard": "security-core",
        "gateguard": "security-core",
        "django-security": "framework-security",
        "laravel-security": "framework-security",
        "springboot-security": "framework-security",
        "quarkus-security": "framework-security",
        "perl-security": "framework-security",
        "hipaa-compliance": "regulated-security",
        "healthcare-phi-compliance": "regulated-security",
        "prediction-market-risk-review": "regulated-security",
        "defi-amm-security": "regulated-security",
        "llm-trading-agent-security": "regulated-security",
        "evm-token-decimals": "regulated-security",
    }
    for old_identifier, canonical in shim_expectations.items():
        shim = catalog.read_entry(old_identifier)
        assert f"# Deprecated: use `{canonical}`" in shim
        assert (
            f"This skill identifier is kept for compatibility. "
            f"Load `{canonical}` for the maintained workflow."
        ) in shim

    reference_expectations = {
        "skills/security-core/references/security-review.md": "# Security Review",
        "skills/framework-security/references/django-security.md": "# Django Security",
        "skills/regulated-security/references/hipaa-compliance.md": "# HIPAA Compliance",
    }
    for path, expected_text in reference_expectations.items():
        assert expected_text in (ROOT / path).read_text(encoding="utf-8")

    manifest = (ROOT / "mergin-plans" / "phase-5-merge-manifest.md").read_text(
        encoding="utf-8"
    )
    assert "`security-review` -> `skills/security-core/references/security-review.md`" in manifest


def test_phase_five_merge_manifest_entries_are_backed_by_files_and_shims():
    import re

    manifest = (ROOT / "mergin-plans" / "phase-5-merge-manifest.md").read_text(
        encoding="utf-8"
    )

    entries = re.findall(
        r"- `([^`]+)` -> `([^`]+)`; shim: `([^`]+)`",
        manifest,
    )

    assert entries
    for _old_identifier, reference_path, shim_path in entries:
        reference = ROOT / reference_path
        shim = ROOT / shim_path

        assert reference.is_file(), reference_path
        assert shim.is_file(), shim_path
        assert "# Deprecated: use `" in shim.read_text(encoding="utf-8")
        reference_content = reference.read_text(encoding="utf-8")
        assert reference_content.strip()
        assert "# Deprecated: use `" not in reference_content


def test_recommend_context_prefers_security_hub_for_auth_token_security():
    catalog = build_catalog(ROOT)

    result = catalog.recommend_context("review auth token security", limit=8)
    identifiers = [item["identifier"] for item in result["recommendations"]]

    assert "security-hub" in identifiers
    assert identifiers.index("security-hub") <= 3


def test_phase_six_docs_research_merge_preserves_compatibility_shims_and_references():
    catalog = build_catalog(ROOT)
    identifiers = {entry["identifier"] for entry in catalog.list_entries(kind="skill")}

    assert {"research-core", "scientific-research", "content-core", "media-doc-processing"}.issubset(identifiers)

    shim_expectations = {
        "research-ops": "research-core",
        "deep-research": "research-core",
        "documentation-lookup": "research-core",
        "search-first": "research-core",
        "exa-search": "research-core",
        "repo-scan": "research-core",
        "code-tour": "research-core",
        "scientific-db-pubmed-database": "scientific-research",
        "scientific-db-uspto-database": "scientific-research",
        "scientific-pkg-gget": "scientific-research",
        "scientific-thinking-literature-review": "scientific-research",
        "scientific-thinking-scholar-evaluation": "scientific-research",
        "article-writing": "content-core",
        "content-engine": "content-core",
        "brand-voice": "content-core",
        "seo": "content-core",
        "marketing-campaign": "content-core",
        "crosspost": "content-core",
        "social-publisher": "content-core",
        "social-graph-ranker": "content-core",
        "fal-ai-media": "media-doc-processing",
        "video-editing": "media-doc-processing",
        "videodb": "media-doc-processing",
        "manim-video": "media-doc-processing",
        "remotion-video-creation": "media-doc-processing",
        "nutrient-document-processing": "media-doc-processing",
        "visa-doc-translate": "media-doc-processing",
    }
    for old_identifier, canonical in shim_expectations.items():
        shim = catalog.read_entry(old_identifier)
        assert f"# Deprecated: use `{canonical}`" in shim
        assert (
            f"This skill identifier is kept for compatibility. "
            f"Load `{canonical}` for the maintained workflow."
        ) in shim

    reference_expectations = {
        "skills/research-core/references/research-ops.md": "# Research Ops",
        "skills/scientific-research/references/scientific-db-pubmed-database.md": "# PubMed Database",
        "skills/content-core/references/article-writing.md": "# Article Writing",
        "skills/media-doc-processing/references/fal-ai-media.md": "# fal.ai Media Generation",
    }
    for path, expected_text in reference_expectations.items():
        assert expected_text in (ROOT / path).read_text(encoding="utf-8")

    manifest = (ROOT / "mergin-plans" / "phase-6-merge-manifest.md").read_text(
        encoding="utf-8"
    )
    assert "`research-ops` -> `skills/research-core/references/research-ops.md`" in manifest


def test_phase_six_merge_manifest_entries_are_backed_by_files_and_shims():
    import re

    manifest = (ROOT / "mergin-plans" / "phase-6-merge-manifest.md").read_text(
        encoding="utf-8"
    )

    entries = re.findall(
        r"- `([^`]+)` -> `([^`]+)`; shim: `([^`]+)`",
        manifest,
    )

    assert entries
    for _old_identifier, reference_path, shim_path in entries:
        reference = ROOT / reference_path
        shim = ROOT / shim_path

        assert reference.is_file(), reference_path
        assert shim.is_file(), shim_path
        assert "# Deprecated: use `" in shim.read_text(encoding="utf-8")
        reference_content = reference.read_text(encoding="utf-8")
        assert reference_content.strip()
        assert "# Deprecated: use `" not in reference_content


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