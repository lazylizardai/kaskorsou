# Wrapper voor de Windows Task Scheduler-taak "KasKorsou-FacebookScraper".
# PLAYWRIGHT_BROWSERS_PATH staat hier expliciet in plaats van te vertrouwen op de
# user-omgevingsvariabele, omdat Task Scheduler die niet altijd meeneemt.
$env:PLAYWRIGHT_BROWSERS_PATH = "C:\pw-browsers"
Set-Location "C:\Users\Peter\KasKorsou"
& "scraper\.venv\Scripts\python.exe" -m scraper.orchestrator --sources facebook --dedup
