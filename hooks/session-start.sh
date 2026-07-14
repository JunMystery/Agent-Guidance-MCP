#!/bin/bash
# agent-guidance-mcp session-start hook
# Passes priority gate and injects project context at session start.
# Tries: installed binary, python -m module, then fallback meta-skill.

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
TARGET_PROJECT_DIR="${CLAUDE_PROJECT_DIR:-$PWD}"

run_session_start() {
  "$1" --session-start --project-path "$TARGET_PROJECT_DIR" 2>/dev/null
}

# Priority 1: installed binary on PATH
if command -v agent-guidance-mcp >/dev/null 2>&1; then
  output=$(run_session_start agent-guidance-mcp)
  if echo "$output" | python -c "import json,sys;json.loads(sys.stdin.read())" 2>/dev/null; then
    echo "$output"; exit 0
  fi
fi

# Priority 2: python -m module (development/editable install)
if python -c "import agent_guidance_mcp" 2>/dev/null; then
  output=$(run_session_start python -m agent_guidance_mcp)
  if echo "$output" | python -c "import json,sys;json.loads(sys.stdin.read())" 2>/dev/null; then
    echo "$output"; exit 0
  fi
fi

# Fallback: inject using-agent-skills meta-skill
SKILLS_DIR="$(dirname "$SCRIPT_DIR")/skills"
META_SKILL="$SKILLS_DIR/using-agent-skills/SKILL.md"
if [ -f "$META_SKILL" ]; then
  SKILL=$(cat "$META_SKILL")
  python -c "import json; print(json.dumps({'priority':'IMPORTANT','message':'agent-skills loaded.\n\n${SKILL}'}))" 2>/dev/null
else
  echo '{"priority": "INFO", "message": "agent-guidance-mcp: session-start unavailable. Install agent-guidance-mcp for full context injection."}'
fi
