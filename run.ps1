param(
    [Parameter(ValueFromRemainingArguments = $true)]
    [string[]]$RemainingArgs
)

$ErrorActionPreference = 'Stop'
$ToolRoot = Split-Path -Parent $MyInvocation.MyCommand.Path

function Resolve-ProjectRoot([string]$ToolRootPath) {
    if ($env:BMADX_PROJECT_ROOT) {
        return [System.IO.Path]::GetFullPath($env:BMADX_PROJECT_ROOT)
    }
    $toolDir = Split-Path $ToolRootPath -Leaf
    $parentDir = Split-Path (Split-Path $ToolRootPath -Parent) -Leaf
    if ($toolDir -eq 'bmad-codex' -and $parentDir -eq 'tools') {
        return [System.IO.Path]::GetFullPath((Join-Path $ToolRootPath '..\..'))
    }
    return [System.IO.Path]::GetFullPath($ToolRootPath)
}

$ProjectRoot = Resolve-ProjectRoot $ToolRoot

function Quote-BashArg([string]$s) {
    return "'" + ($s -replace "'", "'\''") + "'"
}

$wsl = Get-Command wsl.exe -ErrorAction SilentlyContinue
if (-not $wsl) {
    throw "WSL is not installed. Open an elevated PowerShell and run: wsl --install"
}

$WslProjectRoot = (& wsl.exe wslpath -a $ProjectRoot).Trim()
if (-not $WslProjectRoot) {
    throw "Failed to convert Windows project path to a WSL path."
}
$WslToolRoot = (& wsl.exe wslpath -a $ToolRoot).Trim()
if (-not $WslToolRoot) {
    throw "Failed to convert Windows tool path to a WSL path."
}

$EscapedProjectRoot = Quote-BashArg $WslProjectRoot
$EscapedToolRoot = Quote-BashArg $WslToolRoot
$EscapedArgs = @()
foreach ($arg in $RemainingArgs) {
    $EscapedArgs += (Quote-BashArg $arg)
}
$ArgTail = ($EscapedArgs -join ' ')
$Command = "cd $EscapedProjectRoot && export BMADX_PROJECT_ROOT=$EscapedProjectRoot && export BMADX_TOOL_ROOT=$EscapedToolRoot && bash $EscapedToolRoot/run.sh $ArgTail"

Write-Host "[BMADX] delegating to WSL: $WslProjectRoot"
& wsl.exe bash -lc $Command
exit $LASTEXITCODE
