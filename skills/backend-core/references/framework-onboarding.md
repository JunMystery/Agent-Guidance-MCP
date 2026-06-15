---
name: framework-onboarding
description: >-
  First-time user onboarding experience. Keywords: new, first, start, begin,
  welcome, tutorial, guide, learn, help me.
  Activates on first /init or when .brain/preferences.json doesn't exist.
version: 1.0.0
---

# Agent Guidance Onboarding

Guide new users to get familiar with Agent Guidance.

## Trigger Conditions

**Activates when:**
- User runs `/init` for the first time (no `.brain/` folder)
- User runs `/help` and has no preferences yet
- User says "new user", "guide", "don't know where to start"

**Check:**
```
if NOT exists(".brain/preferences.json") AND NOT exists("~/.agent-guidance/preferences.json"):
     Activate onboarding
else:
     Skip (returning user)
```

## Execution Logic

### Step 1: Welcome Message

```
👋 **WELCOME TO Agent Guidance!**

I am your AI assistant, and I will help you turn your ideas into a real app.

🎯 Agent Guidance can help you:
   • Create apps/websites from scratch
   • No coding required (I will do it for you!)
   • Remember everything between work sessions

⏱️ Give me 2 minutes for a quick guide, okay?

1️⃣ Yes, guide me
2️⃣ No need, start right away
```

### Step 2: Quick Assessment (if 1 is chosen)

```
📊 **I NEED TO UNDERSTAND YOU A LITTLE BIT:**

Have you ever built an app/website before?

1️⃣ Never (newbie)
   → I will explain everything simply

2️⃣ Know a little bit (basic)
   → I will explain when needed

3️⃣ IT professional (technical)
   → I will talk like a colleague
```

### Step 3: 5 Commands Tour

```
🗺️ **5 MOST IMPORTANT COMMANDS:**

┌─────────────────────────────────────────┐
│ 1️⃣ /brainstorm                          │
│    "I have an idea but it's not clear"  │
│    → AI helps clarify the idea          │
├─────────────────────────────────────────┤
│ 2️⃣ /plan                                │
│    "I know what I want to do"           │
│    → AI creates a detailed plan         │
├─────────────────────────────────────────┤
│ 3️⃣ /code                                │
│    "Start writing code"                 │
│    → AI codes according to the plan     │
├─────────────────────────────────────────┤
│ 4️⃣ /run                                 │
│    "Let's run and test"                 │
│    → Start the app to see results       │
├─────────────────────────────────────────┤
│ 5️⃣ /debug                               │
│    "There is an error, please fix it"   │
│    → AI finds and fixes errors          │
└─────────────────────────────────────────┘

💡 Tip: No need to remember everything! Type /next at any time
   to have me suggest what to do next.
```

### Step 4: Quick Start Options

```
🚀 **LET'S START!**

What do you want to do?

1️⃣ I already have an app idea → /plan
2️⃣ Not clear, want to discuss first → /brainstorm
3️⃣ More detailed instructions → /help
4️⃣ Customize how AI talks → /customize
```

### Step 5: Initialize .brain/ Folder

**Create folder structure:**
```
.brain/
├── preferences.json
├── session.json
├── session_log.txt
└── brain.json
```

**preferences.json:**
```json
{
  "communication": {
    "tone": "friendly",
    "personality": "assistant"
  },
  "technical": {
    "technical_level": "[user_choice]",
    "detail_level": "simple",
    "autonomy_level": "ask_often"
  },
  "onboarding_completed": true,
  "onboarding_date": "[timestamp]"
}
```

**session.json:**
```json
{
  "updated_at": "[timestamp]",
  "working_on": {
    "feature": null,
    "task": null,
    "status": "idle"
  },
  "pending_tasks": [],
  "errors_encountered": [],
  "decisions_made": [
    {
      "decision": "Technical level set to [level]",
      "reason": "User selection during onboarding"
    }
  ],
  "skipped_tests": []
}
```

**session_log.txt:**
```
[YYYY-MM-DD HH:MM] ONBOARDING COMPLETE
[YYYY-MM-DD HH:MM] Technical level: [level]
[YYYY-MM-DD HH:MM] Ready for first project
```

**brain.json:**
```json
{
  "meta": {
    "schema_version": "1.0.0",
    "framework_version": "4.0.2",
    "created_at": "[timestamp]"
  },
  "project": {
    "name": null,
    "type": null,
    "status": "not_started"
  },
  "updated_at": "[timestamp]"
}
```

### Step 6: Save & Complete

```
✅ **SETUP COMPLETE!**

I have created:
📁 .brain/
   ├── preferences.json  (your settings)
   ├── session.json      (progress tracking)
   ├── session_log.txt   (log)
   └── brain.json        (project knowledge)

💾 Everything will be automatically saved from now on!

────────────────────────

What do you want to do now?

1️⃣ Create your first project → /init
2️⃣ Discuss ideas first → /brainstorm
3️⃣ See detailed guide → /help
```

## Returning User Detection

```
if exists("preferences.json") AND preferences.onboarding_completed == true:

     If not used for > 7 days:
          "👋 Welcome back! Type /recap to have me remind you what you were doing."

     If < 7 days:
          Skip welcome, go straight to workflow
```

## Error Handling

```
If cannot create .brain/ folder:
    Try create in current directory
    If still fail:
        Warning: "⚠️ I could not create the storage folder, but we can still work!"
        Continue in-memory mode

If user skips all steps:
    Use defaults: technical_level = "basic"
    Mark onboarding_completed = true
```

## Integration

**With /init:**
```
/init is called
    ↓
Check .brain/ folder
    ↓
├── Not exists → Run onboarding FIRST
└── Exists → Run /init normally
```

## Performance

- Total time: < 2 minutes
- No external API calls
- Minimal file I/O
