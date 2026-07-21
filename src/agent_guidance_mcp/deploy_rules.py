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

# ── Marker constants for wrapped section detection ──────────────────────────

MARKER_START = "<!-- agent-guidance:start -->"
MARKER_END = "<!-- agent-guidance:end -->"
MARKER = "Agent Guidance MCP — Tool Selection Priority"  # legacy fallback

# ── Content to deploy ────────────────────────────────────────────────────────

AGENT_RULES_BLOCK = (
    "## Agent Guidance MCP — Tool Selection Priority\n\n"
    "| You need to... | Use THIS tool first | Why |\n"
    "|---|---|---|\n"
    "| Start any task or phase | `agent-guidance-mcp_task_pipeline(task=\"...\")` | Recommendations + tree + code search + UI in ONE call |\n"
    "| Check coding standards / skills | `agent-guidance-mcp_guidance(operation=\"search\", query=\"...\")` | No other tool provides standards or skill lookup |\n"
    "| Read a file | `agent-guidance-mcp_project_context(operation=\"read\", relative_path=\"...\")` | Token-capped at 300 lines — prevents context blowout |\n"
    "| Search codebase text | `agent-guidance-mcp_project_context(operation=\"search\", query=\"...\")` | Ranked, bounded results. Fallback when codegraph unavailable |\n"
    "| Understand code structure | `agent-guidance-mcp_project_context(operation=\"structure\", relative_path=\"...\")` | Hierarchical view of classes, methods, functions in a file |\n"
    "| Extract symbols | `agent-guidance-mcp_project_context(operation=\"symbols\", relative_path=\"...\")` | Flat list of classes, functions, methods with signatures |\n"
    "| Get structured workflow | `agent-guidance-mcp_guidance(operation=\"workflow\", identifier=\"plan\")` → `\"code\"` → `\"test\"` | Enriched dev workflow with auto-chaining |\n"
    "| Pre-code checklist | `agent-guidance-mcp_guidance(operation=\"precode\", query=\"...\")` | Coding conventions, security, testing, arch, deploy rules |\n"
    "| Post-code verification | `agent-guidance-mcp_guidance(operation=\"verify\", query=\"...\")` | Auto-detect test/review/security/audit/deploy; suggests next workflow |\n"
    "| Skill feedback loop | `agent-guidance-mcp_guidance(operation=\"feedback\", identifier=\"...\", rating=1-5, query=\"...\")` | Rate skills to boost future recommendations for similar tasks |\n"
    "| Find symbol references | `agent-guidance-mcp_project_context(operation=\"references\", query=\"...\")` | Locate all usages of a symbol across the codebase |\n"
    "| Get UI/design guidance | `agent-guidance-mcp_ui_ux(operation=\"search\", query=\"...\")` | Style, colors, typography, charts, slides |\n"
    "| Check workflow stage | `agent-guidance-mcp_workflow_gate(action=\"check\"/\"status\"/\"set_stage\")` | Verify plan approvals and progress lifecycle |\n"
    "| Persist/recover session | `agent-guidance-mcp_session_continuity(operation=\"save\"/\"load\"/\"clear\")` | State recovery / task checklist continuity |\n"
    "| Browse project tree | `agent-guidance-mcp_project_context(operation=\"tree\")` | Optimized directory tree view |\n\n"
    "### Standard Workflow Lifecycle & Feedback Loops\n\n"
    "You must strictly follow this lifecycle for every feature or task:\n"
    "`[Context] -> [Plan] -> [Ask/Revise] -> [Build] -> [Test/Recheck] -> [Fix] -> [Document/Proposal]`\n\n"
    "**MANDATORY workflow rule:**\n"
    "You BẮT BUỘC phải gọi `workflow_gate(action=\"check\", user_message=\"<tin nhắn cuối cùng của user>\")` ở đầu mỗi lượt phản hồi (turn) trước khi gọi bất kỳ tool nào khác. Nếu `workflow_gate` trả về `plan_approved: false`, bạn tuyệt đối không được viết code hay sửa file.\n\n"
    "1. **Planning Loop (Human <-> Agent):**\n"
    "   - Propose a plan in `Plan` stage.\n"
    "   - Ask the user for approval in `Ask/Revise` stage.\n"
    "   - Move to `Build` ONLY after user has explicitly approved (ok, proceed, approved, start, đồng ý, làm đi...).\n"
    "2. **Execution & Quality Loop (Autonomous):**\n"
    "   - Transition to `Test/Recheck` after writing code in `Build`.\n"
    "   - If errors/regressions arise, transition to `Fix` and then re-test.\n"
    "3. **Circuit Breaker Rule:**\n"
    "   - Max **3 consecutive fix attempts** for the same issue in the Execution Loop.\n"
    "   - If unresolved after 3 attempts, you must STOP editing code, revert stage to `Ask/Revise`, and ask user for guidance.\n\n"
    "### Nine Mandatory Rules\n\n"
    "1. **Context First**: Call `agent-guidance-mcp_task_pipeline` or `agent-guidance-mcp_project_context` BEFORE any file read or code change.\n"
    "2. **Standards Check**: Use `agent-guidance-mcp_guidance(operation=\"search\")` BEFORE implementing or answering any prompt.\n"
    "3. **Token Budget**: Prefer MCP tools over raw file reads — built-in limits prevent context blowout.\n"
    "4. **No Direct FS**: Never manually read/search files when MCP tools do it with optimization.\n"
    "5. **Ground & Plan**: Verify files/functions/symbols via search BEFORE proposing changes. Never guess.\n"
    "6. **300 LOC Cap**: Split files exceeding 300 lines of code. No monolithic files.\n"
    "7. **Intent Gate**: Classify request type (trivial/explicit/exploratory/open-ended/ambiguous) before acting. If ambiguous, clarify first.\n"
    "8. **Delegation Before Action**: Decompose multi-step tasks and delegate to specialized subagents. Never implement directly when delegation is possible.\n"
    "9. **Per-Phase Reset**: For EACH new work phase (plan → implement → test → debug → review → refactor), re-call `agent-guidance-mcp_task_pipeline` with that phase's goal. Do NOT carry old context across phases. A new phase is a new task.\n\n"
    "**CRITICAL: All 9 rules apply to EVERY action without exception — planning, implementation, testing, debugging, reviewing, refactoring, or any other work. There is no action type exempt from these rules.**\n"
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
    "5. Use `agent-guidance-mcp_guidance(operation=\"workflow\", identifier=\"<mode>\")` for dev workflow modes (plan/test/deploy).\n"
    "6. Use `agent-guidance-mcp_guidance(operation=\"precode\", query=\"<task>\")` for pre-code checklists.\n"
    "7. Use `agent-guidance-mcp_guidance(operation=\"verify\", query=\"<changes>\")` for post-change verification.\n"
    "8. Use `agent-guidance-mcp_guidance(operation=\"feedback\", identifier=\"<id>\", rating=1-5)` to rate skills and improve recommendations.\n"
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


def _wrapped_block(content: str) -> str:
    """Wrap *content* in agent-guidance comment markers."""
    return f"{MARKER_START}\n{content}\n{MARKER_END}\n"


def _has_marker(content: str) -> bool:
    """Return True if *content* already has an agent-guidance block (legacy or current)."""
    return MARKER_START in content or MARKER in content


def _atomic_write(path: Path, content: str) -> None:
    """Atomically write *content* to *path* via tempfile + os.replace."""
    tmp = tempfile.NamedTemporaryFile(
        mode="w", encoding="utf-8", suffix=".tmp",
        dir=str(path.parent), delete=False,
    )
    try:
        tmp.write(content)
        tmp.flush()
        os.fsync(tmp.fileno())
    finally:
        tmp.close()
    os.replace(tmp.name, str(path))


def _upsert_block(path: Path, new_block_content: str) -> str:
    """Insert or update the agent-guidance block in a file, preserving user content.

    Marker-based detection:
      1. If ``MARKER_START`` and ``MARKER_END`` exist → replace content between them.
      2. If legacy block (MARKER text only) → replace entire legacy block with new wrapped block.
      3. If no block at all → append wrapped block at end.

    Returns one of ``"created"``, ``"updated"``, ``"skipped (already current)"``.
    """
    new_full_block = _wrapped_block(new_block_content)

    content = path.read_text(encoding="utf-8") if path.exists() else ""

    # Case 1: modern markers present
    start_idx = content.find(MARKER_START)
    end_idx = content.find(MARKER_END)
    if start_idx != -1 and end_idx != -1 and end_idx > start_idx:
        old_block = content[start_idx:end_idx + len(MARKER_END)]
        if old_block.rstrip() == new_full_block.rstrip():
            return "skipped (already current)"
        new_content = content[:start_idx] + new_full_block + content[end_idx + len(MARKER_END):]
        _atomic_write(path, new_content)
        return "updated"

    # Case 2: legacy block (MARKER text found but no HTML comment markers)
    if MARKER in content:
        # Find the line containing the legacy marker and replace from there
        legacy_idx = content.find(MARKER)
        # Find the next heading level or end of area -- use the marker start + known block size estimate
        # The legacy block spans from MARKER to the next blank-line-separated section or EOF.
        # We replace from legacy_idx to the first `\n##` or `\n<!--` after it, or EOF.
        rest = content[legacy_idx:]
        next_section = len(rest)
        for pat in ("\n## ", "\n<!-- "):
            pos = rest.find(pat, 1)
            if pos != -1 and pos < next_section:
                next_section = pos
        old_legacy = rest[:next_section]
        new_content = content[:legacy_idx] + new_full_block + content[legacy_idx + len(old_legacy):]
        _atomic_write(path, new_content)
        return "updated"

    # Case 3: no agent-guidance block at all → append
    new_content = content
    if new_content and not new_content.endswith("\n"):
        new_content += "\n"
    new_content += "\n" + new_full_block
    _atomic_write(path, new_content)
    return "created"


# ── Deployment functions ────────────────────────────────────────────────────

def _deploy_rules(root: Path) -> dict[str, str]:
    """Deploy or update agent rule files. Returns {filename: status}."""
    results: dict[str, str] = {}
    for name in RULE_FILE_NAMES:
        path = root / name
        try:
            path.parent.mkdir(parents=True, exist_ok=True)
            status = _upsert_block(path, AGENT_RULES_BLOCK)
            results[name] = status
        except Exception as exc:
            logger.warning("Failed to deploy rules to %s: %s", name, exc)
            results[name] = "error"
    return results


def _deploy_skills(root: Path) -> dict[str, str]:
    """Deploy or update enforcer skill files. Returns {rel_path: status}."""
    results: dict[str, str] = {}
    for rel_path in SKILL_TARGETS:
        path = root / rel_path
        try:
            path.parent.mkdir(parents=True, exist_ok=True)
            status = _upsert_block(path, ENFORCER_SKILL_CONTENT)
            results[rel_path] = status
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
