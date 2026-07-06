# AGENTS.md

## CRITICAL — Default Tool Rules (READ FIRST)

For EVERY coding action, repository lookup, refactoring, or planning:

### Tool Selection Priority

| You need to... | Use THIS tool first | Why |
|---|---|---|
| Resume work / check state | `session_continuity(operation="load")` | Recovers task checklists and debounces interruption state |
| Check project setup | `project_context(operation="tree", max_depth=1)` | Identifies if folder is new/fresh or has existing code |
| Start any coding task | `task_pipeline(task="...")` | Recommendations + tree + code search + UI in ONE call |
| Check coding standards | `guidance(operation="search", query="...")` | No other tool provides standards or skill lookup |
| Read a file | `project_context(operation="read", relative_path="...")` | Token-capped at 300 lines — prevents context blowout |
| Search codebase text | `project_context(operation="search", query="...")` | Ranked, bounded results |
| Extract symbols | `project_context(operation="symbols", relative_path="...")` | Classes, functions, methods with signatures |
| Find references / callers | `project_context(operation="references", query="...")` | Locate all usages of a symbol before refactoring |
| Diagnose build/test error | `project_context(operation="diff")` | Inspects recent changes that could have caused the error |
| Get UI/design guidance | `ui_ux(operation="search", query="...")` | Style, colors, typography, charts |
| Get live library docs | `guidance(operation="docs", query="...", identifier="lib")` | Query API docs via Context7 |
| Complete a task session | `session_continuity(operation="clear")` | Clears checklist so future tasks start clean |

### Six Mandatory Rules

1. **Context First**: Call `task_pipeline` or `project_context` BEFORE any file read or code change.
2. **Standards Check**: Use `guidance(operation="search")` BEFORE implementing.
3. **Token Budget**: Prefer MCP tools over raw file reads — built-in limits prevent context blowout.
4. **No Direct FS**: Never manually read/search files when MCP tools do it with optimization.
5. **Ground & Plan**: Verify files/functions/symbols via search BEFORE proposing changes. Never guess.
6. **300 LOC Cap**: Split files exceeding 300 lines of code. No monolithic files.

**CRITICAL: All 6 rules apply to EVERY coding action without exception.**

---

## Skills & Personas

168 skills in `/skills/`. For skill workflows, lifecycle mapping, and persona orchestration patterns, use:

```
guidance(operation="search", query="<your task domain>")
guidance(operation="recommend", query="<your task description>")
```

Skills load on-demand via `guidance(operation="get")` — never load all at once.

---

<!-- headroom:rtk-instructions -->
# RTK (Rust Token Killer) - Token-Optimized Commands

When running shell commands, **always prefix with `rtk`**. This reduces context
usage by 60-90% with zero behavior change. If rtk has no filter for a command,
it passes through unchanged — so it is always safe to use.
<!-- /headroom:rtk-instructions -->

## Agent Guidance MCP — Tool Selection Priority

| You need to... | Use THIS tool first | Why |
|---|---|---|
| Resume work / check state | `session_continuity(operation="load")` | Recovers task checklists and debounces interruption state |
| Check project setup | `project_context(operation="tree", max_depth=1)` | Identifies if folder is new/fresh or has existing code |
| Start any coding task | `task_pipeline(task="...")` | Recommendations + tree + code search + UI in ONE call |
| Check coding standards | `guidance(operation="search", query="...")` | No other tool provides standards or skill lookup |
| Read a file | `project_context(operation="read", relative_path="...")` | Token-capped at 300 lines — prevents context blowout |
| Search codebase text | `project_context(operation="search", query="...")` | Ranked, bounded results. Fallback when codegraph unavailable |
| Understand code structure | `project_context(operation="structure", relative_path="...")` | Hierarchical view of classes, methods, functions in a file |
| Extract symbols | `project_context(operation="symbols", relative_path="...")` | Flat list of classes, functions, methods with signatures |
| Find references / callers | `project_context(operation="references", query="...")` | Locate all usages of a symbol before refactoring |
| Diagnose build/test error | `project_context(operation="diff")` | Inspects recent changes that could have caused the error |
| Get UI/design guidance | `ui_ux(operation="search", query="...")` | Style, colors, typography, charts, slides |
| Persist/recover session | `session_continuity(operation="save"/"load"/"clear")` | State recovery / task checklist continuity |
| Browse project tree | `project_context(operation="tree")` | Optimized directory tree view |
| Complete a task session | `session_continuity(operation="clear")` | Clears checklist so future tasks start clean |

### Six Mandatory Rules

1. **Context First**: Call `task_pipeline` or `project_context` BEFORE any file read or code change.
2. **Standards Check**: Use `guidance(operation="search")` BEFORE implementing.
3. **Token Budget**: Prefer MCP tools over raw file reads — built-in limits prevent context blowout.
4. **No Direct FS**: Never manually read/search files when MCP tools do it with optimization.
5. **Ground & Plan**: Verify files/functions/symbols via search BEFORE proposing changes. Never guess.
6. **300 LOC Cap**: Split files exceeding 300 lines of code. No monolithic files.

**CRITICAL: All 6 rules apply to EVERY coding action without exception.**
