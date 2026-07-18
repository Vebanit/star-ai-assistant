$ErrorActionPreference = "SilentlyContinue"

$ProjectRoot = Split-Path -Parent $PSScriptRoot
$RuntimeDir = Join-Path $ProjectRoot "runtime"
$PidFiles = @(
    Join-Path $RuntimeDir "desktop_power_button.pid"
    Join-Path $RuntimeDir "wake_word.pid"
    Join-Path $RuntimeDir "backend.pid"
)

foreach ($pidFile in $PidFiles) {
    if (!(Test-Path $pidFile)) {
        continue
    }
    $processId = [int](Get-Content $pidFile)
    $process = Get-Process -Id $processId
    if ($null -ne $process) {
        Stop-Process -Id $processId -Force
        Write-Host "Stopped PID $processId"
    }
    Remove-Item -LiteralPath $pidFile -Force
}

Write-Host "STAR stopped manually. Normal voice commands never call this script."
