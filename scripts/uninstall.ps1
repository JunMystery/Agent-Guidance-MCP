# Self-contained PowerShell Uninstaller for Agent Guidance MCP on Windows
$ErrorActionPreference = "Stop"

# ── Header ────────────────────────────────────────────────────────────────────
Write-Host ""
Write-Host "╔══════════════════════════════════════════════════════════════╗" -ForegroundColor Red
Write-Host "║        Agent Guidance MCP Uninstaller (Windows)              ║" -ForegroundColor Red
Write-Host "╚══════════════════════════════════════════════════════════════╝" -ForegroundColor Red
Write-Host ""

# ── Resolve tool binary ───────────────────────────────────────────────────────
$toolBin = "$HOME\.local\bin\agent-guidance-mcp.exe"
if (-not (Test-Path $toolBin)) {
    if (Get-Command "agent-guidance-mcp" -ErrorAction SilentlyContinue) {
        $toolBin = "agent-guidance-mcp"
    }
}

# ── Step 1: Remove IDE registrations ──────────────────────────────────────────
Write-Host "🗑️  Step 1/3 — Removing client registrations..." -ForegroundColor White
if (Test-Path $toolBin) {
    & $toolBin --uninstall
    Write-Host "  ✓ IDE registrations removed" -ForegroundColor Green
} else {
    Write-Host "  ⚠ MCP tool not found — skipping registration cleanup" -ForegroundColor Yellow
}

# ── Step 2: Remove skills data ────────────────────────────────────────────────
Write-Host ""
Write-Host "📁 Step 2/3 — Removing skills data..." -ForegroundColor White
$dataDir = "$HOME\.agent-guidance"
if (Test-Path $dataDir) {
    Remove-Item -Recurse -Force $dataDir
    Write-Host "  ✓ Removed $dataDir" -ForegroundColor Green
} else {
    Write-Host "  • Skills data not found — nothing to remove" -ForegroundColor Gray
}

# ── Step 3: Uninstall tool from uv ────────────────────────────────────────────
Write-Host ""
Write-Host "🔧 Step 3/3 — Removing MCP server binary..." -ForegroundColor White
if (Get-Command "uv" -ErrorAction SilentlyContinue) {
    & uv tool uninstall agent-guidance-mcp 2>$null
    if ($LASTEXITCODE -eq 0) {
        Write-Host "  ✓ Uninstalled from uv" -ForegroundColor Green
    } else {
        Write-Host "  • Not found in uv tools" -ForegroundColor Gray
    }
} elseif (Test-Path "$HOME\.local\bin\uv.exe") {
    & "$HOME\.local\bin\uv.exe" tool uninstall agent-guidance-mcp 2>$null
    if ($LASTEXITCODE -eq 0) {
        Write-Host "  ✓ Uninstalled from uv" -ForegroundColor Green
    } else {
        Write-Host "  • Not found in uv tools" -ForegroundColor Gray
    }
}

# ── Footer ────────────────────────────────────────────────────────────────────
Write-Host ""
Write-Host "╔══════════════════════════════════════════════════════════════╗" -ForegroundColor Green
Write-Host "║       ✓  Uninstallation completed successfully!            ║" -ForegroundColor Green
Write-Host "╚══════════════════════════════════════════════════════════════╝" -ForegroundColor Green
Write-Host ""
