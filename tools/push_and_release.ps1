<#
.SYNOPSIS
    One command: refresh the plugin build if stale, push - CI releases the rest.

.DESCRIPTION
    "I want a release every time I push" - and with publish-yak.yml that is now
    literally what a push does:

        git push  ->  PyPI wheels        (wheels.yml, fully automatic)
                  ->  Yak plugin package (publish-yak.yml, fully automatic once
                                          the YAK_TOKEN secret is set)

    The ONE thing CI cannot do is compile compas_wood.rhp (RhinoCode needs a
    licensed Rhino), so this wrapper checks the committed artifact against the
    plugin sources first and rebuilds + stages it when stale - then pushes.
    If nothing plugin-side changed, it just pushes.

.EXAMPLE
    tools/push_and_release.ps1
#>
[CmdletBinding()]
param()

$ErrorActionPreference = 'Stop'
$Root   = Split-Path $PSScriptRoot -Parent
$Python = Join-Path $Root '.venv\Scripts\python.exe'
if (-not (Test-Path $Python)) { $Python = 'python' }

# Refresh the committed .rhp when plugin sources changed - CI would refuse to
# publish a stale one anyway (plugin_source_hash.py --check in publish-yak.yml).
& $Python (Join-Path $Root 'tools\plugin_source_hash.py') --check
if ($LASTEXITCODE -ne 0) {
    Write-Host "push_and_release: plugin sources changed - rebuilding .rhp locally..."
    & (Join-Path $PSScriptRoot 'refresh_plugin_build.ps1')
    git -C $Root add plugin_rhino/plugin/dist plugin_rhino/plugin/compas_wood.rhproj
    git -C $Root commit -m "chore(plugin): refresh compiled compas_wood.rhp"
}

Write-Host "push_and_release: pushing (CI releases PyPI wheels + Yak package)..."
git -C $Root push origin main
if ($LASTEXITCODE -ne 0) { throw "push_and_release: git push failed" }
Write-Host "push_and_release: done - watch the 'Build wheels' and 'Publish compas_wood to Yak' workflows."
