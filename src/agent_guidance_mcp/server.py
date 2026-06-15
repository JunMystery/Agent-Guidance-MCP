"""MCP registration for Agent Guidance MCP."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from .catalog import StandardsCatalog, build_catalog
from . import pipelines

try:
    from mcp.server.fastmcp import FastMCP
except ImportError as exc:  # pragma: no cover - exercised only without optional runtime dependency.
    FastMCP = None  # type: ignore[assignment]
    MCP_IMPORT_ERROR = exc
else:
    MCP_IMPORT_ERROR = None


def create_server(
    root: str | Path | None = None,
) -> Any:
    if FastMCP is None:
        raise RuntimeError(
            "The 'mcp' package is required to run the server. Install with "
            "'pip install -e .', or 'pip install mcp'."
        ) from MCP_IMPORT_ERROR

    catalog = build_catalog(root)
    mcp = FastMCP("Agent Guidance MCP", json_response=True)
    register_handlers(mcp, catalog)
    return mcp


def register_handlers(mcp: Any, catalog: StandardsCatalog) -> None:
    @mcp.resource("standards://manifest", mime_type="application/json")
    def manifest() -> str:
        """Return the indexed standards manifest."""
        return catalog.manifest_json()

    @mcp.resource("standards://document/{identifier}", mime_type="text/markdown")
    def document(identifier: str) -> str:
        """Return a standards document by slug."""
        return catalog.read_entry(identifier)

    @mcp.resource("standards://skill/{name}", mime_type="text/markdown")
    def skill(name: str) -> str:
        """Return a local on-demand skill capsule by name."""
        return catalog.read_entry(name)

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
        """Prepare task recommendations, project context, and optional UI guidance in one call."""
        return pipelines.task_pipeline(
            catalog=catalog,
            task=task,
            project_path=project_path,
            focus=focus,
            code_query=code_query,
            include_tree=include_tree,
            include_ui=include_ui,
            limit=limit,
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
        """Grouped standards catalog operations: list, get, search, recommend."""
        return pipelines.guidance(
            catalog=catalog,
            operation=operation,
            query=query,
            identifier=identifier,
            category=category,
            kind=kind,
            limit=limit,
            include_content=include_content,
        )

    @mcp.tool()
    def project_context(
        operation: str,
        project_path: str = ".",
        query: str | None = None,
        relative_path: str | None = None,
        start_line: int = 1,
        max_lines: int = 300,
        max_depth: int = 3,
        output_path: str = ".agent-context/code-snapshot.json",
        max_file_bytes: int = 200000,
        max_total_bytes: int = 2000000,
        limit: int = 20,
    ) -> dict[str, object]:
        """Grouped project context operations: tree, search, read, snapshot."""
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
        """Grouped UI/UX Pro Max operations: search, design_system, slides."""
        return pipelines.ui_ux(
            catalog=catalog,
            operation=operation,
            query=query,
            domain=domain,
            stack=stack,
            project_name=project_name,
            output_format=output_format,
            limit=limit,
        )

    @mcp.prompt()
    def workflow_prompt(mode: str = "plan", subject: str = "", target: str = "") -> str:
        """Load a workflow prompt by mode."""
        workflow_references = {
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
        mode_key = mode.lower().replace("-", "_")
        if mode_key not in workflow_references:
            supported = ", ".join(sorted(workflow_references))
            return f"Unsupported workflow mode: {mode}. Supported modes: {supported}."

        content = catalog.read_path(workflow_references[mode_key])
        additions = []
        if subject:
            additions.append(f"Subject: {subject}")
        if target:
            additions.append(f"Target: {target}")
        if additions:
            return f"{content}\n\n" + "\n".join(additions)
        return content
