<#
.SYNOPSIS
    Rebuild the compas_wood plugin locally and refresh the committed artifacts
    that CI packages into the Yak release.

.DESCRIPTION
    The ONE step of the Yak pipeline that cannot run on GitHub CI is compiling
    compas_wood.rhp - RhinoCode needs a licensed Rhino. Everything else
    (packaging with a standalone yak.exe, version bump, push) runs in
    .github/workflows/publish-yak.yml on every push, OpenNest-style.

    So the contract is: whenever plugin sources change (commands/, shared/,
    icons, rhproj), run THIS script once and commit plugin_rhino/plugin/dist/.
    CI refuses to publish a stale .rhp - it recomputes the source hash and
    compares it against the stamp this script writes.

    Steps:
      1. gen_rhproj.py            - regenerate the rhproj from commands+icons
      2. RhinoCode project build  - compile .rhp (scratch dir, not the repo)
      3. copy .rhp/.rui/manifest into plugin_rhino/plugin/dist/
      4. stamp dist/source_hash.txt

.EXAMPLE
    tools/refresh_plugin_build.ps1
#>
[CmdletBinding()]
param()

$ErrorActionPreference = 'Stop'

$RhinoCode = 'C:\Program Files\Rhino 8\System\RhinoCode.exe'
$Root      = Split-Path $PSScriptRoot -Parent
$Plugin    = Join-Path $Root 'plugin_rhino\plugin'
$Rhproj    = Join-Path $Plugin 'compas_wood.rhproj'
$Dist      = Join-Path $Plugin 'dist'
$Scratch   = Join-Path $env:TEMP ("compas_wood_rhp_" + [guid]::NewGuid().ToString('N').Substring(0, 8))
$Python    = Join-Path $Root '.venv\Scripts\python.exe'

if (-not (Test-Path $RhinoCode)) { throw "refresh_plugin_build: $RhinoCode not found - is Rhino 8 installed?" }
if (-not (Test-Path $Python))    { $Python = 'python' }

# 1. Regenerate the rhproj so it embeds the current command sources and icons.
Write-Host "refresh_plugin_build: regenerating rhproj..."
& $Python (Join-Path $Plugin 'shared\gen_rhproj.py')
if ($LASTEXITCODE -ne 0) { throw "gen_rhproj.py failed ($LASTEXITCODE)" }

# 2. Compile in a scratch dir - building into the repo previously nested a
#    second build tree inside plugin/build/rh8.
$ver = ([regex]::Match((Get-Content $Rhproj -Raw), '"identity"\s*:\s*\{[^{}]*?"version"\s*:\s*"([^"]+)"',
        [Text.RegularExpressions.RegexOptions]::Singleline)).Groups[1].Value
if (-not $ver) { throw "identity/version not found in rhproj" }
New-Item -ItemType Directory -Force $Scratch | Out-Null
Write-Host "refresh_plugin_build: building .rhp (v$ver) via RhinoCode..."
& $RhinoCode project build $Rhproj --buildversion $ver --buildpath $Scratch
if ($LASTEXITCODE -ne 0) { throw "rhinocode project build failed ($LASTEXITCODE)" }

# 3. Refresh dist/ with the compiled artifacts. shared/ datasets are NOT
#    copied - CI stages them from their tracked source location.
New-Item -ItemType Directory -Force $Dist | Out-Null
# RhinoCode nests output under a target subfolder of the buildpath (rh8/).
$outDir = Join-Path $Scratch 'rh8'
if (-not (Test-Path (Join-Path $outDir 'compas_wood.rhp'))) { $outDir = $Scratch }
foreach ($f in @('compas_wood.rhp', 'compas_wood.rui', 'manifest.yml')) {
    $src = Join-Path $outDir $f
    if (-not (Test-Path $src)) { throw "refresh_plugin_build: $f missing from build output ($outDir)" }
    Copy-Item $src $Dist -Force
}
Remove-Item $Scratch -Recurse -Force -ErrorAction SilentlyContinue

# 4. Freshness stamp - the contract CI enforces before publishing.
& $Python (Join-Path $Root 'tools\plugin_source_hash.py') |
    Select-Object -Last 1 | Set-Content (Join-Path $Dist 'source_hash.txt') -Encoding ascii

Write-Host "refresh_plugin_build: dist/ refreshed - commit plugin_rhino/plugin/dist/ (and the rhproj if it changed)."
