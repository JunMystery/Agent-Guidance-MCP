---
name: error-translator
description: >-
  Translate technical errors to human-friendly language. Keywords: error,
  translate, explain, help, fix, fail, broken, crash, bug.
  Activates on /debug, /code, /test when errors detected.
version: 1.0.0
---

# Agent Guidance Error Translator

Translate technical errors into plain language for non-tech users.

## Trigger Conditions

**Post-hook for:** `/debug`, `/code`, `/test`

**When:** Error message detected in output

## Execution Logic

### Step 1: Detect Error

```
if output contains error patterns:
    → Activate translation
else:
    → Skip (no error)
```

### Step 2: Match & Translate

Match error against database, return human message + action.

### Step 3: Display

```
❌ Error: [human message]
💡 Suggestion: [action]
```

## Error Translation Database

### Database Errors

| Pattern | Human Message | Action |
|---------|---------------|--------|
| `ECONNREFUSED` | Database is not running | Start PostgreSQL/MySQL |
| `ETIMEDOUT` | Database response is too slow | Check network connection |
| `ER_ACCESS_DENIED` | Incorrect database password | Check .env file |
| `relation .* does not exist` | Table does not exist | Run migrations: `/run migrate` |
| `duplicate key` | Duplicate data | Check unique constraints |

### JavaScript/TypeScript Errors

| Pattern | Human Message | Action |
|---------|---------------|--------|
| `TypeError: Cannot read` | Attempting to read an unassigned variable | Check for null/undefined |
| `ReferenceError` | Using an undeclared variable | Check variable name |
| `SyntaxError` | Code syntax error | Check parentheses, semicolons |
| `Maximum call stack` | Infinite loop | Check termination condition |
| `Cannot find module` | Missing package | Run `npm install` |

### Network Errors

| Pattern | Human Message | Action |
|---------|---------------|--------|
| `fetch failed` | Cannot connect to server | Check URL and internet |
| `CORS` | Website blocked the request | Configure CORS on the server |
| `ERR_CERT` | SSL certificate error | Use HTTP instead of HTTPS (dev only) |
| `timeout` | Request took too long | Increase timeout or check server |
| `ENOTFOUND` | Domain does not exist | Double check the URL |

### Package Errors

| Pattern | Human Message | Action |
|---------|---------------|--------|
| `npm ERR!` | Package installation failed | Delete node_modules, reinstall |
| `peer dep` | Incompatible version | Update package.json |
| `EACCES` | Permission denied | Run with sudo or fix permissions |
| `ENOSPC` | Out of disk space | Clean up disk |
| `gyp ERR!` | Error building native module | Install build tools |

### Test Errors

| Pattern | Human Message | Action |
|---------|---------------|--------|
| `Expected .* but received` | Test failed - incorrect result | Fix code or update test |
| `Timeout` | Test took too long | Increase timeout or optimize |
| `before each hook` | Test setup failed | Check beforeEach |
| `snapshot` | UI changed | Update snapshot if correct |
| `coverage` | Missing test coverage | Write more tests |

### Build Errors

| Pattern | Human Message | Action |
|---------|---------------|--------|
| `tsc.*error` | TypeScript error | Fix type errors |
| `ESLint` | Code does not match style guidelines | Run lint fix |
| `Build failed` | Build failed | Read detailed logs |
| `Out of memory` | Out of RAM | Increase memory limit |
| `FATAL ERROR` | Fatal error | Restart and try again |

### Git Errors

| Pattern | Human Message | Action |
|---------|---------------|--------|
| `conflict` | Code conflicts detected | Merge conflict manually |
| `rejected` | Push rejected | Pull before pushing |
| `detached HEAD` | Not on any branch | Checkout to a branch |
| `not a git repo` | Git has not been initialized | Run `git init` |

### Deploy Errors

| Pattern | Human Message | Action |
|---------|---------------|--------|
| `502 Bad Gateway` | Server did not respond | Restart server |
| `503 Service` | Server overloaded | Scale up resources |
| `permission denied` | No deploy permission | Check credentials |
| `quota exceeded` | Quota exceeded | Upgrade plan |

## Output Format

```
🔍 Translating error...

❌ Error: [human_message]
   └─ Original: [original_error_snippet]

💡 Suggestion: [action]
   └─ Or run: /debug to learn more

────────────────────────────────
```

## Fallback

If no pattern matches:
```
❌ Error: An issue occurred
💡 Suggestion: Run /debug for a detailed analysis
```

## Performance

- Translation: < 100ms
- Pattern matching: Simple regex
- No external API calls

## Security

- Sanitize error messages (remove credentials, paths)
- Never expose sensitive info in translations
