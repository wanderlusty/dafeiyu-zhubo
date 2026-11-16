$ErrorActionPreference = 'Stop'
$project = (Resolve-Path (Join-Path $PSScriptRoot '..\..')).Path
$env:DSH_HOME = Join-Path $project '.dsh-home'
$vendor = Join-Path $project 'vendor'
$duty = Join-Path $env:DSH_HOME 'bili-duty'
$venvPy = Join-Path $duty '.venv\Scripts\python.exe'
$biliPy = Join-Path $project '.venv-bili-cli\Scripts\python.exe'

New-Item -ItemType Directory -Force -Path $vendor, $duty | Out-Null
$cfgPath = Join-Path $duty 'config.json'
if (-not (Test-Path -LiteralPath $cfgPath)) {
    $dutyTemplate = Join-Path $project 'workspaces\platform\config\bili-duty.readonly.json'
    if (-not (Test-Path -LiteralPath $dutyTemplate)) {
        $dutyTemplate = Join-Path $project 'workspaces\platform\config\bili-duty.readonly.example.json'
    }
    Copy-Item -LiteralPath $dutyTemplate -Destination $cfgPath
}

$packages = @(
    @{ Name='dsh-bili-scroll'; Version='2.4.0'; Sha256='07D2EB381F559B13A1BCE8D1E80E060EB946CE6A1370EDB9EBDE51BDC6BBCBD0' },
    @{ Name='dsh-world'; Version='0.7.0'; Sha256='97366B3E53F49383049C19C04AC82A8EA8A0C77A5678C9198738A4E847819A64' }
)
foreach ($pkg in $packages) {
    $file = Join-Path $vendor ("{0}-{1}.tgz" -f $pkg.Name, $pkg.Version)
    if (-not (Test-Path -LiteralPath $file)) {
        & npm pack ("{0}@{1}" -f $pkg.Name, $pkg.Version) --pack-destination $vendor --json | Out-Null
        if ($LASTEXITCODE -ne 0) { throw "下载失败：$($pkg.Name)" }
    }
    $hash = (Get-FileHash -LiteralPath $file -Algorithm SHA256).Hash
    if ($hash -ne $pkg.Sha256) { throw "安装包 SHA-256 不匹配：$file" }
}

$biliPackage = Join-Path $vendor 'overrides\dsh-bili-scroll-2.4.0.tgz'
if (-not (Test-Path -LiteralPath $biliPackage)) {
    throw '缺少本地刷视频插件包。请看 docs/HANDOFF.md 的私有运行文件清单。'
}
if ((Get-FileHash -LiteralPath $biliPackage -Algorithm SHA256).Hash -ne '481D1CE9879E7F89C78134815DD6F2F08C57E8B1510E150BB794EB2E95CFA9F3') { throw '本地刷视频插件安装包 SHA-256 不匹配' }
& npx --yes '@deepseek-ai/dsh@0.2.1-rc.5' plugin --profile web add $biliPackage
if ($LASTEXITCODE -ne 0) { throw 'dsh-bili-scroll 安装失败' }
& npx --yes '@deepseek-ai/dsh@0.2.1-rc.5' plugin --profile web add (Join-Path $vendor 'dsh-world-0.7.0.tgz')
if ($LASTEXITCODE -ne 0) { throw 'dsh-world 安装失败' }
& pnpm --dir (Join-Path $env:DSH_HOME 'profiles\web') add '@snowluma/sdk@2.2.1'
if ($LASTEXITCODE -ne 0) { throw 'QQ OneBot SDK 安装失败' }
$livePackage = Join-Path $vendor 'overrides\dsh-livestream-xiaobai-song-queue-v12-0.0.1.tgz'
if (-not (Test-Path -LiteralPath $livePackage)) {
    throw '缺少小白直播插件包。可按 docs/HANDOFF.md 从源码补丁构建，或从本机私有运行文件中恢复。'
}
if (Test-Path -LiteralPath $livePackage) {
    $liveHash = (Get-FileHash -LiteralPath $livePackage -Algorithm SHA256).Hash
    if ($liveHash -ne '6FDA5FBEEBC7EE095BAD6FC1F7776FB517DA56E16349A57FDD02B3EFACA81442') { throw '本地直播插件安装包 SHA-256 不匹配' }
    & npx --yes '@deepseek-ai/dsh@0.2.1-rc.5' plugin --profile web add $livePackage
    if ($LASTEXITCODE -ne 0) { throw '本地直播插件安装失败' }
}
& (Join-Path $project 'workspaces\operations\Enable-OpenCode-Go.ps1')

$profilePatch = Join-Path $env:DSH_HOME 'profiles\web\cordis.patch.yml'
$utf8NoBom = New-Object System.Text.UTF8Encoding($false)
$patchText = [System.IO.File]::ReadAllText($profilePatch, [System.Text.Encoding]::UTF8)
if ($patchText -notmatch '(?m)^- id: dsh-world\s*$') {
    $worldTemplate = Join-Path $project 'workspaces\platform\config\web-world.patch.yml'
    if (-not (Test-Path -LiteralPath $worldTemplate)) {
        $worldTemplate = Join-Path $project 'workspaces\platform\config\web-world.patch.example.yml'
    }
    $worldPatch = [System.IO.File]::ReadAllText($worldTemplate, [System.Text.Encoding]::UTF8)
    [System.IO.File]::AppendAllText($profilePatch, "`n" + $worldPatch, $utf8NoBom)
}

$worldDir = Join-Path $env:DSH_HOME 'worlds\ds'
$personaPath = Join-Path $worldDir 'persona.md'
New-Item -ItemType Directory -Force -Path $worldDir | Out-Null
if (-not (Test-Path -LiteralPath $personaPath)) {
    Copy-Item -LiteralPath (Join-Path $project 'workspaces\platform\config\world-persona.md') -Destination $personaPath
}
$selfPath = Join-Path $worldDir 'room\我是谁.md'
if (-not (Test-Path -LiteralPath $selfPath)) {
    New-Item -ItemType Directory -Force -Path (Split-Path $selfPath -Parent) | Out-Null
    Copy-Item -LiteralPath (Join-Path $project 'workspaces\platform\config\world-self.md') -Destination $selfPath
}
$workspaceInstructions = Join-Path $worldDir 'room\AGENTS.md'
if (-not (Test-Path -LiteralPath $workspaceInstructions)) {
    Copy-Item -LiteralPath (Join-Path $project 'workspaces\platform\config\workspace-AGENTS.md') -Destination $workspaceInstructions
}

if (-not (Test-Path -LiteralPath $venvPy)) {
    & uv venv --seed --python 3.12 (Join-Path $duty '.venv')
    if ($LASTEXITCODE -ne 0) { throw '刷 B 站 Python 环境创建失败' }
}
& uv pip install --python $venvPy -r (Join-Path $project 'workspaces\platform\config\bili-duty-requirements.txt')
if ($LASTEXITCODE -ne 0) { throw '刷 B 站 Python 依赖安装失败' }
$cfg = [System.IO.File]::ReadAllText($cfgPath, [System.Text.Encoding]::UTF8) | ConvertFrom-Json
$cfg | Add-Member -NotePropertyName pythonPath -NotePropertyValue $venvPy -Force
$cfg | Add-Member -NotePropertyName workspace -NotePropertyValue (Join-Path $worldDir 'room') -Force
$cfg | Add-Member -NotePropertyName personaPrompt -NotePropertyValue '' -Force
[System.IO.File]::WriteAllText($cfgPath, ($cfg | ConvertTo-Json -Depth 10), $utf8NoBom)

if (-not (Test-Path -LiteralPath $biliPy)) {
    & uv venv --python 3.12 (Join-Path $project '.venv-bili-cli')
    if ($LASTEXITCODE -ne 0) { throw 'bili-cli Python 环境创建失败' }
}
& uv pip install --python $biliPy 'bili-agent==1.2.1' 'imageio-ffmpeg==0.6.0'
if ($LASTEXITCODE -ne 0) { throw 'bili-cli 安装失败' }
& $venvPy -c 'import bilibili_api, mcp, qrcode, PIL'
if ($LASTEXITCODE -ne 0) { throw '刷 B 站 Python 自检失败' }
Write-Host 'bili-duty Python imports OK'
Write-Host '本地环境已安装。双击“启动小白.cmd”打开控制台。'
