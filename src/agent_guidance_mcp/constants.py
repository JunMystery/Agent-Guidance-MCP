"""Static catalog configuration."""

TEXT_SUFFIXES = {".md", ".markdown", ".mdc", ".txt", ".yaml", ".yml", ".json"}
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
    ".agent-context",
    ".pytest_temp",
    ".codegraph",
})

TASK_ANCHORS = {
    "security": (
        "skills/security-review/SKILL.md",
        "agent-guidance/risk-management/security-constraints.md",
    ),
    "api": (
        "skills/api-design/SKILL.md",
        "agent-guidance/prompts/sample-use-cases/create-api-with-rate-limiting.md",
    ),
    "tests": (
        "skills/tdd-workflow/SKILL.md",
        "agent-guidance/engineering-practices/TESTING_STANDARDS.md",
    ),
    "docs": (
        "skills/deep-research/SKILL.md",
        "agent-guidance/engineering-practices/DOCUMENTATION_STANDARDS.md",
    ),
    "accessibility": (
        "skills/accessibility/SKILL.md",
        "agent-guidance/compliance/A11Y_CHECKLIST.md",
    ),
    "performance": (
        "skills/backend-patterns/SKILL.md",
        "agent-guidance/engineering-practices/NON_FUNCTIONAL_REQUIREMENTS.md",
    ),
    "release": (
        "skills/deployment-patterns/SKILL.md",
        "agent-guidance/engineering-practices/RELEASE_PROCESS.md",
    ),
    "skills": (
        "skills/skill-scout/SKILL.md",
        "SKILL-REFERENCE.md",
    ),
    "review": (
        "skills/code-review-and-quality/SKILL.md",
        "agent-guidance/quality-control/code-review-checklist.md",
    ),
    "ui": (
        "skills/frontend-patterns/SKILL.md",
        "skills/design-system/SKILL.md",
    ),
    "workflow": (
        "skills/verification-loop/SKILL.md",
        "skills/verification-loop/SKILL.md",
    ),
    "backend": (
        "skills/backend-patterns/SKILL.md",
        "skills/api-design/SKILL.md",
    ),
    "build": (
        "skills/planning-and-task-breakdown/SKILL.md",
    ),
    "create": (
        "skills/planning-and-task-breakdown/SKILL.md",
    ),
    "plan": (
        "skills/planning-and-task-breakdown/SKILL.md",
    ),
    "planning": (
        "skills/planning-and-task-breakdown/SKILL.md",
    ),
}

