# Skill Reference - Quick Lookup

**Which files to reference for each type of task.**

Copy the `@file` references into your prompt to activate the relevant skills.
This repository uses agent-specific Markdown instruction files, not a shared skill layer.

---

## Everyday Coding (no extra reference needed)

Your AI agent **already loaded** the 6 Core Principles from the root instruction file (`CLAUDE.md`, `GEMINI.md`, etc.). Just describe your task normally.

*(Note: If you have project-specific rules, add them to `PROJECT-STANDARDS.md`. The AI will automatically read it.)*

---

##  Dynamic Skill Auto-Discovery

Modern AI agents (Cursor, Windsurf, Claude Code, Gemini with tools) are now equipped with **Auto-Discovery**. If your prompt mentions keywords like "Write tests", "Fix accessibility", or "Check security", the AI will *autonomously* read the relevant standard files below without you needing to manually `@reference` them.

Manual `@reference` is only required if you are using a standard web chatbot (without file-reading tools) or if you want to strictly force the AI to read a specific cookbook.

The root instruction file for each agent should still be the primary entrypoint; these references are task-specific additions, not a shared instruction surface.

## Local Skills Implemented Here

The following on-demand skill capsules are available in [skills/](./skills/). Load a hub first, then load deep skills only as needed. See [Skill Grouping Audit](./docs/skill-grouping-audit.md) for the current grouping map.

- [coding-standards](./skills/coding-standards/SKILL.md)
- [frontend-hub](./skills/frontend-hub/SKILL.md)
- [testing-hub](./skills/testing-hub/SKILL.md)
- [security-hub](./skills/security-hub/SKILL.md)
- [docs-research-hub](./skills/docs-research-hub/SKILL.md)
- [workflow-hub](./skills/workflow-hub/SKILL.md)
- [backend-hub](./skills/backend-hub/SKILL.md)
- [tdd-workflow](./skills/tdd-workflow/SKILL.md)
- [verification-loop](./skills/verification-loop/SKILL.md)
- [security-review](./skills/security-review/SKILL.md)
- [codebase-onboarding](./skills/codebase-onboarding/SKILL.md)
- [context-budget](./skills/context-budget/SKILL.md)
- [documentation-lookup](./skills/documentation-lookup/SKILL.md)
- [browser-qa](./skills/browser-qa/SKILL.md)
- [prompt-optimizer](./skills/prompt-optimizer/SKILL.md)
- [skill-scout](./skills/skill-scout/SKILL.md)
- [ui-ux-pro-max](./skills/ui-ux-pro-max/SKILL.md)
- [codex-vscode](./skills/codex-vscode/SKILL.md)
- [large-file-refactor](./skills/large-file-refactor/SKILL.md)
- [accessibility](./skills/accessibility/SKILL.md)
- [api-design](./skills/api-design/SKILL.md)
- [architecture-decision-records](./skills/architecture-decision-records/SKILL.md)
- [database-migrations](./skills/database-migrations/SKILL.md)
- [error-handling](./skills/error-handling/SKILL.md)
- [git-workflow](./skills/git-workflow/SKILL.md)
- [production-audit](./skills/production-audit/SKILL.md)
- [search-first](./skills/search-first/SKILL.md)
- [skill-stocktake](./skills/skill-stocktake/SKILL.md)
- [rules-distill](./skills/rules-distill/SKILL.md)

---

## By Task Type

### Security-Sensitive Code
> Auth, payments, encryption, user data, API keys

```
@skills/security-hub/SKILL.md
```

### RAG / AI Pipeline
> Vector DB retrieval, LLM generation, embeddings

```
@agent-guidance/prompts/sample-use-cases/rag-implementation-cookbook.md
```

### Writing a Complex Prompt
> Multi-step tasks, strict constraints, specific output format

```
@agent-guidance/prompts/PROMPT-TEMPLATE.md
```

### Code Review / Audit
> Reviewing AI-generated code before merge

```
@agent-guidance/quality-control/audit-ai-code-full.md
@agent-guidance/quality-control/code-review-checklist.md
@skills/workflow-hub/SKILL.md
```

### Large File Refactor
> Splitting large files, reducing monolithic modules, extracting React hooks/components, or bringing files closer to the 300 LOC guideline

```
@skills/large-file-refactor/SKILL.md
```

### Detecting Hallucinations
> AI imports fake libraries, calls non-existent APIs

```
@agent-guidance/quality-control/hallucination-detection.md
```

### Database Migrations
> Schema changes, data migration, rollback strategy

```
@skills/backend-hub/SKILL.md
```

### Caching & Performance
> Redis, cache invalidation, query optimization

```
@skills/backend-hub/SKILL.md
```

### Unit Test Generation
> Writing tests for existing or new code

```
@skills/testing-hub/SKILL.md
```

### Security Audit
> Scanning for vulnerabilities in existing code

```
@skills/security-hub/SKILL.md
```

### API Development
> REST endpoints, rate limiting, authentication

```
@skills/backend-hub/SKILL.md
```

### Mobile Development
> Android, iOS, Flutter, React Native - lifecycle, permissions, offline

```
@agent-guidance/prompts/sample-use-cases/mobile-development-cookbook.md
```

### Documentation & Changelogs
> Writing README, API Specs, Docstrings, or Changelogs

```
@skills/docs-research-hub/SKILL.md
```

### Release & Branching Strategy
> Bumping versions (SemVer), Gitflow, or pre-release checks

```
@skills/workflow-hub/SKILL.md
```

### Testing Strategy & TDD
> Setting up test pyramids, coverage bounds, or adhering to FIRST principles

```
@skills/testing-hub/SKILL.md
```

### Performance & DB Optimization
> Caching strategy, N+1 queries, concurrency, response time budgets

```
@skills/backend-hub/SKILL.md
```

### Industry Compliance
> OWASP, NIST, or CISA alignment checks

```
@agent-guidance/compliance/COMPLIANCE.md
```

### UI Accessibility (A11Y)
> Reviewing HTML/React for WCAG 2.1 AA, ARIA, and Keyboard Navigation

```
@skills/frontend-hub/SKILL.md
```

### UI/UX, Frontend Design, Dashboards, Landing Pages, Slides
> Visual design, component styling, product-specific UX, design systems, brand assets, and slide/presentation UI

```
@skills/frontend-hub/SKILL.md
@skills/ui-ux-pro-max/SKILL.md
```

Use this as the single public UI/UX Pro Max entrypoint. Banner, brand, slides,
UI styling, and imported design-system references are internal files under
`skills/ui-ux-pro-max/` and should be loaded only as needed.

---

## Multi-Agent Setup

Assign the appropriate file as system instructions for each agent:

| Agent | File to load |
|-------|-------------|
| Coder | `@agent-guidance/multi-agent/coder-agent.md` |
| Test | `@agent-guidance/multi-agent/test-agent.md` |
| Reviewer | `@agent-guidance/multi-agent/reviewer-agent.md` |
| Documentation | `@agent-guidance/multi-agent/documentation-agent.md` |

---

## Combining References

For complex tasks, combine multiple references:

```
# Example: Build a secure API with tests

@agent-guidance/risk-management/security-constraints.md
@agent-guidance/prompts/sample-use-cases/create-api-with-rate-limiting.md
@agent-guidance/prompts/PROMPT-TEMPLATE.md

Build POST /api/v1/register with email validation,
bcrypt password hashing, and JWT response.
Include unit tests and Self-Check report.
```

---

## Verify Agent Skills

At any time, ask your agent:

> **"What coding standards are you following?"** or type **`/standards`**

Expected:
> [OK] AI-Coding-Standards with 6 Core Principles active.
