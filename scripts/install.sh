#!/usr/bin/env bash
set -e

# ── Colors ────────────────────────────────────────────────────────────────────
RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'
CYAN='\033[0;36m'; PURPLE='\033[0;35m'; BOLD='\033[1m'
GRAY='\033[0;90m'; NC='\033[0m'

# ── Header ────────────────────────────────────────────────────────────────────
echo -e ""
echo -e "${PURPLE}${BOLD}╔══════════════════════════════════════════════════════════════╗${NC}"
echo -e "${PURPLE}${BOLD}║           Agent Guidance MCP (macOS/Linux)                  ║${NC}"
echo -e "${PURPLE}${BOLD}╚══════════════════════════════════════════════════════════════╝${NC}"
echo -e ""

# ── Choose mode FIRST ─────────────────────────────────────────────────────────
echo -e "${BOLD}What would you like to do?${NC}"
echo -e "  ${GREEN}[1]${NC} Install — auto-configure all detected IDEs"
echo -e "  ${CYAN}[2]${NC} Install — manual (choose which IDEs to configure)"
echo -e "  ${RED}[3]${NC} Uninstall — remove everything"
echo -e ""

if [ -t 0 ]; then
    read -p "Choice [1]: " ACTION
else
    read -p "Choice [1]: " ACTION < /dev/tty 2>/dev/null || ACTION=""
fi
ACTION="${ACTION:-1}"

# ── Uninstall path ────────────────────────────────────────────────────────────
if [ "$ACTION" = "3" ]; then
    echo -e ""
    echo -e "${RED}${BOLD}🗑️  Uninstalling Agent Guidance MCP...${NC}"
    echo -e ""

    TOOL_BIN="$HOME/.local/bin/agent-guidance-mcp"
    if [ ! -f "$TOOL_BIN" ]; then
        command -v agent-guidance-mcp &> /dev/null && TOOL_BIN="agent-guidance-mcp"
    fi

    echo -e "${BOLD}Step 1/3 — Removing IDE registrations...${NC}"
    if [ -f "$TOOL_BIN" ] || command -v agent-guidance-mcp &> /dev/null; then
        "$TOOL_BIN" --uninstall 2>/dev/null && echo -e "  ${GREEN}✓${NC} Done" || echo -e "  ${GREEN}✓${NC} Done"
    else
        echo -e "  ${YELLOW}⚠${NC}  Tool not found — skipping"
    fi

    echo -e ""
    echo -e "${BOLD}Step 2/3 — Removing skills data...${NC}"
    if [ -d "$HOME/.agent-guidance" ]; then
        rm -rf "$HOME/.agent-guidance"
        echo -e "  ${GREEN}✓${NC} Removed ${GRAY}$HOME/.agent-guidance${NC}"
    else
        echo -e "  ${GRAY}•${NC}  Not found"
    fi

    echo -e ""
    echo -e "${BOLD}Step 3/3 — Removing MCP server...${NC}"
    if command -v uv &> /dev/null; then
        uv tool uninstall agent-guidance-mcp 2>/dev/null && echo -e "  ${GREEN}✓${NC} Uninstalled from uv" || echo -e "  ${GRAY}•${NC}  Not found in uv"
    elif [ -f "$HOME/.local/bin/uv" ]; then
        "$HOME/.local/bin/uv" tool uninstall agent-guidance-mcp 2>/dev/null && echo -e "  ${GREEN}✓${NC} Uninstalled from uv" || echo -e "  ${GRAY}•${NC}  Not found in uv"
    fi

    echo -e ""
    echo -e "${GREEN}${BOLD}╔══════════════════════════════════════════════════════════════╗${NC}"
    echo -e "${GREEN}${BOLD}║       ✓  Uninstallation complete!                           ║${NC}"
    echo -e "${GREEN}${BOLD}╚══════════════════════════════════════════════════════════════╝${NC}"
    echo -e ""
    exit 0
fi

# ── Install path ──────────────────────────────────────────────────────────────
echo -e ""

# ── Step 1: Detect or Install 'uv' ────────────────────────────────────────────
echo -e "${BOLD}📦 Step 1/3 — Checking Python toolchain (uv)...${NC}"
UV_BIN=""
if command -v uv &> /dev/null; then
    UV_BIN="uv"
    echo -e "  ${GREEN}✓${NC} Found 'uv' in PATH"
else
    if [ -f "$HOME/.local/bin/uv" ]; then
        UV_BIN="$HOME/.local/bin/uv"
        echo -e "  ${GREEN}✓${NC} Found 'uv' at ${GRAY}$UV_BIN${NC}"
    else
        echo -e "  ${YELLOW}⚡${NC} Installing uv (fast Python package manager)..."
        curl -LsSf https://astral.sh/uv/install.sh | sh
        UV_BIN="$HOME/.local/bin/uv"
        echo -e "  ${GREEN}✓${NC} uv installed"
    fi
fi

# ── Step 2: Install the MCP server ────────────────────────────────────────────
echo -e ""
echo -e "${BOLD}🔧 Step 2/3 — Installing agent-guidance-mcp...${NC}"

if [ -f "pyproject.toml" ]; then
    echo -e "  ${CYAN}📂${NC} Found local project — installing from source..."
    if ! "$UV_BIN" tool install . --force -q; then
        echo -e "  ${YELLOW}⚠${NC}  Local install failed — falling back to GitHub..."
        "$UV_BIN" tool install git+https://github.com/JunMystery/Agent-Guidance-MCP.git --force
    fi
else
    echo -e "  ${CYAN}🌐${NC} Installing from GitHub repository..."
    "$UV_BIN" tool install git+https://github.com/JunMystery/Agent-Guidance-MCP.git --force
fi
echo -e "  ${GREEN}✓${NC} MCP server installed"

# ── Resolve tool binary path ──────────────────────────────────────────────────
TOOL_BIN="$HOME/.local/bin/agent-guidance-mcp"
if [ ! -f "$TOOL_BIN" ]; then
    if command -v agent-guidance-mcp &> /dev/null; then
        TOOL_BIN="agent-guidance-mcp"
    fi
fi

# ── Step 3: Post-install configuration ────────────────────────────────────────
echo -e ""
echo -e "${BOLD}⚙️  Step 3/3 — Configuring IDE clients...${NC}"
MODE_FLAG=""
if [ "$ACTION" = "2" ]; then
    MODE_FLAG="--mode=ide"
fi

echo -e ""
echo -e "  ${PURPLE}▶${NC}  Registering with detected IDEs..."
if [ -f "$TOOL_BIN" ] || command -v agent-guidance-mcp &> /dev/null; then
    "$TOOL_BIN" --setup $MODE_FLAG
    echo -e "  ${PURPLE}▶${NC}  Downloading skill catalog..."
    "$TOOL_BIN" --update
else
    "$UV_BIN" tool run agent-guidance-mcp --setup $MODE_FLAG
    echo -e "  ${PURPLE}▶${NC}  Downloading skill catalog..."
    "$UV_BIN" tool run agent-guidance-mcp --update
fi

# ── Footer ────────────────────────────────────────────────────────────────────
echo -e ""
echo -e "${GREEN}${BOLD}╔══════════════════════════════════════════════════════════════╗${NC}"
echo -e "${GREEN}${BOLD}║         ✓  Installation completed successfully!             ║${NC}"
echo -e "${GREEN}${BOLD}╚══════════════════════════════════════════════════════════════╝${NC}"
echo -e ""
echo -e "  ${BOLD}Next steps:${NC}"
echo -e "    • Restart your IDE / MCP Client"
echo -e "    • Run ${CYAN}agent-guidance-mcp --help${NC} to see options"
echo -e "    • Update skills: ${CYAN}agent-guidance-mcp --update${NC}"
echo -e ""
