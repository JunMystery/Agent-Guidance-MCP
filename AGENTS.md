# AGENTS.md

## CRITICAL — Default Tool Rules (READ FIRST)

For EVERY coding action, repository lookup, refactoring, or planning:

### Tool Selection Priority

| You need to... | Use THIS tool first | Why |
|---|---|---|
| Start any coding task | `task_pipeline(task="...")` | Recommendations + tree + code search + UI in ONE call |
| Check coding standards | `guidance(operation="search", query="...")` | No other tool provides standards or skill lookup |
| Search library docs | `guidance(operation="docs", query="question", identifier="lib")` | Query live API documentation via Context7 |
| Read a file | `project_context(operation="read", relative_path="...")` | Token-capped at 300 lines — prevents context blowout |
| Search codebase text | `project_context(operation="search", query="...")` | Ranked, bounded results. Fallback when codegraph unavailable |
| Understand code structure | `project_context(operation="structure", relative_path="...")` | Hierarchical view of classes, methods, functions in a file |
| Extract symbols | `project_context(operation="symbols", relative_path="...")` | Flat list of classes, functions, methods with signatures |
| Find symbol references | `project_context(operation="references", query="...")` | Locate all usages of a symbol across the codebase |
| Find symbol callers | `project_context(operation="callers", query="symbol_id")` | Find all callers of a symbol in the index |
| Find symbol callees | `project_context(operation="callees", query="symbol_id")` | Find all callees of a symbol in the index |
| Get UI/design guidance | `ui_ux(operation="search", query="...")` | Style, colors, typography, charts, slides |
| Browse project structure | `project_context(operation="tree")` | Optimized directory tree view |

### Six Mandatory Rules

1. **Context First**: Call `task_pipeline` or `project_context` BEFORE any file read or code change.
2. **Standards Check**: Use `guidance(operation="search")` BEFORE implementing.
3. **Token Budget**: Prefer MCP tools over raw file reads — built-in limits prevent context blowout.
4. **No Direct FS**: Never manually read/search files when MCP tools do it with optimization.
5. **Ground & Plan**: Verify files/functions/symbols via search BEFORE proposing changes. Never guess.
6. **300 LOC Cap**: Split files exceeding 300 lines of code. No monolithic files.

**CRITICAL: All 6 rules apply to EVERY coding action without exception.**

---

## Custom MCP Integrations (Upstream & Maintenance)

Our custom MCP includes built-in semantic indexing (caching, AST symbol parsing, reference call edges) and Context7 library documentation lookup. For details on database schema, custom modules, and sync instructions for future upstream releases, see the [Mcp Integrations Guide](file:///e:/Github/Agent-Guidance-MCP/agent-guidance/mcp-integrations/README.md).

---

## Repository Overview

A collection of 168 skills sourced from [ECC v2.0.0](https://github.com/affaan-m/ECC) and community contributions, covering backend, frontend, testing, security, DevOps, data, research, and 12+ language ecosystems. Skills are packaged instructions that extend AI coding agents' capabilities through the MCP catalog.

## OpenCode Integration

OpenCode uses a **skill-driven execution model** powered by the `skill` tool and this repository's `/skills` directory.

### Core Rules

- If a task matches a skill, you MUST invoke it
- Skills are located in `skills/<skill-name>/SKILL.md`
- Never implement directly if a skill applies
- Always follow the skill instructions exactly (do not partially apply them)

### Intent → Skill Mapping

The agent should automatically map user intent to skills:

- Feature / new functionality → `spec-driven-development`, then `incremental-implementation`, `test-driven-development`
- Planning / breakdown → `planning-and-task-breakdown`
- Bug / failure / unexpected behavior → `debugging-and-error-recovery`
- Code review → `code-review-and-quality`
- Refactoring / simplification → `code-simplification`
- API or interface design → `api-and-interface-design`
- UI work → `frontend-ui-engineering`

### Lifecycle Mapping (Implicit Commands)

OpenCode does not support slash commands like `/spec` or `/plan`.

Instead, the agent must internally follow this lifecycle:

- DEFINE → `spec-driven-development`
- PLAN → `planning-and-task-breakdown`
- BUILD → `incremental-implementation` + `test-driven-development`
- VERIFY → `debugging-and-error-recovery`
- REVIEW → `code-review-and-quality`
- SHIP → `shipping-and-launch`

### Execution Model

For every request:

1. Determine if any skill applies (even 1% chance)
2. Invoke the appropriate skill using the `skill` tool
3. Follow the skill workflow strictly
4. Only proceed to implementation after required steps (spec, plan, etc.) are complete

### Anti-Rationalization

The following thoughts are incorrect and must be ignored:

- "This is too small for a skill"
- "I can just quickly implement this"
- "I’ll gather context first"

Correct behavior:

- Always check for and use skills first

This ensures OpenCode behaves similarly to Claude Code with full workflow enforcement.

## Orchestration: Personas, Skills, and Commands

This repo has three composable layers. They have different jobs and should not be confused:

- **Skills** (`skills/<name>/SKILL.md`) — workflows with steps and exit criteria. The *how*. Mandatory hops when an intent matches.
- **Personas** (`agents/<role>.md`) — roles with a perspective and an output format. The *who*.
- **Slash commands** (`.claude/commands/*.md`) — user-facing entry points. The *when*. The orchestration layer.

Composition rule: **the user (or a slash command) is the orchestrator. Personas do not invoke other personas.** A persona may invoke skills.

The only multi-persona orchestration pattern this repo endorses is **parallel fan-out with a merge step** — used by `/ship` to run `code-reviewer`, `security-auditor`, and `test-engineer` concurrently and synthesize their reports. Do not build a "router" persona that decides which other persona to call; that's the job of slash commands and intent mapping.

See [docs/agents.md](docs/agents.md) for the decision matrix and [references/orchestration-patterns.md](references/orchestration-patterns.md) for the full pattern catalog.

**Claude Code interop:** the personas in `agents/` work as Claude Code subagents (auto-discovered from this plugin's `agents/` directory) and as Agent Teams teammates (referenced by name when spawning). Two platform constraints align with our rules: subagents cannot spawn other subagents, and teams cannot nest. Plugin agents silently ignore the `hooks`, `mcpServers`, and `permissionMode` frontmatter fields.

## Creating a New Skill

### Directory Structure

```
skills/
  {skill-name}/           # kebab-case directory name
    SKILL.md              # Required: skill definition
    scripts/              # Required: executable scripts
      {script-name}.sh    # Bash scripts (preferred)
  {skill-name}.zip        # Required: packaged for distribution
```

### Naming Conventions

- **Skill directory**: `kebab-case` (e.g. `web-quality`)
- **SKILL.md**: Always uppercase, always this exact filename
- **Scripts**: `kebab-case.sh` (e.g., `deploy.sh`, `fetch-logs.sh`)
- **Zip file**: Must match directory name exactly: `{skill-name}.zip`

### SKILL.md Format

```markdown
---
name: {skill-name}
description: {One sentence describing what the skill does, followed by one or more "Use when" trigger conditions. Include trigger phrases like "Deploy my app" or "Check logs" when helpful.}
---

# {Skill Title}

{Brief overview of what the skill does and why it matters.}

## How It Works

{Numbered list explaining the skill's workflow}

Equivalent headings like `Workflow`, `Core Process`, or `When to Use` are fine when they communicate the same structure clearly.

## Usage (Optional)

Include this section only if the skill ships runnable helpers under `scripts/`. Markdown-only skills can omit both the section and the directory entirely.

```bash
bash /mnt/skills/user/{skill-name}/scripts/{script}.sh [args]
```

**Arguments:**
- `arg1` - Description (defaults to X)

**Examples:**
{Show 2-3 common usage patterns}

## Output

{Show example output users will see}

## Present Results to User

{Template for how Claude should format results when presenting to users}

## Troubleshooting

{Common issues and solutions, especially network/permissions errors}
```

### Best Practices for Context Efficiency

Skills are loaded on-demand — only the skill name and description are loaded at startup. The full `SKILL.md` loads into context only when the agent decides the skill is relevant. To minimize context usage:

- **Keep SKILL.md under 500 lines** — put detailed reference material in separate files
- **Write specific descriptions** — helps the agent know exactly when to activate the skill
- **Use progressive disclosure** — reference supporting files that get read only when needed
- **Prefer scripts over inline code** — script execution doesn't consume context (only output does)
- **File references work one level deep** — link directly from SKILL.md to supporting files

### Script Requirements

- Use `#!/bin/bash` shebang
- Use `set -e` for fail-fast behavior
- Write status messages to stderr: `echo "Message" >&2`
- Write machine-readable output (JSON) to stdout
- Include a cleanup trap for temp files
- Reference the script path as `/mnt/skills/user/{skill-name}/scripts/{script}.sh`

### Creating the Zip Package

After creating or updating a skill:

```bash
cd skills
zip -r {skill-name}.zip {skill-name}/
```

### End-User Installation

Document these two installation methods for users:

**Claude Code:**
```bash
cp -r skills/{skill-name} ~/.claude/skills/
```

**claude.ai:**
Add the skill to project knowledge or paste SKILL.md contents into the conversation.

If the skill requires network access, instruct users to add required domains at `claude.ai/settings/capabilities`.

## Agent Guidance MCP Server Tool Usage

Whenever the user prompts you to perform any coding action, repository lookup, refactoring, or planning, you MUST involve the custom `agent-guidance-mcp` server tools.

### Rules:
1. **Always Start with Context Gathering**: Before you read files or make changes, invoke `task_pipeline` or `project_context(operation="tree" / "search" / "read")` to load optimized project states.
2. **Consult Standards**: Use the `guidance` tool (with `operation="search"` or `operation="recommend"`) to check if any coding standard or instruction applies to the implementation.
3. **Minimize Tokens**: Ensure that you leverage the optimized output of the MCP server tools to run context-efficient development.
4. **Enforce Execution**: Never perform direct filesystem lookups or file reads manually if the corresponding context can be loaded and optimized through the MCP server tools.
5. **Grounding & Planning**: Always find related files, functions, and symbols (using `project_context(operation="search")` or `task_pipeline`) and formulate an implementation plan before proposing changes. Even if the user prompt does not mention specific files/code directly, or references a function name without its location, AI Agents MUST NOT guess anything; they must verify via search first.
6. **Max 300 LOC Files**: Keep code files focused and split them when they exceed 300 lines of code (LOC). Avoid monolithic files and dumping grounds.

**CRITICAL**: All 6 rules MUST be evaluated and executed for every single coding action, repository lookup, refactoring, or planning phase without exception.


<!-- headroom:rtk-instructions -->
# RTK (Rust Token Killer) - Token-Optimized Commands

When running shell commands, **always prefix with `rtk`**. This reduces context
usage by 60-90% with zero behavior change. If rtk has no filter for a command,
it passes through unchanged — so it is always safe to use.

## Key Commands
```bash
# Git (59-80% savings)
rtk git status          rtk git diff            rtk git log

# Files & Search (60-75% savings)
rtk ls <path>           rtk read <file>         rtk grep <pattern>
rtk find <pattern>      rtk diff <file>

# Test (90-99% savings) — shows failures only
rtk pytest tests/       rtk cargo test          rtk test <cmd>

# Build & Lint (80-90% savings) — shows errors only
rtk tsc                 rtk lint                rtk cargo build
rtk prettier --check    rtk mypy                rtk ruff check

# Analysis (70-90% savings)
rtk err <cmd>           rtk log <file>          rtk json <file>
rtk summary <cmd>       rtk deps                rtk env

# GitHub (26-87% savings)
rtk gh pr view <n>      rtk gh run list         rtk gh issue list

# Infrastructure (85% savings)
rtk docker ps           rtk kubectl get         rtk docker logs <c>

# Package managers (70-90% savings)
rtk pip list            rtk pnpm install        rtk npm run <script>
```

## Rules
- In command chains, prefix each segment: `rtk git add . && rtk git commit -m "msg"`
- For debugging, use raw command without rtk prefix
- `rtk proxy <cmd>` runs command without filtering but tracks usage
<!-- /headroom:rtk-instructions -->

## Maintenance Commands

When asked to update skills, refresh the MCP, or pull the latest from upstream repositories,
run the orchestrator:

| User says | Run this |
|---|---|
| "update MCP tools", "refresh skills", "update everything" | `python scripts/update_all.py` |
| "update ECC skills" | `python scripts/update_ecc.py` |
| "update UI/UX data" | `python scripts/update_ui_ux.py` |
| "update RTK" | `python scripts/update_rtk.py` |

The orchestrator (`update_all.py`) runs all three updaters in sequence and prints a pass/fail summary. Each updater downloads the latest snapshot from its upstream GitHub repo, strips non-essential files, and deploys the minimal vendored copy.

