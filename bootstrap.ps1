$ErrorActionPreference = 'Stop'
$ToolRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$ProjectRoot = Resolve-Path (Join-Path $ToolRoot '..\..')
$env:BMADX_PROJECT_ROOT = [string]$ProjectRoot
$env:BMADX_TOOL_ROOT = [string](Resolve-Path $ToolRoot)

function Find-Python {
  if (Get-Command py -ErrorAction SilentlyContinue) { return @('py', '-3') }
  if (Get-Command python -ErrorAction SilentlyContinue) { return @('python') }
  throw 'Python 3 not found. Install Python or run from WSL.'
}

$py = Find-Python
$cmd = @()
$cmd += $py
$cmd += (Join-Path $ToolRoot 'bootstrap.py')
$cmd += $args
& $cmd[0] $cmd[1..($cmd.Length-1)]
exit $LASTEXITCODE
