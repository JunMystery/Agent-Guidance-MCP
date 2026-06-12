"""Static catalog configuration."""

TEXT_SUFFIXES = {".md", ".mdc", ".txt", ".yaml", ".yml", ".json"}
SKIP_PARTS = {".git", "__pycache__", ".pytest_cache", ".venv", "venv", "node_modules"}
DEFAULT_INCLUDE_DIRS = ("karpathy", "agent-guidance", "skills", "docs")

TASK_ANCHORS = {
    "security": (
        "agent-guidance/risk-management/security-constraints.md",
        "skills/security-review/SKILL.md",
    ),
    "api": (
        "skills/api-design/SKILL.md",
        "agent-guidance/prompts/sample-use-cases/create-api-with-rate-limiting.md",
    ),
    "tests": (
        "agent-guidance/engineering-practices/TESTING_STANDARDS.md",
        "skills/tdd-workflow/SKILL.md",
    ),
    "docs": (
        "agent-guidance/engineering-practices/DOCUMENTATION_STANDARDS.md",
        "skills/documentation-lookup/SKILL.md",
    ),
    "accessibility": (
        "agent-guidance/compliance/A11Y_CHECKLIST.md",
        "skills/accessibility/SKILL.md",
    ),
    "performance": (
        "agent-guidance/engineering-practices/NON_FUNCTIONAL_REQUIREMENTS.md",
        "skills/production-audit/SKILL.md",
    ),
    "release": (
        "agent-guidance/engineering-practices/RELEASE_PROCESS.md",
        "skills/git-workflow/SKILL.md",
    ),
    "skills": (
        "SKILL-REFERENCE.md",
        "skills/skill-scout/SKILL.md",
    ),
    "review": (
        "agent-guidance/quality-control/code-review-checklist.md",
        "agent-guidance/quality-control/audit-ai-code-full.md",
    ),
}
