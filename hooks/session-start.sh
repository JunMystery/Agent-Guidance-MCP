#!/bin/bash
# agent-guidance-mcp session-start hook
# Passes the priority gate and injects project context at session start.
#
# Tries, in order:
#   1. agent-guidance-mcp --session-start (installed binary or pipx/uv tool)
#   2. python -m agent_guidance_mcp --session-start (development install)
#   3. Fallback: inject using-agent-skills meta-skill only

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"

run_session_start() {
  local cmd="$1"
  shift
  "$cmd" --session-start --project-path "$PROJECT_DIR" "$@" 2>/dev/null
}

# Priority 1: installed binary on PATH
if command -v agent-guidance-mcp >/dev/null 2>&1; then
  output=$(run_session_start agent-guidance-mcp)
  if [ -n "$output" ] && echo "$output" | python -c "import json,sys;json.loads(sys.stdin.read())" 2>/dev/null; then
    echo "$output"
    exit 0
  fi
fi

# Priority 2: python -m module (development / editable install)
if python -c "import agent_guidance_mcp" 2>/dev/null; then
  output=$(run_session_start python -m agent_guidance_mcp)
  if [ -n "$output" ] && echo "$output" | python -c "import json,sys;json.loads(sys.stdin.read())" 2>/dev/null; then
    echo "$output"
    exit 0
  fi
fi

# Fallback: inject using-agent-skills meta-skill
SKILLS_DIR="$(dirname "$SCRIPT_DIR")/skills"
META_SKILL="$SKILLS_DIR/using-agent-skills/SKILL.md"

if command -v jq >/dev/null 2>&1 && [ -f "$META_SKILL" ]; then
  CONTENT=$(cat "$META_SKILL")
  jq -cn \
    --arg message "agent-skills loaded. Use the skill discovery flowchart to find the right skill for your task.

$CONTENT" \
    '{priority: "IMPORTANT", message: $message}'
elif [ -f "$META_SKILL" ]; then
  # jq not available, use python for JSON construction
  python -c "
import json
skill = open('$META_SKILL', encoding='utf-8').read()
print(json.dumps({
  'priority': 'IMPORTANT',
  'message': 'agent-skills loaded. Use the skill discovery flowchart to find the right skill for your task.\n\n' + skill
}))
" 2>/dev/null || echo '{"priority": "INFO", "message": "agent-guidance-mcp: session-start unavailable. Install agent-guidance-mcp or jq for full context injection."}'
else
  echo '{"priority": "INFO", "message": "agent-guidance-mcp: session-start unavailable and meta-skill not found. Skills remain available individually."}'
fi
