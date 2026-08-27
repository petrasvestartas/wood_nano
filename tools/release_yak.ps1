<#
.SYNOPSIS
    Manual fallback: package + publish the compas_wood Yak release locally.

.DESCRIPTION
    The normal path is automatic: every push to main runs publish-yak.yml,
    which packages the committed plugin_rhino/plugin/dist/ artifacts with the
    standalone yak.exe and pushes to the Yak server (OpenNest-style). Use this
    script only when CI is unavailable.

    It stages exactly what CI stages (dist/ artifacts + shared/ datasets),
    bumps the manifest patch version from whatever is live on the Yak server,
    builds, and pushes with the locally cached `yak login` token.

.EXAMPLE
    tools/release_yak.ps1              # refresh if stale, package, push
    tools/release_yak.ps1 -DryRun     # package only
#>
[CmdletBinding()]
param(
    [Parameter()] [string] $Version,
    [Parameter()] [switch] $DryRun
)

$ErrorActionPreference = 'Stop'

$Yak    = 'C:\Program Files\Rhino 8\System\Yak.exe'
$Root   = Split-Path $PSScriptRoot -Parent
$Dist   = Join-Path $Root 'plugin_rhino\plugin\dist'
$Shared = Join-Path $Root 'plugin_rhino\plugin\shared'
$Stage  = Join-Path $Root 'plugin_rhino\plugin\build\yak_stage'
$Python = Join-Path $Root '.venv\Scripts\python.exe'
if (-not (Test-Path $Python)) { $Python = 'python' }
if (-not (Test-Path $Yak)) { throw "release_yak: $Yak not found - is Rhino 8 installed?" }

# Ensure the committed .rhp matches the sources; rebuild if not.
& $Python (Join-Path $Root 'tools\plugin_source_hash.py') --check
if ($LASTEXITCODE -ne 0) {
    & (Join-Path $PSScriptRoot 'refresh_plugin_build.ps1')
}

# Version: highest of manifest and live Yak server, patch+1 (same as CI).
$manifest = Get-Content (Join-Path $Dist 'manifest.yml') -Raw
if ($manifest -notmatch 'version:\s*([0-9]+)\.([0-9]+)\.([0-9]+)') { throw 'version not found in manifest' }
$base = [version]"$($Matches[1]).$($Matches[2]).$($Matches[3])"
if (-not $Version) {
    try {
        $y = (Invoke-RestMethod -Uri 'https://yak.rhino3d.com/packages/compas_wood' -TimeoutSec 20).version
        if ($y -match '([0-9]+)\.([0-9]+)\.([0-9]+)') {
            $yv = [version]"$($Matches[1]).$($Matches[2]).$($Matches[3])"
            if ($yv -gt $base) { $base = $yv }
        }
    } catch { Write-Host "release_yak: Yak version query failed; using manifest. $_" }
    $Version = "$($base.Major).$($base.Minor).$($base.Build + 1)"
}
Write-Host "release_yak: packaging version $Version"

# Stage exactly like CI.
if (Test-Path $Stage) { Remove-Item $Stage -Recurse -Force }
New-Item -ItemType Directory -Force $Stage | Out-Null
Copy-Item (Join-Path $Dist 'compas_wood.rhp') $Stage
Copy-Item (Join-Path $Dist 'compas_wood.rui') $Stage
Copy-Item $Shared (Join-Path $Stage 'shared') -Recurse
$manifest = $manifest -replace 'version:\s*[0-9][^\r\n]*', "version: $Version"
Set-Content (Join-Path $Stage 'manifest.yml') $manifest -NoNewline

Push-Location $Stage
try {
    & $Yak build
    if ($LASTEXITCODE -ne 0) { throw "yak build failed ($LASTEXITCODE)" }
} finally { Pop-Location }
Get-ChildItem "$Stage/*.yak" | ForEach-Object {
    $n = $_.Name -replace '-(any|rh[0-9_]+)-(win|mac|any)\.yak$', '-rh8-any.yak'
    if ($n -ne $_.Name) { Rename-Item $_.FullName $n }
}
$yakFile = Get-ChildItem "$Stage/*.yak" | Select-Object -First 1
if (-not $yakFile) { throw 'release_yak: no .yak produced' }
Write-Host ("release_yak: built {0}" -f $yakFile.Name)

if ($DryRun) {
    Write-Host "release_yak: dry run - not pushing."
    exit 0
}
& $Yak push $yakFile.FullName
if ($LASTEXITCODE -ne 0) {
    throw "release_yak: yak push failed ($LASTEXITCODE). If never logged in here, run: & '$Yak' login"
}
Write-Host "release_yak: published $($yakFile.Name)"
