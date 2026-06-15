---
name: context-help
description: >-
  Context-aware help based on current workflow state. Keywords: help, what,
  how, confused, stuck, lost, guide, tutorial, explain.
  Activates on /help or when user asks questions.
version: 1.0.0
---

# Agent Guidance Context Help

Smart help based on the current context.

## Trigger Conditions

**Activates when:**
- User runs `/help`
- User types "?", "help", "how"
- User seems confused (repeated errors, long pause)

## Execution Logic

### Step 1: Read Context

```
context = {}

if exists(".brain/session.json"):
    context.workflow = session.working_on.feature
    context.task = session.working_on.task
    context.status = session.working_on.status
    context.pending = session.pending_tasks

if exists(".brain/brain.json"):
    context.project = brain.project.name
    context.tech = brain.tech_stack
```

### Step 2: Detect State

| State | Detection | Response |
|-------|-----------|----------|
| `no_project` | No .brain/ folder | Show onboarding |
| `planning` | workflow contains "plan" | Planning help |
| `coding` | workflow contains "code" | Coding help |
| `debugging` | workflow contains "debug" | Debug help |
| `deploying` | workflow contains "deploy" | Deploy help |
| `stuck` | status = "blocked" or pending > 5 | Stuck help |
| `idle` | No active workflow | General help |

### Step 3: Show Contextual Help

## Help Templates

### No Project State
```
🆕 No project yet

You can:
1. /brainstorm - Discuss ideas first
2. /init - Create a new project
3. Describe your idea to me

I will guide you step-by-step!
```

### Planning State
```
📋 Planning: {context.workflow}

You can:
1. Continue the current plan
2. /code - Start the first coding phase
3. Ask me about the design

💡 Tip: Good plan = Faster coding!
```

### Coding State
```
💻 Coding: {context.task}
   Status: {context.status}

You can:
1. Continue coding
2. /test - Check the code you just wrote
3. /debug - If you encounter an error
4. /save-brain - Save progress

💡 Pending tasks: {context.pending.length}
```

### Debugging State
```
🔧 Debugging: {context.task}

You can:
1. Describe the error in more detail
2. Paste the error message
3. /code - Go back to coding after fixing

💡 Tip: Copying and pasting errors helps me understand faster!
```

### Deploying State
```
🚀 Deploying: {context.workflow}

You can:
1. Continue the deployment process
2. /rollback - Rollback to the previous version if there is an error
3. Check the logs after deployment

⚠️ Remember to test thoroughly before deploying to production!
```

### Stuck State
```
😅 It seems you are stuck

Try these ways:
1. /recap - Review what you are doing
2. /debug - If there is an error
3. Take a 5-minute break and come back
4. Ask me about the specific problem

💡 {context.pending.length} pending tasks.
   Can temporarily skip the difficult task and do something else first?
```

### Idle/General State
```
👋 How can I help you?

Common commands:
┌─────────────────────────────────────┐
│ /next      │ Suggest the next task  │
│ /recap     │ Recall context         │
│ /brainstorm│ Discuss new ideas      │
│ /plan      │ Plan                   │
│ /code      │ Write code             │
└─────────────────────────────────────┘

Or ask me anything!
```

## Adaptive Language

Help responses adapt to `technical_level`:

**newbie:**
- Use pure Vietnamese
- Explain every concept
- Small, detailed steps

**basic:**
- Mix Vietnamese-English
- Explain terms on first occurrence
- Moderate steps

**technical:**
- Use standard terminology
- No explanation needed
- Focus on action

## Fallback

If context unreadable:
```
👋 I am here to help you!

Type /next for me to suggest what to do,
or describe your problem to me.
```

## Performance

- Context read: < 200ms
- Response generation: Instant
- No external API calls
