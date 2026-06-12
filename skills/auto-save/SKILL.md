---
name: auto-save
description: >-
  Eternal Context System - Auto-save session to prevent context loss.
  Triggers: workflow end, user leaving, decisions, periodic checkpoint.
  Warns when context is getting full.
version: 1.0.0
---

# Agent Guidance Auto-Save (Eternal Context)

Tu dong luu session de khong bao gio mat context.

## Trigger Conditions

### 1. Workflow End (Automatic)
Sau khi hoan thanh bat ky workflow nao:
- `/plan` → Save decisions, specs
- `/code` → Save progress, files changed
- `/debug` → Save errors resolved
- `/test` → Save test results
- `/deploy` → Save deployment info

### 2. User Leaving Detection
Pattern matching trong tin nhan user:
```
patterns:
  - "bye", "tam biet", "tam nghi"
  - "toi di", "di an com", "nghi thoi"
  - "het gio", "mai lam tiep", "save"
  - "dong app", "tat may"
```

### 3. Decision Made Detection
Khi user dua ra quyet dinh:
```
patterns:
  - "chon phuong an", "dung cai nay"
  - "ok", "dong y", "lam vay"
  - "quyet dinh la", "se dung"
```

### 4. Periodic Checkpoint
Moi 15 tin nhan → Background save

### 5. Context Warning (80% estimate)
```
token_estimate = message_count * 150 + code_blocks * 300
if token_estimate > 100000:  # 80% of 128K
    trigger_emergency_save()
    show_warning()
```

## Execution Logic

### Step 1: Detect Trigger

```
on_message(user_input):
    increment message_count

    if matches_leaving_pattern(user_input):
        trigger = "user_leaving"
    elif matches_decision_pattern(user_input):
        trigger = "decision_made"
    elif message_count % 15 == 0:
        trigger = "periodic"
    elif estimate_tokens() > 100000:
        trigger = "emergency"
    else:
        return  # No save needed

    execute_save(trigger)
```

### Step 2: Generate Summary

```
summary = {
    project: brain.project.name,
    current_feature: session.working_on.feature,
    current_task: session.working_on.task,
    status: session.working_on.status,
    progress_percent: calculate_progress(),
    last_action: get_last_action(),
    next_step: suggest_next_step()
}
```

### Step 3: Save to Session

```
session.summary = summary
session.message_count = current_count
session.context_checkpoints.append({
    timestamp: now(),
    trigger: trigger_type,
    summary: compress_summary(summary),
    message_count: current_count
})
save_to_file(".brain/session.json")
```

### Step 4: Notify User (if enabled)

```
if trigger == "user_leaving":
    show: "💾 Thay ban chuan bi di, da auto-save session."

if trigger == "workflow_end":
    show: "💾 Da luu tien do. Ban co the dong app an toan."

if trigger == "emergency":
    show: "⚠️ Context sap day. Da save backup. Nen bat dau session moi."

if trigger == "periodic" or "decision_made":
    # Silent save - no notification
```

## Token Estimation Heuristic

```
function estimate_tokens():
    base = message_count * 150
    code_blocks = count_code_blocks() * 300
    error_dumps = count_errors() * 200

    return base + code_blocks + error_dumps

function get_warning_level():
    tokens = estimate_tokens()
    if tokens > 115000: return "critical"  # 90%
    if tokens > 100000: return "warning"   # 80%
    if tokens > 80000: return "info"       # 60%
    return "safe"
```

## Snapshot Management

### Save Snapshot (7 days retention)
```
on_workflow_end():
    snapshot = {
        timestamp: now(),
        session: session.json,
        brain_summary: extract_brain_summary()
    }
    save_to(".brain/snapshots/{date}_{time}.json")

    # Cleanup old snapshots
    delete_snapshots_older_than(7_days)
```

### Restore from Snapshot
```
if session.json corrupted:
    latest_snapshot = get_latest_snapshot()
    restore_from(latest_snapshot)
    show: "Da khoi phuc tu backup gan nhat."
```

## User Messages

```yaml
workflow_end:
  vi: "💾 Da luu tien do. Ban co the dong app an toan."
  en: "💾 Progress saved. You can safely close the app."

user_leaving:
  vi: "💾 Thay ban chuan bi di, da auto-save session."
  en: "💾 Detected you're leaving, session auto-saved."

context_warning:
  vi: "⚠️ Context sap day. Da save backup. Nen go /save-brain roi bat dau session moi."
  en: "⚠️ Context nearly full. Backup saved. Consider starting new session."

emergency_save:
  vi: "⚠️ Da luu khan cap. Go /recap trong session moi de tiep tuc."
  en: "⚠️ Emergency save complete. Use /recap in new session to continue."
```

## Integration with Workflows

Moi workflow PHAI goi auto-save khi ket thuc:

```markdown
# Cuoi moi workflow.md:

## Post-Workflow: Auto-Save

Sau khi hoan thanh workflow:
1. Cap nhat session.summary
2. Append vao context_checkpoints
3. Hien thong bao: "💾 Da luu tien do."
```

## Config Options

```json
{
  "auto_save_config": {
    "enabled": true,
    "notify_on_save": true,
    "checkpoint_interval": 15,
    "warn_threshold": 80,
    "snapshot_retention_days": 7
  }
}
```

## Error Handling

```
if save_fails:
    retry 3 times with exponential backoff
    if still fails:
        show: "⚠️ Khong the luu session. Kiem tra quyen ghi file."
        log error to console

if disk_full:
    delete oldest snapshots
    retry save
```
