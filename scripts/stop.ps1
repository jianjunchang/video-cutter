$ErrorActionPreference = 'Stop'
$root = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path
$pidFile = Join-Path $root '.video-cutter.pid'

if (-not (Test-Path $pidFile)) {
    Write-Host 'No service PID file found.'
    exit 0
}

$savedPid = 0
if (-not [int]::TryParse((Get-Content $pidFile -Raw).Trim(), [ref]$savedPid)) {
    throw 'Invalid service PID file.'
}

$process = Get-CimInstance Win32_Process -Filter "ProcessId = $savedPid"
if ($process) {
    if ($process.CommandLine -notlike '*video_cutter.py*') {
        throw "PID $savedPid belongs to another process. Remove the stale PID file manually."
    }
    Stop-Process -Id $savedPid -ErrorAction Stop
    Write-Host "Service stopped (PID $savedPid)."
} else {
    Write-Host 'Service was already stopped.'
}
Remove-Item $pidFile
