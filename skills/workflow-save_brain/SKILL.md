---
description: Save project knowledge and session context
---

# WORKFLOW: /save-brain - The Infinite Memory Keeper v2.0

You are the **Librarian**. Mission: Fight against "Context Drift" - ensure the AI never forgets.

**Principle:** "Code changes → Docs change IMMEDIATELY"

---

## ⚡ PROACTIVE HANDOVER (Workflow system) 🆕

> **When context is > 80% full, AUTOMATICALLY create a Handover Document**

### Trigger Proactive Handover:
- Context window > 80% (AI self-detects)
- Long conversation > 50 messages
- Before asking a complex question

### Handover Document Format:

```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📋 HANDOVER DOCUMENT
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

📍 Working on: [Feature name]
🔢 Current step: Phase [X], Task [Y]

✅ DONE:
   - Phase 01: Setup ✓
   - Phase 02: Database ✓ (3/3 tasks)
   - Phase 03: Backend (2/5 tasks)

⏳ REMAINING:
   - Task 3.3: Create order API
   - Task 3.4: Payment integration
   - Phase 04, 05, 06

🔧 IMPORTANT DECISIONS:
   - Use Supabase (user wants it free)
   - No dark mode (wait for phase 2)
   - Prisma instead of raw SQL

⚠️ NOTES FOR NEXT SESSION:
   - File src/api/orders.ts is partially edited
   - API /payments not tested yet
   - SPECS-03 has special acceptance criteria

📁 IMPORTANT FILES:
   - docs/SPECS.md (main scope)
   - .brain/session.json (progress)
   - .brain/session_log.txt (details)

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📍 Saved! To continue: Type /recap
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```

### Actions after Proactive Handover:
1. Save handover to `.brain/handover.md`
2. Update session.json with current state
3. Notify user: "Context is almost full, I have saved the progress. You can continue right away or type /recap in a new session."

---

## 🎯 Non-Tech Mode (v4.0)

**Read preferences.json to adjust language:**

```
if technical_level == "newbie":
    → Hide JSON structure
    → Explain by benefits: "When you return next time, I'll remember everything!"
    → Only ask: "Save what I just learned about this project?"
```

### Explanation for non-tech:

```
❌ DON'T: "Update brain.json with tech_stack and database_schema"
✅ DO: "I am remembering things about your project:
         ✅ Technologies in use
         ✅ How data is stored
         ✅ APIs created

         Next time you return, I will remember everything!"
```

### Simple questions:

```
❌ DON'T: "Update session.json or brain.json?"
✅ DO:  "Do you want me to remember:
         1️⃣ What we did today (to continue tomorrow)
         2️⃣ Project overview knowledge
         3️⃣ Both"
```

### Progress indicator:

```
🧠 Remembering...
   ✅ Technologies used
   ✅ Data structure
   ✅ API endpoints
   ✅ Current progress

💾 Saved! Type /recap next time so I can remember.
```

### Explaining database_schema to a newbie:

```
When saving database structure, DO NOT just save technical JSON:
{
  "tables": [{"name": "users", "columns": ["id", "email"]}]
}

BUT MUST include plain language description in brain.json:

"database_schema": {
  "summary": "App stores: user info, orders, products",
  "tables": [...],
  "relationships_explained": "1 user has many orders, 1 order has many products"
}
```

### Explaining API endpoints to a newbie:

```
DO NOT just save:
"api_endpoints": [{"method": "POST", "path": "/api/auth/login"}]

BUT MUST include a description:
"api_endpoints": [
  {
    "path": "/api/auth/login",
    "explained": "Login - send email + password, receive token"
  }
]
```

---

## Phase 1: Change Analysis

### 1.1. Ask User
*   "What important changes did we make today?"
*   Or: "Should I scan the modified files myself?"

### 1.2. Automatic Analysis
*   Review files changed in the session
*   Categorize:
    *   **Major:** Add module, DB changes → Update Architecture
    *   **Minor:** Bug fixes, refactoring → Only note log

---

## Phase 2: Documentation Update

### 2.1. System Architecture
*   File: `docs/architecture/system_overview.md`
*   Update if there are:
    *   New modules
    *   New third-party APIs
    *   Database changes

### 2.2. Database Schema
*   File: `docs/database/schema.md`
*   Update when there are:
    *   New tables
    *   New columns
    *   New relationships

### 2.3. API Documentation (⚠️ SDD Requirement) 🆕

#### 2.3.0. Ask User about API Docs

```
"📄 Do you want to create API documentation?

1️⃣ Markdown format (easy to read, easy to edit)
   → Create docs/api/endpoints.md

2️⃣ OpenAPI/Swagger format (industry standard)
   → Create docs/api/openapi.yaml
   → Can be imported into Postman, Swagger UI

3️⃣ Both (recommended for large projects)

4️⃣ Skip (simple API, no docs needed)"
```

#### 2.3.1. Markdown API Docs

Scan all API routes in the project and create `docs/api/endpoints.md`:

```markdown
# API Documentation

Last updated: [Date]
Base URL: [https://api.example.com]

---

## 🔐 Authentication

### POST /api/auth/login
Log in to the system

**Request:**
```json
{ "email": "user@example.com", "password": "xxx" }
```

**Response (200):**
```json
{ "token": "eyJ...", "user": { "id": 1, "email": "..." } }
```

**Errors:**
- 401: Incorrect email or password
- 422: Missing email or password

---

## 👤 Users

### GET /api/users
Get user list (Admin permission required)

**Headers:** `Authorization: Bearer {token}`

**Query Parameters:**
| Param | Type | Default | Description |
|-------|------|---------|-------------|
| page | number | 1 | Current page |
| limit | number | 10 | Items per page |

**Response (200):**
```json
{ "users": [...], "total": 100, "page": 1 }
```
```

#### 2.3.2. OpenAPI/Swagger Format

Create file `docs/api/openapi.yaml` standard OpenAPI 3.0:

```yaml
openapi: 3.0.0
info:
  title: [App Name] API
  version: 1.0.0
  description: API documentation for [App Name]

servers:
  - url: http://localhost:3000/api
    description: Development
  - url: https://api.example.com
    description: Production

paths:
  /auth/login:
    post:
      summary: Login
      tags: [Authentication]
      requestBody:
        required: true
        content:
          application/json:
            schema:
              type: object
              properties:
                email: { type: string, format: email }
                password: { type: string, minLength: 6 }
      responses:
        '200':
          description: Successful login
        '401':
          description: Incorrect credentials
```

#### 2.3.3. Sync API Docs

When there is a new API, automatically append it to the existing docs file.

### 2.4. Business Logic Documentation
*   File: `docs/business/rules.md`
*   Record business rules:
    *   "Reward points expire after 1 year"
    *   "Orders > 500k get free shipping"
    *   "Admin can override prices"

### 2.5. Spec Status Update
*   Move Specs from `Draft` → `Implemented`
*   Update if there are changes compared to the original plan

---

## Phase 3: Codebase Documentation

### 3.1. README Update
*   Update setup instructions if there are new dependencies
*   Update new environment variables

### 3.2. Inline Documentation
*   Check if complex functions have JSDoc
*   Propose adding comments if missing

### 3.3. Changelog (⚠️ Important for the team)
*   Create/update `CHANGELOG.md`:

```markdown
# Changelog

## [2026-01-15]
### Added
- Customer reward points feature
- API `/api/points/redeem`

### Changed
- Updated Dashboard UI

### Fixed
- Fixed bug where confirmation email failed to send
```

---

## Phase 4: Knowledge Items Sync

### 4.1. Update KI if there is new knowledge
*   New patterns used
*   Gotchas/Bugs encountered and how to fix them
*   Integration with third-party services

---

## Phase 5: Deployment Config Documentation

### 5.1. Environment Variables
*   Update `.env.example` with new variables
*   Document the meaning of each variable

### 5.2. Infrastructure
*   Record server/hosting configuration
*   Record scheduled tasks

---

## Phase 6: Structured Context Generation ⭐ v3.3

> **Goal:** Separate static knowledge and dynamic session so the AI can parse faster

### 6.1. Folder structure of `.brain/`

```
.brain/                            # LOCAL (per-project)
├── brain.json                     # 🧠 Static knowledge (rarely changes)
├── session.json                   # 📍 Dynamic session (changes constantly)
└── preferences.json               # ⚙️ Local override (if different from global)

~/.agent-guidance/                    # GLOBAL (all projects)
├── preferences.json               # Default preferences
└── defaults/                      # Templates
```

### 6.2. File brain.json (Static Knowledge)

Contains rarely changing information:

```json
{
  "meta": { "schema_version": "1.1.0", "framework_version": "3.3.0" },
  "project": { "name": "...", "type": "...", "status": "..." },
  "tech_stack": { "frontend": {...}, "backend": {...}, "database": {...} },
  "database_schema": { "tables": [...], "relationships": [...] },
  "api_endpoints": [...],
  "business_rules": [...],
  "features": [...],
  "knowledge_items": { "patterns": [...], "gotchas": [...], "conventions": [...] }
}
```

### 6.3. File session.json (Dynamic Session) ⭐ NEW

Contains constantly changing information:

```json
{
  "updated_at": "2026-01-17T18:30:00Z",
  "working_on": {
    "feature": "Revenue Reports",
    "task": "Implement daily revenue chart",
    "status": "coding",
    "files": ["src/features/reports/components/revenue-chart.tsx"],
    "blockers": [],
    "notes": "Using recharts"
  },
  "pending_tasks": [
    { "task": "Add date filter", "priority": "medium", "notes": "User request" }
  ],
  "recent_changes": [
    { "timestamp": "...", "type": "feature", "description": "...", "files": [...] }
  ],
  "errors_encountered": [
    { "error": "...", "solution": "...", "resolved": true }
  ],
  "decisions_made": [
    { "decision": "Use recharts", "reason": "Better React integration" }
  ]
}
```

### 6.4. Update rules

| Trigger | File to update |
|---------|-----------------|
| Add new API | `brain.json` → api_endpoints |
| Change DB | `brain.json` → database_schema |
| Fix bug | `session.json` → errors_encountered |
| Add dependency | `brain.json` → tech_stack |
| New feature | `brain.json` → features |
| Working on task | `session.json` → working_on |
| Task completed | `session.json` → pending_tasks, recent_changes |
| End of day | Both |

### 6.5. Steps to create/update

**Step 1: Update brain.json (if there are project changes)**
- Scan `package.json` → tech_stack
- Scan `prisma/schema.prisma` → database_schema
- Scan `src/app/api/**` → api_endpoints
- Scan `docs/specs/*.md` → features

**Step 2: Update session.json (always update)**
- Modified files → recent_changes
- Task currently working on → working_on
- Errors encountered → errors_encountered
- Decisions made → decisions_made

**Step 3: Validate**
- Schema: `schemas/brain.schema.json`, `schemas/session.schema.json`
- Ensure JSON is valid before saving

**Step 4: Save**
- `.brain/brain.json` - add to `.gitignore` or commit if shared by the team
- `.brain/session.json` - always in `.gitignore` (local state)

---

## Phase 7: Confirmation

1. Report: "I have updated the memory. Updated files:"
    *   `docs/architecture/system_overview.md`
    *   `docs/api/endpoints.md`
    *   `.brain/brain.json` ⭐
    *   `CHANGELOG.md`
    *   ...
2. "Now I have memorized this knowledge permanently."
3. "You can safely power off. Tomorrow, using `/recap` will restore all context."

### 7.1. Quick Stats
```
📊 Brain Stats:
- Tables: X | APIs: Y | Features: Z
- Pending tasks: N
- Last updated: [timestamp]
```

---

## ⚠️ NEXT STEPS (Numbered menu):
```
1️⃣ Finished work session? Let's rest!
2️⃣ Returning tomorrow? /recap to remember context
3️⃣ Need to continue? /plan or /code
```

## 💡 BEST PRACTICES:
*   Run `/save-brain` after each major feature
*   Run `/save-brain` at the end of each workday
*   Run `/save-brain` before a long time off

---

## 🛡️ RESILIENCE PATTERNS (Hidden from User)

### When file write fails:
```
1. Retry 1st time (wait 1s)
2. Retry 2nd time (wait 2s)
3. Retry 3rd time (wait 4s)
4. If it still fails → Report to user:
   "Failed to save file 😅

   Do you want to:
   1️⃣ Retry
   2️⃣ Save temporarily to clipboard
   3️⃣ Skip this file, save the rest"
```

### When JSON is invalid:
```
If brain.json/session.json is corrupted:
→ Create backup: brain.json.bak
→ Create new file from template
→ Report to user: "The old file was corrupted, I have created a new one and backed up the old file"
```

### Simple error messages:
```
❌ "ENOENT: no such file or directory"
✅ "Folder .brain/ doesn't exist yet, I'll create it!"

❌ "EACCES: permission denied"
✅ "No permission to write file. Please check folder permissions?"
```
