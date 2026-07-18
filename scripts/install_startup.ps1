$ErrorActionPreference = "Stop"

$ProjectRoot = Split-Path -Parent $PSScriptRoot
$StartScript = Join-Path $PSScriptRoot "start_star.ps1"
$TaskName = "STAR Assistant"
$PowerShell = "$env:SystemRoot\System32\WindowsPowerShell\v1.0\powershell.exe"
$Argument = "-NoProfile -ExecutionPolicy Bypass -File `"$StartScript`""

if (!(Test-Path $StartScript)) {
    throw "Cannot find start script: $StartScript"
}

$action = New-ScheduledTaskAction -Execute $PowerShell -Argument $Argument -WorkingDirectory $ProjectRoot
$trigger = New-ScheduledTaskTrigger -AtLogOn -User $env:USERNAME
$settings = New-ScheduledTaskSettingsSet -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries -ExecutionTimeLimit (New-TimeSpan -Days 365)
$principal = New-ScheduledTaskPrincipal -UserId $env:USERNAME -LogonType Interactive -RunLevel Limited

Register-ScheduledTask `
    -TaskName $TaskName `
    -Action $action `
    -Trigger $trigger `
    -Settings $settings `
    -Principal $principal `
    -Force | Out-Null

Write-Host "Installed startup task: $TaskName"
Write-Host "STAR will start automatically when this Windows user logs in."
Write-Host "Starting STAR now..."
& $StartScript
