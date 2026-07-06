#!/usr/bin/env bash
set -e

# ── Colors ────────────────────────────────────────────────────────────────────
RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'
CYAN='\033[0;36m'; PURPLE='\033[0;35m'; BOLD='\033[1m'
GRAY='\033[0;90m'; NC='\033[0m'

# ── Header ────────────────────────────────────────────────────────────────────
echo -e ""
echo -e "${RED}${BOLD}╔══════════════════════════════════════════════════════════════╗${NC}"
echo -e "${RED}${BOLD}║        Agent Guidance MCP Uninstaller (macOS/Linux)         ║${NC}"
echo -e "${RED}${BOLD}╚══════════════════════════════════════════════════════════════╝${NC}"
echo -e ""

# ── Resolve tool binary ───────────────────────────────────────────────────────
TOOL_BIN="$HOME/.local/bin/agent-guidance-mcp"
if [ ! -f "$TOOL_BIN" ]; then
    if command -v agent-guidance-mcp &> /dev/null; then
        TOOL_BIN="agent-guidance-mcp"
    fi
fi

# ── Step 1: Remove IDE registrations ──────────────────────────────────────────
echo -e "${BOLD}🗑️  Step 1/3 — Removing client registrations...${NC}"
if [ -f "$TOOL_BIN" ] || command -v agent-guidance-mcp &> /dev/null; then
    "$TOOL_BIN" --uninstall
    echo -e "  ${GREEN}✓${NC} IDE registrations removed"
else
    echo -e "  ${YELLOW}⚠${NC}  MCP tool not found — skipping registration cleanup"
fi

# ── Step 2: Remove skills data ────────────────────────────────────────────────
echo -e ""
echo -e "${BOLD}📁 Step 2/3 — Removing skills data...${NC}"
DATA_DIR="$HOME/.agent-guidance"
if [ -d "$DATA_DIR" ]; then
    rm -rf "$DATA_DIR"
    echo -e "  ${GREEN}✓${NC} Removed ${GRAY}$DATA_DIR${NC}"
else
    echo -e "  ${GRAY}•${NC}  Skills data not found — nothing to remove"
fi

# ── Step 3: Uninstall tool from uv ────────────────────────────────────────────
echo -e ""
echo -e "${BOLD}🔧 Step 3/3 — Removing MCP server binary...${NC}"
if command -v uv &> /dev/null; then
    uv tool uninstall agent-guidance-mcp 2>/dev/null && echo -e "  ${GREEN}✓${NC} Uninstalled from uv" || echo -e "  ${GRAY}•${NC}  Not found in uv tools"
elif [ -f "$HOME/.local/bin/uv" ]; then
    "$HOME/.local/bin/uv" tool uninstall agent-guidance-mcp 2>/dev/null && echo -e "  ${GREEN}✓${NC} Uninstalled from uv" || echo -e "  ${GRAY}•${NC}  Not found in uv tools"
fi

# ── Footer ────────────────────────────────────────────────────────────────────
echo -e ""
echo -e "${GREEN}${BOLD}╔══════════════════════════════════════════════════════════════╗${NC}"
echo -e "${GREEN}${BOLD}║       ✓  Uninstallation completed successfully!            ║${NC}"
echo -e "${GREEN}${BOLD}╚══════════════════════════════════════════════════════════════╝${NC}"
echo -e ""
