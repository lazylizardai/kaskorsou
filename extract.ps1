$zipPath = "C:\Users\peter\Desktop\KasKorsou-web\src-files.zip"
$destPath = "C:\Users\peter\Desktop\KasKorsou-web"
$b64 = Get-Content "C:\Users\peter\Desktop\KasKorsou-web\src-b64.txt" -Raw
[System.IO.File]::WriteAllBytes($zipPath, [System.Convert]::FromBase64String($b64.Trim()))
Expand-Archive -Path $zipPath -DestinationPath $destPath -Force
Remove-Item $zipPath -Force
Remove-Item "C:\Users\peter\Desktop\KasKorsou-web\src-b64.txt" -Force
Write-Host "DONE - All source files extracted!"
