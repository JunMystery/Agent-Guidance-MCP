# Self-contained PowerShell Uninstaller for Agent Guidance MCP on Windows
$ErrorActionPreference = "Stop"

Write-Host "=== Agent Guidance MCP Uninstaller (Windows) ===" -ForegroundColor Cyan

# 1. Resolve path of the installed tool to run the clean-up
$toolBin = "$HOME\.local\bin\agent-guidance-mcp.exe"
if (-not (Test-Path $toolBin)) {
    if (Get-Command "agent-guidance-mcp" -ErrorAction SilentlyContinue) {
        $toolBin = "agent-guidance-mcp"
    }
}

# 2. Run setup's uninstall logic to remove integrations
Write-Host "Removing client registrations and local standards data..." -ForegroundColor Cyan
if (Test-Path $toolBin) {
    & $toolBin --uninstall
} else {
    # Fallback to uv tool run
    if (Get-Command "uv" -ErrorAction SilentlyContinue) {
        & uv tool run agent-guidance-mcp --uninstall
    } elseif (Test-Path "$HOME\.local\bin\uv.exe") {
        & "$HOME\.local\bin\uv.exe" tool run agent-guidance-mcp --uninstall
    }
}

# 3. Uninstall the tool from uv
Write-Host "Uninstalling agent-guidance-mcp tool..." -ForegroundColor Cyan
if (Get-Command "uv" -ErrorAction SilentlyContinue) {
    & uv tool uninstall agent-guidance-mcp
} elseif (Test-Path "$HOME\.local\bin\uv.exe") {
    & "$HOME\.local\bin\uv.exe" tool uninstall agent-guidance-mcp
}

Write-Host "`n✓ Uninstallation completed successfully!" -ForegroundColor Green
