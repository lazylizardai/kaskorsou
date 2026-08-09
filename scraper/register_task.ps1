# KasKorsou Facebook-scraper - Windows Task Scheduler-taak registreren.
# Geen admin nodig: draait als de ingelogde gebruiker (Limited run level).
# Gebruikt run_facebook_scraper.ps1 als wrapper zodat PLAYWRIGHT_BROWSERS_PATH
# altijd goed staat (Task Scheduler neemt user-env-vars niet betrouwbaar mee).
$ErrorActionPreference = "Stop"
$repoPath = "C:\Users\Peter\KasKorsou"
$action = New-ScheduledTaskAction -Execute "powershell.exe" `
    -Argument "-NoProfile -ExecutionPolicy Bypass -File `"$repoPath\scraper\run_facebook_scraper.ps1`"" `
    -WorkingDirectory $repoPath
$trigger = New-ScheduledTaskTrigger -Daily -At 8:00AM
Register-ScheduledTask -TaskName "KasKorsou-FacebookScraper" -Action $action -Trigger $trigger -Force
Write-Host "Taak geregistreerd."
Get-ScheduledTask -TaskName "KasKorsou-FacebookScraper" | Select-Object TaskName, State
