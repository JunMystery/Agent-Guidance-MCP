---
name: agent-guidance
description: Core system standards check and token-optimized codebase context retrieval. Run this skill before performing any tool execution or codebase changes.
---

## When to use me
- Run this skill at the beginning of EVERY task, repository lookup, or codebase refactoring.
- Run this skill to check project conventions and avoid raw file reading/search operations.

## How to use me
You must invoke the `agent-guidance-mcp` tools in this priority order:
1. Call `task_pipeline(task="...")` at the start of any coding task to retrieve workspace context, tree, and recommendations.
2. Call `guidance(operation="search", query="...")` before implementing coding standards.
3. Call `project_context(operation="read", relative_path="...")` instead of standard file reads (capped at 300 lines).
4. Call `project_context(operation="search", query="...")` instead of standard file search.
