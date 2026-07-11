"""MCP registration for Agent Guidance MCP."""


import logging
import os
import sys
import threading
from pathlib import Path
from typing import Any

from .catalog import StandardsCatalog, build_catalog
from . import pipelines
from . import project_context as project_context_helpers
from . import __version__
from .response_optimizer import TokenBudget, estimate_tokens, optimize_markdown
from .token_analytics import TokenTracker
from .token_config import TokenOptimizationConfig, load_config_from_env

AGENT_INSTRUCTIONS = (
    "## Agent Guidance MCP — Quick Reference\n\n"
    "Call task_pipeline(task=\"...\") FIRST for any coding task. "
    "It returns recommendations, project tree, code search, and UI guidance in ONE call.\n\n"
    "Available tools:\n"
    "- task_pipeline: context prep (call first)\n"
    "- guidance: standards, skills, live docs, reasoning frameworks\n"
    "- project_context: bounded file ops (read/search/tree/symbols/references/diff)\n"
    "- ui_ux: design guidance (search/design_system/slides)\n"
    "- session_continuity: persist task state (save/load/clear)\n"
    "- health_check / diagnose / token_stats: operational\n\n"
    "LOADING SKILLS: guidance(operation='get', identifier='skill-name', include_content=True) "
    "loads any of 168 skills on-demand. Search first: guidance(operation='search', "
    "query='humanizer') then load with 'get'. The built-in skill tool only lists a few "
    "external skills; use guidance for all Agent-Guidance-MCP skills.\n\n"
    "For detailed tool usage and the 6 mandatory rules, see AGENTS.md."
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
# Enforces that task_pipeline() is called before any other tool can be used.
#
# Two layers:
#   1. In-memory flag (_priority_gate_passed) — per-process, resets on restart.
#   2. Sentinel file (~/.agent-guidance/.gate_passed) — bridges the session-start
#      hook process and the MCP server process. Written by --session-start CLI,
#      read by create_server() on MCP startup.
_priority_gate_passed: bool = False
_priority_gate_lock = threading.Lock()

AGENT_GUIDANCE_DIR = Path.home() / ".agent-guidance"
GATE_SENTINEL_PATH = AGENT_GUIDANCE_DIR / ".gate_passed"
"""Sentinel file path for cross-process gate persistence."""


def _gate_sentinel_write(project_path: str) -> None:
    """Write a sentinel file so the MCP server process inherits the passed gate."""
    import json
    AGENT_GUIDANCE_DIR.mkdir(parents=True, exist_ok=True)
    sentinel_data = json.dumps({
        "project_path": project_path,
        "version": __version__,
    })
    GATE_SENTINEL_PATH.write_text(sentinel_data, encoding="utf-8")


def _gate_sentinel_check() -> bool:
    if not GATE_SENTINEL_PATH.exists():
        return False
    try:
        import json
        data = json.loads(GATE_SENTINEL_PATH.read_text(encoding="utf-8"))
        return isinstance(data, dict) and "project_path" in data
    except (json.JSONDecodeError, OSError):
        return False


def _gate_sentinel_clear() -> None:
    try:
        GATE_SENTINEL_PATH.unlink(missing_ok=True)
    except OSError:
        pass


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

## Always-available tools (no gate)
- health_check
- diagnose
- token_stats

## How to proceed
1. Call `task_pipeline(task="describe what you want to do")`
2. Use any other tool as needed
"""


def priority_gate_check() -> dict[str, object] | None:
    """Return an error dict if the priority gate has not been passed, else None.

    Falls back to the sentinel file so a prior --session-start call (different
    process) is recognised as having already passed the gate.
    """
    global _priority_gate_passed
    with _priority_gate_lock:
        if not _priority_gate_passed:
            if _gate_sentinel_check():
                _priority_gate_passed = True
            else:
                return dict(PRIORITY_ERROR)
    return None


def priority_gate_pass() -> None:
    """Mark the priority gate as passed (called by task_pipeline)."""
    global _priority_gate_passed
    with _priority_gate_lock:
        _priority_gate_passed = True


def priority_gate_reset() -> None:
    """Reset the priority gate (for testing)."""
    global _priority_gate_passed
    with _priority_gate_lock:
        _priority_gate_passed = False


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
        import sys as _sys
        print(f"Warning: catalog build failed — {e}. Starting with empty catalog.", file=_sys.stderr)
        from .catalog import StandardsCatalog
        catalog = StandardsCatalog(Path(root or ".").resolve() if root else Path("."), [])

    # Auto-index project workspace on startup (watcher is optional & configurable)
    try:
        from .database import CodeGraphDatabase
        from .indexer import CodeGraphIndexer
        from .watcher import CodeGraphWatcher
        import threading

        project_root = Path(root or ".").resolve()
        db_path = project_root / ".agent-context" / "codegraph.db"
        db = CodeGraphDatabase(db_path)

        watcher_enabled = os.environ.get("AGENT_WATCHER_ENABLED", "true").strip().lower()

        def _run_initial_index_bg() -> None:
            try:
                indexer = CodeGraphIndexer(project_root, db)
                indexer.run()

                # File watcher is CPU-aware; disable via AGENT_WATCHER_ENABLED=false
                if watcher_enabled not in ("0", "false", "no", "off"):
                    watcher_interval_raw = os.environ.get("AGENT_WATCHER_INTERVAL")
                    watcher_kwargs: dict[str, object] = {}
                    if watcher_interval_raw:
                        try:
                            watcher_kwargs["interval_seconds"] = float(watcher_interval_raw)
                        except ValueError:
                            pass
                    watcher = CodeGraphWatcher(project_root, db, **watcher_kwargs)  # type: ignore[arg-type]
                    watcher.start()
            except Exception:
                pass

        threading.Thread(target=_run_initial_index_bg, daemon=True).start()
    except Exception:
        pass

    # Check for sentinel file from --session-start (cross-process gate persistence)
    if _gate_sentinel_check():
        _priority_gate_passed = True
        _gate_sentinel_clear()

    # Belt-and-suspenders: all logging must go to stderr so MCP stdio frames stay intact
    logging.basicConfig(level=logging.WARNING, stream=sys.stderr)

    mcp = FastMCP("Agent Guidance MCP", instructions=AGENT_INSTRUCTIONS, json_response=True)
    register_handlers(mcp, catalog)
    return mcp


def run_session_start(
    root: str | Path | None = None,
    project_path: str = ".",
    task: str | None = None,
    focus: str = "general",
) -> str:
    """Session-start auto-activation: passes priority gate and returns context.

    Called by the --session-start CLI flag from a session-start shell hook.
    Writes the sentinel file so the MCP server process inherits the passed gate.

    Returns a JSON string in the session-start hook protocol format:
    {"priority": "IMPORTANT", "message": "..."}
    """
    import json as _json

    try:
        from .catalog import build_catalog as _build_catalog
        catalog = _build_catalog(root)
    except Exception as exc:
        return _json.dumps({
            "priority": "INFO",
            "message": f"agent-guidance-mcp: catalog build failed — {exc}. Skills not available.",
        })

    config = load_config_from_env()
    tracker = TokenTracker(enabled=False)

    priority_gate_pass()
    _gate_sentinel_write(project_path)

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

    lines.append("Agent Guidance MCP tools are now available. Start with `task_pipeline` for any coding task.")

    return _json.dumps({
        "priority": "IMPORTANT",
        "message": "\n".join(lines),
    })


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
        return optimized

    @mcp.resource("agent-guidance-mcp://system/priority", mime_type="text/markdown")
    def priority_instructions() -> str:
        """Return priority gate instructions — read when PRIORITY_REQUIRED error is returned."""
        return PRIORITY_RESOURCE_CONTENT

    @mcp.tool()
    def task_pipeline(
        task: str,
        project_path: str = ".",
        focus: str = "general",
        code_query: str | None = None,
        include_tree: bool = True,
        include_ui: bool = True,
        limit: int = 8,
    ) -> dict[str, object]:
        """CALL FIRST before any coding task. Prepares recommendations, project tree,
        code search, and optional UI guidance in ONE optimized call. Use BEFORE
        codegraph, file reads, or implementation.

        Calling this tool passes the priority gate, enabling all other tools.

        Example: task_pipeline(task="Add JWT auth to Express API", focus="backend")

        Args:
            task: Description of the work to perform (required).
            project_path: Root of the project to scan (default ".").
            focus: Domain focus — "general", "frontend", or "backend" (default "general").
            code_query: Optional search override; auto-detected from task if omitted.
            include_tree: Include project directory tree in result (default True).
            include_ui: Attach UI/UX guidance when task signals UI intent (default True).
            limit: Maximum number of recommendations to return (default 8).
        """
        priority_gate_pass()
        return pipelines.task_pipeline(
            catalog=catalog,
            task=task,
            project_path=project_path,
            focus=focus,
            code_query=code_query,
            include_tree=include_tree,
            include_ui=include_ui,
            limit=limit,
            config=get_config(),
            tracker=get_tracker(),
        )

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
    ) -> dict[str, object] | list[dict[str, object]]:
        """Standards catalog and skill lookup. 168 skills available on-demand.

        Use guidance(operation='search') BEFORE implementing to find applicable
        coding standards, security rules, and skill workflows.
        Use guidance(operation='get', identifier='skill-name') to load a specific
        skill on-demand with its full content.
        Use guidance(operation='reason') for structured reasoning frameworks
        (decision, bug, architecture, security, performance).
        Use guidance(operation='docs') for live library/API documentation via Context7.

        Examples:
          guidance(operation="search", query="humanizer writing")
          guidance(operation="get", identifier="humanizer", include_content=True)
          guidance(operation="docs", query="jsonwebtoken sign", identifier="node-jsonwebtoken")

        Args:
            operation: One of list, get, search, recommend, reason, docs (required).
            query: Search/recommend/reason query string, or technical question for docs.
            identifier: Skill/document identifier for "get"; library/package name for
                "docs" (e.g. "react", "nextjs", "express").
            category: Filter entries by category.
            kind: Filter by kind — skill, doc, principle, etc.
            limit: Maximum results (default 10).
            include_content: Set True for "get" to include full skill body (default False).
            resolve_dependencies: Set True for "get" to recursively load transitive dependencies (default False).
        """
        gate = priority_gate_check()
        if gate:
            return gate
        return pipelines.guidance(
            catalog=catalog,
            operation=operation,
            query=query,
            identifier=identifier,
            category=category,
            kind=kind,
            limit=limit,
            include_content=include_content,
            resolve_dependencies=resolve_dependencies,
            config=get_config(),
            tracker=get_tracker(),
        )

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

        Examples:
          project_context(operation="read", relative_path="src/auth.js")
          project_context(operation="search", query="JWT middleware")

        Args:
            operation: One of tree, search, read, snapshot, symbols, references,
                structure, callers, callees, diff (required).
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
        gate = priority_gate_check()
        if gate:
            return gate
        return pipelines.project_context(
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
        gate = priority_gate_check()
        if gate:
            return gate
        return pipelines.ui_ux(
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
        gate = priority_gate_check()
        if gate:
            return gate
        from .session import save_session, load_session, clear_session
        from .project_scan import resolve_project_root

        try:
            validated_root = str(resolve_project_root(project_path))
        except Exception as e:
            return {"success": False, "error": f"Invalid project_path: {e}"}

        if operation == "save":
            if not task:
                return {"success": False, "error": "task is required for save operation"}
            data = save_session(
                project_path=validated_root,
                task=task,
                checklist=checklist or [],
                current_step_index=current_step_index,
                metadata=metadata
            )
            return {"success": True, "session": data}
        elif operation == "load":
            data = load_session(project_path=validated_root)
            if data:
                return {"success": True, "session_active": True, "session": data}
            return {"success": True, "session_active": False, "message": "No active session found."}
        elif operation == "clear":
            cleared = clear_session(project_path=validated_root)
            return {"success": cleared}
        else:
            return {"success": False, "error": f"Invalid operation: {operation}"}

    @mcp.tool()
    def token_stats() -> dict[str, object]:
        """Return token optimization statistics for this session. No parameters."""
        return get_tracker().summary()

    @mcp.tool()
    def health_check() -> dict[str, object]:
        """Return server health status and basic metadata. No parameters."""
        return {
            "status": "ok",
            "server": "agent-guidance-mcp",
            "version": __version__,
            "entries": catalog.manifest()["entry_count"],
        }

    @mcp.tool()
    def diagnose() -> dict[str, object]:
        """Perform comprehensive self-diagnostics on the server, tree-sitter capabilities, SQLite CodeGraph database, and Context7 network connectivity. No parameters."""
        from .diagnostics import run_diagnostics
        root_path = Path(catalog.root or ".").resolve()
        return run_diagnostics(root_path, catalog)


    @mcp.prompt()
    def workflow_prompt(mode: str = "plan", subject: str = "", target: str = "") -> str:
        """Load a workflow prompt by mode. Parameters: mode (str) — workflow mode key: init/plan/design/visualize/code/run/test/deploy/debug/refactor/audit/rollback/recap/review/next/help/readme/customize/brainstorm/save_brain (default 'plan'); subject (str) — optional subject to contextualize the prompt; target (str) — optional target description."""
        mode_key = mode.lower().replace("-", "_")
        if mode_key not in WORKFLOW_MODE_MAP:
            supported = ", ".join(sorted(WORKFLOW_MODE_MAP))
            return f"Unsupported workflow mode: {mode}. Supported modes: {supported}."

        config = get_config()
        try:
            raw_content = catalog.read_path(WORKFLOW_MODE_MAP[mode_key])
        except (FileNotFoundError, UnicodeDecodeError, PermissionError, IsADirectoryError, OSError) as exc:
            return (
                f"Workflow prompt '{mode}' could not be loaded: {exc}. "
                "Please verify your Agent Guidance installation."
            )
        if config.enabled:
            content = optimize_markdown(
                raw_content,
                max_tokens=config.workflow_max_tokens,
                config=config,
            )
        else:
            content = raw_content
        _record_savings("workflow_prompt", mode_key, raw_content, content)
        additions = []
        if subject:
            additions.append(f"Subject: {subject}")
        if target:
            additions.append(f"Target: {target}")
        if additions:
            return f"{content}\n\n" + "\n".join(additions)
        return content


def _record_savings(
    tool_name: str,
    operation: str,
    original: str,
    optimized: str,
) -> None:
    from .utils import record_savings
    record_savings(get_tracker(), tool_name, operation, original, optimized)

