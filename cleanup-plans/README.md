# Codebase Cleanup Plans

Since we are freely making changes to this codebase without strict external compatibility constraints, we can proceed to completely clean up the legacy files, deprecation shims, and obsolete tests. This document outlines the phases to decommission and remove the compatibility shims, streamline the `skills/` directory, and update the catalog tests.

## Cleanup Phases

1. **[Phase 1: Remove Workflow, Orchestration, Testing & Verification Shims](phase-1-remove-workflow-testing-shims.md)**
   - Remove shims for Phase 1 (Workflow & Orchestration) and Phase 2 (Testing & Verification).
   - Clean up corresponding tests and manifests.

2. **[Phase 2: Remove Frontend, UI, Motion, Backend, API, & Data Shims](phase-2-remove-frontend-backend-shims.md)**
   - Remove shims for Phase 3 (Frontend, UI, Motion) and Phase 4 (Backend, API, Data).
   - Clean up corresponding tests and manifests.

3. **[Phase 3: Remove Security, Compliance, Docs, Research, Content, & Media Shims](phase-3-remove-security-docs-shims.md)**
   - Remove shims for Phase 5 (Security & Compliance) and Phase 6 (Docs, Research, Content, Media).
   - Clean up corresponding tests and manifests.

4. **[Phase 4: Test Suite & Routing Consolidation](phase-4-test-suite-refactoring.md)**
   - Refactor `tests/test_catalog.py` to remove legacy compatibility tests.
   - Verify that the recommendation engine works exclusively with the canonical skills.
   - Standardize `docs/skill-grouping-audit.md` to reflect a clean canonical-only layout.

## Global Rules for Decommissioning

- **Keep References**: Keep the original pre-shimmed content files inside the canonical `references/` directories (e.g., `skills/frontend-frameworks/references/react-patterns.md`) so that granular guidance is not lost.
- **Remove Directories**: Completely delete the directories of absorbed skills under `skills/` (e.g., delete `skills/react-patterns/`).
- **Update Tests**: Update or remove test assertions in `tests/test_catalog.py` that check for the existence of shimmed identifiers.
