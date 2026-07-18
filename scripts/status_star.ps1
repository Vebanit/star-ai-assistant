$ErrorActionPreference = "SilentlyContinue"

$ProjectRoot = Split-Path -Parent $PSScriptRoot
$RuntimeDir = Join-Path $ProjectRoot "runtime"
$BackendPidFile = Join-Path $RuntimeDir "backend.pid"
$WakePidFile = Join-Path $RuntimeDir "wake_word.pid"
$WakeErrorLog = Join-Path $RuntimeDir "wake_word.err.log"

function Get-PidStatus {
    param([string]$Name, [string]$PidFile)
    if (!(Test-Path $PidFile)) {
        return "${Name}: no pid file"
    }
    $processId = [int](Get-Content $PidFile)
    $process = Get-Process -Id $processId
    if ($null -eq $process) {
        return "${Name}: stopped (last PID $processId)"
    }
    return "${Name}: running (PID $processId)"
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

try {
    $health = Invoke-WebRequest -UseBasicParsing "http://127.0.0.1:8000/health" -TimeoutSec 2
    $backendHealth = "Backend health: $($health.StatusCode)"
} catch {
    $backendHealth = "Backend health: not reachable"
}

Write-Host $backendHealth
Write-Host (Get-PidStatus "Backend process" $BackendPidFile)
Write-Host (Get-PidStatus "Wake listener" $WakePidFile)
if (Test-Path $WakeErrorLog) {
    $wakeErrors = Get-Content $WakeErrorLog -Tail 5
    if ($wakeErrors) {
        Write-Host "Last wake listener error:"
        $wakeErrors | ForEach-Object { Write-Host $_ }
    }
}
Write-Host "Dashboard: http://127.0.0.1:8000/dashboard"
$mobileUrls = Get-StarLanUrls
if ($mobileUrls) {
    Write-Host "Mobile companion URLs:"
    $mobileUrls | ForEach-Object { Write-Host $_ }
}
