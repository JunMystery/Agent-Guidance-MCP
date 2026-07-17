# Agent Guidance MCP — Full Gap-to-Fix Plan

## Gap 1 — Proactive Skill Injection

**Problem**: Skills only return when user explicitly calls `task_pipeline` or `guidance`. The gate returns a terse `PRIORITY_REQUIRED` error on first uncalled tool — unhelpful.

**Fix**: Smart gate — instead of return blocking error, auto-run lightweight context enrichment:

1. On any gated tool's first call: auto-call a **minimal `task_pipeline`** with a task derived from tool name + parameters (e.g., `guidance(search="JWT")` → task="JWT authentication")
2. Prepend the enriched context (essential skills + framework detection) to the tool result
3. Pass the gate only after this auto-context cycle

**Changes needed**:
| File | What |
|---|---|
| `server.py` gate logic | Replace `PRIORITY_REQUIRED` with `_auto_context(catalog, tool_name, params)` → returns enriched response instead of error |
| `pipelines.py` | New `auto_context()` function — lightweight version of `task_pipeline` that does framework detection + 3 essential skills only (no tree/code search, no UI/UX) |
| `pipeline_helpers.py` | Export `_detect_frameworks()` as public (currently private) |

---

## Gap 2 — Workflow Prompts → Active Tools

**Problem**: `workflow_prompt` is `@mcp.prompt()` (passive resource). The agent must fetch it explicitly. No tool exists to actively guide the developer through a structured cycle.

**Fix**: Add a `workflow` MCP **tool** that:
1. Takes `mode`, `subject`, `target` — same params as the prompt
2. Returns the workflow instructions as tool result
3. Auto-enriches with relevant skills for that mode
4. Suggests the next mode (e.g., `code` → suggest `test` next)

**Changes needed**:
| File | What |
|---|---|
| `server.py` | Add `@mcp.tool()` for `workflow(mode, subject, target)` |
| `pipelines.py` | New `workflow_mode()` handler — reads markdown, enriches with skills, chains next mode |
| `pipeline_helpers.py` | New `next_workflow_mode(mode) -> str` — maps `code→test`, `test→review`, etc. |

---

## Gap 3 — Pre-code Checklist

**Problem**: No structured check before writing code — coding standards, security rules, and project conventions aren't checked.

**Fix**: Add a `precode` tool that returns a checklist before code writing begins:

1. Takes task description + optional file paths
2. Fetches relevant coding standards from `catalog.search_entries()`
3. Returns checklist: language-specific rules, security constraints, test requirements

**Changes needed**:
| File | What |
|---|---|
| `server.py` | Add `@mcp.tool()` for `precode_check(task, paths?)` |
| `pipelines.py` | New `precode_check()` handler — query catalog for coding standards + framework-specific rules |
| `usage.py` | (optional) Track precode runs for analytics |

---

## Gap 4 — Post-code Verification Chain

**Problem**: After code is written, no automated verification step. Testing patterns, security review, linting rules aren't presented.

**Fix**: Add a `verify` tool that chains the appropriate verification mode based on what was done:

1. Takes changed file paths + description of changes
2. Auto-selects verification type: test | security | review | audit
3. Loads relevant testing/security patterns from catalog
4. Returns structured verification steps

**Changes needed**:
| File | What |
|---|---|
| `server.py` | Add `@mcp.tool()` for `verify(changes, kind?)` |
| `pipelines.py` | New `verify()` handler — match changes to verification mode, load patterns |
| `pipeline_helpers.py` | New `infer_verification_kind(changes, kind?)` |

---

## Gap 5 — Pattern Learning

**Problem**: `session_continuity` saves/loads state but doesn't analyze past sessions. No feedback loop to improve recommendations.

**Fix**: Add a lightweight feedback + learning mechanism:

1. New `feedback(skill_id, rating)` tool — users rate skill relevance (1-5)
2. New `skill_feedback` table in `usage.db`
3. In `recommend_context()`, boost skills with high historical ratings for similar task keywords

**Changes needed**:
| File | What |
|---|---|
| `usage.py` | New `skill_feedback` table + `record_feedback()` method |
| `server.py` | New `@mcp.tool()` for `feedback(skill_id, rating, task?)` |
| `catalog.py` | In `recommend_context()`, query `get_usage().get_top_skills(task_keywords)` and boost results |
| `dashboard_src` | (optional) Show feedback data in dashboard |

---

## Gap 6 — Code Generation Scaffolding

**Problem**: No standardized code generation pipeline. Developer says "add JWT auth" and must manually figure out the implementation plan.

**Fix**: Enhance `task_pipeline` with explicit code-generation scaffolding:

1. When the task implies code creation, `task_pipeline` auto-includes a `codegen_plan` section:
   - Files to create/modify
   - Patterns/libraries to use
   - Implementation order
   - Relevant skill snippets embedded in the plan
2. New `codegen_plan` field in `task_pipeline` response

**Changes needed**:
| File | What |
|---|---|
| `pipeline_helpers.py` | New `infer_codegen_plan(task, frameworks, skills)` — build implementation plan from task + detected stack + matched skills |
| `pipelines.py` | In `task_pipeline()`, call `infer_codegen_plan()` when task signals code intent; add `codegen_plan` to response |

---

## Priority & Effort

| Gap | Effort | Impact | Phase |
|---|---|---|---|
| **2** — workflow tool | ~small (40 lines) | High | 1 |
| **1** — smart gate | ~small (60 lines) | High | 1 |
| **3** — precode check | ~medium (80 lines) | Medium | 2 |
| **4** — verify chain | ~medium (100 lines) | Medium | 2 |
| **6** — codegen plan | ~medium (120 lines) | Medium | 3 |
| **5** — pattern learning | ~large (200+ lines) | Low | 4 |

## Execution order

1. **Phase 1**: Smart gate (G1) + workflow tool (G2) — big impact, small code
2. **Phase 2**: Precode check (G3) + verify chain (G4) — closing the dev loop
3. **Phase 3**: Codegen scaffolding (G6) — making `task_pipeline` produce plans
4. **Phase 4**: Pattern learning (G5) — feedback loop, only if usage warrants

---

## Status

| Gap | Phase | Status |
|---|---|---|
| G1 — smart gate | 1 | ✅ Done |
| G2 — workflow tool | 1 | ✅ Done |
| G3 — precode check | 2 | ✅ Done |
| G4 — verify chain | 2 | ✅ Done |
| G5 — pattern learning | 4 | ✅ Done |
| G6 — codegen scaffolding | 3 | ✅ Done |
