#!/usr/bin/env sh
set -eu

SCRIPT_DIR=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
REPO_ROOT=$(CDPATH= cd -- "$SCRIPT_DIR/.." && pwd)
SRC_PATH="$REPO_ROOT/src"

if [ -x "$REPO_ROOT/.venv/bin/python" ]; then
    PYTHON="$REPO_ROOT/.venv/bin/python"
elif command -v python3 >/dev/null 2>&1; then
    PYTHON="python3"
else
    PYTHON="python"
fi

if [ -z "${PYTHONPATH:-}" ]; then
    export PYTHONPATH="$SRC_PATH"
else
    export PYTHONPATH="$SRC_PATH:$PYTHONPATH"
fi

if [ -t 0 ] && [ $# -eq 0 ]; then
    echo "[INFO] Running MCP server in stdio transport mode (waiting for JSON-RPC input)..."
    echo "[INFO] Press Ctrl+C to exit."
fi

exec "$PYTHON" -m ai_agent_standards_mcp "$@"
