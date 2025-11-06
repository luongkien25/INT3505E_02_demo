<#
.SYNOPSIS
  Run a Postman collection with Newman in parallel workers.

.DESCRIPTION
  Spawns N parallel jobs, each running a given collection for a number of iterations.
  Useful to approximate load using Postman/Newman (not a full load test framework).

.PARAMETER CollectionPath
  Path to the Postman collection (.json)

.PARAMETER Iterations
  Iterations per worker (default: 100)

.PARAMETER Workers
  Number of parallel jobs (default: 5)

.PARAMETER EnvPath
  Optional Postman environment file (.json)

.PARAMETER ReportDir
  Directory to store per-job JSON reports (default: ./newman-reports)

.EXAMPLE
  powershell.exe -ExecutionPolicy Bypass -File .\scripts\newman_parallel.ps1 -CollectionPath .\postman\UsersAPI.postman_collection.json -Iterations 100 -Workers 5

.NOTES
  Requires Node.js and Newman installed globally:
    npm install -g newman
#>
[CmdletBinding()]
param(
  [Parameter(Mandatory=$true)][string]$CollectionPath,
  [int]$Iterations = 100,
  [int]$Workers = 5,
  [string]$EnvPath,
  [string]$ReportDir = "newman-reports"
)

function Assert-NewmanInstalled {
  $version = & newman -v 2>$null
  if (-not $?) {
    Write-Error "Newman is not installed or not in PATH. Install with: npm install -g newman"
    exit 1
  }
  Write-Host "Using Newman $version" -ForegroundColor Cyan
}

function Ensure-ReportDir($path) {
  if (-not (Test-Path $path)) { New-Item -ItemType Directory -Path $path | Out-Null }
}

Assert-NewmanInstalled
Ensure-ReportDir -path $ReportDir

if (-not (Test-Path $CollectionPath)) { Write-Error "Collection not found: $CollectionPath"; exit 1 }
if ($EnvPath -and -not (Test-Path $EnvPath)) { Write-Error "Environment not found: $EnvPath"; exit 1 }

$jobs = @()
for ($i = 1; $i -le $Workers; $i++) {
  $reportJson = Join-Path $ReportDir ("job_$i.json")
  $reportCli  = Join-Path $ReportDir ("job_$i.txt")
  $args = @('run', $CollectionPath, '-n', $Iterations, '-r', 'cli,json', '--reporter-json-export', $reportJson)
  if ($EnvPath) { $args += @('-e', $EnvPath) }
  Write-Host "Starting worker #$i: newman $($args -join ' ')" -ForegroundColor Yellow
  $jobs += Start-Job -ScriptBlock {
    param($ArgsForNewman, $ReportCli)
    $psi = New-Object System.Diagnostics.ProcessStartInfo
    $psi.FileName = 'newman'
    $psi.Arguments = ($ArgsForNewman -join ' ')
    $psi.RedirectStandardOutput = $true
    $psi.RedirectStandardError = $true
    $psi.UseShellExecute = $false
    $proc = New-Object System.Diagnostics.Process
    $proc.StartInfo = $psi
    $null = $proc.Start()
    $stdout = $proc.StandardOutput.ReadToEnd()
    $stderr = $proc.StandardError.ReadToEnd()
    $proc.WaitForExit()
    Set-Content -Path $ReportCli -Value ($stdout + "`n" + $stderr)
    return $proc.ExitCode
  } -ArgumentList ($args, $reportCli)
}

Write-Host "Waiting for $Workers workers..." -ForegroundColor Cyan
Wait-Job -Job $jobs | Out-Null
$results = $jobs | Receive-Job

$failed = ($results | Where-Object { $_ -ne 0 }).Count
$passed = $Workers - $failed
Write-Host "Completed. Workers passed: $passed, failed: $failed" -ForegroundColor Green

# Optional: summarize request counts from JSON reports
try {
  $totalReq = 0; $totalFail = 0
  Get-ChildItem $ReportDir -Filter 'job_*.json' | ForEach-Object {
    $j = Get-Content $_.FullName -Raw | ConvertFrom-Json
    $stats = $j.run.stats
    $totalReq += $stats.requests.total
    $totalFail += $stats.requests.failed
  }
  Write-Host ("Summary: total requests={0}, failed={1}" -f $totalReq, $totalFail) -ForegroundColor Magenta
} catch { }
