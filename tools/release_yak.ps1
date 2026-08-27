<#
.SYNOPSIS
    Build the compas_wood Rhino plugin and publish it to the Yak server.

.DESCRIPTION
    PyPI wheels release automatically on every push to main (wheels.yml), but
    Yak CANNOT be released from GitHub CI: the .yak contains a compiled
    compas_wood.rhp, and only RhinoCode with a licensed Rhino installation can
    produce it - GitHub runners have neither. This script is the local half of
    the release story: one command builds and publishes the plugin.

    Steps:
      1. Bump the patch version in compas_wood.rhproj (identity/version),
         unless -Version is given explicitly or -NoBump is set.
      2. rhinocode project build -> compas_wood.rhp + manifest.yml + .yak
         under plugin_rhino/plugin/build/rh8.
      3. yak push the freshest .yak (skipped with -DryRun).

    First-time setup: run "& 'C:\Program Files\Rhino 8\System\Yak.exe' login"
    once so the push has a cached token.

.EXAMPLE
    tools/release_yak.ps1              # bump patch, build, push
    tools/release_yak.ps1 -DryRun     # bump + build only
    tools/release_yak.ps1 -Version 3.11.0
#>
[CmdletBinding()]
param(
    [Parameter()] [string] $Version,
    [Parameter()] [switch] $NoBump,
    [Parameter()] [switch] $DryRun
)

$ErrorActionPreference = 'Stop'

$RhinoCode = 'C:\Program Files\Rhino 8\System\RhinoCode.exe'
$Yak       = 'C:\Program Files\Rhino 8\System\Yak.exe'
$Root      = Split-Path $PSScriptRoot -Parent
$Rhproj    = Join-Path $Root 'plugin_rhino\plugin\compas_wood.rhproj'
$BuildDir  = Join-Path $Root 'plugin_rhino\plugin\build\rh8'

foreach ($exe in @($RhinoCode, $Yak)) {
    if (-not (Test-Path $exe)) { throw "release_yak: $exe not found - is Rhino 8 installed?" }
}
if (-not (Test-Path $Rhproj)) { throw "release_yak: $Rhproj not found" }

# ── 1. Version ───────────────────────────────────────────────────────────────
# Surgical regex bump - NEVER round-trip the rhproj through ConvertTo-Json:
# it holds base64-encoded command payloads and a full JSON rewrite in
# PowerShell 5.1 can reformat or mangle them.
$raw = Get-Content $Rhproj -Raw -Encoding UTF8
$m = [regex]::Match($raw, '"identity"\s*:\s*\{[^{}]*?"version"\s*:\s*"([^"]+)"',
                    [Text.RegularExpressions.RegexOptions]::Singleline)
if (-not $m.Success) { throw 'release_yak: identity/version not found in rhproj' }
$current = $m.Groups[1].Value
if ($Version) {
    $new = $Version
} elseif ($NoBump) {
    $new = $current
} else {
    $parts = $current.Split('.')
    if ($parts.Count -lt 3) { $parts = @($parts + @('0', '0'))[0..2] }
    $parts[2] = [string]([int]$parts[2] + 1)
    $new = $parts -join '.'
}
if ($new -ne $current) {
    $g = $m.Groups[1]
    $raw = $raw.Substring(0, $g.Index) + $new + $raw.Substring($g.Index + $g.Length)
    # Write back byte-faithfully except for the version substring.
    [IO.File]::WriteAllText($Rhproj, $raw, (New-Object Text.UTF8Encoding($false)))
    Write-Host "release_yak: version $current -> $new (written to rhproj)"
} else {
    Write-Host "release_yak: version $new"
}

# ── 2. Build (needs Rhino license; may briefly start Rhino headless) ─────────
New-Item -ItemType Directory -Force $BuildDir | Out-Null
Write-Host "release_yak: building plugin via RhinoCode..."
& $RhinoCode project build $Rhproj --buildversion $new --buildpath $BuildDir
if ($LASTEXITCODE -ne 0) { throw "release_yak: rhinocode project build failed ($LASTEXITCODE)" }

# The build drops manifest.yml + compas_wood.rhp; ensure there is a fresh .yak
$yakFile = Get-ChildItem $BuildDir -Filter '*.yak' |
           Sort-Object LastWriteTime -Descending | Select-Object -First 1
$manifest = Join-Path $BuildDir 'manifest.yml'
if (-not $yakFile -or ((Test-Path $manifest) -and
        $yakFile.LastWriteTime -lt (Get-Item $manifest).LastWriteTime)) {
    Write-Host "release_yak: packing .yak..."
    Push-Location $BuildDir
    try {
        & $Yak build
        if ($LASTEXITCODE -ne 0) { throw "release_yak: yak build failed ($LASTEXITCODE)" }
    } finally { Pop-Location }
    $yakFile = Get-ChildItem $BuildDir -Filter '*.yak' |
               Sort-Object LastWriteTime -Descending | Select-Object -First 1
}
if (-not $yakFile) { throw "release_yak: no .yak produced" }
Write-Host ("release_yak: built {0}" -f $yakFile.Name)

# ── 3. Push ──────────────────────────────────────────────────────────────────
if ($DryRun) {
    Write-Host "release_yak: dry run - NOT pushing. Push manually with:"
    Write-Host ("  & '{0}' push '{1}'" -f $Yak, $yakFile.FullName)
    exit 0
}
Write-Host "release_yak: pushing to Yak server..."
& $Yak push $yakFile.FullName
if ($LASTEXITCODE -ne 0) {
    throw ("release_yak: yak push failed ({0}). If you have never logged in on this " +
           "machine, run: & '{1}' login" -f $LASTEXITCODE, $Yak)
}
Write-Host ("release_yak: published {0} - it appears in Rhino's Package Manager " -f $yakFile.Name) `
           "after server indexing (usually minutes)."
