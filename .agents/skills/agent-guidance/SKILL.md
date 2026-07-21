---
name: agent-guidance
description: Core system standards check and token-optimized codebase context retrieval. Run this skill before performing any tool execution or codebase changes.
---

## When to use me
- Run this skill at the beginning of EVERY task, repository lookup, or codebase refactoring.
- Run this skill to check project conventions and avoid raw file reading/search operations.

## How to use me
You must invoke the `agent-guidance-mcp` tools in this priority order:
1. Call `agent-guidance-mcp_task_pipeline(task="...")` at the start of any coding task to retrieve workspace context, tree, and recommendations.
2. Call `agent-guidance-mcp_guidance(operation="search", query="...")` before implementing coding standards.
3. Call `agent-guidance-mcp_project_context(operation="read", relative_path="...")` instead of standard file reads (capped at 300 lines).
4. Call `agent-guidance-mcp_project_context(operation="search", query="...")` instead of standard file search.
<!-- agent-guidance-skill:start -->
---
name: agent-guidance
description: Core system standards check and token-optimized codebase context retrieval. Run this skill before performing any tool execution or codebase changes.
---

## When to use me
- Run this skill at the beginning of EVERY task, repository lookup, or codebase refactoring.
- Run this skill to check project conventions and avoid raw file reading/search operations.
- Re-run this skill at EACH phase transition (plan → implement → test → review).

## How to use me
You must invoke the `agent-guidance-mcp` tools in this priority order:
1. Call `agent-guidance-mcp_task_pipeline(task="...")` at the start of any task or phase to retrieve workspace context, tree, and recommendations.
2. Call `agent-guidance-mcp_guidance(operation="search", query="...")` before implementing coding standards.
3. Call `agent-guidance-mcp_project_context(operation="read", relative_path="...")` instead of standard file reads (capped at 300 lines).
4. Call `agent-guidance-mcp_project_context(operation="search", query="...")` instead of standard file search.

## Critical Behavioral Rules
- When unsure about anything, ASK! DO NOT GUESS.
- Propose an implementation plan before making any big or complex changes.
- For each new work phase, re-call `agent-guidance-mcp_task_pipeline` with the phase goal. Do not carry old context.
<!-- agent-guidance-skill:end -->

<!-- agent-guidance:start -->
---
name: agent-guidance
description: Core system standards check and token-optimized codebase context retrieval. Run this skill before performing any tool execution or codebase changes.
---

## When to use me
- Run this skill at the beginning of EVERY task, repository lookup, or codebase refactoring.
- Run this skill to check project conventions and avoid raw file reading/search operations.

## How to use me
You must invoke the `agent-guidance-mcp` tools in this priority order:
1. Call `agent-guidance-mcp_task_pipeline(task="...")` at the start of any coding task to retrieve workspace context, tree, and recommendations.
2. Call `agent-guidance-mcp_guidance(operation="search", query="...")` before implementing coding standards.
3. Call `agent-guidance-mcp_project_context(operation="read", relative_path="...")` instead of standard file reads (capped at 300 lines).
4. Call `agent-guidance-mcp_project_context(operation="search", query="...")` instead of standard file search.
5. Use `agent-guidance-mcp_guidance(operation="workflow", identifier="<mode>")` for dev workflow modes (plan/test/deploy).
6. Use `agent-guidance-mcp_guidance(operation="precode", query="<task>")` for pre-code checklists.
7. Use `agent-guidance-mcp_guidance(operation="verify", query="<changes>")` for post-change verification.
8. Use `agent-guidance-mcp_guidance(operation="feedback", identifier="<id>", rating=1-5)` to rate skills and improve recommendations.

<!-- agent-guidance:end -->
