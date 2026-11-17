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
    if ($template -match '(?m)^- id: llm-pi-ai\s*$') {
        if ($template -notmatch '(?m)^      opencode-go:\s*$' -or $template -notmatch '(?m)^        apiKeyEnv: OPENCODE_GO_API_KEY\s*$') {
            throw 'Existing llm-pi-ai template entry is not the expected OpenCode Go provider'
        }
    } else {
        $provider = [System.IO.File]::ReadAllText($providerPath, [System.Text.Encoding]::UTF8).Trim()
        $template = $template.TrimEnd() + "`n`n" + $marker + "`n" + $provider + "`n"
        [System.IO.File]::WriteAllText($templatePath, $template, $utf8NoBom)
    }
}

# Match the web profile's reasoning setting in the unattended Bilibili duty
# profile and its reinstall template.
$dutyProfilePath = Join-Path $env:DSH_HOME 'profiles\bili-duty\cordis.patch.yml'
$dutyModelPattern = [regex]'(?m)^(- id: agent-default-model\r?\n  config:\r?\n    provider: opencode-go\r?\n    model: deepseek-v4\.1-flash)(?:\r?\n    reasoningEffort: [^\r\n]+)?'
foreach ($profilePath in @($dutyProfilePath, $templatePath)) {
    if (-not (Test-Path -LiteralPath $profilePath)) { continue }
    $profileText = [System.IO.File]::ReadAllText($profilePath, [System.Text.Encoding]::UTF8)
    if ($dutyModelPattern.Matches($profileText).Count -ne 1) {
        throw "Expected one OpenCode Go duty model in $profilePath"
    }
    $profileText = $dutyModelPattern.Replace($profileText, [System.Text.RegularExpressions.MatchEvaluator]{
        param($match)
        $lineEnding = if ($match.Value.Contains("`r`n")) { "`r`n" } else { "`n" }
        $match.Groups[1].Value + $lineEnding + '    reasoningEffort: high'
    }, 1)
    [System.IO.File]::WriteAllText($profilePath, $profileText, $utf8NoBom)
}

# A private endpoint override survives reinstalling the Bilibili plugin. The
# API key stays in DSH's ignored credential store, never in this source file.
$endpointPath = Join-Path $project 'local-data\accounts\opencode-go-base-url.txt'
if (Test-Path -LiteralPath $endpointPath) {
    $baseUrl = [System.IO.File]::ReadAllText($endpointPath, [System.Text.Encoding]::UTF8).Trim()
    $uri = $null
    if (-not [Uri]::TryCreate($baseUrl, [UriKind]::Absolute, [ref]$uri) -or $uri.Scheme -ne 'https') {
        throw "Invalid OpenCode Go endpoint in $endpointPath"
    }
    $profilePaths = @(
        (Join-Path $env:DSH_HOME 'profiles\web\cordis.patch.yml'),
        (Join-Path $env:DSH_HOME 'profiles\bili-duty\cordis.patch.yml'),
        $templatePath
    )
    $routePattern = [regex]'(?m)^(      opencode-go:)(\r?\n)(?:        baseURL:[^\r\n]*(\r?\n))?'
    foreach ($profilePath in $profilePaths) {
        if (-not (Test-Path -LiteralPath $profilePath)) { continue }
        $profileText = [System.IO.File]::ReadAllText($profilePath, [System.Text.Encoding]::UTF8)
        if ($routePattern.Matches($profileText).Count -ne 1) {
            throw "Expected one OpenCode Go route in $profilePath"
        }
        $profileText = $routePattern.Replace($profileText, [System.Text.RegularExpressions.MatchEvaluator]{
            param($match)
            $match.Groups[1].Value + $match.Groups[2].Value + '        baseURL: ' + $baseUrl + $match.Groups[2].Value
        }, 1)
        [System.IO.File]::WriteAllText($profilePath, $profileText, $utf8NoBom)
    }
}

Write-Host 'OpenCode Go profile patch ready. Restart DSH web to load it.'
