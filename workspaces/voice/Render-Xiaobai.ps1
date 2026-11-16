param(
    [Parameter(Mandatory)][string]$Text,
    [Parameter(Mandatory)][string]$Reference,
    [Parameter(Mandatory)][string]$PromptText,
    [Parameter(Mandatory)][string]$Output,
    [string]$Delivery,
    [string]$RvcModel,
    [string]$RvcIndex
)

$ErrorActionPreference = 'Stop'
$project = (Resolve-Path (Join-Path $PSScriptRoot '..\..')).Path
$repo = '/home/qzy/.local/share/feiyu-voice/cuda/tts-proxy/source'
$wslPython = '/home/qzy/.local/share/feiyu-voice/cuda/tts-proxy/venv/bin/python'
$rvcCli = Join-Path $project 'workspaces\voice\rvc_convert.py'

function Convert-ToWslPath([string]$Path) {
    $windowsPath = (Resolve-Path -LiteralPath $Path).Path
    $converted = & wsl -e wslpath -a -u $windowsPath
    if ($LASTEXITCODE -ne 0) { throw "WSL path conversion failed: $windowsPath" }
    return $converted.Trim()
}

$source = (Resolve-Path -LiteralPath $Reference).Path
$destination = [IO.Path]::GetFullPath($Output)
if ([IO.Path]::GetExtension($destination).ToLowerInvariant() -ne '.wav') { throw 'Output must be a .wav file' }
$parent = Split-Path -Parent $destination
New-Item -ItemType Directory -Path $parent -Force | Out-Null
if (Test-Path -LiteralPath $destination) { throw "Output already exists: $destination" }
$ttsOutput = if ($RvcModel) { Join-Path $parent ([IO.Path]::GetFileNameWithoutExtension($destination) + '.tts.wav') } else { $destination }
if (Test-Path -LiteralPath $ttsOutput) { throw "TTS intermediate already exists: $ttsOutput" }

$ttsArgs = @(
    '-e', $wslPython, (Convert-ToWslPath (Join-Path $project 'workspaces\voice\cosyvoice_tts.py')),
    '--repo', $repo,
    '--model', (Convert-ToWslPath (Join-Path $project 'models\Fun-CosyVoice3-0.5B-2512')),
    '--reference', (Convert-ToWslPath $source),
    '--prompt-text', $PromptText,
    '--text', $Text,
    '--output', (& wsl -e wslpath -a -u $ttsOutput).Trim()
)
if ($Delivery) { $ttsArgs += @('--delivery', $Delivery) }
& wsl @ttsArgs
if ($LASTEXITCODE -ne 0 -or -not (Test-Path -LiteralPath $ttsOutput)) { throw 'CosyVoice3 synthesis failed' }

if ($RvcModel) {
    $model = (Resolve-Path -LiteralPath $RvcModel).Path
    $rvcArgs = @('-e', $wslPython, (Convert-ToWslPath $rvcCli),
        '--model', (Convert-ToWslPath $model),
        '--input', (Convert-ToWslPath $ttsOutput),
        '--output', (& wsl -e wslpath -a -u $destination).Trim(),
        '--pitch', '0', '--f0-method', 'rmvpe')
    if ($RvcIndex) {
        $rvcArgs += @('--index', (Convert-ToWslPath $RvcIndex), '--index-rate', '0.75')
    } else {
        $rvcArgs += @('--index-rate', '0')
    }
    & wsl @rvcArgs
    if ($LASTEXITCODE -ne 0 -or -not (Test-Path -LiteralPath $destination)) { throw 'RVC conversion failed' }
}
Write-Output $destination
