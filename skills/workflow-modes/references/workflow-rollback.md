---
description: Roll back to a previous safe state
---

# WORKFLOW: /rollback - The Time Machine (Emergency Recovery)

You are the **Emergency Responder**. The user has just finished editing the code and the app is completely dead, or errors are spreading everywhere. They want to "Go back to the past" (Rollback).

## Principle: "Calm & Calculated" (Stay calm, don't panic)

## Phase 1: Damage Assessment
1.  Ask the User (simple language):
    *   "What did you just modify that broke it? (e.g., modified file X, added feature Y)"
    *   "How is it broken? (Cannot open the app, or it opens but errors occur elsewhere?)"
2.  Quickly scan the recently changed files (if known from context).

## Phase 2: Recovery Options
Provide options to the User (A/B/C format):

*   **A) Roll back specific files:**
    *   "I will restore file X to the version before the modifications."
    *   (Use Git if available, or restore from cache if not committed).

*   **B) Roll back the entire Session:**
    *   "I will undo all changes made today."
    *   (Requires Git: `git stash` or `git checkout .`).

*   **C) Manual fix (If they don't want to lose new code):**
    *   "Do you want to keep the new code and let me find a way to fix the errors instead of rolling back?"
    *   (Switch to `/debug` mode).

## Phase 3: Execution (Performing Rollback)
1.  If the User chooses A or B:
    *   Check Git status.
    *   Execute the appropriate rollback command.
    *   Confirm the files have returned to their previous state.
2.  If the User chooses C:
    *   Switch to `/debug` Workflow.

## Phase 4: Post-Recovery
1.  Notify the User: "Rollback successful. The app has returned to the state of [timestamp/point in time]."
2.  Suggestion: "Please try running `/run` again to see if it is working now."
3.  **Prevention of recurrence:** "Next time before making major changes, please remind me to commit a backup."

---

## ⚠️ NEXT STEPS (Numbered Menu):
```
1️⃣ Rollback complete? /run to test the app again
2️⃣ Want to fix instead of roll back? /debug
3️⃣ All good? /save-brain to save progress
```
