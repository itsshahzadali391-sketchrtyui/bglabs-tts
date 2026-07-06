# Get Current TTS Server URL
$urlFile = "C:\Users\Administrator\bglabs-tts\CURRENT_URL.txt"
if (Test-Path $urlFile) {
    $url = Get-Content $urlFile -Raw
    Write-Host ""
    Write-Host "========================================"
    Write-Host "BG LABS TTS SERVER URL"
    Write-Host "========================================"
    Write-Host "URL: $url"
    Write-Host ""
    Write-Host "Health Check: $url/api/health"
    Write-Host "Web UI: $url/"
    Write-Host "API: $url/api/tts/url"
    Write-Host "========================================"
} else {
    Write-Host "No URL found. Start tunnel first!"
}
