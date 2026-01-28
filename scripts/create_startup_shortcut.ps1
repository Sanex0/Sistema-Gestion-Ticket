$wsh = New-Object -ComObject WScript.Shell
$startup = [Environment]::GetFolderPath('Startup')
$lnk = Join-Path $startup 'GestionTicket_EmailIdle.lnk'
$target = 'C:\Users\Usuario\Desktop\gestion_ticket\run_email_idle.bat'
$sc = $wsh.CreateShortcut($lnk)
$sc.TargetPath = $target
$sc.WorkingDirectory = 'C:\Users\Usuario\Desktop\gestion_ticket'
$sc.WindowStyle = 7
$sc.Save()
Write-Output "Shortcut created at $lnk"
