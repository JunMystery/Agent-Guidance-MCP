# Self-contained PowerShell Installer for Agent Guidance MCP on Windows
$ErrorActionPreference = "Stop"

Write-Host "=== Agent Guidance MCP Installer (Windows) ===" -ForegroundColor Cyan

# 1. Detect or Install 'uv'
$uvBin = ""
if (Get-Command "uv" -ErrorAction SilentlyContinue) {
    $uvBin = "uv"
    Write-Host "Found existing 'uv' installation in PATH."
} else {
    $defaultUvPath = "$HOME\.local\bin\uv.exe"
    if (Test-Path $defaultUvPath) {
        $uvBin = $defaultUvPath
        Write-Host "Found 'uv' at $uvBin"
    } else {
        Write-Host "'uv' toolchain not found. Installing uv (fast, zero-dependency Python toolrunner)..." -ForegroundColor Yellow
        # Set execution policy for process and download
        Set-ExecutionPolicy Bypass -Scope Process -Force
        Invoke-Expression (Invoke-RestMethod "https://astral.sh/uv/install.ps1")
        $uvBin = "$HOME\.local\bin\uv.exe"
    }
}

# 2. Install the Agent Guidance MCP tool
Write-Host "Installing agent-guidance-mcp from PyPI..." -ForegroundColor Cyan
& $uvBin tool install agent-guidance-mcp --force

# 3. Resolve the path of the installed tool to run the setup
$toolBin = "$HOME\.local\bin\agent-guidance-mcp.exe"
if (-not (Test-Path $toolBin)) {
    if (Get-Command "agent-guidance-mcp" -ErrorAction SilentlyContinue) {
        $toolBin = "agent-guidance-mcp"
    }
}

Write-Host "Running post-install configuration..." -ForegroundColor Cyan
if (Test-Path $toolBin) {
    & $toolBin --setup
} else {
    # Fallback to uv tool run
    & $uvBin tool run agent-guidance-mcp --setup
}

Write-Host "`n✓ Installation completed successfully!" -ForegroundColor Green
