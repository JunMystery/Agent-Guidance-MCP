# Workflow Hardening Implementation Plan (Workflow Loops & Circuit Breaker)

This document contains the detailed specifications and step-by-step development plan to enforce structured workflow loops and circuit breakers on AI agents.

---

## 📊 Standard Workflow Lifecycle
Every task must strictly move through these stages:
`Context` -> `Plan` -> `Ask/Revise` -> `Build` -> `Test/Recheck` -> `Fix` -> `Document/Proposal`

---

## 🔁 Feedback Loops & Rules

### 1. Planning Loop (Human <-> Agent)
- **Stages:** `Plan` -> `Ask/Revise`
- **Enforcement:** The agent cannot progress to the `Build` stage until the user explicitly approves the plan.
- **Trigger:** The MCP server automatically parses user messages for approval keywords (`proceed`, `ok`, `okay`, `go ahead`, `approved`, `approve`, `start`, `yes`, `run`, `do it`, `bắt đầu`, `chạy đi`, `làm đi`, `đồng ý`, `nhất trí`, `tiến hành`). If matching, `plan_approved` metadata flips to `true`, enabling transition to `Build`.

### 2. Execution & Quality Loop (Autonomous)
- **Stages:** `Test/Recheck` <-> `Fix`
- **Enforcement:** Following code edits in `Build`, the agent must transition to `Test/Recheck` to verify changes. If failures are detected, it transitions to `Fix`.

### 3. Circuit Breaker Rule
- **Threshold:** Max **3 consecutive fix attempts** within the `Fix` stage for the same issue.
- **Action:** If unresolved after 3 attempts, the MCP enforcer will:
  1. Force-transition the stage to `Ask/Revise`.
  2. Set `plan_approved = false`.
  3. Reset `fix_attempts = 0`.
  4. Return a critical error blocking further edits until the user adjusts the strategy.

---

## 🛠️ Step-by-Step Implementation Steps

### Task 1: Update Session Management (`src/agent_guidance_mcp/session.py`)
- Write `check_approval_in_text(text: str) -> bool` using the Vietnamese and English approval regex.
- Update `save_session()` to initialize and load state schemas containing:
  - `current_stage` (default: `"Context"`)
  - `plan_approved` (default: `false`)
  - `fix_attempts` (default: `0`)
  - `last_error_signature` (default: `""`)
- Automatically set `plan_approved = true` when user approval is found in incoming `task` text.

### Task 2: Implement Workflow Loops & Circuit Breaker Pipeline (`src/agent_guidance_mcp/pipelines.py`)
- Enhance `session_continuity(operation="save")`:
  - If target stage is `Build` and `plan_approved` is `false`, block and warn the agent to ask the user.
  - Track `fix_attempts` during stage transitions (increment when saving state in `Fix`).
  - Enforce the 3-strikes Circuit Breaker: Reset attempts, revert stage to `Ask/Revise`, set `plan_approved = false`, and return the lock warning.
  - Reset `fix_attempts = 0` when transitioning to stages other than `Fix`.

### Task 3: Soft-Gate Enforcer Warn Warnings (`src/agent_guidance_mcp/server.py`)
- In `priority_gate_check()`:
  - Load the active session via `load_session()`.
  - If stage mismatch occurs (e.g. `Ask_Revise` but agent is calling analysis tools without asking user), insert a soft warning into the response metadata: `"warning": "Workflow stage mismatch. Please focus on resolving user feedback."`
  - If Circuit Breaker is active, append the lock notice.

### Task 4: Auto-Deploy Rules update (`src/agent_guidance_mcp/deploy_rules.py`)
- Inject the structured 7-stage lifecycle, Planning/Execution Loops, and the Circuit Breaker warning directly into `AGENT_RULES_BLOCK` for Aider/Cursor/Windsurf.

### Task 5: Verification Tests (`tests/test_workflow_gate.py`)
- Write unit tests verifying:
  - Soft warnings trigger on wrong stage sequence.
  - Approval keyword scanning toggles `plan_approved`.
  - Hard reset/circuit breaker flips stage to `Ask_Revise` after 3 consecutive failures.
