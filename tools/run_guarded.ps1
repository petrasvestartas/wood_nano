<#
.SYNOPSIS
    Run a command under a wall-clock timeout AND a hard memory cap.

.DESCRIPTION
    On 2026-08-27 three concurrent copies of wood's main_wood_04_all_datasets.exe
    grew to 51 GB, 45 GB and 18 GB of committed memory on a 32 GB machine. Windows
    logged Resource-Exhaustion-Detector (event 2004) three times and then died with
    a dirty shutdown (Kernel-Power 41). Nothing bounded those runs.

    A timeout on its own would not have prevented that: the machine was already
    thrashing minutes before any sensible time limit expired. So this wrapper
    applies three independent guards:

      1. A Windows Job Object memory cap. This is kernel-enforced: the process is
         REFUSED memory past the cap and dies of a failed allocation, instead of
         pushing the rest of the system into the page file. This is the guard that
         actually protects the machine.
      2. A wall-clock timeout, after which the whole process tree is killed.
      3. A single-instance check, because concurrency is what turned a survivable
         leak into a machine crash. Three copies also raced on the same
         data/output/ files, so their results were garbage anyway.

    JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE means that if THIS script is killed, the
    child dies with it - no orphans surviving into the next session.

.EXAMPLE
    tools/run_guarded.ps1 -FilePath build/Release/main_all_datasets.exe

.EXAMPLE
    tools/run_guarded.ps1 -FilePath python -Arguments 'examples/foo.py' -TimeoutMinutes 2 -MemoryLimitGB 8
#>
[CmdletBinding()]
param(
    [Parameter(Mandatory = $true)][string]   $FilePath,
    [Parameter()]                 [string[]] $Arguments      = @(),
    [Parameter()]                 [double]   $TimeoutMinutes = 10,
    [Parameter()]                 [double]   $MemoryLimitGB  = 4,
    [Parameter()]                 [string]   $WorkingDirectory,
    # Identity for the one-at-a-time check. Defaults to the command plus its
    # arguments, so two different examples may run at once but two copies of the
    # same sweep may not.
    [Parameter()]                 [string]   $Name,
    # Opt out of the one-at-a-time rule. Only pass this after actually weighing
    # the peak memory of N copies against the RAM in the machine.
    [Parameter()]                 [switch]   $AllowConcurrent
)

$ErrorActionPreference = 'Stop'

if (-not (Get-Command $FilePath -ErrorAction SilentlyContinue)) {
    throw "run_guarded: '$FilePath' not found."
}
$resolved = (Get-Command $FilePath).Source
$procName = [IO.Path]::GetFileNameWithoutExtension($resolved)

# -- Guard 3: one at a time --------------------------------------------------
# Keyed on the command AND its arguments, tracked through a lock file rather
# than a process-name scan. Matching on the image name alone is useless for an
# interpreter: it cannot tell this sweep from an unrelated python.exe, so it
# would block on the user's Rhino session while still permitting two copies of
# the same sweep launched as `python a.py` and `python b.py`.
if (-not $Name) { $Name = "$procName $($Arguments -join ' ')" }
$lockKey  = -join ([Security.Cryptography.MD5]::Create().ComputeHash(
                       [Text.Encoding]::UTF8.GetBytes($Name)
                   ) | ForEach-Object { $_.ToString('x2') })
$lockDir  = Join-Path $env:TEMP 'run_guarded'
$lockFile = Join-Path $lockDir "$lockKey.lock"
New-Item -ItemType Directory -Path $lockDir -Force | Out-Null

if (-not $AllowConcurrent -and (Test-Path $lockFile)) {
    $holder = (Get-Content $lockFile -ErrorAction SilentlyContinue | Select-Object -First 1)
    if ($holder -and (Get-Process -Id $holder -ErrorAction SilentlyContinue)) {
        throw ("run_guarded: '{0}' is already running under a guard (PID {1}). Refusing to " -f $Name, $holder) +
              "start a second copy - concurrent runs are what exhausted memory on 2026-08-27. " +
              "Wait for it, or pass -AllowConcurrent if you are certain."
    }
    Remove-Item $lockFile -Force -ErrorAction SilentlyContinue   # stale, holder is gone
}
Set-Content -Path $lockFile -Value $PID -Encoding ascii

# -- Guard 1: kernel-enforced memory cap via a Job Object ---------------------
if (-not ('WoodGuard.Job' -as [type])) {
    Add-Type -Language CSharp -TypeDefinition @'
using System;
using System.Runtime.InteropServices;

namespace WoodGuard {
    [StructLayout(LayoutKind.Sequential)]
    public struct IO_COUNTERS {
        public ulong ReadOperationCount, WriteOperationCount, OtherOperationCount;
        public ulong ReadTransferCount,  WriteTransferCount,  OtherTransferCount;
    }

    [StructLayout(LayoutKind.Sequential)]
    public struct JOBOBJECT_BASIC_LIMIT_INFORMATION {
        public long    PerProcessUserTimeLimit;
        public long    PerJobUserTimeLimit;
        public uint    LimitFlags;
        public UIntPtr MinimumWorkingSetSize;
        public UIntPtr MaximumWorkingSetSize;
        public uint    ActiveProcessLimit;
        public UIntPtr Affinity;
        public uint    PriorityClass;
        public uint    SchedulingClass;
    }

    [StructLayout(LayoutKind.Sequential)]
    public struct JOBOBJECT_EXTENDED_LIMIT_INFORMATION {
        public JOBOBJECT_BASIC_LIMIT_INFORMATION BasicLimitInformation;
        public IO_COUNTERS IoInfo;
        public UIntPtr ProcessMemoryLimit;
        public UIntPtr JobMemoryLimit;
        public UIntPtr PeakProcessMemoryUsed;
        public UIntPtr PeakJobMemoryUsed;
    }

    public static class Job {
        const uint JOB_OBJECT_LIMIT_PROCESS_MEMORY    = 0x00000100;
        const uint JOB_OBJECT_LIMIT_JOB_MEMORY        = 0x00000200;
        const uint JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE = 0x00002000;
        const int  ExtendedLimitInformation           = 9;

        [DllImport("kernel32.dll", CharSet = CharSet.Unicode, SetLastError = true)]
        static extern IntPtr CreateJobObject(IntPtr a, string name);

        [DllImport("kernel32.dll", SetLastError = true)]
        static extern bool SetInformationJobObject(IntPtr job, int infoClass, IntPtr info, uint len);

        [DllImport("kernel32.dll", SetLastError = true)]
        static extern bool AssignProcessToJobObject(IntPtr job, IntPtr process);

        [DllImport("kernel32.dll", SetLastError = true)]
        static extern bool QueryInformationJobObject(IntPtr job, int infoClass, IntPtr info,
                                                     uint len, IntPtr returnedLen);

        [DllImport("kernel32.dll", SetLastError = true)]
        static extern bool TerminateJobObject(IntPtr job, uint exitCode);

        // A job capped at `bytes` of committed memory, per process and in total,
        // that kills its members when the handle closes.
        public static IntPtr CreateCapped(ulong bytes) {
            IntPtr job = CreateJobObject(IntPtr.Zero, null);
            if (job == IntPtr.Zero) throw new System.ComponentModel.Win32Exception();

            var info = new JOBOBJECT_EXTENDED_LIMIT_INFORMATION();
            info.BasicLimitInformation.LimitFlags =
                JOB_OBJECT_LIMIT_PROCESS_MEMORY |
                JOB_OBJECT_LIMIT_JOB_MEMORY |
                JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE;
            info.ProcessMemoryLimit = new UIntPtr(bytes);
            info.JobMemoryLimit     = new UIntPtr(bytes);

            int    len = Marshal.SizeOf(typeof(JOBOBJECT_EXTENDED_LIMIT_INFORMATION));
            IntPtr buf = Marshal.AllocHGlobal(len);
            try {
                Marshal.StructureToPtr(info, buf, false);
                if (!SetInformationJobObject(job, ExtendedLimitInformation, buf, (uint)len))
                    throw new System.ComponentModel.Win32Exception();
            } finally {
                Marshal.FreeHGlobal(buf);
            }
            return job;
        }

        public static void Assign(IntPtr job, IntPtr process) {
            if (!AssignProcessToJobObject(job, process))
                throw new System.ComponentModel.Win32Exception();
        }

        // Peak committed memory across every process in the job, children
        // included. Per-process counters are not enough: a venv python.exe is a
        // launcher that re-execs the real interpreter, so the process we started
        // reports a few hundred KB while its child holds gigabytes. The job
        // keeps this figure after its processes have exited.
        public static ulong PeakMemory(IntPtr job) {
            int    len = Marshal.SizeOf(typeof(JOBOBJECT_EXTENDED_LIMIT_INFORMATION));
            IntPtr buf = Marshal.AllocHGlobal(len);
            try {
                if (!QueryInformationJobObject(job, ExtendedLimitInformation, buf, (uint)len, IntPtr.Zero))
                    return 0;
                var info = (JOBOBJECT_EXTENDED_LIMIT_INFORMATION)Marshal.PtrToStructure(
                    buf, typeof(JOBOBJECT_EXTENDED_LIMIT_INFORMATION));
                return info.PeakJobMemoryUsed.ToUInt64();
            } finally {
                Marshal.FreeHGlobal(buf);
            }
        }

        // Kills every process in the job at once. Killing the process we started
        // is not enough when it has spawned children.
        public static void Terminate(IntPtr job) {
            TerminateJobObject(job, 1);
        }
    }
}
'@
}

$capBytes = [uint64]($MemoryLimitGB * 1GB)
$job      = [WoodGuard.Job]::CreateCapped($capBytes)

$psi = New-Object System.Diagnostics.ProcessStartInfo
$psi.FileName        = $resolved
$psi.Arguments       = ($Arguments -join ' ')
$psi.UseShellExecute = $false
if ($WorkingDirectory) { $psi.WorkingDirectory = (Resolve-Path $WorkingDirectory).Path }

Write-Host ("run_guarded: {0} {1}" -f $resolved, $psi.Arguments)
Write-Host ("run_guarded: limits - {0} min wall clock, {1} GB memory" -f $TimeoutMinutes, $MemoryLimitGB)

$sw   = [Diagnostics.Stopwatch]::StartNew()
$proc = [Diagnostics.Process]::Start($psi)
try {
    try {
        # Assign before the child can allocate anything substantial.
        [WoodGuard.Job]::Assign($job, $proc.Handle)
    } catch {
        $proc.Kill()
        throw "run_guarded: could not apply the memory cap, refusing to run unguarded. $_"
    }

    # -- Guard 2: wall clock -------------------------------------------------
    # Poll rather than one long WaitForExit so the deadline is checked as we go.
    while (-not $proc.WaitForExit(500)) {
        if ($sw.Elapsed.TotalMinutes -ge $TimeoutMinutes) {
            $peak = [math]::Round([WoodGuard.Job]::PeakMemory($job) / 1GB, 2)
            Write-Warning ("run_guarded: still running after {0} min - killing it (peak commit {1} GB)." -f $TimeoutMinutes, $peak)
            [WoodGuard.Job]::Terminate($job)   # the whole tree, not just the process we started
            $proc.WaitForExit()
            exit 124                           # conventional timeout exit code
        }
    }

    $sw.Stop()
    $peak = [math]::Round([WoodGuard.Job]::PeakMemory($job) / 1GB, 2)
    Write-Host ("run_guarded: exit {0} after {1:n1}s, peak commit {2} GB" -f $proc.ExitCode, $sw.Elapsed.TotalSeconds, $peak)

    if ($proc.ExitCode -ne 0 -and $peak -ge ($MemoryLimitGB * 0.95)) {
        Write-Warning (("run_guarded: peak commit sat at the {0} GB cap - the memory limit is " -f $MemoryLimitGB) +
                       "what stopped this run. That is a bug in the program, not in the cap.")
    }
    exit $proc.ExitCode
}
finally {
    # Release the one-at-a-time lock however we leave: normal exit, timeout,
    # throw, or Ctrl-C. A lock left behind would block the next run.
    Remove-Item $lockFile -Force -ErrorAction SilentlyContinue
}
