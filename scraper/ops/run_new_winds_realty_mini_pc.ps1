# KasKorsou — New Winds Realty scraper, dagelijkse run vanaf de Mini PC.
#
# WAAROM dit script bestaat: newwindsrealty.com draait op WordPress.com/WPCloud
# (Automattic-hosting), die GitHub Actions-runner-IP's hard blokkeert (elke
# request -> HTTP 429, ook na retry/backoff — bevestigd op 2 losse GH Actions
# test-runs, 11 aug 2026). Vanaf een gewoon "consumenten"-IP (zoals de Mini PC)
# werkt dezelfde code gewoon (200 OK, live geverifieerd vanuit de Cowork-
# sandbox). Dus: dit ene bronnetje draait apart, buiten daily-scrape.yml om.
#
# EENMALIGE SETUP (rechtsklik -> Run with PowerShell, of in een PowerShell-
# venster op de Mini PC als gebruiker Peter):
#
#   schtasks /Create /TN "KasKorsou-NewWindsRealty" /SC DAILY /ST 06:00 `
#     /TR "powershell.exe -NoProfile -ExecutionPolicy Bypass -File `"C:\Users\Peter\kaskorsou\scraper\ops\run_new_winds_realty_mini_pc.ps1`"" `
#     /RU Peter
#
# Dat registreert 'm in Windows Task Scheduler, dagelijks 06:00 lokale tijd,
# zelfde patroon als de bestaande "KasKorsou-FacebookScraper"-taak.
#
# Pas $RepoPath hieronder aan als de repo niet in C:\Users\Peter\kaskorsou staat.

$RepoPath = "C:\Users\Peter\kaskorsou"
$LogDir   = Join-Path $RepoPath "scraper\ops\logs"
$LogFile  = Join-Path $LogDir ("new_winds_realty_{0}.log" -f (Get-Date -Format "yyyy-MM-dd_HHmmss"))

if (-not (Test-Path $LogDir)) { New-Item -ItemType Directory -Path $LogDir | Out-Null }

Set-Location $RepoPath

# Zorg dat de repo up-to-date is vóór het draaien (andere sessies/machines
# pushen ook naar main).
git pull --ff-only 2>&1 | Tee-Object -FilePath $LogFile -Append

# Draait alleen deze ene bron — de rest loopt gewoon via GH Actions.
python -m scraper.orchestrator --sources new_winds_realty --dedup 2>&1 | Tee-Object -FilePath $LogFile -Append

Write-Output "Klaar. Log: $LogFile"
