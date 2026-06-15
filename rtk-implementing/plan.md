# Plan: RTK Token Reduction Integration into Agent Guidance MCP

Created: 2026-06-15
Status: 🟡 In Progress

## Overview

Port RTK's (Rust Token Killer) core token reduction strategies into the Agent Guidance MCP Python codebase as a **native Python module**. Every MCP tool response will automatically pass through the token optimization pipeline, reducing token consumption by 60-90% — matching RTK's savings without requiring an external Rust binary.

> **Design Principle:** No linking to the `rtk/` folder. All logic is re-implemented in Python, inspired by RTK's algorithms. The `rtk/` folder will be removed after implementation.

## Tech Stack

- Language: Python 3.10+
- Framework: MCP (FastMCP)
- No new dependencies (only stdlib `re`, `json`, `pathlib`)

## Architecture

```
MCP Tool Call → Pipeline Dispatcher → [Token Filter Engine] → Response
                                            ↓
                                    ┌───────────────────┐
                                    │  8-Stage Pipeline  │
                                    │ 1. strip_ansi      │
                                    │ 2. replace          │
                                    │ 3. match_output     │
                                    │ 4. strip/keep_lines │
                                    │ 5. truncate_lines   │
                                    │ 6. head/tail        │
                                    │ 7. max_lines        │
                                    │ 8. on_empty         │
                                    └───────────────────┘
```

## Phases

| Phase | Name | Status | Progress |
|-------|------|--------|----------|
| 01 | Core Filter Engine | ⬜ Pending | 0% |
| 02 | Content Compressor | ⬜ Pending | 0% |
| 03 | Response Optimizer | ⬜ Pending | 0% |
| 04 | MCP Pipeline Integration | ⬜ Pending | 0% |
| 05 | Token Analytics & Config | ⬜ Pending | 0% |
| 06 | Testing & Verification | ⬜ Pending | 0% |

## Quick Reference

- Start Phase 1: Read `phase-01-core-filter-engine.md`
- Check progress: Review `plan.md` table
