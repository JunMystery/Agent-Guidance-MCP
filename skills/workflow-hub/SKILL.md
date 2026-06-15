---
name: workflow-hub
description: Use for workflow modes, orchestration, planning, multi-agent coordination, context/session recovery, parallel execution, team building, rollback, recap, review, and pipeline design.
---

# Workflow Hub

Use this as the first workflow skill call. Load only the focused skill(s) needed for the task:

- Mode prompts: `workflow-modes`
- Orchestration: `orchestration-pipeline`
- Agentic and autonomous workflows: `agent-workflow-ops`
- Session/context continuity: `session-context-ops`
- Planning and execution strategy: `intent-driven-development`
- Team and role design: `team-builder`, `council`
- GitHub, git, terminal, hooks, and deployment workflows: `git-workflow`, `github-ops`, `terminal-ops`, `hookify-rules`, `deployment-patterns`
- Refactor, audit, and review workflows: `large-file-refactor`, `production-audit`, `codehealth-mcp`
- Prompt and context management: `prompt-optimizer`
- Skill and standards maintenance: `skill-scout`, `skill-stocktake`, `skill-comply`, `rules-distill`, `standards-guide`, `configure-mcp`

Legacy workflow identifiers such as `workflow-plan`, `orch-pipeline`, `agentic-engineering`, and `ck` are compatibility shims for one release cycle. Prefer the canonical skills above for new routing.

Use the smallest workflow that clarifies the next action, then move to implementation and verification.
