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
echo "Installing agent-guidance-mcp..."
INSTALLED=false

# Try local path first
if [ -f "pyproject.toml" ]; then
    echo "Found local pyproject.toml, installing from local path..."
    if "$UV_BIN" tool install . --force -q; then
        INSTALLED=true
    fi
fi

# Try PyPI next
if [ "$INSTALLED" = false ]; then
    echo "Attempting installation from PyPI..."
    if "$UV_BIN" tool install agent-guidance-mcp --force &> /dev/null; then
        INSTALLED=true
    else
        echo "PyPI installation failed (package may not be published yet). Falling back to GitHub..."
    fi
fi

# Fallback to GitHub Git installation
if [ "$INSTALLED" = false ]; then
    echo "Installing directly from GitHub repository..."
    "$UV_BIN" tool install git+https://github.com/JunMystery/Agent-Guidance-MCP.git --force
fi

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
