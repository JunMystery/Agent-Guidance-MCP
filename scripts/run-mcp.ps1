param(
    [Parameter(ValueFromRemainingArguments = $true)]
    [string[]] $McpArgs
)

# WARNING: Launching this script in stdio transport mode can sometimes fail with a 
# "JSONRPCMessage validation error (EOF while parsing)" if PowerShell's pipeline wrapper 
# automatically passes a newline/empty input to Python's stdin.
#
# If configured as a client stdio transport tool, prefer calling 'scripts/run-mcp.cmd' 
# or running python directly, since CMD/native processes do not inject blank inputs.

$ErrorActionPreference = "Stop"
$RepoRoot = Resolve-Path (Join-Path $PSScriptRoot "..")
$SrcPath = Join-Path $RepoRoot "src"
$VenvPython = Join-Path $RepoRoot ".venv\Scripts\python.exe"

if (Test-Path -LiteralPath $VenvPython) {
    $Python = $VenvPython
} else {
    $Python = "python"
}

if ([string]::IsNullOrEmpty($env:PYTHONPATH)) {
    $env:PYTHONPATH = $SrcPath
} else {
    $env:PYTHONPATH = "$SrcPath;$env:PYTHONPATH"
}

& $Python -m agent_guidance_mcp @McpArgs
exit $LASTEXITCODE
