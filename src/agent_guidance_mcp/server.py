"""MCP registration for Agent Guidance MCP."""


from pathlib import Path
import threading
from typing import Any

from .catalog import StandardsCatalog, build_catalog
from . import pipelines
from . import project_context as project_context_helpers
from . import __version__
from .response_optimizer import TokenBudget, estimate_tokens, optimize_markdown
from .token_analytics import TokenTracker
from .token_config import TokenOptimizationConfig, load_config_from_env

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
    global _global_tracker
    with _config_lock:
        if _global_tracker is None:
            config = get_config()
            _global_tracker = TokenTracker(
                enabled=config.enabled and config.track_savings,
                max_records=config.tracker_max_records,
                trim_to=config.tracker_trim_to,
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
    catalog = build_catalog(root)
    mcp = FastMCP("Agent Guidance MCP", json_response=True)
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
        return optimized

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
        """Prepare task recommendations, project context, and optional UI guidance in one call. Parameters: task (str, required) — description of the work; project_path (str) — root of the project to scan; focus (str) — domain focus like 'general', 'frontend', 'backend'; code_query (str|None) — optional code search override; include_tree (bool) — include project directory tree; include_ui (bool) — attach UI/UX guidance when task signals UI intent; limit (int) — max recommendations (default 8)."""
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
    ) -> dict[str, object] | list[dict[str, object]]:
        """Grouped standards catalog operations: list (list entries), get (fetch by identifier with dependency resolution), search (query with ranking and snippets), recommend (task-context-aware). Parameters: operation (str, required) — one of list/get/search/recommend; query (str) — search/recommend query string; identifier (str) — entry identifier for get; category (str) — filter by category; kind (str) — filter by kind (skill/doc/principle/etc.); limit (int) — max results (default 10); include_content (bool) — include full body in get response (default False)."""
        return pipelines.guidance(
            catalog=catalog,
            operation=operation,
            query=query,
            identifier=identifier,
            category=category,
            kind=kind,
            limit=limit,
            include_content=include_content,
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
        """Grouped project context operations: tree (directory tree), search (grep file contents), read (read file by path with line range), snapshot (export project snapshot). Parameters: operation (str, required) — one of tree/search/read/snapshot; project_path (str) — root of the project; query (str) — search query for grep; relative_path (str) — file path for read; start_line (int) — line offset for read (default 1); max_lines (int) — max lines to read (default 300); max_depth (int) — directory tree depth (default 8); output_path (str) — snapshot output path; max_file_bytes (int) — per-file cap for snapshot; max_total_bytes (int) — total cap for snapshot; limit (int) — max search results (default 20)."""
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
        """Grouped UI/UX Pro Max operations: search (query guidance data by domain/stack), design_system (generate compact design system recommendation), slides (search slide strategy/layout/copy/chart). Parameters: operation (str, required) — one of search/design_system/slides; query (str, required) — search query; domain (str) — UI domain filter (style/color/chart/landing/product/ux/typography/icons/react/web); stack (str) — framework stack filter (react/nextjs/vue/svelte/astro/etc.); project_name (str) — project name for design_system; output_format (str) — markdown or ascii (default markdown); limit (int) — max results (default 3)."""
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

