---
name: session-restore
description: >-
  Lazy-loading context restore with 3 levels. Fast startup with minimal tokens.
  Keywords: context, memory, session, restore, recap, remember, resume, continue.
version: 2.0.0
---

# Agent Guidance Session Restore (Lazy Loading)

Khoi phuc context voi 3 cap do de tiet kiem token.

## Load Levels

| Level | Tokens | Khi nao | Gi duoc load |
|-------|--------|---------|--------------|
| 1 | ~200 | Luon luon | summary, current task, blockers |
| 2 | ~800 | /recap full | + decisions, pending tasks, recent files |
| 3 | ~2000 | /recap deep | + full history, all errors, conversation |

## Trigger Conditions

### Auto-Trigger (Level 1 only)
- Bat dau session moi
- Truoc moi Agent Guidance workflow

### Manual Trigger
- `/recap` → Level 1 (nhanh)
- `/recap full` → Level 1 + 2
- `/recap deep` → Level 1 + 2 + 3
- `/recap [topic]` → Smart search

## Execution Logic

### Level 1: Instant Load (Always)

```
load_level_1():
    summary = session.summary

    show:
    """
    👋 Chao mung tro lai!

    📍 Project: {summary.project}
    📍 Dang lam: {summary.current_feature}
       └─ Task: {summary.current_task}
       └─ Status: {summary.status} ({summary.progress_percent}%)

    ⏭️ Buoc tiep: {summary.next_step}
    🕐 Last saved: {format_time(updated_at)}
    """

    # Token cost: ~200
```

### Level 2: On-Demand (When Requested)

```
load_level_2():
    load_level_1()

    decisions = session.decisions_made[-5:]  # Last 5
    pending = session.pending_tasks[:5]       # Next 5
    files = session.working_on.files

    show:
    """
    ─────────────────────────────
    📋 Quyet dinh gan day:
    {format_decisions(decisions)}

    📝 Viec can lam:
    {format_pending(pending)}

    📁 Files dang sua:
    {format_files(files)}
    """

    # Token cost: ~800 total
```

### Level 3: Deep Dive (Explicit Request)

```
load_level_3():
    load_level_2()

    errors = session.errors_encountered
    checkpoints = session.context_checkpoints
    changes = session.recent_changes

    show:
    """
    ─────────────────────────────
    🐛 Lich su loi:
    {format_errors(errors)}

    💾 Checkpoints:
    {format_checkpoints(checkpoints)}

    📜 Thay doi gan day:
    {format_changes(changes)}
    """

    # Token cost: ~2000 total
```

### Smart Search: /recap [topic]

```
recap_topic(topic):
    # Search in all tiers
    results = search_session(topic)
    results += search_brain(topic)

    show:
    """
    🔍 Tim kiem: "{topic}"

    {format_search_results(results)}
    """

    # Only load relevant context
```

## Auto-Inject (System Prompt)

Khi bat dau session, inject Level 1 vao system prompt:

```markdown
## Session Context (Auto-loaded)

- Project: {project}
- Feature: {current_feature}
- Task: {current_task}
- Status: {status} ({progress}%)
- Blockers: {blockers_count}

[Conversation continues below...]
```

## Token Budget

```
Total context: 128K tokens
├── System prompt: 10K (fixed)
├── Conversation: 100K (dynamic)
├── Session load: 8K max
│   ├── Level 1: 200 (always)
│   ├── Level 2: 600 (on-demand)
│   └── Level 3: 1200 (explicit)
└── Buffer: 10K (safety)
```

## Output Format

### /recap (Level 1)
```
👋 Chao mung tro lai!

📍 Project: ThaoCoffe
📍 Dang lam: User Authentication
   └─ Task: Login form validation
   └─ Status: coding (65%)

⏭️ Buoc tiep: Add password validation
🕐 Last saved: 2 gio truoc

💡 Go /recap full de xem chi tiet.
```

### /recap full (Level 1+2)
```
[Level 1 output]
─────────────────────────────
📋 Quyet dinh gan day:
  • Dung NextAuth (don gian hon)
  • Validation bang Zod
  • Session-based auth

📝 Viec can lam:
  1. [HIGH] Add password validation
  2. [MED] Implement remember me
  3. [LOW] Add forgot password

📁 Files dang sua:
  • src/app/login/page.tsx
  • src/lib/auth.ts
```

### /recap deep (All levels)
```
[Level 1+2 output]
─────────────────────────────
🐛 Lich su loi:
  • CORS error → Fixed: added middleware
  • Type error → Fixed: added null check

💾 Checkpoints (7 ngay):
  • 2024-01-15 14:30 - workflow_end
  • 2024-01-16 09:00 - user_leaving

📜 Thay doi gan day:
  • [feature] Added login form
  • [bugfix] Fixed CORS issue
```

## Error Handling

```
if session.json not found:
    show: "Chua co session. Bat dau moi nhe!"
    skip restore

if session.json corrupted:
    try: restore from latest snapshot
    if success:
        show: "Da khoi phuc tu backup."
    else:
        show: "Session bi loi. Bat dau fresh!"
        create new session

if summary missing:
    generate summary from available data
    save to session.json
```

## Performance

- Level 1 load: < 100ms
- Level 2 load: < 300ms
- Level 3 load: < 500ms
- Search: < 1s
