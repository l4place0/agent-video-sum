[CmdletBinding()]
param([Parameter(ValueFromRemainingArguments = $true)][string[]]$CliArgs)
$ErrorActionPreference = "Stop"
& py -3 (Join-Path $PSScriptRoot "issue_report.py") @CliArgs
exit $LASTEXITCODE
