param([switch]$NoOpen, [switch]$NoVoice)

$ErrorActionPreference = 'Stop'
$project = (Resolve-Path (Join-Path $PSScriptRoot '..\..')).Path
$env:DSH_HOME = Join-Path $project '.dsh-home'
if (-not $NoVoice) {
    try {
        & (Join-Path $project 'workspaces\operations\Start-Voice.ps1') | ForEach-Object { Write-Host $_ }
    } catch {
        Write-Warning "小白本地语音未就绪；控制台会在彩排或入场前重新加载：$($_.Exception.Message)"
    }
}
if ($NoVoice) {
    # Keep the live TTS endpoint configured for the next time Start-Xiaobai loads it.
    $env:DS_XIAOBAI_TTS_URL = 'http://127.0.0.1:7391/synthesize'
}
try {
    $voiceHealth = Invoke-RestMethod -Uri 'http://127.0.0.1:7391/health' -TimeoutSec 2
    if ($voiceHealth.ready -and $voiceHealth.engine -eq 'cosyvoice3') {
        $env:DS_XIAOBAI_TTS_URL = 'http://127.0.0.1:7391/synthesize'
        Write-Host '小白舞台语音：本地 CosyVoice3 + RVC'
    }
} catch {}
$profile = Join-Path $env:DSH_HOME 'profiles\web\package.json'
if (-not (Test-Path -LiteralPath $profile)) {
    throw '本地 DSH 尚未安装。请先运行 Setup-Local.ps1。'
}

$dshArgs = @('--yes', '@deepseek-ai/dsh@0.2.1-rc.5', 'web', '--host', '127.0.0.1', '--port', '3081', '--no-open')
$tokenFile = Join-Path $env:DSH_HOME 'control-center-token'
$opened = $false
Write-Host '小白后台正在启动。按 Ctrl+C 停止本地服务。'
& npx @dshArgs 2>&1 | ForEach-Object {
    $line = [string]$_
    if ($line -match '[?&]token=([A-Za-z0-9_-]{20,200})') {
        Set-Content -LiteralPath $tokenFile -Value $Matches[1] -NoNewline -Encoding utf8
        $siteReady = Get-NetTCPConnection -LocalAddress '127.0.0.1' -LocalPort 3090 -State Listen -ErrorAction SilentlyContinue
        if (-not $siteReady) {
            Start-Process -FilePath 'node.exe' -ArgumentList 'workspaces/control-center/server.mjs' -WorkingDirectory $project -WindowStyle Hidden
        }
        if (-not $NoOpen -and -not $opened) {
            $opened = $true
            Start-Process 'http://127.0.0.1:3090/'
        }
        Write-Host '小白控制台：http://127.0.0.1:3090/'
    } else {
        Write-Output $line
    }
}
exit $LASTEXITCODE
