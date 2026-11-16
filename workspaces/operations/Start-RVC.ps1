param([switch]$NoWait)

$ErrorActionPreference = 'Stop'
$project = (Resolve-Path (Join-Path $PSScriptRoot '..\..')).Path
$url = 'http://127.0.0.1:7392/health'
$settings = Get-Content -LiteralPath (Join-Path $project 'workspaces\voice\rvc_config.json') -Raw -Encoding UTF8 | ConvertFrom-Json
$expected = [IO.Path]::GetFileName([string]$settings.model)
$health = $null
try { $health = Invoke-RestMethod -Uri $url -TimeoutSec 2 } catch {}
if ($health.ready -and $health.engine -eq 'rvc-v2') {
    if ($health.model -ne $expected) { throw "已运行的是 $($health.model)，当前配置需要 $expected" }
    Write-Output "小白 RVC 已在运行：$($health.model)"
    return
}

$python = '/home/qzy/.local/share/feiyu-voice/cuda/tts-proxy/venv/bin/python'
$script = '/mnt/d/PRJ/ds-zhubo/workspaces/voice/serve_rvc.py'
$config = '/mnt/d/PRJ/ds-zhubo/workspaces/voice/rvc_config.json'
$output = Join-Path $project 'outputs\xiaobai-rvc-server.log'
$errorOutput = Join-Path $project 'outputs\xiaobai-rvc-server.err.log'
Start-Process -FilePath 'wsl.exe' -ArgumentList @('-e', $python, $script, '--config', $config) `
    -WorkingDirectory $project -WindowStyle Hidden `
    -RedirectStandardOutput $output -RedirectStandardError $errorOutput | Out-Null
if ($NoWait) { return }
for ($i = 0; $i -lt 90; $i++) {
    Start-Sleep -Seconds 1
    try {
        $health = Invoke-RestMethod -Uri $url -TimeoutSec 2
        if ($health.ready -and $health.engine -eq 'rvc-v2') {
            Write-Output "小白 RVC 已就绪：$($health.model)"
            return
        }
    } catch {}
}
throw "小白 RVC 启动超时。请查看 $errorOutput"
