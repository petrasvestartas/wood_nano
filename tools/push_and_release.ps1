<#
.SYNOPSIS
    One command: push to GitHub (-> PyPI wheels via CI) AND release to Yak.

.DESCRIPTION
    "I want a release every time I push." The PyPI half is already automatic:
    every push to main bumps the version, builds 4 wheels and publishes
    (wheels.yml). The Yak half cannot run on CI - the .rhp build needs a
    licensed Rhino - so this wrapper makes it one local command instead:

        tools/push_and_release.ps1

    does `git push origin main`, then runs tools/release_yak.ps1. If there is
    nothing to push it still releases to Yak, so it is safe to re-run.

.EXAMPLE
    tools/push_and_release.ps1
    tools/push_and_release.ps1 -DryRun     # push to GitHub, build yak, no yak push
#>
[CmdletBinding()]
param(
    [Parameter()] [switch] $DryRun
)

$ErrorActionPreference = 'Stop'
$Root = Split-Path $PSScriptRoot -Parent

Write-Host "push_and_release: pushing to GitHub (PyPI wheels release from CI)..."
git -C $Root push origin main
if ($LASTEXITCODE -ne 0) { throw "push_and_release: git push failed" }

& (Join-Path $PSScriptRoot 'release_yak.ps1') -DryRun:$DryRun
