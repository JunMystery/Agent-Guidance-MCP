---
description: Review and hand over project context
---

# WORKFLOW: /review - The Project Scanner

You are a **Project Analyst**. Mission: Scan the entire project and create an easy-to-understand report to:
1. You (or someone else) can take over the project quickly
2. Assess the "health" of the current code
3. Plan for upgrades

---

## 🎯 Non-Tech Mode (v4.0)

**Read preferences.json to adjust language:**

```
if technical_level == "newbie":
    → Hide technical details (dependencies, architecture)
    → Only show: "What the app does", "How to run", "Simple fixes"
    → Use casual/everyday language
```

### Report for newbie:
```
❌ DON'T: "Architecture: Next.js App Router with Server Components..."
✅ DO:  "📱 Expense tracker app - Helps track daily cash flow"
```

---

## Phase 1: Ask for Purpose

```
"🔍 What is the purpose of reviewing the project?

1️⃣ **Self-review** - Forgot what I was doing
2️⃣ **Handover** - Transfer it to someone else to take over  
3️⃣ **Evaluation** - See if there are any issues with the code
4️⃣ **Plan upgrades** - Prepare to add new features

(Or tell me your purpose directly)"
```

---

## Phase 2: Automatic Project Scan

AI automatically executes:

### 2.1. Read directory structure
```bash
# List main files/folders
# Count code files
# Detect framework being used
```

### 2.2. Read package.json (if available)
```bash
# Determine tech stack
# Library versions
# Available scripts
```

### 2.3. Read README, docs/ (if available)
```bash
# Project description
# Installation guide
```

### 2.4. Read .brain/ (if available)
```bash
# Most recent session
# Working context
```

---

## Phase 3: Create Report

### 3.1. Report for "Self-review" or "Handover" purpose

```markdown
# 📊 PROJECT REPORT: [Name]

## 🎯 What does this app do?
[2-3 sentences description in everyday language]

## 📁 Main structure
```
[Simple folder tree, only important folders]
```

## 🛠️ Tech Stack Used
| Component | Technology |
|------------|-----------|
| Framework | [Next.js 14] |
| Interface | [TailwindCSS] |
| Database | [Supabase] |

## 🚀 How to run
```bash
npm install
npm run dev
# Open http://localhost:3000
```

## 📍 What is currently work-in-progress?
[Read from session.json if available]
- Feature: [...]
- Next task: [...]

## 📝 Important files to know
| File | Function |
|------|-----------|
| `app/page.tsx` | Homepage |
| `components/...` | UI components |
| `lib/...` | Processing/helper logic |

## ⚠️ Handover Notes
- [Note 1]
- [Note 2]
```

### 3.2. Report for "Evaluation" purpose

```markdown
# 🏥 CODE HEALTH ASSESSMENT: [Name]

## 📊 Overview
| Metric | Result | Assessment |
|--------|---------|----------|
| Build | ✅ Success / ❌ Error | [Good/Needs fixing] |
| Lint | X warnings | [Good/Needs improvement] |
| TypeScript | X errors | [Good/Needs fixing] |

## ✅ Good points
- [Point 1]
- [Point 2]

## ⚠️ Needs Improvement
| Issue | Priority | Suggestion |
|--------|---------|-------|
| [Issue 1] | 🔴 High | [How to fix] |
| [Issue 2] | 🟡 Medium | [How to fix] |
| [Issue 3] | 🟢 Low | [How to fix] |

## 🔧 Improvement Suggestions
1. [Suggestion 1]
2. [Suggestion 2]
```

### 3.3. Report for "Upgrade Planning" purpose

```markdown
# 🚀 UPGRADE PLAN: [Name]

## 📍 Current Status
[Short description]

## ⬆️ Potential Upgrades

### Dependencies that need update
| Package | Current | Latest | Risk |
|---------|----------|----------|--------|
| next | 14.0 | 14.2 | 🟢 Safe |
| [pkg] | [v1] | [v2] | 🟡 Needs testing |

### Features that can be added
Based on the current architecture, we can easily add:
1. [Feature 1]
2. [Feature 2]

### Refactorings to perform
1. [Task 1] - Priority: 🔴 High
2. [Task 2] - Priority: 🟡 Medium

## ⚠️ Upgrade Risks
- [Risk 1]
- [Risk 2]
```

---

## Phase 4: Save Report

```
Create file: docs/PROJECT_REVIEW_[date].md

"📋 Created report at: docs/PROJECT_REVIEW_260130.md

What would you like to do next?
1️⃣ View details of a specific section
2️⃣ Start fixing the identified issues
3️⃣ Plan upgrades with /plan
4️⃣ Save for later with /save-brain"
```

---

## ⚠️ NEXT STEPS (Numbered Menu):
```
1️⃣ Fix issues? /debug or /refactor
2️⃣ Add features? /plan
3️⃣ Handover? /save-brain to package context
4️⃣ Continue coding? /code
```

---

## 🛡️ Resilience Patterns

### When package.json is missing
```
→ Inform user: "This is not a Node.js project. I will scan based on folder structure."
→ List file types found (.py, .java, .html...)
```

### When the folder is too large
```
→ Only scan the first 3 levels
→ Priority: src/, app/, components/, lib/, pages/
→ Ignore: node_modules/, .git/, dist/
```

### When there are no docs
```
→ "The project has no documentation. I will generate an overview based on the code."
```
