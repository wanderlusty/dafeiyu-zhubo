param([switch]$NoOpen)

$ErrorActionPreference = 'Stop'
$project = (Resolve-Path (Join-Path $PSScriptRoot '..\..')).Path
$dshReady = Get-NetTCPConnection -LocalAddress '127.0.0.1' -LocalPort 3081 -State Listen -ErrorAction SilentlyContinue

if (-not $dshReady) {
    & (Join-Path $project 'workspaces\operations\Start-DS.ps1') -NoOpen:$NoOpen
    exit $LASTEXITCODE
}

try {
    & (Join-Path $project 'workspaces\operations\Start-Voice.ps1') | ForEach-Object { Write-Host $_ }
} catch {
    Write-Warning "小白本地语音未就绪；控制台会在彩排或入场前重新加载：$($_.Exception.Message)"
}

$tokenFile = Join-Path $project '.dsh-home\control-center-token'
if (-not (Test-Path -LiteralPath $tokenFile)) {
    throw '小白后台已运行，但控制台连接文件不存在。请停止旧服务后重新运行“启动小白.cmd”。'
}
$siteReady = Get-NetTCPConnection -LocalAddress '127.0.0.1' -LocalPort 3090 -State Listen -ErrorAction SilentlyContinue
if (-not $siteReady) {
    Start-Process -FilePath 'node.exe' -ArgumentList 'workspaces/control-center/server.mjs' -WorkingDirectory $project -WindowStyle Hidden
    Start-Sleep -Milliseconds 500
}
if (-not $NoOpen) { Start-Process 'http://127.0.0.1:3090/' }
Write-Host '小白控制台：http://127.0.0.1:3090/'
