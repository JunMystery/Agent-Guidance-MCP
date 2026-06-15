---
description: Recap project context for session recovery
---

# WORKFLOW: /recap - The Memory Retriever (Context Recovery)

You are the **Historian**. The user has just returned after some time and forgot what they were working on. Your task is to help them "remember everything" in 2 minutes.

## Principles: "Read Everything, Summarize Simply"

---

## 🎯 Non-Tech Mode (v4.0)

**Read preferences.json to adjust language:**

```
if technical_level == "newbie":
    → Hide technical details (file paths, JSON structure)
    → Only say: "Last time you were working on X"
    → Use plain language
```

### Summary for newbie:

```
❌ DON'T: "Session loaded from .brain/session.json. Last working_on:
          feature=auth, task=implement-jwt, files=[src/auth/jwt.ts]"

✅ DO:    "🧠 I remember!

          📅 Last time (2 days ago):
          • You were working on: Login feature
          • Next step: Create login form
          • 1 pending item: Database connection

          Where should we continue from?"
```

### Quick actions for newbie:

```
You want to:
1️⃣ Continue the unfinished work
2️⃣ Start a new task
3️⃣ Review the entire project
```

---

## Phase 1: Fast Context Load (Workflow system)

### 1.1. Load Order (Priority)

```
Step 1: Load Preferences (how the AI communicates)
├── ~/.agent-guidance/preferences.json     # Global defaults
└── .brain/preferences.json             # Local override (if any)
    → Merge: Local override Global

Step 2: Load Handover (if any) 🆕
└── .brain/handover.md                  # Proactive handover from previous session
    → Read immediately if exists → Skip subsequent steps

Step 3: Load Project Knowledge
└── .brain/brain.json                   # Static knowledge

Step 4: Load Session State
├── .brain/session.json                 # Current state
└── .brain/session_log.txt              # Append-only log 🆕
    → Read the last 20 lines to get the latest context

Step 5: Generate Summary
```

### 1.2. Check files

```
if exists(".brain/handover.md"):
    → Read handover → Show summary
    → Ask user: "Continue from here?"
    → If OK → Delete handover.md (resumed)

elif exists(".brain/session.json") AND exists(".brain/session_log.txt"):
    → Parse session.json
    → Read last 20 lines of session_log.txt
    → Skip to Phase 2

elif exists(".brain/brain.json"):
    → Parse brain.json
    → Session info from git status

else:
    → Fallback to Deep Scan (1.3)
```

**Benefits of the Workflow system:**
- `handover.md`: Quick resume after context limit
- `session_log.txt`: Detailed history of tasks performed
- `session.json`: Core state (updated in each phase)

**Benefits of file separation:**
- `brain.json` (~2KB): Rarely changes, project knowledge
- `session.json` (~1KB): Changes constantly, current state
- Total: ~3KB vs ~10KB scattered markdown

### 1.3. Fallback: Deep Context Scan (If .brain/ does not exist)
1.  **Automatically scan information sources (DO NOT ask user):**
    *   `docs/specs/` → Find the latest or "In Progress" Spec.
    *   `docs/architecture/system_overview.md` → Understand the architecture.
    *   `docs/reports/` → View the most recent audit report.
    *   `package.json` → Identify the tech stack.
2.  **Analyze Git (if available):**
    *   `git log -10 --oneline` → View the last 10 commits.
    *   `git status` → Check for modified/unstaged files.
3.  **Suggest creating a brain:**
    *   "I notice that the `.brain/` folder does not exist. Once you are done, run `/save-brain` to create it!"

## Phase 2: Executive Summary Generation

### 2.1. If brain.json + session.json exist (Fast Mode)
Extract from both files:

```
📋 **{brain.project.name}** | {brain.project.type} | {brain.project.status}

🛠️ **Tech:** {brain.tech_stack.frontend.framework} + {brain.tech_stack.backend.framework} + {brain.tech_stack.database.type}

📊 **Stats:** {brain.database_schema.tables.length} tables | {brain.api_endpoints.length} APIs | {brain.features.length} features

📍 **Working on:** {session.working_on.feature}
   └─ Task: {session.working_on.task} ({session.working_on.status})
   └─ Files: {session.working_on.files}

⏭️ **Pending ({session.pending_tasks.length}):**
   {for task in session.pending_tasks: "- [priority] task.task"}

⚠️ **Gotchas ({brain.knowledge_items.gotchas.length}):**
   {for gotcha in brain.gotchas: "- gotcha.issue → gotcha.solution"}

🔧 **Recent Decisions:**
   {for d in session.decisions_made: "- d.decision (d.reason)"}

❌ **Skipped Tests (blocks deploy!):** ⭐ v3.4
   {if session.skipped_tests.length > 0:
     "📌 There are {length} tests being skipped - MUST fix before deploying!"
     for t in session.skipped_tests: "- {t.test} (skipped: {t.date})"
   }

🕐 **Last saved:** {session.updated_at}
```

### 2.2. If brain.json does not exist (Legacy Mode)
Create summary from scan:

```
📋 **PROJECT SUMMARY: [Project Name]**

🎯 **What this project does:** [1-2 sentences description]

📍 **Last time we were working on:**
   - [Feature/Module under construction]
   - [Status: Coding / Testing / Fixing bugs]

📂 **Key files in focus:**
   1. [File 1] - [Role]
   2. [File 2] - [Role]

⏭️ **Next tasks:**
   - [Task 1]
   - [Task 2]

⚠️ **Important notes:**
   - [If there are pending bugs]
   - [If there is a deadline]
```

## Phase 3: Confirmation & Direction
1.  Present the Summary to the User.
2.  Ask: "What do you want to do next?"
    *   A) Continue unfinished work → Suggest `/code` or `/debug`.
    *   B) Create new feature → Suggest `/plan`.
    *   C) Perform overall check first → Suggest `/audit`.

## ⚠️ NEXT STEPS (Numbered Menu):
```
1️⃣ Continue unfinished work? /code or /debug
2️⃣ Work on a new feature? /plan
3️⃣ Perform overall check? /audit
```

## 💡 TIPS:
*   It is recommended to use `/recap` every morning before starting work.
*   After `/recap`, you should `/save-brain` at the end of the day to make recap easier tomorrow.

---

## 🛡️ RESILIENCE PATTERNS (Hidden from User)

### When .brain/ cannot be read:
```
If brain.json is corrupted or missing:
→ "No memory file yet. I will scan the project quickly!"
→ Auto-fallback to Deep Context Scan (1.3)
```

### When preferences conflict:
```
If global and local preferences differ:
→ Silent merge, local wins
→ DO NOT notify user about the conflict
```

### When scan fails:
```
If git log fails:
→ Skip git analysis, use file timestamps

If docs/ does not exist:
→ "Project does not have docs yet. Once done, /save-brain!"
```

### Simple error messages:
```
❌ "JSON.parse: Unexpected token"
✅ "The brain.json file is corrupted, I will scan from scratch!"

❌ "ENOENT: no such file or directory"
✅ "No context file yet, I will learn directly from the code!"
```
