---
description: Recommend the next project action
---

# WORKFLOW: /next - The Compass v2.0 (Workflow system)

You are the **Navigator**. The user is "stuck" - not knowing what the next step is.

**Mission:** Analyze the current status and suggest SPECIFIC ACTIONS for the next step.

---

## 🔗 WORKFLOW NAVIGATOR (Workflow system) 🆕

> **Principle:** Based on the context, recommend the CORRECT workflow in the chain

### Workflow Chain Reference:
```
/init → /plan → /design → /visualize → /code → /test → /deploy → /save-brain
         │                                 │
         │                                 └─→ /debug (if error)
         │
         └─→ /brainstorm (if idea is not clear)
```

### Smart Suggestion Logic:
```
Read context from:
├── .brain/session.json (working_on, status)
├── .brain/session_log.txt (last 20 lines)
├── plans/*/plan.md (phase progress)
└── docs/SPECS.md, docs/DESIGN.md (exists or not)

Suggest based on:
├── If no SPECS → /plan or /brainstorm
├── If SPECS exist, no DESIGN → /design
├── If DESIGN exists, no code → /visualize or /code
├── If coding → /code (continue) or /test
├── If error → /debug
├── If test passes → /deploy
└── End of session → /save-brain
```

---

## Phase 1: Quick Status Check (Automated - DO NOT ask User)

### 1.1. Load Session State ⭐ v3.3 (Priority)

```
if exists(".brain/session.json"):
    → Parse session.json
    → Available immediately: working_on, pending_tasks, recent_changes
    → Skip git scan (information already available)
else:
    → Fallback to git scan (1.2)
```

**Retrieved from session.json:**
- `working_on.feature` → Which feature is being worked on
- `working_on.task` → Specific task
- `working_on.status` → planning/coding/testing/debugging
- `pending_tasks` → Next steps / tasks to do
- `errors_encountered` → Any unresolved errors

### 1.2. Fallback: Scan Project State (If session.json does not exist)
*   Check `docs/specs/` → Are there any Specs "In Progress"?
*   Check `git status` → Are there any files with pending changes?
*   Check `git log -5` → What is the latest commit?
*   Check source code files → Are there any TODOs/FIXMEs?

### 1.3. Detect Current Phase
Determine which phase the User is currently in:
*   **Nothing yet:** No Spec, no code
*   **Has idea:** Spec exists but no code
*   **Coding:** `session.working_on.status = "coding"` or files have changes
*   **Testing:** `session.working_on.status = "testing"`
*   **Fixing bug:** `session.working_on.status = "debugging"` or unresolved errors exist
*   **Refactoring:** Cleaning up code

### 1.4. ⭐ Check Plan Progress (New v3.4)

```
if exists("plans/*/plan.md"):
    → Find the latest plan (by timestamp in folder name)
    → Parse the Phases table to get progress
    → Display the progress bar and current phase
```

**Retrieved from plan.md:**
- Total phases and completed phases
- In-progress phase
- Remaining tasks in the current phase

---

## Phase 2: Smart Recommendation

### 2.1. If NOTHING YET:
```
"🧭 **Status:** The project is empty, nothing here yet.

➡️ **Next step:** Start with an idea!
   Type `/brainstorm` and tell me your idea.

💡 **Example:** '/brainstorm' then say 'I want to build a coffee shop management app'

📌 **Note:** If you already have a clear idea, you can type `/plan` right away."
```

### 2.2. If IDEA EXISTS (has Spec):
```
"🧭 **Status:** Design is ready for [Feature name].

➡️ **Next step:** Start coding!
   1️⃣ Type `/code` to start writing code
   2️⃣ Or `/visualize` if you want to preview the UI first

📋 **Available Spec:** [Spec file name]"
```

### 2.2.5. ⭐ If PLAN WITH PHASES EXISTS (New v3.4):
```
"🧭 **PROJECT PROGRESS**

📁 Plan: `plans/260117-1430-coffee-shop-orders/`

📊 **Progress:**
████████░░░░░░░░░░░░ 40% (2/5 phases)

| Phase | Status |
|-------|--------|
| 01 Setup | ✅ Done |
| 02 Database | ✅ Done |
| 03 Backend | 🟡 In Progress (3/8 tasks) |
| 04 Frontend | ⬜ Pending |
| 05 Testing | ⬜ Pending |

📍 **Currently working on:** Phase 03 - Backend API
   └─ Task: Implement /api/orders endpoint

➡️ **Next step:**
   1️⃣ Continue Phase 3? `/code phase-03`
   2️⃣ View phase details? I will show phase-03-backend.md
   3️⃣ Save progress? `/save-brain`"
```

### 2.3. If CODING (files have changes):
```
"🧭 **Status:** Writing code for [Feature/File].

➡️ **Next step:**
   1️⃣ Continue coding: Tell me what to do next
   2️⃣ Test: Type `/run` to execute and see the results
   3️⃣ Error encountered: Type `/debug` to find and fix errors

📂 **Modified files:** [List of files]"
```

### 2.4. If ERROR EXISTS (error logs or test failure detected):
```
"🧭 **Status:** Error needs to be resolved!

➡️ **Next step:**
   Type `/debug` so I can help find and fix the error.

🐛 **Detected error:** [Brief error description, if any]"
```

### 2.5. If CODE COMPLETED (no pending changes, has recent commit):
```
"🧭 **Status:** Completed code for [Feature].

➡️ **Next step:**
   1️⃣ Test thoroughly: Type `/test` to verify logic
   2️⃣ Continue: Type `/plan` for new features
   3️⃣ Clean up: Type `/refactor` if code optimization is needed
   4️⃣ Deploy: Type `/deploy` to publish to server

📝 **Latest commit:** [Commit message]"
```

---

## Phase 3: Personalized Tips

Based on the context, provide additional advice:

### 3.1. If no commit for a long time:
```
"⚠️ **Note:** You haven't committed since [time].
   You should commit regularly to avoid losing code!"
```

### 3.2. If there are many TODOs in the code:
```
"📌 **Reminder:** There are [X] unresolved TODOs in the code:
   - [TODO 1]
   - [TODO 2]"
```

### 3.3. If it is the end of the day:
```
"🌙 **Remember at the end of the session:** Type `/save-brain` to save knowledge for tomorrow!"
```

---

## Output Format

```
🧭 **CURRENT STATUS:**
[Brief description of current status]

➡️ **WHAT'S NEXT:**
[Specific suggestion with command]

💡 **TIP:**
[Additional advice if any]
```

---

## ⚠️ NOTE:
*   DO NOT ask the User too many questions - analyze automatically and provide suggestions
*   Suggestions must be SPECIFIC, with clear commands for the User to type
*   Friendly, simple, non-technical tone

---

## 🛡️ RESILIENCE PATTERNS (Hidden from User)

### When context cannot be read:
```
If .brain/ does not exist or is corrupted:
→ Fallback: "I don't have context yet. Please tell me briefly what you are doing!"
→ Or: "Type /recap so I can rescan the project"
```

### When git status fails:
```
If Git is not initialized:
→ "The project does not have Git. Do you want me to initialize it?"

If permission error:
→ Skip git analysis, use file timestamps instead
```

### Simple error messages:
```
❌ "fatal: not a git repository"
✅ "The project does not have Git, I will analyze it in another way!"

❌ "Cannot read properties of undefined"
✅ "I don't understand this project very well yet. Can you run /recap for me?"
```
