param([switch]$NoWait)

$ErrorActionPreference = 'Stop'
$project = (Resolve-Path (Join-Path $PSScriptRoot '..\..')).Path
$url = 'http://127.0.0.1:7391/health'
$configPath = Join-Path $project 'workspaces\voice\voice_config.json'
$voiceConfig = Get-Content -LiteralPath $configPath -Raw -Encoding UTF8 | ConvertFrom-Json
if ($voiceConfig.rvc_url) {
    & (Join-Path $project 'workspaces\operations\Start-RVC.ps1')
}
$health = $null
try { $health = Invoke-RestMethod -Uri $url -TimeoutSec 2 } catch {}
if ($health.ready) {
    if ([bool]$health.rvc -ne [bool]$voiceConfig.rvc_url) {
        throw '已运行的语音服务与当前 RVC 配置不同，请先停止旧语音服务'
    }
    Write-Output '小白 CosyVoice3 已在运行'
    return
}

$python = '/home/qzy/.local/share/feiyu-voice/cuda/tts-proxy/venv/bin/python'
$script = '/mnt/d/PRJ/ds-zhubo/workspaces/voice/serve_tts.py'
$config = '/mnt/d/PRJ/ds-zhubo/workspaces/voice/voice_config.json'
$output = Join-Path $project 'outputs\xiaobai-voice-server.log'
$errorOutput = Join-Path $project 'outputs\xiaobai-voice-server.err.log'
Start-Process -FilePath 'wsl.exe' -ArgumentList @('-e', $python, $script, '--config', $config) `
    -WorkingDirectory $project -WindowStyle Hidden `
    -RedirectStandardOutput $output -RedirectStandardError $errorOutput | Out-Null
if ($NoWait) { return }
$ready = $false
for ($i = 0; $i -lt 90; $i++) {
    Start-Sleep -Seconds 1
    try {
        $health = Invoke-RestMethod -Uri $url -TimeoutSec 2
        if ($health.ready) {
            $ready = $true
            break
        }
    } catch {}
}
if (-not $ready) { throw "小白 CosyVoice3 启动超时。请查看 $errorOutput" }

$warmupFile = Join-Path $project 'outputs\xiaobai-voice-warmup.mp3'
try {
    Invoke-WebRequest -Uri 'http://127.0.0.1:7391/synthesize' -Method Post `
        -ContentType 'application/json; charset=utf-8' -Body '{"text":"小白在这儿。"}' `
        -OutFile $warmupFile -TimeoutSec 90 | Out-Null
    if ((Get-Item -LiteralPath $warmupFile).Length -lt 1000) { throw '预热音频为空' }
} catch {
    throw "小白语音端到端预热失败：$($_.Exception.Message)。请查看 $errorOutput"
} finally {
    Remove-Item -LiteralPath $warmupFile -ErrorAction SilentlyContinue
}
try { & (Join-Path $project 'workspaces\operations\回收WSL文件缓存.ps1') | Out-Null }
catch { Write-Warning "语音已就绪，但 WSL 缓存回收失败：$($_.Exception.Message)" }
Write-Output '小白 CosyVoice3 + RVC 已预热：http://127.0.0.1:7391'
