#!/usr/bin/env bash
set -e

echo "=== Agent Guidance MCP Uninstaller (macOS/Linux) ==="

# 1. Resolve path of the installed tool to run the clean-up
TOOL_BIN="$HOME/.local/bin/agent-guidance-mcp"
if [ ! -f "$TOOL_BIN" ]; then
    if command -v agent-guidance-mcp &> /dev/null; then
        TOOL_BIN="agent-guidance-mcp"
    fi
fi

# 2. Run setup's uninstall logic to remove integrations
echo "Removing client registrations and local standards data..."
if [ -f "$TOOL_BIN" ] || command -v agent-guidance-mcp &> /dev/null; then
    "$TOOL_BIN" --uninstall
else
    # Fallback to run via uv tool run directly
    if command -v uv &> /dev/null; then
        uv tool run agent-guidance-mcp --uninstall
    elif [ -f "$HOME/.local/bin/uv" ]; then
        "$HOME/.local/bin/uv" tool run agent-guidance-mcp --uninstall
    fi
fi

# 3. Uninstall the tool from uv
echo "Uninstalling agent-guidance-mcp tool..."
if command -v uv &> /dev/null; then
    uv tool uninstall agent-guidance-mcp
elif [ -f "$HOME/.local/bin/uv" ]; then
    "$HOME/.local/bin/uv" tool uninstall agent-guidance-mcp
fi

echo ""
echo "✓ Uninstallation completed successfully!"
