---
description: Initialize a new project workspace
---

# WORKFLOW: /init - Initialize Project

**Role:** Project Initializer
**Goal:** Capture ideas and create a basic workspace. DO NOT install packages, DO NOT setup database.

**LANGUAGE: Always reply in English.**

---

## Flow Position

```
[/init] ← YOU ARE HERE
   ↓
/brainstorm (if the idea is not yet clear)
   ↓
/plan (plan features)
   ↓
/design (technical design)
   ↓
/code (write code)
```

---

## Stage 1: Capture Vision (ASK BRIEFLY)

### 1.1. Project Name
"What is the project name? (e.g., my-coffee-app)"

### 1.2. 1-sentence description
"Briefly describe what the app does? (1-2 sentences)"

### 1.3. Location
"Create in the current directory or somewhere else?"

**DONE. Do not ask more.**

---

## Stage 2: Create Workspace (FOLDER ONLY)

Only create basic folder structure:

```
{project-name}/
├── .brain/
│   └── brain.json      # Project context (empty template)
├── docs/
│   └── ideas.md        # Write down ideas
└── README.md           # Name + description
```

### brain.json template:
```json
{
  "project": {
    "name": "{project-name}",
    "description": "{description}",
    "created_at": "{timestamp}"
  },
  "tech_stack": [],
  "features": [],
  "decisions": []
}
```

### README.md template:
```markdown
# {Project Name}

{1-sentence description}

## Status: 🚧 Planning

The project is currently in the ideation phase.

## Next Steps

1. Type `/brainstorm` to explore ideas
2. Or `/plan` if you already know what you want to do
```

---

## Stage 3: Confirmation & Guidance

```
✅ Workspace created for "{project-name}"!

📁 Location: {path}

🚀 NEXT STEPS:

Choose 1 of 2:

1️⃣ /brainstorm - If you are not sure what to do yet, need to explore ideas
2️⃣ /plan - If you already know the features that need to be made

💡 Tip: Newbies should choose /brainstorm first!
```

---

## IMPORTANT - DO NOT DO

❌ DO NOT install packages (let /code do it)
❌ DO NOT setup database (let /design do it)
❌ DO NOT create code files (let /code do it)
❌ DO NOT run npm/yarn/pnpm
❌ DO NOT ask about tech stack (AI will decide later)

---

## First-time User

If `.brain/preferences.json` does not exist yet:

```
👋 Welcome to Agent Guidance!

This is your first time. Do you want to:
1️⃣ Use defaults (Recommended)
2️⃣ Customize (/customize)
```

---

## Error Handling

### Folder already exists:
```
⚠️ Folder "{name}" already exists.
1️⃣ Use this folder (may overwrite)
2️⃣ Rename it
```

### No permission to create folder:
```
❌ Could not create folder. Please check write permissions!
```
