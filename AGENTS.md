# AGENTS.md

## IMPORTANT — MCP Server Constraint (READ FIRST)

**Serena MCP is REMOVED.** Only ONE code-intelligence MCP can be active at a time.
The `agent-guidance-mcp` pipeline is the primary MCP. Do NOT re-add Serena alongside
it — running both MCPs simultaneously causes Serena's `initial_instructions` gate to
stall the session (it injects a "call initial_instructions first" CRITICAL instruction
while the `agent` context excludes that tool). Use agent-guidance-mcp as the single
source of truth for context/code search. If Serena is ever needed, disable
agent-guidance-mcp first (one at a time, never both).

## Token Saving — Built-in Optimization

agent-guidance-mcp saves tokens through 4 automatic mechanisms:

1. **Bounded reads** — `project_context(operation="read")` caps at 300 lines; `search` caps snippets at 300 chars and `limit` at 20 results. Replaces expensive raw file reads.
2. **Content compression** — Language-aware comment/whitespace removal, dedup, badge-stripping. Applies to every read/search response automatically.
3. **Per-type token budgets** — Source files 3K, docs 2K, skills 3K, task_pipeline 12K tokens max per call.
4. **Tracking & reporting** — Every optimized call records original vs. optimized tokens to SQLite. View with `token_stats` (session) or `usage_report(scope="all")` (lifetime).

**Config** (already set globally): `AGENT_GUIDANCE_FILTER_LEVEL=aggressive`, doc/skill caps reduced to 2K/3K — aggressive filtering by default.

**How to maximize savings:**
- Always use `task_pipeline` → `project_context`/`guidance` instead of raw tools (Rule 3).
- Call `token_stats` at end of each phase to verify compression ratio.
- If token usage is still high, set `AGENT_GUIDANCE_TOKEN_OPT=0` to disable (not recommended).

## CRITICAL — Tool Rules (READ FIRST)

For EVERY user interaction — planning, implementation, testing, debugging, reviewing, refactoring, or any other action:

<!-- agent-guidance:start -->
## Agent Guidance MCP — Tool Selection Priority

| You need to... | Use THIS tool first | Why |
|---|---|---|
| Start any task or phase | `task_pipeline(task="...")` | Recommendations + tree + code search + UI in ONE call |
| Check coding standards / skills | `guidance(operation="search", query="...")` | No other tool provides standards or skill lookup |
| Read a file | `project_context(operation="read", relative_path="...")` | Token-capped at 300 lines — prevents context blowout |
| Search codebase text | `project_context(operation="search", query="...")` | Ranked, bounded results. Fallback when codegraph unavailable |
| Understand code structure | `project_context(operation="structure", relative_path="...")` | Hierarchical view of classes, methods, functions in a file |
| Extract symbols | `project_context(operation="symbols", relative_path="...")` | Flat list of classes, functions, methods with signatures |
| Get structured workflow | `workflow(mode="plan")` → `"code"` → `"test"` | Enriched dev workflow with auto-chaining |
| Pre-code checklist | `precode_check(task="...")` | Coding conventions, security, testing, arch, deploy rules |
| Post-code verification | `verify(changes="...")` | Auto-detect test/review/security/audit/deploy; suggests next workflow |
| Skill feedback loop | `feedback(skill_id="...", rating=1-5)` | Rate skills to boost future recommendations for similar tasks |
| Find symbol references | `project_context(operation="references", query="...")` | Locate all usages of a symbol across the codebase |
| Get UI/design guidance | `ui_ux(operation="search", query="...")` | Style, colors, typography, charts, slides |
| Persist/recover session | `session_continuity(operation="save"/"load"/"clear")` | State recovery / task checklist continuity |
| Browse project tree | `project_context(operation="tree")` | Optimized directory tree view |

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
<!-- agent-guidance:end -->

10. NEVER call Subagents. They never works.