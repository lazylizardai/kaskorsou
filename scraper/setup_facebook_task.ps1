# KasKorsou - Facebook Marketplace-scraper opzetten op de Mini PC (Windows)
# Draai dit EEN keer in PowerShell (als Administrator) op de Mini PC.
#
# Wat dit doet:
#   1. Clonet/pullt de repo (GitHub = bron van waarheid)
#   2. Zet een losse venv op voor de scraper (met Playwright)
#   3. Installeert Chromium voor Playwright
#   4. Registreert een dagelijkse Windows Task Scheduler-taak die
#      alleen de facebook-scraper + dedup draait (los van de GitHub
#      Actions-cron, die kan geen headed browser draaien)
#
# fb_cookies.json staat al in de repo (geldig tot ~18 apr 2027, c_user
# 61557698407004) - dus geen nieuwe FB-login nodig, tenzij Facebook
# de sessie eerder afkeurt (zie opmerking onderaan over IP-herkomst).

$ErrorActionPreference = "Stop"
$repoPath = "C:\Users\Peter\KasKorsou"

if (-not (Test-Path $repoPath)) {
    Write-Host "Clonen naar $repoPath ..."
    git clone https://github.com/lazylizardai/kaskorsou.git $repoPath
} else {
    Write-Host "Repo bestaat al, pull laatste versie..."
    Set-Location $repoPath
    git pull
}
Set-Location $repoPath

Write-Host "`nPython venv aanmaken (scraper\.venv)..."
python -m venv scraper\.venv
& "scraper\.venv\Scripts\pip.exe" install --upgrade pip
& "scraper\.venv\Scripts\pip.exe" install -r scraper\requirements-facebook.txt

Write-Host "`nChromium installeren voor Playwright..."
& "scraper\.venv\Scripts\python.exe" -m playwright install chromium

if (-not (Test-Path "scraper\fb_cookies.json")) {
    Write-Warning "scraper\fb_cookies.json ontbreekt op deze machine - pull is mogelijk niet gelukt of .gitignore blokkeert 'm. Check handmatig."
} else {
    Write-Host "`nfb_cookies.json aanwezig. Vervaldatum check:"
    & "scraper\.venv\Scripts\python.exe" -c "import json,datetime;d=json.load(open('scraper/fb_cookies.json'));print(datetime.datetime.utcfromtimestamp(max(c.get('expirationDate',0) for c in d)))"
}

Write-Host "`nWindows Task Scheduler-taak registreren..."
$action = New-ScheduledTaskAction -Execute "$repoPath\scraper\.venv\Scripts\python.exe" `
    -Argument "-m scraper.orchestrator --sources facebook --dedup" `
    -WorkingDirectory $repoPath
$trigger = New-ScheduledTaskTrigger -Daily -At 8:00AM
Register-ScheduledTask -TaskName "KasKorsou-FacebookScraper" -Action $action -Trigger $trigger -RunLevel Highest -Force

Write-Host "`nKlaar. Taak 'KasKorsou-FacebookScraper' draait dagelijks om 08:00 lokale tijd (America/Curacao) - headed Chrome, dus laat de Mini PC niet in slaap gaan op dat tijdstip (Energiebeheer > 'Nooit slapen' aanzetten of alleen op stroom)."
Write-Host "Los testen zonder te wachten op de taak:"
Write-Host "  scraper\.venv\Scripts\python.exe -m scraper.orchestrator --sources facebook --dry-run"
Write-Host "`nAls FB tijdens de run naar een loginpagina redirect: cookies zijn verlopen/geweigerd. Opnieuw inloggen op facebook.com in Chrome op DEZE machine, cookies exporteren (EditThisCookie-extensie) en scraper\fb_cookies.json overschrijven - daarna committen naar de repo."
