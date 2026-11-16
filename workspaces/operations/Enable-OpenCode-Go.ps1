$ErrorActionPreference = 'Stop'
$project = (Resolve-Path (Join-Path $PSScriptRoot '..\..')).Path
$pluginDir = Join-Path $project '.dsh-home\profiles\web\node_modules\dsh-bili-scroll'
$indexPath = Join-Path $pluginDir 'index.js'
$templatePath = Join-Path $pluginDir 'profile-template\bili-duty\cordis.patch.yml'
$providerPath = Join-Path $project 'workspaces\platform\config\bili-duty-opencode.patch.yml'
$utf8NoBom = New-Object System.Text.UTF8Encoding($false)

foreach ($path in @($indexPath, $templatePath, $providerPath)) {
    if (-not (Test-Path -LiteralPath $path)) { throw "Missing required file: $path" }
}
$packagePath = Join-Path $pluginDir 'package.json'
$package = [System.IO.File]::ReadAllText($packagePath, [System.Text.Encoding]::UTF8) | ConvertFrom-Json
if ($package.version -ne '2.4.0') { throw "Unsupported dsh-bili-scroll version: $($package.version)" }

$source = [System.IO.File]::ReadAllText($indexPath, [System.Text.Encoding]::UTF8)
$before = "const PROFILE_ONLY_PROVIDERS = { 'google-antigravity': 'headless' }"
$after = "const PROFILE_ONLY_PROVIDERS = { 'google-antigravity': 'headless', 'opencode-go': 'bili-duty' }"
if (-not $source.Contains($after)) {
    if (-not $source.Contains($before)) { throw 'Unexpected dsh-bili-scroll provider list; patch not applied' }
    $source = $source.Replace($before, $after)
    [System.IO.File]::WriteAllText($indexPath, $source, $utf8NoBom)
}

$template = [System.IO.File]::ReadAllText($templatePath, [System.Text.Encoding]::UTF8)
$marker = '# Local OpenCode Go provider for bili-duty'
if (-not $template.Contains($marker)) {
    if ($template -match '(?m)^- id: llm-pi-ai\s*$') { throw 'Existing llm-pi-ai template entry; inspect before patching' }
    $provider = [System.IO.File]::ReadAllText($providerPath, [System.Text.Encoding]::UTF8).Trim()
    $template = $template.TrimEnd() + "`n`n" + $marker + "`n" + $provider + "`n"
    [System.IO.File]::WriteAllText($templatePath, $template, $utf8NoBom)
}

Write-Host 'OpenCode Go profile patch ready. Restart DSH web to load it.'
