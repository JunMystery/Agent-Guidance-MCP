---
name: workflow-hub
description: Use for workflow modes, orchestration, planning, multi-agent coordination, context/session recovery, parallel execution, team building, rollback, recap, review, and pipeline design.
---

# Workflow Hub

Use this as the first workflow skill call. Load only the focused skill(s) needed for the task:

- Mode prompts: `workflow-modes`
- Agentic and autonomous workflows: `agent-workflow-ops`
- Session/context continuity: `session-context-ops`
- Planning and execution strategy: `intent-driven-development`
- Team and role design: `team-builder`, `council`
- GitHub, git, terminal, hooks, and deployment workflows: `git-workflow`, `github-ops`, `terminal-ops`, `hookify-rules`, `deployment-patterns`
- Refactor, audit, and review workflows: `large-file-refactor`, `production-audit`, `codehealth-mcp`
- Prompt and context management: `prompt-optimizer`
- Skill and standards maintenance: `skill-scout`, `skill-stocktake`, `skill-comply`, `rules-distill`, `standards-guide`, `configure-mcp`

### Orchestration & Parallel Execution References
- `orch-pipeline`: [references/orch-pipeline.md](references/orch-pipeline.md)
- `orch-add-feature`: [references/orch-add-feature.md](references/orch-add-feature.md)
- `orch-build-mvp`: [references/orch-build-mvp.md](references/orch-build-mvp.md)
- `orch-change-feature`: [references/orch-change-feature.md](references/orch-change-feature.md)
- `orch-fix-defect`: [references/orch-fix-defect.md](references/orch-fix-defect.md)
- `orch-refine-code`: [references/orch-refine-code.md](references/orch-refine-code.md)
- `plan-orchestrate`: [references/plan-orchestrate.md](references/plan-orchestrate.md)
- `team-agent-orchestration`: [references/team-agent-orchestration.md](references/team-agent-orchestration.md)
- `parallel-execution-optimizer`: [references/parallel-execution-optimizer.md](references/parallel-execution-optimizer.md)

Legacy workflow identifiers such as `workflow-plan`, `orch-pipeline`, `agentic-engineering`, and `ck` are compatibility shims for one release cycle. Prefer the canonical skills above for new routing.

Use the smallest workflow that clarifies the next action, then move to implementation and verification.
