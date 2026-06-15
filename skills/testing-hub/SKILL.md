---
name: testing-hub
description: Use for unit, integration, e2e, regression, TDD, coverage, verification-loop, and language or framework testing tasks. Routes to focused testing skills while keeping one public recommendation target.
---

# Testing Hub

Use this as the first testing skill call. Load only the focused skill(s) needed for the task:

- General test strategy, TDD, verification, E2E, benchmarks, and evals: `testing-core`
- Framework and language-specific testing: `framework-testing`
- Browser QA that includes visual interaction checks, not just tests: `browser-qa`
- Healthcare and scientific evaluation tasks: `healthcare-eval-harness`, `scientific-thinking-scholar-evaluation`

Legacy testing identifiers such as `tdd-workflow`, `verification-loop`, `react-testing`, and `python-testing` are compatibility shims for one release cycle. Prefer `testing-core` or `framework-testing` for new routing.

Choose the smallest test layer that proves the changed behavior, then broaden only when risk or shared contracts require it.
