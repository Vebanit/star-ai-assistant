$ErrorActionPreference = "Stop"

$ProjectRoot = Split-Path -Parent $PSScriptRoot
$RuntimeDir = Join-Path $ProjectRoot "runtime"
$BackendPidFile = Join-Path $RuntimeDir "backend.pid"
$WakePidFile = Join-Path $RuntimeDir "wake_word.pid"
$BackendLog = Join-Path $RuntimeDir "backend.log"
$BackendErrorLog = Join-Path $RuntimeDir "backend.err.log"
$WakeLog = Join-Path $RuntimeDir "wake_word.log"
$WakeErrorLog = Join-Path $RuntimeDir "wake_word.err.log"
$Python = Join-Path $ProjectRoot "venv\Scripts\python.exe"

if (!(Test-Path $Python)) {
    $Python = "python"
}

New-Item -ItemType Directory -Force -Path $RuntimeDir | Out-Null

function Test-StarBackend {
    try {
        $response = Invoke-WebRequest -UseBasicParsing "http://127.0.0.1:8000/health" -TimeoutSec 2
        return $response.StatusCode -eq 200
    } catch {
        return $false
    }
}

function Get-StarLanUrls {
    $ips = Get-NetIPAddress -AddressFamily IPv4 |
        Where-Object {
            $_.IPAddress -ne "127.0.0.1" -and
            $_.IPAddress -notlike "169.254.*" -and
            $_.IPAddress -notlike "0.*"
        } |
        Select-Object -ExpandProperty IPAddress

    return $ips | ForEach-Object { "http://${_}:8000/mobile" }
}

function Test-RunningPid {
    param([string]$PidFile)
    if (!(Test-Path $PidFile)) {
        return $false
    }
    try {
        $processId = [int](Get-Content $PidFile -ErrorAction Stop)
        $process = Get-Process -Id $processId -ErrorAction SilentlyContinue
        return $null -ne $process
    } catch {
        return $false
    }
}

if (Test-StarBackend) {
    Write-Host "STAR backend already running on http://127.0.0.1:8000"
} else {
    $backend = Start-Process `
        -FilePath $Python `
        -ArgumentList @("-m", "uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000") `
        -WorkingDirectory $ProjectRoot `
        -WindowStyle Hidden `
        -RedirectStandardOutput $BackendLog `
        -RedirectStandardError $BackendErrorLog `
        -PassThru
    Set-Content -Path $BackendPidFile -Value $backend.Id
    Write-Host "STAR backend started with PID $($backend.Id)"

    for ($i = 0; $i -lt 20; $i++) {
        if (Test-StarBackend) {
            break
        }
        Start-Sleep -Milliseconds 500
    }
}

if (Test-RunningPid $WakePidFile) {
    Write-Host "STAR wake listener already running."
} else {
    $wake = Start-Process `
        -FilePath $Python `
        -ArgumentList @("wake_word.py") `
        -WorkingDirectory $ProjectRoot `
        -WindowStyle Hidden `
        -RedirectStandardOutput $WakeLog `
        -RedirectStandardError $WakeErrorLog `
        -PassThru
    Set-Content -Path $WakePidFile -Value $wake.Id
    Start-Sleep -Seconds 2
    if ($null -eq (Get-Process -Id $wake.Id -ErrorAction SilentlyContinue)) {
        Write-Host "STAR wake listener tried to start, but exited early."
        if (Test-Path $WakeErrorLog) {
            Write-Host "Wake listener error:"
            Get-Content $WakeErrorLog -Tail 12
        }
    } else {
        Write-Host "STAR wake listener started with PID $($wake.Id)"
    }
}

Write-Host "STAR is ready. Dashboard: http://127.0.0.1:8000/dashboard"
$mobileUrls = Get-StarLanUrls
if ($mobileUrls) {
    Write-Host "Mobile companion URLs:"
    $mobileUrls | ForEach-Object { Write-Host $_ }
}
