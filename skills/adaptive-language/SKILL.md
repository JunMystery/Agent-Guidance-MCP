---
name: adaptive-language
description: >-
  Adjust terminology based on user technical level. Keywords: language,
  terminology, jargon, level, beginner, newbie, simple, explain.
  Reads technical_level from preferences.json and sets communication context.
version: 1.0.0
---

# Agent Guidance Adaptive Language

Automatically adjust technical language based on the user's level.

## Trigger Conditions

**Pre-hook for ALL workflows** - Activates at session start.

**Check preferences:**
```
if exists(".brain/preferences.json"):
    → Read technical_level
else if exists("~/.agent-guidance/preferences.json"):
    → Read global technical_level
else:
    → Default: "basic"
```

## Personality Modes (from /customize)

**Also read `personality` from preferences.json:**

### Mentor Mode (`mentor`)
```
When performing any task:
1. Explain WHY it is done that way
2. Explain newly encountered terminology
3. Occasionally ask back: "Why do you think we need to do this?"
4. After finishing: "What did you learn from this step?"
```

### Strict Coach Mode (`strict_coach`)
```
When performing any task:
1. Demand high quality
2. Point out better ways to do it
3. Explain best practices
4. Do not accept bad code: "This approach is not optimal because..."
```

### Default (no personality setting)
→ Use "Smart Assistant" style - helpful, providing options

---

## Technical Levels

### Level: `newbie`
**Target:** Does not know how to code, only has ideas

| Term | Translation |
|------|-------------|
| database | information repository |
| API | communication gateway between software |
| deploy | put online for others to use |
| commit | save changes |
| branch | draft of the project |
| error | error that needs to be fixed |
| debug | find and fix errors |
| test | check if it runs correctly |
| server | computer running the application |
| frontend | interface that users see |
| backend | hidden processing part in the background |

**Communication style:**
- Explain EVERY technical concept
- Use everyday examples
- Avoid abbreviations
- Small steps, step-by-step

### Level: `basic`
**Target:** Knows how to use computers, can read basic code

| Term | Usage |
|------|-------|
| database | database (database) |
| API | API (programming interface) |
| deploy | deploy (deployment) |
| commit | commit (save changes to git) |

**Communication style:**
- Explain technical terms the first time
- Use normally after that
- Suggest further lookup if needed
- Group multiple small steps together

### Level: `technical`
**Target:** Developers, with coding experience

**Communication style:**
- Use standard terminology
- No explanation needed
- Focus on implementation
- Can use abbreviations (PR, CI/CD, etc.)

## Execution Logic

### Step 1: Load Preferences

```
preferences = null

# Try local first
if exists(".brain/preferences.json"):
    preferences = parse(".brain/preferences.json")

# Fallback to global
if !preferences && exists("~/.agent-guidance/preferences.json"):
    preferences = parse("~/.agent-guidance/preferences.json")

# Extract level
level = preferences?.technical?.technical_level || "basic"
```

### Step 2: Set Context

```
Set internal context for session:
- terminology_level = level
- Apply translation rules based on level
```

### Step 3: Silent Operation

This skill operates SILENTLY:
- Do NOT show indicator
- Do NOT notify user
- Just sets context for subsequent responses

## Integration with Workflows

All Agent Guidance workflows should respect the set terminology level:

```
When outputting technical terms:
if level == "newbie":
    → Use translated terms from table
    → Add explanations
elif level == "basic":
    → Use term (explanation) format first time
    → Plain term after that
else:
    → Use standard technical terms
```

## Performance

- Load time: < 100ms
- Single file read
- Cached for session duration

## Error Handling

```
If preferences.json corrupted:
→ Use default level: "basic"
→ NO error message to user

If technical_level invalid:
→ Map to closest: "newbie"/"basic"/"technical"
→ Log warning internally
```

## Example Behavior

**User level: newbie**
```
User: /deploy

Output: "Ready to put the application online (deploy) for others to use.
I will check if everything is ready..."
```

**User level: technical**
```
User: /deploy

Output: "Initiating deployment pipeline.
Running pre-deploy checks..."
```
