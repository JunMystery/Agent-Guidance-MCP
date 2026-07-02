"""Static catalog configuration."""

TEXT_SUFFIXES = {".md", ".mdc", ".txt", ".yaml", ".yml", ".json"}
SKIP_PARTS = {".git", "__pycache__", ".pytest_cache", ".venv", "venv", "node_modules"}
DEFAULT_INCLUDE_DIRS = ("karpathy", "agent-guidance", "skills", "docs", "references", "agents")

# PROJECT_IGNORED_PARTS is the comprehensive skip-list for arbitrary project
# scanning (used by project_scan.py). It includes more entries than SKIP_PARTS
# because arbitrary projects may contain additional tooling/cache directories.
# SKIP_PARTS is for catalog content scanning (used by paths.py) within known
# directory structures and needs fewer exclusions.
PROJECT_IGNORED_PARTS = frozenset({
    ".git",
    ".hg",
    ".svn",
    ".venv",
    "venv",
    "node_modules",
    "__pycache__",
    ".pytest_cache",
    ".mypy_cache",
    ".ruff_cache",
    ".cache",
    ".tox",
})

TASK_ANCHORS = {
    "security": (
        "skills/security-hub/SKILL.md",
        "agent-guidance/risk-management/security-constraints.md",
    ),
    "api": (
        "skills/backend-hub/SKILL.md",
        "agent-guidance/prompts/sample-use-cases/create-api-with-rate-limiting.md",
    ),
    "tests": (
        "skills/testing-hub/SKILL.md",
        "agent-guidance/engineering-practices/TESTING_STANDARDS.md",
    ),
    "docs": (
        "skills/docs-research-hub/SKILL.md",
        "agent-guidance/engineering-practices/DOCUMENTATION_STANDARDS.md",
    ),
    "accessibility": (
        "skills/frontend-hub/SKILL.md",
        "agent-guidance/compliance/A11Y_CHECKLIST.md",
    ),
    "performance": (
        "skills/backend-hub/SKILL.md",
        "agent-guidance/engineering-practices/NON_FUNCTIONAL_REQUIREMENTS.md",
    ),
    "release": (
        "skills/workflow-hub/SKILL.md",
        "agent-guidance/engineering-practices/RELEASE_PROCESS.md",
    ),
    "skills": (
        "skills/workflow-hub/SKILL.md",
        "SKILL-REFERENCE.md",
    ),
    "review": (
        "skills/workflow-hub/SKILL.md",
        "agent-guidance/quality-control/code-review-checklist.md",
    ),
    "ui": (
        "skills/frontend-hub/SKILL.md",
        "skills/ui-ux-pro-max/SKILL.md",
    ),
    "workflow": (
        "skills/workflow-hub/SKILL.md",
        "skills/verification-loop/SKILL.md",
    ),
    "backend": (
        "skills/backend-hub/SKILL.md",
        "skills/api-design/SKILL.md",
    ),
}
