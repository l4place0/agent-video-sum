[CmdletBinding()]
param([Parameter(ValueFromRemainingArguments = $true)][string[]]$CliArgs)
& (Join-Path $PSScriptRoot "install.ps1") @CliArgs
exit $LASTEXITCODE
