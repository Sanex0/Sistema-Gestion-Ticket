# Register scheduled task to run the email ingestor at logon
$taskName = 'GestionTicket_EmailIdle'
$batPath = 'C:\Users\Usuario\Desktop\gestion_ticket\run_email_idle.bat'
$action = New-ScheduledTaskAction -Execute $batPath
$trigger = New-ScheduledTaskTrigger -AtLogOn
$settings = New-ScheduledTaskSettingsSet -RestartCount 5 -RestartInterval (New-TimeSpan -Minutes 1) -AllowStartIfOnBatteries -StartWhenAvailable
try {
    Register-ScheduledTask -TaskName $taskName -Action $action -Trigger $trigger -Settings $settings -RunLevel Highest -Force
    Write-Output "Scheduled task '$taskName' registered"
} catch {
    Write-Error "Failed to register scheduled task: $_"
}
Get-ScheduledTask -TaskName $taskName | Format-List | Out-String | Write-Output
