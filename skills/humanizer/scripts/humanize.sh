#!/bin/bash
set -e

if [ $# -eq 0 ]; then
    echo "Error: No text provided." >&2
    echo "Usage: $0 <text>" >&2
    exit 1
fi

TEXT="$1"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Try local path first, fallback to /mnt/skills/user/ if not found
if [ -f "$SCRIPT_DIR/humanize_logic.py" ]; then
    python3 "$SCRIPT_DIR/humanize_logic.py" "$TEXT"
else
    python3 /mnt/skills/user/humanizer/scripts/humanize_logic.py "$TEXT"
fi
