$ErrorActionPreference = 'Stop'
$root = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path
$pidFile = Join-Path $root '.video-cutter.pid'
$app = Join-Path $root 'video_cutter.py'
$python = Join-Path $root '.venv\Scripts\python.exe'

if (Test-Path $pidFile) {
    $savedPid = 0
    if ([int]::TryParse((Get-Content $pidFile -Raw).Trim(), [ref]$savedPid) -and
        (Get-Process -Id $savedPid -ErrorAction SilentlyContinue)) {
        throw "Service may already be running (PID $savedPid)."
    }
    Remove-Item $pidFile
}

if (-not (Test-Path $python)) {
    $python = (Get-Command python -ErrorAction Stop).Source
}
if (-not (Get-Command ffmpeg -ErrorAction SilentlyContinue)) {
    throw 'ffmpeg was not found on PATH.'
}

$process = Start-Process -FilePath $python -ArgumentList @('-u', "`"$app`"", '--no-browser') `
    -WorkingDirectory $root -RedirectStandardOutput (Join-Path $root '.video-cutter.stdout.log') `
    -RedirectStandardError (Join-Path $root '.video-cutter.stderr.log') -WindowStyle Hidden -PassThru

Start-Sleep -Seconds 1
if ($process.HasExited) {
    throw "Service failed to start. See .video-cutter.stderr.log (exit code $($process.ExitCode))."
}

Set-Content -Path $pidFile -Value $process.Id
Write-Host "Service started (PID $($process.Id)): http://127.0.0.1:8765/"
