$ErrorActionPreference = "SilentlyContinue"

$TaskName = "STAR Assistant"
Unregister-ScheduledTask -TaskName $TaskName -Confirm:$false
Write-Host "Removed startup task: $TaskName"
