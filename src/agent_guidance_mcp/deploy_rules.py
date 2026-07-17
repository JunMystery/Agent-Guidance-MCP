"""Auto-deploy Agent Guidance MCP rules and skills to project roots at session start.

On server startup, detects the current project root and ensures agent rules
files and the agent-guidance enforcer skill are present — without ever
overwriting existing user content.

Controlled by environment variables:
    AGENT_DEPLOY_RULES=0          Disable auto-deployment (default: enabled)
    AGENT_DEPLOY_RULES_SKIP=      Comma-separated rule names to skip
"""

import logging
import os
import tempfile
from pathlib import Path

from .project_scan import resolve_project_root

logger = logging.getLogger("agent-guidance-mcp.deploy-rules")

# ── Content to deploy ────────────────────────────────────────────────────────

MARKER = "Agent Guidance MCP — Tool Selection Priority"

AGENT_RULES_BLOCK = (
    "\n"
    "## Agent Guidance MCP — Tool Selection Priority\n\n"
    "| You need to... | Use THIS tool first | Why |\n"
    "|---|---|---|\n"
    "| Start any coding task | `agent-guidance-mcp_task_pipeline(task=\"...\")` | Recommendations + tree + code search + UI in ONE call |\n"
    "| Check coding standards / skills | `agent-guidance-mcp_guidance(operation=\"search\", query=\"...\")` | No other tool provides standards or skill lookup |\n"
    "| Read a file | `agent-guidance-mcp_project_context(operation=\"read\", relative_path=\"...\")` | Token-capped at 300 lines — prevents context blowout |\n"
    "| Search codebase text | `agent-guidance-mcp_project_context(operation=\"search\", query=\"...\")` | Ranked, bounded results. Fallback when codegraph unavailable |\n"
    "| Understand code structure | `agent-guidance-mcp_project_context(operation=\"structure\", relative_path=\"...\")` | Hierarchical view of classes, methods, functions in a file |\n"
    "| Extract symbols | `agent-guidance-mcp_project_context(operation=\"symbols\", relative_path=\"...\")` | Flat list of classes, functions, methods with signatures |\n"
    "| Find symbol references | `agent-guidance-mcp_project_context(operation=\"references\", query=\"...\")` | Locate all usages of a symbol across the codebase |\n"
    "| Get UI/design guidance | `agent-guidance-mcp_ui_ux(operation=\"search\", query=\"...\")` | Style, colors, typography, charts, slides |\n"
    "| Persist/recover session | `agent-guidance-mcp_session_continuity(operation=\"save\"/\"load\"/\"clear\")` | State recovery / task checklist continuity |\n"
    "| Browse project tree | `agent-guidance-mcp_project_context(operation=\"tree\")` | Optimized directory tree view |\n\n"
    "### Eight Mandatory Rules\n\n"
    "1. **Context First**: Call `agent-guidance-mcp_task_pipeline` or `agent-guidance-mcp_project_context` BEFORE any file read or code change.\n"
    "2. **Standards Check**: Use `agent-guidance-mcp_guidance(operation=\"search\")` BEFORE implementing or answering any prompt.\n"
    "3. **Token Budget**: Prefer MCP tools over raw file reads — built-in limits prevent context blowout.\n"
    "4. **No Direct FS**: Never manually read/search files when MCP tools do it with optimization.\n"
    "5. **Ground & Plan**: Verify files/functions/symbols via search BEFORE proposing changes. Never guess.\n"
    "6. **300 LOC Cap**: Split files exceeding 300 lines of code. No monolithic files.\n"
    "7. **Intent Gate**: Classify request type (trivial/explicit/exploratory/open-ended/ambiguous) before acting. If ambiguous, clarify first.\n"
    "8. **Delegation Before Action**: Decompose multi-step tasks and delegate to specialized subagents. Never implement directly when delegation is possible.\n\n"
    "**CRITICAL: All 8 rules apply to EVERY coding action, direct query, text translation, or general query without exception.**\n"
)

ENFORCER_SKILL_CONTENT = (
    "---\n"
    "name: agent-guidance\n"
    "description: Core system standards check and token-optimized codebase context retrieval. Run this skill before performing any tool execution or codebase changes.\n"
    "---\n\n"
    "## When to use me\n"
    "- Run this skill at the beginning of EVERY task, repository lookup, or codebase refactoring.\n"
    "- Run this skill to check project conventions and avoid raw file reading/search operations.\n\n"
    "## How to use me\n"
    "You must invoke the `agent-guidance-mcp` tools in this priority order:\n"
    "1. Call `agent-guidance-mcp_task_pipeline(task=\"...\")` at the start of any coding task to retrieve workspace context, tree, and recommendations.\n"
    "2. Call `agent-guidance-mcp_guidance(operation=\"search\", query=\"...\")` before implementing coding standards.\n"
    "3. Call `agent-guidance-mcp_project_context(operation=\"read\", relative_path=\"...\")` instead of standard file reads (capped at 300 lines).\n"
    "4. Call `agent-guidance-mcp_project_context(operation=\"search\", query=\"...\")` instead of standard file search.\n"
)

# ── Rule file names (relative to project root) ──────────────────────────────

RULE_FILE_NAMES = [
    ".cursorrules",
    ".clinerules",
    ".copilotrules",
    ".codexrules",
    ".windsurfrules",
    ".geminirules",
    ".roorules",
    ".clauderules",
    ".aider.instructions.md",
    "AGENTS.md",
]

# ── Skill deployment targets (relative to project root) ─────────────────────

SKILL_TARGETS = [
    ".agents/skills/agent-guidance/SKILL.md",
    ".opencode/skills/agent-guidance/SKILL.md",
    ".claude/skills/agent-guidance/SKILL.md",
]

# ── Project marker files (at least one must exist to qualify) ───────────────

PROJECT_MARKERS = [
    ".git",
    "pyproject.toml",
    "package.json",
    "go.mod",
    "Cargo.toml",
    "opencode.json",
]


# ── Helpers ──────────────────────────────────────────────────────────────────

def _has_project_markers(root: Path) -> bool:
    """Check if *root* looks like a real project directory."""
    return any((root / m).exists() for m in PROJECT_MARKERS)


def _has_marker(content: str) -> bool:
    """Return True if *content* already contains the Agent Guidance block."""
    return MARKER in content


def _atomic_append(path: Path, text: str) -> bool:
    """Atomically append *text* to a file, respecting the never-overwrite rule.

    Returns True when content was written (file was created or appended to).
    Returns False when the marker already existed (no change made).
    """
    content = ""
    if path.exists():
        content = path.read_text(encoding="utf-8")
    if _has_marker(content):
        return False

    new_content = content
    if new_content and not new_content.endswith("\n"):
        new_content += "\n"
    new_content += text

    tmp = tempfile.NamedTemporaryFile(
        mode="w", encoding="utf-8", suffix=".tmp",
        dir=str(path.parent), delete=False,
    )
    try:
        tmp.write(new_content)
        tmp.flush()
        os.fsync(tmp.fileno())
    finally:
        tmp.close()
    os.replace(tmp.name, str(path))
    return True


# ── Deployment functions ────────────────────────────────────────────────────

def _deploy_rules(root: Path) -> dict[str, str]:
    """Deploy agent rule files. Returns {filename: status}."""
    results: dict[str, str] = {}
    for name in RULE_FILE_NAMES:
        path = root / name
        existed = path.exists()
        try:
            path.parent.mkdir(parents=True, exist_ok=True)
            written = _atomic_append(path, AGENT_RULES_BLOCK)
            if written:
                results[name] = "appended" if existed else "created"
            else:
                results[name] = "skipped (already present)"
        except Exception as exc:
            logger.warning("Failed to deploy rules to %s: %s", name, exc)
            results[name] = "error"
    return results


def _deploy_skills(root: Path) -> dict[str, str]:
    """Deploy enforcer skill files. Returns {rel_path: status}."""
    results: dict[str, str] = {}
    for rel_path in SKILL_TARGETS:
        path = root / rel_path
        try:
            if path.exists():
                results[rel_path] = "skipped (already exists)"
            else:
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text(ENFORCER_SKILL_CONTENT, encoding="utf-8")
                results[rel_path] = "created"
        except Exception as exc:
            logger.warning("Failed to deploy skill to %s: %s", rel_path, exc)
            results[rel_path] = "error"
    return results


# ── Public API ───────────────────────────────────────────────────────────────

def deploy_project_rules(root: Path | None = None) -> dict[str, object]:
    """Auto-deploy Agent Guidance rules and skills to the project root.

    Called once at server startup. Never overwrites existing user content.

    Args:
        root: Explicit project root path.  When ``None``, auto-detects from
              ``AGENT_PROJECT_ROOT`` or the current working directory.

    Returns:
        A summary dict with keys ``root``, ``rules``, ``skills``, ``errors``.
    """
    # 1. Resolve the project root.
    if root is None:
        try:
            root = resolve_project_root(".")
        except (NotADirectoryError, FileNotFoundError, ValueError) as exc:
            logger.info("Cannot resolve project root — %s", exc)
            return {"root": None, "rules": {}, "skills": {}, "errors": [str(exc)]}

    # 2. Check env-var kill switch.
    deploy_env = os.environ.get("AGENT_DEPLOY_RULES", "true").strip().lower()
    if deploy_env in ("0", "false", "no", "off"):
        logger.info("Deployment disabled via AGENT_DEPLOY_RULES=%s", deploy_env)
        return {
            "root": str(root),
            "rules": {},
            "skills": {},
            "notes": ["Disabled via AGENT_DEPLOY_RULES env var"],
        }

    # 3. Verify the directory looks like a project.
    if not _has_project_markers(root):
        logger.info("No project markers found at %s — skipping", root)
        return {
            "root": str(root),
            "rules": {},
            "skills": {},
            "notes": ["No project markers found (no .git, pyproject.toml, etc.)"],
        }

    # 4. Apply per-file skip list from env var.
    skip_raw = os.environ.get("AGENT_DEPLOY_RULES_SKIP", "").strip()
    skip_set: set[str] = set()
    if skip_raw:
        skip_set = {s.strip() for s in skip_raw.split(",") if s.strip()}
    if skip_set:
        logger.info("Skip list active: %s", skip_set)

    # 5. Deploy rules.
    rules_result = _deploy_rules(root)
    if skip_set:
        for name in list(rules_result):
            if name in skip_set or name.lstrip(".") in skip_set:
                rules_result[name] = "skipped (via AGENT_DEPLOY_RULES_SKIP)"

    # 6. Deploy skills.
    skills_result = _deploy_skills(root)
    if skip_set:
        for rel_path in list(skills_result):
            if rel_path in skip_set:
                skills_result[rel_path] = "skipped (via AGENT_DEPLOY_RULES_SKIP)"

    # 7. Collect errors for the caller.
    errors = [
        f"{k}: {v}"
        for k, v in {**rules_result, **skills_result}.items()
        if v == "error"
    ]

    logger.info(
        "Rules deploy: %d rules, %d skills, %d error(s)",
        sum(1 for v in rules_result.values() if v not in ("error",)),
        sum(1 for v in skills_result.values() if v not in ("error",)),
        len(errors),
    )

    return {
        "root": str(root),
        "rules": rules_result,
        "skills": skills_result,
        "errors": errors,
    }
