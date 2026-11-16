param([Parameter(ValueFromRemainingArguments = $true)][string[]]$BiliArgs)

$ErrorActionPreference = 'Stop'
$project = (Resolve-Path (Join-Path $PSScriptRoot '..\..')).Path
$env:BILI_CLI_HOME = Join-Path $project '.dsh-home\bili-cli'
$env:PYTHONIOENCODING = 'utf-8'
$bili = Join-Path $project '.venv-bili-cli\Scripts\bili.exe'
if (-not (Test-Path -LiteralPath $bili)) {
    throw 'bili-cli 尚未安装。请先运行 Setup-Local.ps1。'
}
& $bili @BiliArgs
exit $LASTEXITCODE
