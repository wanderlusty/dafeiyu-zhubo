$ErrorActionPreference = 'Stop'
$project = (Resolve-Path (Join-Path $PSScriptRoot '..\..')).Path
$state = Invoke-RestMethod -Uri 'http://127.0.0.1:3090/api/live' -TimeoutSec 10
if ($state.show.onAir -or $state.broadcast.phase -ne 'idle' -or $state.show.live.state -eq 'live') {
    throw '小白正在彩排或直播；请先结束，再释放语音内存。'
}
$python = '/home/qzy/.local/share/feiyu-voice/cuda/tts-proxy/venv/bin/python'
$script = '/mnt/d/PRJ/ds-zhubo/workspaces/voice/unload_idle_voice.py'
& wsl --exec $python $script
if ($LASTEXITCODE -ne 0) { throw '释放语音内存失败。' }
Write-Output '语音模型已卸载；小白后台仍在运行。再次运行“启动小白.cmd”可重新加载。'
