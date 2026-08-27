<#
.SYNOPSIS
    Run every example under tools/run_guarded.ps1 and report pass/fail.

.DESCRIPTION
    Sequentially - never in parallel. One example at a time is the whole point of
    the guard; see CLAUDE.md.

    Examples run through tools/headless_example.py, which stubs out any GUI
    viewer call so nothing blocks on a window.

.EXAMPLE
    tools/run_all_examples.ps1
#>
[CmdletBinding()]
param(
    [Parameter()] [string] $Python         = '.\.venv\Scripts\python.exe',
    [Parameter()] [double] $TimeoutMinutes = 5,
    [Parameter()] [double] $MemoryLimitGB  = 4
)

$ErrorActionPreference = 'Continue'

$root    = Split-Path $PSScriptRoot -Parent
$guard   = Join-Path $PSScriptRoot 'run_guarded.ps1'
$headless= Join-Path $PSScriptRoot 'headless_example.py'

$examples = @(
    Get-ChildItem -Path (Join-Path $root 'examples_session_py') -Filter '*.py' -Recurse
) | Sort-Object FullName

Write-Host ("Running {0} examples, one at a time, {1} min / {2} GB each.`n" -f $examples.Count, $TimeoutMinutes, $MemoryLimitGB)

$results = @()
foreach ($ex in $examples) {
    $rel = $ex.FullName.Substring($root.Length + 1)
    Write-Host ("--- {0}" -f $rel)

    # -X utf8 because several examples print arrows (-> and <->) in their
    # tables. Capturing stdout here makes Python fall back to the console
    # codepage, cp1252, which cannot encode them - the examples themselves are
    # fine when run straight into a UTF-8 terminal.
    $output = & $guard -FilePath $Python -Arguments '-X', 'utf8', $headless, $ex.FullName `
                       -TimeoutMinutes $TimeoutMinutes -MemoryLimitGB $MemoryLimitGB 2>&1
    $code = $LASTEXITCODE
    $output | ForEach-Object { Write-Host "    $_" }

    $status = switch ($code) {
        0       { 'PASS' }
        124     { 'TIMEOUT' }
        default { 'FAIL' }
    }
    $results += [pscustomobject]@{ Example = $rel; Status = $status; ExitCode = $code }
    Write-Host ""
}

Write-Host "`n===================== SUMMARY ====================="
$results | Sort-Object Status, Example | Format-Table -AutoSize | Out-String -Width 200 | Write-Host

$failed = @($results | Where-Object { $_.Status -ne 'PASS' })
Write-Host ("{0}/{1} passed." -f ($results.Count - $failed.Count), $results.Count)
if ($failed.Count -gt 0) {
    Write-Host "FAILURES:"
    $failed | ForEach-Object { Write-Host ("  {0}  [{1}]" -f $_.Example, $_.Status) }
    exit 1
}
exit 0
