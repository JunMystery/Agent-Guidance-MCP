#!/usr/bin/env bash
set -e

echo "=== Agent Guidance MCP Installer (macOS/Linux) ==="

# 1. Detect or Install 'uv'
UV_BIN=""
if command -v uv &> /dev/null; then
    UV_BIN="uv"
    echo "Found existing 'uv' installation."
else
    # Check ~/.local/bin/uv
    if [ -f "$HOME/.local/bin/uv" ]; then
        UV_BIN="$HOME/.local/bin/uv"
        echo "Found 'uv' at $UV_BIN"
    else
        echo "'uv' toolchain not found. Installing uv (fast, zero-dependency Python package runner)..."
        curl -LsSf https://astral.sh/uv/install.sh | sh
        UV_BIN="$HOME/.local/bin/uv"
    fi
fi

# 2. Install the Agent Guidance MCP tool
echo "Installing agent-guidance-mcp from PyPI..."
"$UV_BIN" tool install agent-guidance-mcp --force

# 3. Resolve the path of the installed tool to run the setup
TOOL_BIN="$HOME/.local/bin/agent-guidance-mcp"
if [ ! -f "$TOOL_BIN" ]; then
    # Fallback to look up in path or cargo/uv default locations
    if command -v agent-guidance-mcp &> /dev/null; then
        TOOL_BIN="agent-guidance-mcp"
    fi
fi

echo "Running post-install configuration..."
if [ -f "$TOOL_BIN" ] || command -v agent-guidance-mcp &> /dev/null; then
    "$TOOL_BIN" --setup
    "$TOOL_BIN" --update
else
    # Fallback: run via uv tool run directly
    "$UV_BIN" tool run agent-guidance-mcp --setup
    "$UV_BIN" tool run agent-guidance-mcp --update
fi

echo ""
echo "✓ Installation completed successfully!"
