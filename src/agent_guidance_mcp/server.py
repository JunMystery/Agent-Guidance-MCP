"""MCP registration for Agent Guidance MCP."""

import logging
import os
import sys
import threading
import time
from pathlib import Path
from typing import Any

from .catalog import StandardsCatalog, build_catalog
from . import pipelines
from . import project_context as project_context_helpers
from . import __version__
from .response_optimizer import TokenBudget, estimate_tokens, optimize_markdown
from .token_analytics import TokenTracker
from .token_config import TokenOptimizationConfig, load_config_from_env
from .usage import UsageTracker

AGENT_INSTRUCTIONS = (
    "## Agent Guidance MCP — Quick Reference\n\n"
    "Call task_pipeline(task=\"...\") FIRST for any task or phase. "
    "Note: your host may prefix tool names with `agent-guidance-mcp_` "
    "(e.g. `agent-guidance-mcp_task_pipeline`). Use the exact names "
    "shown in your tool list.\n\n"
    "Available tools:\n"
    "- task_pipeline: context prep (call first)\n"
    "- guidance: standards, skills, live docs, reasoning, workflow, precode, verify, feedback\n"
    "- project_context: bounded file ops (read/search/tree/symbols/references/diff)\n"
    "- ui_ux: design guidance (search/design_system/slides)\n"
    "- session_continuity: persist task state (save/load/clear)\n"
    "- health_check / diagnose / token_stats / usage_report: operational\n\n"
    "LOADING SKILLS: guidance(operation='get', identifier='skill-name', include_content=True) "
    "loads any of 168 skills on-demand. Search first: guidance(operation='search', "
    "query='humanizer') then load with 'get'. The built-in skill tool only lists a few "
    "external skills; use guidance for all Agent-Guidance-MCP skills.\n\n"
    "WORKFLOW MODES: guidance(operation='workflow', identifier='plan') → design → code → test → review → deploy → audit.\n"
    "Each mode returns structured instructions + the suggested next mode for task completion.\n\n"
    "CODEGEN: task_pipeline returns a `codegen_plan` (phases + matched skills) when the "
    "task signals code intent — then call guidance(operation='precode') before editing "
    "and guidance(operation='verify') after.\n\n"
    "For detailed tool usage and the 9 mandatory rules, see AGENTS.md.\n\n"
    "IMPORTANT — Tool naming: Some hosts add a server-name prefix to tool names "
    "(e.g. `agent-guidance-mcp_task_pipeline` instead of `task_pipeline`). "
    "Always use the exact tool names as they appear in your available tools list. "
    "Do NOT guess or drop the prefix — if the list shows `agent-guidance-mcp_task_pipeline`, "
    "you must call `agent-guidance-mcp_task_pipeline`, not `task_pipeline`."
)

WORKFLOW_MODE_MAP: dict[str, str] = {
    "init": "skills/workflow-modes/references/workflow-init.md",
    "plan": "skills/workflow-modes/references/workflow-plan.md",
    "design": "skills/workflow-modes/references/workflow-design.md",
    "visualize": "skills/workflow-modes/references/workflow-visualize.md",
    "code": "skills/workflow-modes/references/workflow-code.md",
    "run": "skills/workflow-modes/references/workflow-run.md",
    "test": "skills/workflow-modes/references/workflow-test.md",
    "deploy": "skills/workflow-modes/references/workflow-deploy.md",
    "debug": "skills/workflow-modes/references/workflow-debug.md",
    "refactor": "skills/workflow-modes/references/workflow-refactor.md",
    "audit": "skills/workflow-modes/references/workflow-audit.md",
    "rollback": "skills/workflow-modes/references/workflow-rollback.md",
    "recap": "skills/workflow-modes/references/workflow-recap.md",
    "review": "skills/workflow-modes/references/workflow-review.md",
    "next": "skills/workflow-modes/references/workflow-next.md",
    "help": "skills/workflow-modes/references/workflow-help.md",
    "readme": "skills/workflow-modes/references/workflow-readme.md",
    "customize": "skills/workflow-modes/references/workflow-customize.md",
    "brainstorm": "skills/workflow-modes/references/workflow-brainstorm.md",
    "save_brain": "skills/workflow-modes/references/workflow-save_brain.md",
}

try:
    from mcp.server.fastmcp import FastMCP
except ImportError as exc:  # pragma: no cover - exercised only without optional runtime dependency.
    FastMCP = None  # type: ignore[assignment]
    MCP_IMPORT_ERROR = exc
else:
    MCP_IMPORT_ERROR = None

_global_config: TokenOptimizationConfig | None = None
_global_tracker: TokenTracker | None = None
_config_lock = threading.Lock()

# ── Priority Gate ───────────────────────────────────────────────────────────
_priority_gate_passed: bool = False
_priority_gate_lock = threading.Lock()

PRIORITY_ERROR: dict[str, object] = {
    "success": False,
    "error": "PRIORITY_REQUIRED",
    "message": (
        "Call task_pipeline(task='<your task>') first. "
        "It returns project context, code recommendations, and code search in one call. "
        "After task_pipeline, all other tools become available."
    ),
    "resource": "agent-guidance-mcp://system/priority",
    "resolution": "task_pipeline(task='describe your goal here')",
}
"""Error dict returned when a gated tool is called before task_pipeline()."""

GATE_WHITELIST = frozenset({"health_check", "diagnose", "token_stats"})
"""Tool names that bypass the priority gate (operational/liveness checks only)."""

PRIORITY_RESOURCE_CONTENT = """\
# Agent Guidance MCP — Priority Instructions

## Rule
Call `task_pipeline(task="<your task>")` FIRST before any other tool on this server.

## Why
- `task_pipeline` returns project context, recommendations, code search, and UI guidance in a single call.
- It prepares the AI with the full context needed for efficient tool usage.
- After it is called, all other tools become available.

## Gated tools (require task_pipeline first)
- guidance
- project_context
- ui_ux
- session_continuity

Note: workflow, precode_check, verify, and feedback were consolidated into
`guidance` operations (`operation="workflow"|"precode"|"verify"|"feedback"`).

## Always-available tools (no gate)
- health_check
- diagnose
- token_stats

## How to proceed
1. Call `task_pipeline(task="describe what you want to do")`
2. Use any other tool as needed
"""

# ── Sentinel file bridge (cross-process gate persistence) ─────────────────
AGENT_GUIDANCE_DIR = Path.home() / ".agent-guidance"
GATE_SENTINEL_PATH = AGENT_GUIDANCE_DIR / ".gate_passed"


def _infer_task_from_params(tool_name: str, params: dict[str, Any]) -> str:
    """Derive a human-readable task from a tool call's parameters."""
    task = params.get("task", "")
    query = params.get("query", "")
    subject = params.get("subject", "")
    identifier = params.get("identifier", "")
    description = params.get("description", "")
    mode = params.get("mode", "")
    return task or query or subject or identifier or description or mode or f"using {tool_name}"


def priority_gate_check(
    project_path: Path | str | None = None,
    catalog: "StandardsCatalog | None" = None,
    tool_name: str = "",
    tool_params: dict[str, Any] | None = None,
) -> dict[str, object] | None:
    """Return an error dict if the priority gate has not been passed, else None.

    Also performs soft workflow stage warnings for active tasks.
    Ui/Ux tool (read-only operations) bypasses the gate entirely.
    """
    # ui_ux bypasses priority gate (read-only design guidance)
    if tool_name == "ui_ux":
        return None

    global _priority_gate_passed
    resolved_root = str(Path(project_path or ".").resolve())
    
    # Process stage checks & soft warning insertions
    warning_message = None
    try:
        from .session import load_session
        session_data = load_session(project_path=resolved_root)
        if session_data and isinstance(session_data, dict):
            meta = session_data.get("metadata", {})
            current_stage = meta.get("current_stage", "Context")
            plan_approved = meta.get("plan_approved", False)

            # Warn if agent tries to do things without checking workflow_gate
            if current_stage == "Ask_Revise" and not plan_approved:
                warning_message = "⚠️ Workflow Stage Warning: Current stage is 'Ask_Revise'. You must wait for User approval (e.g. 'proceed', 'ok') before starting code modification. Call workflow_gate(action='check', user_message='...') first."
            elif current_stage in ("Context", "Plan", "Ask_Revise") and tool_name == "project_context" and tool_params:
                op = tool_params.get("operation", "")
                if op in ("read", "search"):
                    warning_message = f"⚠️ Workflow Stage Mismatch: Current stage is '{current_stage}'. You are reading/searching project files before plan approval. Proceed with caution."
    except Exception:
        pass

    with _priority_gate_lock:
        if not _priority_gate_passed:
            if _gate_sentinel_check(project_path):
                _priority_gate_passed = True
            elif catalog and tool_name:
                try:
                    task = _infer_task_from_params(tool_name, tool_params or {})
                    from . import pipelines as _p
                    _p.auto_context(
                        catalog,
                        task=task,
                        project_path=str(project_path or "."),
                        config=get_config(),
                    )
                except Exception:
                    pass
                _priority_gate_passed = True
                return None
            else:
                return dict(PRIORITY_ERROR)
    
    if warning_message:
        sys.stderr.write(f"\n{warning_message}\n")
        sys.stderr.flush()
        
    return None

def workflow_gate_check(
    project_path: Path | str | None = None,
    tool_name: str = "",
    tool_params: dict[str, Any] | None = None,
) -> dict[str, object] | None:
    """Enforces the Workflow Stage Access Matrix. Returns error if blocked."""
    resolved_root = str(Path(project_path or ".").resolve())
    try:
        from .session import load_session
        session_data = load_session(project_path=resolved_root)
        if not session_data or not isinstance(session_data, dict):
            current_stage = "Context"
            plan_approved = False
        else:
            meta = session_data.get("metadata", {})
            current_stage = meta.get("current_stage", "Context")
            plan_approved = meta.get("plan_approved", False)
    except Exception:
        current_stage = "Context"
        plan_approved = False

    if tool_name in ("workflow_gate", "session_continuity", "task_pipeline"):
        return None

    # ui_ux: search/slides always allowed (read-only). design_system blocked in early stages.
    if tool_name == "ui_ux" and tool_params:
        op = tool_params.get("operation", "")
        if op in ("search", "slides"):
            return None
        # design_system requires approved plan
        if current_stage in ("Context", "Plan", "Ask_Revise"):
            return {
                "success": False,
                "error": "WORKFLOW_STAGE_BLOCKED",
                "message": f"🚨 WORKFLOW GATE BLOCKED: Cannot call ui_ux(operation='design_system') in stage '{current_stage}'. Transition to 'Build' with an approved plan first."
            }
        return None  # allowed in Build/Fix/Test_Recheck/Proposal

    if current_stage == "Context":
        return {
            "success": False,
            "error": "WORKFLOW_STAGE_BLOCKED",
            "message": f"🚨 WORKFLOW GATE BLOCKED: Stage is 'Context'. You cannot call '{tool_name}'. You must call task_pipeline first, then transition stage using workflow_gate."
        }

    elif current_stage == "Plan":
        if tool_name == "project_context" and tool_params:
            op = tool_params.get("operation", "")
            if op in ("diff", "architecture"):
                return {
                    "success": False,
                    "error": "WORKFLOW_STAGE_BLOCKED",
                    "message": f"🚨 WORKFLOW GATE BLOCKED: Stage is 'Plan'. Operation '{op}' is not permitted."
                }
        return None

    elif current_stage == "Ask_Revise":
        if tool_name in ("project_context", "guidance", "ui_ux"):
            if tool_name == "project_context" and tool_params:
                op = tool_params.get("operation", "")
                if op in ("read", "search", "symbols", "references", "structure", "callers", "callees", "diff"):
                    return {
                        "success": False,
                        "error": "WORKFLOW_STAGE_BLOCKED",
                        "message": f"🚨 WORKFLOW GATE BLOCKED: Stage is 'Ask_Revise' (plan_approved={plan_approved}). Context code reads are blocked. You must ask user for approval, then call workflow_gate(action='check', user_message='...') to proceed."
                    }
            if tool_name == "guidance" and tool_params:
                op = tool_params.get("operation", "")
                if op in ("precode", "verify"):
                    return {
                        "success": False,
                        "error": "WORKFLOW_STAGE_BLOCKED",
                        "message": f"🚨 WORKFLOW GATE BLOCKED: Stage is 'Ask_Revise'. Operation '{op}' is blocked. Transition to 'Build' first."
                    }
        return None

    elif current_stage == "Build":
        if not plan_approved:
            return {
                "success": False,
                "error": "WORKFLOW_STAGE_BLOCKED",
                "message": "🚨 WORKFLOW GATE BLOCKED: Stage is 'Build' but plan is NOT approved. You must seek user approval first."
            }
        return None

    elif current_stage == "Test_Recheck":
        if tool_name == "guidance" and tool_params:
            op = tool_params.get("operation", "")
            if op in ("precode",):
                return {
                    "success": False,
                    "error": "WORKFLOW_STAGE_BLOCKED",
                    "message": "🚨 WORKFLOW GATE BLOCKED: Stage is 'Test_Recheck'. You cannot generate new code checklists. Focus on verifying existing changes."
                }
        return None

    elif current_stage == "Fix":
        return None

    elif current_stage == "Proposal":
        if tool_name == "project_context" and tool_params:
            op = tool_params.get("operation", "")
            if op in ("diff", "structure", "symbols"):
                return {
                    "success": False,
                    "error": "WORKFLOW_STAGE_BLOCKED",
                    "message": "🚨 WORKFLOW GATE BLOCKED: Stage is 'Proposal'. Code modification operations are blocked."
                }
        return None

    return None

def priority_gate_pass(project_path: str = ".") -> None:
    """Mark the priority gate as passed (called by task_pipeline).

    Also re-writes the sentinel file so a future server restart (e.g. after
    subagent spawn) can recover the gate state.
    """
    global _priority_gate_passed
    with _priority_gate_lock:
        _priority_gate_passed = True
    _gate_sentinel_write(project_path)


def priority_gate_reset() -> None:
    """Reset the priority gate (for testing)."""
    global _priority_gate_passed
    with _priority_gate_lock:
        _priority_gate_passed = False


def _gate_sentinel_write(project_path: str) -> None:
    AGENT_GUIDANCE_DIR.mkdir(parents=True, exist_ok=True)
    import json
    import time as _time
    sentinel_data = json.dumps({
        "project_path": str(Path(project_path).resolve()),
        "version": __import__("agent_guidance_mcp").__version__,
        "written_at": _time.time(),
        "expires_at": _time.time() + 86400,
    })
    GATE_SENTINEL_PATH.write_text(sentinel_data, encoding="utf-8")


def _gate_sentinel_check(expected_project_path: Path | str | None = None) -> bool:
    if not GATE_SENTINEL_PATH.exists():
        return False
    try:
        import json
        import time as _time
        data = json.loads(GATE_SENTINEL_PATH.read_text(encoding="utf-8"))
        if not (isinstance(data, dict) and "project_path" in data):
            return False
        expires_at = data.get("expires_at")
        if expires_at is not None and _time.time() > expires_at:
            _gate_sentinel_clear()
            return False
        if expected_project_path:
            sentinel_path = Path(data["project_path"]).resolve()
            expected_path = Path(expected_project_path).resolve()
            return sentinel_path == expected_path
        return True
    except (json.JSONDecodeError, OSError):
        return False


def _gate_sentinel_clear() -> None:
    try:
        GATE_SENTINEL_PATH.unlink(missing_ok=True)
    except OSError:
        pass


def run_session_start(
    root: str | None = None,
    project_path: str = ".",
    task: str | None = None,
    focus: str = "general",
) -> str:
    """Session-start auto-activation: passes gate + returns session context."""
    import json as _json

    from .catalog import build_catalog as _build_catalog
    from . import pipelines
    from .token_config import load_config_from_env
    from .token_analytics import TokenTracker

    try:
        catalog = _build_catalog(root)
    except Exception as exc:
        return _json.dumps({
            "priority": "INFO",
            "message": f"agent-guidance-mcp: catalog build failed — {exc}. Skills not available.",
        })

    config = load_config_from_env()
    tracker = TokenTracker(enabled=False)

    priority_gate_pass(project_path)

    resolved_path = str(Path(project_path).resolve())
    effective_task = task or "Initialize project context for workspace awareness"

    result = pipelines.task_pipeline(
        catalog=catalog,
        task=effective_task,
        project_path=resolved_path,
        focus=focus,
        config=config,
        tracker=tracker,
    )

    lines: list[str] = [
        "## Agent Guidance — Session Context Loaded",
        "",
        f"**Project:** `{resolved_path}`",
        f"**Task:** {effective_task}",
        "",
    ]

    recs = result.get("recommendations", {})
    if isinstance(recs, dict):
        skill_list = recs.get("recommendations", [])
        if skill_list:
            names = [
                r.get("identifier", "?")
                for r in skill_list[:5]
                if isinstance(r, dict)
            ]
            lines.append(f"**Recommended Skills:** {', '.join(names)}")
            lines.append("")

    seq = result.get("execution_sequence")
    if seq:
        lines.append(f"**Execution Sequence:** {', '.join(seq)}")
        lines.append("")

    lines.append(
        "Agent Guidance MCP tools are now available. "
        "Use `task_pipeline` for any coding task."
    )

    return _json.dumps({
        "priority": "IMPORTANT",
        "message": "\n".join(lines),
    })


def run_re_gate(project_path: str = ".") -> str:
    """Re-pass the priority gate and refresh the sentinel file.

    Call this after a subagent returns to recover gate state if the MCP
    server restarted during the subagent lifecycle.
    """
    import json as _json
    priority_gate_pass(project_path)
    return _json.dumps({
        "success": True,
        "message": "Gate re-passed. All gated MCP tools are available.",
    })


def get_config() -> TokenOptimizationConfig:
    """Return the process-level token optimization config."""
    global _global_config
    with _config_lock:
        if _global_config is None:
            _global_config = load_config_from_env()
        return _global_config


def set_config(config: TokenOptimizationConfig | None) -> None:
    """Set the process-level token optimization config."""
    global _global_config, _global_tracker
    with _config_lock:
        _global_config = config
        _global_tracker = None


def get_tracker() -> TokenTracker:
    """Return the process-level token savings tracker."""
    global _global_config, _global_tracker
    with _config_lock:
        if _global_tracker is None:
            if _global_config is None:
                _global_config = load_config_from_env()
            _global_tracker = TokenTracker(
                enabled=_global_config.enabled and _global_config.track_savings,
                max_records=_global_config.tracker_max_records,
                trim_to=_global_config.tracker_trim_to,
            )
        return _global_tracker


def reset_tracker() -> None:
    """Reset token tracking data."""
    get_tracker().reset()


def get_usage() -> UsageTracker | None:
    """Return the process-level usage tracker, or None if not started."""
    from .usage import get_usage as _gu
    return _gu()


def set_usage(usage: UsageTracker | None) -> None:
    """Set the process-level usage tracker."""
    from .usage import set_usage as _su
    _su(usage)


_CONFIG_UNSET = object()


def create_server(
    root: str | Path | None = None,
    config: TokenOptimizationConfig | None = _CONFIG_UNSET,
) -> Any:
    if FastMCP is None:
        raise RuntimeError(
            "The 'mcp' package is required to run the server. Install with "
            "'pip install -e .', or 'pip install mcp'."
        ) from MCP_IMPORT_ERROR

    if config is _CONFIG_UNSET:
        set_config(load_config_from_env())
    else:
        set_config(config)
    try:
        catalog = build_catalog(root)
    except Exception as e:
        logger = logging.getLogger("agent-guidance-mcp")
        logger.warning(f"Catalog build failed — {e}. Starting with empty catalog.")
        from .catalog import StandardsCatalog
        catalog = StandardsCatalog(Path(root or ".").resolve() if root else Path("."), [])

        # Auto-index project workspace on startup (watcher is optional & configurable)
    try:
        from .database import CodeGraphDatabase
        from .indexer import CodeGraphIndexer
        from .watcher import CodeGraphWatcher
        import threading

        project_root = Path(os.environ.get("AGENT_PROJECT_ROOT", str(catalog.root))).resolve()
        db_path = project_root / ".agent-context" / "codegraph.db"
        db = CodeGraphDatabase(db_path)

        watcher_enabled = os.environ.get("AGENT_WATCHER_ENABLED", "true").strip().lower()
        indexer_enabled = os.environ.get("AGENT_INDEXER_ENABLED", "true").strip().lower()

        def _run_initial_index_bg() -> None:
            logger = logging.getLogger("agent-guidance-mcp")
            try:
                if indexer_enabled not in ("0", "false", "no", "off"):
                    indexer = CodeGraphIndexer(project_root, db)
                    indexer.run()

                # File watcher is CPU-aware; disable via AGENT_WATCHER_ENABLED=false
                if watcher_enabled not in ("0", "false", "no", "off"):
                    watcher_interval_raw = os.environ.get("AGENT_WATCHER_INTERVAL")
                    watcher_kwargs: dict[str, Any] = {}
                    if watcher_interval_raw:
                        try:
                            watcher_kwargs["interval_seconds"] = float(watcher_interval_raw)
                        except ValueError:
                            pass
                    watcher = CodeGraphWatcher(project_root, db, **watcher_kwargs)
                    watcher.start()
            except Exception as e:
                logger.error(f"Error in initial index background thread: {e}", exc_info=True)

        threading.Thread(target=_run_initial_index_bg, daemon=True).start()
    except Exception as e:
        logger = logging.getLogger("agent-guidance-mcp")
        logger.error(f"Failed to start initial index background thread: {e}", exc_info=True)

    try:
        from .deploy_rules import deploy_project_rules

        deploy_root = Path(os.environ.get("AGENT_PROJECT_ROOT", str(catalog.root))).resolve()

        def _deploy_rules_bg() -> None:
            logger = logging.getLogger("agent-guidance-mcp")
            try:
                result = deploy_project_rules(deploy_root)
                rules_count = sum(1 for v in result.get("rules", {}).values() if v not in ("error",))
                skills_count = sum(1 for v in result.get("skills", {}).values() if v not in ("error",))
                if rules_count or skills_count:
                    logger.info("Rules deploy: %d rule files, %d skill files deployed", rules_count, skills_count)
            except Exception as e:
                logger.error(f"Error in deploy rules background thread: {e}", exc_info=True)

        threading.Thread(target=_deploy_rules_bg, daemon=True).start()
    except Exception as e:
        logger = logging.getLogger("agent-guidance-mcp")
        logger.error(f"Failed to start deploy rules background thread: {e}", exc_info=True)

    logging.basicConfig(level=logging.WARNING, stream=sys.stderr)

    # Start persistent usage tracker
    import atexit
    from .usage import UsageTracker
    set_usage(UsageTracker())

    def _close_usage() -> None:
        u = get_usage()
        if u is not None:
            u.close()

    atexit.register(_close_usage)

    # Pre-warm LLM selector in background so guidance search doesn't block
    try:
        def _warm_llm_bg() -> None:
            try:
                from .llm_selector import LLMSelector
                sel = LLMSelector()
                sel._load()
            except Exception:
                pass
        threading.Thread(target=_warm_llm_bg, daemon=True).start()
    except Exception:
        pass

    # Check for sentinel file from --session-start (cross-process gate persistence).
    # Sentinel is NOT cleared — it persists for the session lifetime so a future
    # server restart (e.g. after subagent spawn) can recover the gate state.
    if _gate_sentinel_check(deploy_root):
        _priority_gate_passed = True

    mcp = FastMCP("Agent Guidance MCP", instructions=AGENT_INSTRUCTIONS, json_response=True)
    register_handlers(mcp, catalog)
    return mcp


def register_handlers(mcp: Any, catalog: StandardsCatalog) -> None:
    @mcp.resource("standards://manifest", mime_type="application/json")
    def manifest() -> str:
        """Return the indexed standards manifest."""
        return catalog.manifest_json()

    @mcp.resource("standards://version", mime_type="application/json")
    def version() -> str:
        """Return server version information."""
        import json
        return json.dumps({
            "server": "agent-guidance-mcp",
            "version": __version__,
            "mcp_protocol": "2024-11-05",
        })

    @mcp.resource("standards://document/{identifier}", mime_type="text/markdown")
    def document(identifier: str) -> str:
        """Return a standards document by slug."""
        config = get_config()
        try:
            raw = catalog.read_entry(identifier, optimize=False)
            optimized = catalog.read_entry(identifier, config=config)
        except KeyError as exc:
            return f"Document not found: {exc}"
        _record_savings("resource", "document", raw, optimized)
        return optimized

    @mcp.resource("standards://skill/{name}", mime_type="text/markdown")
    def skill(name: str) -> str:
        """Return a local on-demand skill capsule by name."""
        config = get_config()
        try:
            raw = catalog.read_entry(name, optimize=False)
            optimized = catalog.read_entry(name, config=config)
        except KeyError as exc:
            return f"Skill not found: {exc}"
        _record_savings("resource", "skill", raw, optimized)
        usage = get_usage()
        if usage:
            usage.record_skill_load(name)
        return optimized

    @mcp.resource("agent-guidance-mcp://system/priority", mime_type="text/markdown")
    def priority_instructions() -> str:
        """Return priority gate instructions — read when PRIORITY_REQUIRED error is returned."""
        return PRIORITY_RESOURCE_CONTENT

    @mcp.resource("agent-guidance-mcp://system/gate", mime_type="application/json")
    def gate_status() -> str:
        """Return gate status: passed (bool) and sentinel_present (bool)."""
        import json
        return json.dumps({
            "passed": _priority_gate_passed,
            "sentinel_present": GATE_SENTINEL_PATH.exists(),
        })

    @mcp.tool()
    def task_pipeline(
        task: str,
        project_path: str = ".",
        focus: str = "general",
        code_query: str | None = None,
        include_tree: bool = True,
        include_ui: bool = True,
        limit: int = 8,
        timeout: float | None = 30.0,
    ) -> dict[str, object]:
        """CALL FIRST before any coding task. Prepares recommendations, project tree,
        code search, and optional UI guidance in ONE optimized call. Use BEFORE
        codegraph, file reads, or implementation.

        Example: task_pipeline(task="Add JWT auth to Express API", focus="backend")

        Args:
            task: Description of the work to perform (required).
            project_path: Root of the project to scan (default ".").
            focus: Domain focus — "general", "frontend", or "backend" (default "general").
            code_query: Optional search override; auto-detected from task if omitted.
            include_tree: Include project directory tree in result (default True).
            include_ui: Attach UI/UX guidance when task signals UI intent (default True).
            limit: Maximum number of recommendations to return (default 8).
            timeout: Per-task timeout in seconds (default 30.0).
        """
        priority_gate_pass(project_path)
        t0 = _now_ms()
        try:
            result = pipelines.task_pipeline(
                catalog=catalog,
                task=task,
                project_path=project_path,
                focus=focus,
                code_query=code_query,
                include_tree=include_tree,
                include_ui=include_ui,
                limit=limit,
                timeout=timeout,
                config=get_config(),
                tracker=get_tracker(),
            )
        except Exception as exc:  # record errored calls (F5)
            _track_error("task_pipeline", "run", _now_ms() - t0, error=str(exc))
            raise
        _record_savings("task_pipeline", "run", result, result, duration_ms=_now_ms() - t0, project_path=project_path)
        return result

    @mcp.tool()
    def guidance(
        operation: str,
        query: str | None = None,
        identifier: str | None = None,
        category: str | None = None,
        kind: str | None = None,
        limit: int = 10,
        include_content: bool = False,
        resolve_dependencies: bool = False,
        rating: int = 0,
    ) -> dict[str, object] | list[dict[str, object]]:
        """Standards catalog and skill lookup. 168 skills available on-demand.

        Use guidance(operation='search') BEFORE implementing to find applicable
        coding standards, security rules, and skill workflows.
        Use guidance(operation='get', identifier='skill-name') to load a specific
        skill on-demand with its full content.
        Use guidance(operation='reason') for structured reasoning frameworks
        (decision, bug, architecture, security, performance).
        Use guidance(operation='docs') for live library/API documentation via Context7.
        Use guidance(operation='workflow', identifier='plan') for dev workflow modes.
        Use guidance(operation='precode', query='task description') for pre-code checklist.
        Use guidance(operation='verify', query='changed files') for post-change verification.
        Use guidance(operation='feedback', identifier='skill-id', rating=5) to rate skills.

        Examples:
          guidance(operation="search", query="humanizer writing")
          guidance(operation="get", identifier="humanizer", include_content=True)
          guidance(operation="docs", query="jsonwebtoken sign", identifier="node-jsonwebtoken")
          guidance(operation="workflow", identifier="plan")
          guidance(operation="precode", query="add JWT auth to Express API")
          guidance(operation="verify", query="src/auth.py, src/middleware.py")
          guidance(operation="feedback", identifier="backend-patterns", rating=5, query="auth task")

        Args:
            operation: One of list, get, search, recommend, reason, docs,
                workflow, precode, verify, feedback (required).
            query: Search/recommend/reason query string, or technical question for docs.
                For precode: task description. For verify: changed files/description.
                For feedback: optional task context.
            identifier: Skill/document identifier for "get"; library/package name for
                "docs" (e.g. "react", "nextjs", "express"). For workflow: mode key
                (e.g. "plan", "code", "test"). For feedback: skill_id to rate.
            category: Filter entries by category.
            kind: Filter by kind — skill, doc, principle, etc.
            limit: Maximum results (default 10).
            include_content: Set True for "get" to include full skill body (default False).
            resolve_dependencies: Set True for "get" to recursively load transitive dependencies (default False).
            rating: Integer 1-5 for "feedback" operation (default 0, ignored for other ops).
        """
        gate = priority_gate_check(catalog.root, catalog, "guidance", {
            "query": query, "identifier": identifier, "operation": operation,
        })
        if gate:
            return gate
        w_gate = workflow_gate_check(catalog.root, "guidance", {
            "query": query, "identifier": identifier, "operation": operation,
        })
        if w_gate:
            return w_gate
        t0 = _now_ms()
        try:
            result = pipelines.guidance(
                catalog=catalog,
                operation=operation,
                query=query,
                identifier=identifier,
                category=category,
                kind=kind,
                limit=limit,
                include_content=include_content,
                resolve_dependencies=resolve_dependencies,
                rating=rating,
                config=get_config(),
                tracker=get_tracker(),
            )
        except Exception as exc:  # record errored calls (F5)
            _track_error("guidance", operation, _now_ms() - t0, error=str(exc))
            raise
        usage = get_usage()
        if usage:
            if operation == "get" and identifier:
                usage.record_skill_load(identifier, query=query, search_term=query, project_path=None)
            elif operation == "recommend" and query:
                # Count LLM-recommended skills as "called" (F2/F5/F6). Bulk
                # `search` hits are intentionally NOT counted to avoid inflating
                # the skill-call metric with candidate lists. The e5 embed query
                # for recommend is logged inside search_entries on success.
                usage.record_recommend_skill_loads(result, query)
        _record_savings("guidance", operation, result, result, duration_ms=_now_ms() - t0, project_path=None)
        return result

    @mcp.tool()
    def project_context(
        operation: str,
        project_path: str = ".",
        query: str | None = None,
        relative_path: str | None = None,
        start_line: int = 1,
        max_lines: int = project_context_helpers.DEFAULT_MAX_READ_LINES,
        max_depth: int = project_context_helpers.DEFAULT_MAX_DEPTH,
        output_path: str = project_context_helpers.DEFAULT_SNAPSHOT_PATH,
        max_file_bytes: int = project_context_helpers.DEFAULT_MAX_FILE_BYTES,
        max_total_bytes: int = project_context_helpers.DEFAULT_MAX_TOTAL_BYTES,
        limit: int = 20,
    ) -> dict[str, object]:
        """Read and search project files with built-in token budgets.

        Supported operations:
        - read: Bounded file reading (capped at 300 lines).
        - search: Codebase text search (primary fallback when codegraph unavailable).
        - tree: Directory overview with file metadata.
        - snapshot: Export project snapshot to disk.
        - symbols: Extract classes, functions, methods from a file.
        - references: Find symbol usage across the codebase.
        - structure: Hierarchical file overview (classes, methods, functions).
        - callers: Get all callers of a symbol from the CodeGraph database.
        - callees: Get all callees of a symbol from the CodeGraph database.
        - diff: View the git diff of workspace changes.
        - architecture: Detailed project architecture mapping (tech stack, modules, core hubs).

        Examples:
          project_context(operation="read", relative_path="src/auth.js")
          project_context(operation="search", query="JWT middleware")

        Args:
            operation: One of tree, search, read, snapshot, symbols, references,
                structure, callers, callees, diff, architecture (required).
            project_path: Root of the project (default ".").
            query: Search query for grep, symbol name for references, or symbol ID
                for callers/callees.
            relative_path: File path for read, symbols, or structure operations.
            start_line: Line offset for read (default 1).
            max_lines: Maximum lines to read (default 300).
            max_depth: Directory tree depth (default 8).
            output_path: Snapshot output path.
            max_file_bytes: Per-file cap for snapshot (default 200000).
            max_total_bytes: Total cap for snapshot (default 2000000).
            limit: Maximum search or reference results (default 20).
        """
        gate = priority_gate_check(catalog.root, catalog, "project_context", {
            "query": query, "relative_path": relative_path, "operation": operation,
        })
        if gate:
            return gate
        w_gate = workflow_gate_check(catalog.root, "project_context", {
            "query": query, "relative_path": relative_path, "operation": operation,
        })
        if w_gate:
            return w_gate
        t0 = _now_ms()
        try:
            result = pipelines.project_context(
                operation=operation,
                project_path=project_path,
                query=query,
                relative_path=relative_path,
                start_line=start_line,
                max_lines=max_lines,
                max_depth=max_depth,
                output_path=output_path,
                max_file_bytes=max_file_bytes,
                max_total_bytes=max_total_bytes,
                limit=limit,
                config=get_config(),
                tracker=get_tracker(),
            )
        except Exception as exc:  # record errored calls (F5)
            _track_error("project_context", operation, _now_ms() - t0, error=str(exc))
            raise
        _record_savings("project_context", operation, result, result, duration_ms=_now_ms() - t0, project_path=project_path)
        return result

    @mcp.tool()
    def ui_ux(
        operation: str,
        query: str,
        domain: str | None = None,
        stack: str | None = None,
        project_name: str | None = None,
        output_format: str = "markdown",
        limit: int = 3,
    ) -> dict[str, object]:
        """UI/UX design guidance.

        Use for style recommendations, color palettes, typography pairings,
        chart selection, and slide layouts.

        Examples:
          ui_ux(operation="search", query="minimalist dashboard design", domain="style")
          ui_ux(operation="design_system", query="SaaS landing page", project_name="MyApp")

        Args:
            operation: One of search, design_system, slides (required).
            query: Search query (required).
            domain: UI domain filter — style, color, chart, landing, product,
                ux, typography, icons, react, web.
            stack: Framework stack filter — react, nextjs, vue, svelte, astro, etc.
            project_name: Project name used for design_system generation.
            output_format: "markdown" or "ascii" (default "markdown").
            limit: Maximum results (default 3).
        """
        gate = priority_gate_check(catalog.root, catalog, "ui_ux", {
            "query": query, "operation": operation,
        })
        if gate:
            return gate
        w_gate = workflow_gate_check(catalog.root, "ui_ux", {
            "query": query, "operation": operation,
        })
        if w_gate:
            return w_gate
        t0 = _now_ms()
        try:
            result = pipelines.ui_ux(
                catalog=catalog,
                operation=operation,
                query=query,
                domain=domain,
                stack=stack,
                project_name=project_name,
                output_format=output_format,
                limit=limit,
                config=get_config(),
                tracker=get_tracker(),
            )
        except Exception as exc:  # record errored calls (F5)
            _track_error("ui_ux", operation, _now_ms() - t0, error=str(exc))
            raise
        _record_savings("ui_ux", operation, result, result, duration_ms=_now_ms() - t0, project_path=None)
        return result

    @mcp.tool()
    def session_continuity(
        operation: str,
        project_path: str = ".",
        task: str | None = None,
        checklist: list[dict] | None = None,
        current_step_index: int = 0,
        metadata: dict | None = None,
    ) -> dict[str, object]:
        """Persist or recover task session state for continuity.

        Use operation='save' to save the current task checklist progress.
        Use operation='load' to resume after interruptions.
        Use operation='clear' when the task is completed.

        Args:
            operation: One of save, load, clear (required).
            project_path: Project root path (default ".").
            task: Task description (required for save).
            checklist: List of checklist dicts, e.g.
                [{"title": "...", "status": "todo"|"done"}].
            current_step_index: Index of current checklist step (default 0).
            metadata: Optional context variables as a dict.
        """
        gate = priority_gate_check(catalog.root, catalog, "session_continuity", {
            "task": task, "operation": operation,
        })
        if gate:
            return gate
        t0 = _now_ms()
        try:
            result = pipelines.session_continuity(
                operation=operation,
                project_path=project_path,
                task=task,
                checklist=checklist,
                current_step_index=current_step_index,
                metadata=metadata,
                tracker=get_tracker(),
            )
        except Exception as exc:  # record errored calls (F5)
            _track_error("session_continuity", operation, _now_ms() - t0, error=str(exc))
            raise
        _record_savings("session_continuity", operation, result, result, duration_ms=_now_ms() - t0, project_path=project_path)
        return result

    @mcp.tool()
    def workflow_gate(
        action: str,
        project_path: str = ".",
        user_message: str | None = None,
        target_stage: str | None = None,
    ) -> dict[str, object]:
        """Manage and validate the active workflow stage.

        Use action='status' to view current stage.
        Use action='check' with user_message to parse user approval and check transitions.
        Use action='set_stage' with target_stage to transition.

        Args:
            action: One of status, check, set_stage (required).
            project_path: Project root path (default ".").
            user_message: Last message from the user to analyze approval (required for check).
            target_stage: Stage to transition to (required for set_stage).
        """
        gate = priority_gate_check(catalog.root, catalog, "workflow_gate", {
            "action": action, "user_message": user_message, "target_stage": target_stage,
        })
        if gate:
            return gate
        t0 = _now_ms()
        try:
            result = pipelines.workflow_gate(
                action=action,
                project_path=project_path,
                user_message=user_message,
                target_stage=target_stage,
                tracker=get_tracker(),
            )
        except Exception as exc:
            _track_error("workflow_gate", action, _now_ms() - t0, error=str(exc))
            raise
        _record_savings("workflow_gate", action, result, result, duration_ms=_now_ms() - t0, project_path=project_path)
        return result

    @mcp.tool()
    def token_stats() -> dict[str, object]:
        """Return token optimization statistics for this session. No parameters."""
        return get_tracker().summary()

    @mcp.tool()
    def usage_report(scope: str = "session") -> dict[str, object]:
        """Return recorded usage statistics for the current or all sessions.

        Args:
            scope: "session" for active session only, "all" for lifetime data.
        """
        usage = get_usage()
        if usage is None:
            return {"success": False, "error": "Usage tracking not started."}
        if scope not in ("session", "all"):
            return {"success": False, "error": f"Invalid scope '{scope}'. Must be 'session' or 'all'."}
        return usage.summary(scope=scope)

    @mcp.tool()
    def health_check() -> dict[str, object]:
        """Return server health status and basic metadata. No parameters."""
        try:
            manifest = catalog.manifest()
            entry_count = manifest.get("entry_count", 0)
        except Exception as exc:
            return {
                "status": "degraded",
                "server": "agent-guidance-mcp",
                "version": __version__,
                "error": str(exc),
            }
        status = "ok" if entry_count > 0 else "degraded"
        return {
            "status": status,
            "server": "agent-guidance-mcp",
            "version": __version__,
            "entries": entry_count,
        }

    @mcp.tool()
    def diagnose() -> dict[str, object]:
        """Perform comprehensive self-diagnostics on the server, tree-sitter capabilities, SQLite CodeGraph database, and Context7 network connectivity. No parameters."""
        from .diagnostics import run_diagnostics
        root_path = Path(catalog.root or ".").resolve()
        return run_diagnostics(root_path, catalog)


def _record_savings(
    tool_name: str,
    operation: str,
    original: str,
    optimized: str,
    duration_ms: int = 0,
    project_path: str | None = None,
) -> None:
    """Record token savings in-memory and persist token values to SQLite."""
    from .utils import record_savings
    record_savings(get_tracker(), tool_name, operation, original, optimized)

    usage = get_usage()
    if usage is not None:
        from .response_optimizer import estimate_tokens
        tok_orig = estimate_tokens(original if isinstance(original, str) else str(original))
        tok_opt = estimate_tokens(optimized if isinstance(optimized, str) else str(optimized))
        usage.record_tool_call(tool_name, operation, duration_ms=duration_ms, tokens_original=tok_orig, tokens_optimized=tok_opt, project_path=project_path)


def _now_ms() -> int:
    """Return current monotonic time in milliseconds."""
    return int(time.time() * 1000)


def _track_error(tool_name: str, operation: str | None, duration_ms: int, error: str | None = None) -> None:
    """Record a failed/errored tool call in the persistent usage tracker (F5)."""
    usage = get_usage()
    if usage is None:
        return
    usage.record_tool_call(tool_name, operation, duration_ms=duration_ms, error_message=error)
