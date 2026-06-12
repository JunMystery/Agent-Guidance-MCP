---
description: Comprehensive workflow command guide for AI-assisted project work
---

# 🚀 workflow framework v2.0

**COMPREHENSIVE Workflow System for all levels** - From newbie to pro, AI has it covered.

> 💡 **Workflow system philosophy:**
> - AI PROPOSES, You APPROVE (Smart Proposal)
> - Each workflow has its own PERSONA (PM, Developer, Designer, Detective...)
> - NEVER lose context (Lazy Checkpoint + Proactive Handover)

---

## 📋 Command List (15 Workflows)

### 🌟 Startup & Context
| Command | Description | Blind spots handled |
|------|-------|-------------------|
| `/init` | Create a complete new project | Env vars, Git, Code quality tools |
| `/recap` | Summarize context when returning | Context recovery |
| `/save-brain` | Save knowledge at the end of session | API Docs, Changelog, Business rules |

### 🎯 Feature Development
| Command | Description | Blind spots handled |
|------|-------|-------------------|
| `/plan` | Design feature (Smart Proposal) | Auth, DB, Charts, Scheduled Tasks |
| `/design` | **Detailed design** ⭐ NEW | Database, Workflows, Acceptance Criteria |
| `/visualize` | Beautiful UI/UX design | Loading/Error states, Accessibility |
| `/code` | Write high-quality code | Security, Validation, Error handling |

### ⚙️ Operations
| Command | Description | Blind spots handled |
|------|-------|-------------------|
| `/run` | Start the app | Environment detection, Port conflicts |
| `/test` | Test logic | Auto-generate tests if missing |
| `/deploy` | Deploy to production | SEO, Analytics, Legal, Backup, Monitoring |

### 🔧 Maintenance
| Command | Description | Blind spots handled |
|------|-------|-------------------|
| `/debug` | Fix errors (Investigation Protocol) | Hypothesis + 3 max attempts |
| `/refactor` | Refactor code | Safe execution, Before/After comparison |
| `/audit` | Health check | Security, Performance, Dependencies |
| `/rollback` | Rollback to old version | Emergency recovery |
| `/review` | **Project overview** ⭐ NEW | Handover, evaluation, upgrade planning |


---

## 🔥 VIBE CODER BLIND SPOTS COMPREHENSIVELY HANDLED

### 📐 During planning (`/plan`)
| Blind spot | AI asks itself |
|---------|-----------|
| Database Design | "Is there existing data? What needs to be managed?" |
| Auth/Login | "Is login required? OAuth? Roles?" |
| File Upload | "Is image upload needed? Size limit?" |
| Email/Notifications | "Need to send notifications?" |
| Payment | "Is payment processing needed?" |
| Search | "Is search functionality needed? Fuzzy search?" |
| Scheduled Tasks | "Are automated daily tasks required?" |
| Charts/Graphs | "Are charts/graphs required?" |
| PDF/Print | "Need to print invoices/receipts?" |
| Maps | "Are maps required?" |
| Real-time | "Are live updates needed?" |

### 🎨 During UI design (`/visualize`)
| Blind spot | AI handles automatically |
|---------|-------------|
| Loading States | Skeleton, Spinner, Progress bar |
| Error States | Toast, Modal, Inline error |
| Empty States | Illustration + Call-to-action |
| Accessibility | Color contrast, ARIA, Keyboard nav |
| Mobile | Responsive, Touch-friendly |
| Dark Mode | Dual theme design |

### 🚀 During deployment (`/deploy`)
| Blind spot | AI handles automatically |
|---------|-------------|
| SEO | Meta tags, Sitemap, robots.txt |
| Analytics | Google Analytics / Plausible |
| Legal | Privacy Policy, Terms, Cookie consent |
| Backup | Database backup strategy |
| Monitoring | Uptime + Error tracking |
| SSL | Auto HTTPS |
| Maintenance | Maintenance mode page |

### 📚 During saving/storage (`/save-brain`)
| Blind spot | AI auto-generates |
|---------|-----------|
| API Documentation | Auto-generate from routes |
| Changelog | Version history |
| Business Rules | Business rules |
| **Structured Context** | `.brain/brain.json` ⭐ NEW |

---

## 🚀 Workflow system - NEW FEATURES

### 1️⃣ Deep Interview (3 Golden Questions)
Before proposing, AI asks 3 core questions:
- WHAT to manage?
- WHO uses it?
- What is MOST IMPORTANT?

→ Helps AI understand correctly from the beginning, avoiding errors and rework.

### 2️⃣ Lazy Checkpoint (Save tokens)
```
.brain/
├── session.json        # Update every PHASE (~450 tokens)
└── session_log.txt     # Append every TASK (~20 tokens)
```
→ Reduces token overhead by 80% compared to rewriting JSON for every task.

### 3️⃣ Proactive Handover
When context is > 80% full:
- AI auto-generates Handover Document
- Saved to `.brain/handover.md`
- Next session, type `/recap` to resume immediately

→ NEVER lose context between sessions.

### 4️⃣ Step Confirmation Protocol
After each milestone, display:
```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
✅ DONE: [Task name]
📊 Progress: ████████░░ 80%
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
→ Continue? (y/adjust/stop)
```
→ Users always know where they are, avoiding feeling "out of control".

### 5️⃣ Agent Personas (BMAD-Inspired)
| Workflow | Persona | Personality / Tone |
|----------|---------|-----------|
| `/plan` | Ha (PM) | Listens, proposes options |
| `/design` | Minh (Architect) | Explains technical concepts simply |
| `/code` | Tuan (Senior Dev) | Meticulous, checks thoroughly |
| `/visualize` | Mai (UX Designer) | Visual, uses examples |
| `/debug` | Long (Detective) | Calm, methodical |
| `/audit` | Khang (Code Doctor) | Calm/reassuring tone |

---

## 🧠 Structured Context - v3.3 (Separate brain + session)

### Problem in v3.2
- `brain.json` contains both static and dynamic data
- Every save requires updating the entire file
- Session state is mixed with project knowledge

### Solution in v3.3: Separate into 2 files
```
.brain/                            # LOCAL (per-project)
├── brain.json                     # 🧠 Static knowledge (rarely changes)
├── session.json                   # 📍 Dynamic session (changes constantly)
└── preferences.json               # ⚙️ Local override (if different from global)

~/.agent-guidance/                    # GLOBAL (all projects)
├── preferences.json               # Default AI preferences
└── defaults/                      # Templates
```

### Benefits
| Metric | v3.2 | v3.3 |
|--------|------|------|
| Files to scan | 1 (brain.json) | 2 (brain + session) |
| Token usage | ~3KB | ~3KB (equivalent) |
| Update frequency | Every save | brain: when project changes, session: constantly |
| Scope | Local only | Local + Global preferences |

### Workflow
```
/save-brain → Update brain.json (if needed) + session.json (always)
/recap → Load preferences → brain.json → session.json → Summary
/customize → Save preferences (local/global/both)
```

### Schema files
- `schemas/brain.schema.json` - Project knowledge
- `schemas/session.schema.json` - Session state ⭐ NEW
- `schemas/preferences.schema.json` - User preferences ⭐ NEW

### Template files
- `templates/brain.example.json`
- `templates/session.example.json` ⭐ NEW
- `templates/preferences.example.json` ⭐ NEW

### brain.json (Static - rarely changes)
- `project`: Name, type, status
- `tech_stack`: Frontend, Backend, DB, Dependencies
- `database_schema`: Tables, Relationships
- `api_endpoints`: Routes with auth info
- `business_rules`: Business rules
- `features`: Features and statuses
- `knowledge_items`: Patterns, Gotchas, Conventions

### session.json (Dynamic - constantly changing) ⭐ NEW
- `working_on`: Feature, task, status, files being modified
- `pending_tasks`: Tasks to do next
- `recent_changes`: Recent changes
- `errors_encountered`: Errors encountered and how to fix them
- `decisions_made`: Decisions made in this session

### preferences.json (User settings) ⭐ NEW
- `communication`: Tone, persona
- `technical`: Detail level, autonomy, quality
- `working_style`: Pace, feedback style
- `custom_rules`: User's custom rules

---

## 🛡️ Resilience Patterns - v3.3 (Hidden from User)

> **Principle:** Users do not need to know about retry, timeout, fallback. AI handles them in the background.

### Auto-Retry (Hidden)
```
When encountering a transient error (network, rate limit):
1. Retry 1st time (wait 1s)
2. Retry 2nd time (wait 2s)
3. Retry 3rd time (wait 4s)
4. If still failing → Notify user in simple language
```

### Timeout Protection (Hidden)
```
Each task has a default timeout:
- /code: 5 minutes
- /deploy: 10 minutes
- /debug: 5 minutes
- Others: 3 minutes

Upon timeout → "This is taking too long, do you want to continue?"
```

### Fallback Conversation (Shown when needed)
```
Instead of complex syntax like: /deploy production || staging

AI asks in simple language:
"Could not deploy to production 😅
 Do you want to try staging first?
 1️⃣ Yes - Deploy staging
 2️⃣ No - I will inspect the error"
```

### Error Messages (Simplified)
```
❌ Old: "Error: ECONNREFUSED 127.0.0.1:5432 - Connection refused"

✅ New: "Could not connect to database 😅
        Please check if PostgreSQL is running!
        Type /debug if you need my help."
```

### Error Categories
| Error Type | AI Action | User Sees |
|----------|----------|-----------|
| Network timeout | Auto-retry 3x | Nothing (if successful) |
| Rate limit | Wait and retry | "Waiting for API..." |
| Auth failed | Report immediately | "Please check your credentials" |
| Code syntax | Suggest fix | "Error in file X, type /debug" |
| Build failed | Analyze log | "Build failed due to Y, I propose..." |

---

## 🎮 Recommended Workflow

### 📦 New project
```
/init → /plan → /visualize → /code → /run → /test → /deploy → /save-brain
```

### 🌅 Starting a new day
```
/recap → /code → /run → /test → /save-brain
```

### 🐛 Encountering errors
```
/debug → /test → (if messy) /rollback
```

### 🚀 Before release
```
/audit → /test → /deploy → /save-brain
```

---

## 📊 System Statistics v3.4

| Workflow | Size | Quality |
|----------|------|------------|
| `/plan` | **5.4KB** | ⭐⭐⭐⭐⭐ Ultimate |
| `/deploy` | **5.3KB** | ⭐⭐⭐⭐⭐ Ultimate |
| `/init` | 4.9KB | ⭐⭐⭐⭐⭐ Complete |
| `/visualize` | 4.8KB | ⭐⭐⭐⭐⭐ Complete |
| `/debug` | 4.7KB | ⭐⭐⭐⭐⭐ Complete |

| `/save-brain` | **4.2KB** | ⭐⭐⭐⭐⭐ Ultimate |
| `/audit` | 4.2KB | ⭐⭐⭐⭐⭐ Complete |
| `/refactor` | 4.2KB | ⭐⭐⭐⭐⭐ Complete |
| `/code` | 3.6KB | ⭐⭐⭐⭐⭐ Complete |
| `/run` | 2.6KB | ⭐⭐⭐⭐ Good |
| `/test` | 2.4KB | ⭐⭐⭐⭐ Good |
| `/recap` | 2.4KB | ⭐⭐⭐⭐ Good |
| `/rollback` | 2.2KB | ⭐⭐⭐⭐ Good |

**Total:** 13 workflows | **~55KB** instructions | **50+ blind spots** handled

---

## 💡 Tips for Vibe Coders

1. **Just speak naturally** - AI will ask if anything is missing
2. **Don't fear making mistakes** - `/rollback` is available
3. **`/save-brain` at the end of the day** - No context lost tomorrow
4. **`/audit` periodically** - Prevention is better than cure
5. **`/deploy` before release** - Fully covers SEO, Analytics, Legal

---

*Vibe Coding Suite v3.4 - Your dreams, our engineering.*
