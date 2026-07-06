# Self-contained PowerShell Installer/Uninstaller for Agent Guidance MCP on Windows
# Usage: irm ... | iex                    (install)
#        irm ... | iex ; Uninstall-MCP    (uninstall after sourcing)
#        & ([scriptblock]::Create((irm ...))) -Uninstall   (uninstall mode)

param([switch]$Uninstall)

$ErrorActionPreference = "Stop"

# ── Uninstall Mode ────────────────────────────────────────────────────────────
if ($Uninstall) {
    Write-Host ""
    Write-Host "╔══════════════════════════════════════════════════════════════╗" -ForegroundColor Red
    Write-Host "║        Agent Guidance MCP Uninstaller (Windows)              ║" -ForegroundColor Red
    Write-Host "╚══════════════════════════════════════════════════════════════╝" -ForegroundColor Red
    Write-Host ""

    $toolBin = "$HOME\.local\bin\agent-guidance-mcp.exe"
    if (-not (Test-Path $toolBin)) {
        if (Get-Command "agent-guidance-mcp" -ErrorAction SilentlyContinue) { $toolBin = "agent-guidance-mcp" }
    }

    Write-Host "🗑️  Step 1/3 — Removing client registrations..." -ForegroundColor White
    if (Test-Path $toolBin) {
        & $toolBin --uninstall 2>$null
        Write-Host "  ✓ IDE registrations removed" -ForegroundColor Green
    } else {
        Write-Host "  ⚠ MCP tool not found — skipping" -ForegroundColor Yellow
    }

    Write-Host ""
    Write-Host "📁 Step 2/3 — Removing skills data..." -ForegroundColor White
    if (Test-Path "$HOME\.agent-guidance") {
        Remove-Item -Recurse -Force "$HOME\.agent-guidance"
        Write-Host "  ✓ Removed skills data" -ForegroundColor Green
    } else {
        Write-Host "  • Skills data not found" -ForegroundColor Gray
    }

    Write-Host ""
    Write-Host "🔧 Step 3/3 — Removing MCP server binary..." -ForegroundColor White
    if (Get-Command "uv" -ErrorAction SilentlyContinue) {
        & uv tool uninstall agent-guidance-mcp 2>$null
        Write-Host "  ✓ Uninstalled from uv" -ForegroundColor Green
    } elseif (Test-Path "$HOME\.local\bin\uv.exe") {
        & "$HOME\.local\bin\uv.exe" tool uninstall agent-guidance-mcp 2>$null
        Write-Host "  ✓ Uninstalled from uv" -ForegroundColor Green
    } else {
        Write-Host "  • uv not found" -ForegroundColor Gray
    }

    Write-Host ""
    Write-Host "╔══════════════════════════════════════════════════════════════╗" -ForegroundColor Green
    Write-Host "║       ✓  Uninstallation completed successfully!            ║" -ForegroundColor Green
    Write-Host "╚══════════════════════════════════════════════════════════════╝" -ForegroundColor Green
    Write-Host ""
    exit 0
}

# ── Header ────────────────────────────────────────────────────────────────────
Write-Host ""
Write-Host "╔══════════════════════════════════════════════════════════════╗" -ForegroundColor Magenta
Write-Host "║         Agent Guidance MCP Installer (Windows)               ║" -ForegroundColor Magenta
Write-Host "╚══════════════════════════════════════════════════════════════╝" -ForegroundColor Magenta
Write-Host ""

# ── Step 1: Detect or Install 'uv' ────────────────────────────────────────────
Write-Host "📦 Step 1/3 — Checking Python toolchain (uv)..." -ForegroundColor White
$uvBin = ""
if (Get-Command "uv" -ErrorAction SilentlyContinue) {
    $uvBin = "uv"
    Write-Host "  ✓ Found 'uv' in PATH" -ForegroundColor Green
} else {
    $defaultUvPath = "$HOME\.local\bin\uv.exe"
    if (Test-Path $defaultUvPath) {
        $uvBin = $defaultUvPath
        Write-Host "  ✓ Found 'uv' at $uvBin" -ForegroundColor Green
    } else {
        Write-Host "  ⚡ Installing uv (fast Python package manager)..." -ForegroundColor Yellow
        Set-ExecutionPolicy Bypass -Scope Process -Force
        Invoke-Expression (Invoke-RestMethod "https://astral.sh/uv/install.ps1")
        $uvBin = "$HOME\.local\bin\uv.exe"
        Write-Host "  ✓ uv installed" -ForegroundColor Green
    }
}

# ── Step 2: Install the MCP server ────────────────────────────────────────────
Write-Host ""
Write-Host "🔧 Step 2/3 — Installing agent-guidance-mcp..." -ForegroundColor White

if (Test-Path "pyproject.toml") {
    Write-Host "  📂 Found local project — installing from source..." -ForegroundColor Cyan
    try {
        & $uvBin tool install . --force -q
    } catch {
        Write-Host "  ⚠ Local install failed — falling back to GitHub..." -ForegroundColor Yellow
        & $uvBin tool install git+https://github.com/JunMystery/Agent-Guidance-MCP.git --force
    }
} else {
    Write-Host "  🌐 Installing from GitHub repository..." -ForegroundColor Cyan
    & $uvBin tool install git+https://github.com/JunMystery/Agent-Guidance-MCP.git --force
}
Write-Host "  ✓ MCP server installed" -ForegroundColor Green

# ── Resolve tool binary path ──────────────────────────────────────────────────
$toolBin = "$HOME\.local\bin\agent-guidance-mcp.exe"
if (-not (Test-Path $toolBin)) {
    if (Get-Command "agent-guidance-mcp" -ErrorAction SilentlyContinue) {
        $toolBin = "agent-guidance-mcp"
    }
}

# ── Step 3: Post-install configuration ────────────────────────────────────────
Write-Host ""
Write-Host "⚙️  Step 3/3 — Configuring IDE clients..." -ForegroundColor White
$modeChoice = Read-Host "  Choose install mode [1=Auto / 2=Manual] (default: 1)"
$modeFlag = ""
if ($modeChoice -eq "2") {
    $modeFlag = "--mode=manual"
}

Write-Host ""
Write-Host "  ▶ Registering with detected IDEs..." -ForegroundColor Magenta
if (Test-Path $toolBin) {
    & $toolBin --setup $modeFlag
    Write-Host "  ▶ Downloading skill catalog..." -ForegroundColor Magenta
    & $toolBin --update
} else {
    & $uvBin tool run agent-guidance-mcp --setup $modeFlag
    Write-Host "  ▶ Downloading skill catalog..." -ForegroundColor Magenta
    & $uvBin tool run agent-guidance-mcp --update
}

# ── Footer ────────────────────────────────────────────────────────────────────
Write-Host ""
Write-Host "╔══════════════════════════════════════════════════════════════╗" -ForegroundColor Green
Write-Host "║         ✓  Installation completed successfully!             ║" -ForegroundColor Green
Write-Host "╚══════════════════════════════════════════════════════════════╝" -ForegroundColor Green
Write-Host ""
Write-Host "  Next steps:"
Write-Host "    • Restart your IDE / MCP Client"
Write-Host "    • Run agent-guidance-mcp --help to see options" -ForegroundColor Cyan
Write-Host "    • Update skills: agent-guidance-mcp --update" -ForegroundColor Cyan
Write-Host ""
