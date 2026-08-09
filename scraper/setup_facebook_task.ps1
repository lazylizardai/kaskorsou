# KasKorsou - Facebook Marketplace-scraper opzetten op de Mini PC (Windows)
# Draai dit EEN keer in PowerShell op de Mini PC. GEEN Administrator nodig
# (eerder geprobeerd met -RunLevel Highest, maar dat vereist elevatie zonder
# nut - de scraper heeft geen adminrechten nodig. Limited run level werkt prima).
#
# Wat dit doet:
#   1. Clonet/pullt de repo (GitHub = bron van waarheid)
#   2. Zet een losse venv op voor de scraper (met Playwright)
#   3. Installeert Chromium voor Playwright naar C:\pw-browsers
#      (NIET naar het AppData\Local\ms-playwright default-pad - op deze
#      machine gaf dat een Windows SxS-fout "kan afhankelijke assembly niet
#      vinden" bij het starten van chrome.exe; vanuit een ander pad werkte
#      exact dezelfde build meteen. Root cause niet honderd procent zeker,
#      maar het omzeilen werkt betrouwbaar.)
#   4. Registreert een dagelijkse Windows Task Scheduler-taak die
#      alleen de facebook-scraper + dedup draait (los van de GitHub
#      Actions-cron, die kan geen headed browser draaien)
#
# fb_cookies.json staat al in de repo (geldig tot mei 2027, c_user
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

Write-Host "`nChromium installeren voor Playwright (naar C:\pw-browsers)..."
$env:PLAYWRIGHT_BROWSERS_PATH = "C:\pw-browsers"
[System.Environment]::SetEnvironmentVariable("PLAYWRIGHT_BROWSERS_PATH", "C:\pw-browsers", "User")
& "scraper\.venv\Scripts\python.exe" -m playwright install chromium

if (-not (Test-Path "scraper\fb_cookies.json")) {
    Write-Warning "scraper\fb_cookies.json ontbreekt op deze machine - pull is mogelijk niet gelukt of .gitignore blokkeert 'm. Check handmatig."
} else {
    Write-Host "`nfb_cookies.json aanwezig. Vervaldatum check:"
    & "scraper\.venv\Scripts\python.exe" -c "import json,datetime;d=json.load(open('scraper/fb_cookies.json'));print(datetime.datetime.utcfromtimestamp(max(c.get('expirationDate',0) for c in d)))"
}

Write-Host "`nWindows Task Scheduler-taak registreren (geen admin nodig)..."
& "$repoPath\scraper\register_task.ps1"

Write-Host "`nKlaar. Taak 'KasKorsou-FacebookScraper' draait dagelijks om 08:00 lokale tijd (America/Curacao) - headed Chrome, dus laat de Mini PC niet in slaap gaan op dat tijdstip (Energiebeheer > 'Nooit slapen' aanzetten of alleen op stroom)."
Write-Host "Los testen zonder te wachten op de taak:"
Write-Host "  `$env:PLAYWRIGHT_BROWSERS_PATH = 'C:\pw-browsers'; scraper\.venv\Scripts\python.exe -m scraper.orchestrator --sources facebook --dry-run"
Write-Host "`nAls FB tijdens de run naar een loginpagina redirect: cookies zijn verlopen/geweigerd. Opnieuw inloggen op facebook.com in Chrome op DEZE machine, cookies exporteren (EditThisCookie-extensie) en scraper\fb_cookies.json overschrijven - daarna committen naar de repo."
