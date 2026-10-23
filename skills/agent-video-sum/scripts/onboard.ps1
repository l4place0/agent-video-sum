[CmdletBinding()]
param([Parameter(ValueFromRemainingArguments = $true)][string[]]$CliArgs)
$ErrorActionPreference = "Stop"
& py -3 (Join-Path $PSScriptRoot "bootstrap.py") onboard @CliArgs
exit $LASTEXITCODE
