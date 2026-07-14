# AGENTS.md

## CRITICAL — Tool Rules (READ FIRST)

For EVERY user interaction — planning, implementation, testing, debugging, reviewing, refactoring, or any other action:

### Tool Selection Priority

| You need to... | Use THIS tool first | Why |
|---|---|---|
| Start any task or phase | `task_pipeline(task="...")` | Recommendations + tree + code search + UI in ONE call |
| Check coding standards / skills | `guidance(operation="search", query="...")` | No other tool provides standards or skill lookup |
| Read a file | `project_context(operation="read", relative_path="...")` | Token-capped at 300 lines — prevents context blowout |
| Search codebase text | `project_context(operation="search", query="...")` | Ranked, bounded results. Fallback when codegraph unavailable |
| Understand code structure | `project_context(operation="structure", relative_path="...")` | Hierarchical view of classes, methods, functions in a file |
| Extract symbols | `project_context(operation="symbols", relative_path="...")` | Flat list of classes, functions, methods with signatures |
| Find symbol references | `project_context(operation="references", query="...")` | Locate all usages of a symbol across the codebase |
| Get UI/design guidance | `ui_ux(operation="search", query="...")` | Style, colors, typography, charts, slides |
| Persist/recover session | `session_continuity(operation="save"/"load"/"clear")` | State recovery / task checklist continuity |
| Browse project tree | `project_context(operation="tree")` | Optimized directory tree view |
| Diagnose build/test error | `project_context(operation="diff")` | Inspects recent changes that could have caused the error |
| Resume work / check state | `session_continuity(operation="load")` | Recovers task checklists and debounces interruption state |
| Get live library docs | `guidance(operation="docs", query="...", identifier="lib")` | Query API docs via Context7 |

### Nine Mandatory Rules

1. **Context First**: Call `task_pipeline` or `project_context` BEFORE any file read or code change.
2. **Standards Check**: Use `guidance(operation="search")` BEFORE implementing or answering any prompt.
3. **Token Budget**: Prefer MCP tools over raw file reads — built-in limits prevent context blowout.
4. **No Direct FS**: Never manually read/search files when MCP tools do it with optimization.
5. **Ground & Plan**: Verify files/functions/symbols via search BEFORE proposing changes. Never guess.
6. **300 LOC Cap**: Split files exceeding 300 lines of code. No monolithic files.
7. **Intent Gate**: Classify request type (trivial/explicit/exploratory/open-ended/ambiguous) before acting. If ambiguous, clarify first.
8. **Delegation Before Action**: Decompose multi-step tasks and delegate to specialized subagents. Never implement directly when delegation is possible.
9. **Per-Phase Reset**: For EACH new work phase (plan → implement → test → debug → review → refactor), re-call `task_pipeline` with that phase's goal. Do NOT carry old context across phases. A new phase is a new task.

**CRITICAL: All 9 rules apply to EVERY action without exception — planning, implementation, testing, debugging, reviewing, refactoring, or any other work. There is no action type exempt from these rules.**

---

## Skills & Personas

168 skills in `/skills/`. For skill workflows, lifecycle mapping, and persona orchestration patterns, use:

```
guidance(operation="search", query="<your task domain>")
guidance(operation="recommend", query="<your task description>")
```

Skills load on-demand via `guidance(operation="get")` — never load all at once.
