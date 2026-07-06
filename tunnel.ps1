# BG LABS TTS - Persistent Tunnel
# Ye script tunnel maintain karti hai aur URL save karti hai

$urlFile = "C:\Users\Administrator\bglabs-tts\CURRENT_URL.txt"
$logFile = "C:\Users\Administrator\bglabs-tts\tunnel.log"
$serverUrl = "http://localhost:8000"

function Write-Log($msg) {
    $ts = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
    "$ts - $msg" | Out-File -FilePath $logFile -Append
}

Write-Log "=== Starting BG LABS TTS Tunnel ==="

while ($true) {
    try {
        # Check server
        $health = Invoke-WebRequest -Uri "$serverUrl/api/health" -TimeoutSec 5 -ErrorAction Stop
        Write-Log "Server OK"
        
        # Kill old SSH
        Get-Process ssh -ErrorAction SilentlyContinue | Stop-Process -Force
        Start-Sleep -Seconds 2
        
        # Start tunnel
        Write-Log "Starting tunnel..."
        $job = Start-Job { ssh -o StrictHostKeyChecking=no -o ServerAliveInterval=60 -R 80:localhost:8000 nokey@localhost.run 2>&1 }
        Start-Sleep -Seconds 12
        
        $output = Receive-Job -Job $job
        $url = ($output | Select-String -Pattern "https://[a-z0-9]+\.lhr\.life" | Select-Object -First 1).Matches.Value
        
        if ($url) {
            Write-Log "TUNNEL ACTIVE: $url"
            $url | Out-File -FilePath $urlFile -Encoding utf8 -Force
            Write-Host "`n========================================"
            Write-Host "TUNNEL ACTIVE: $url"
            Write-Host "========================================`n"
            
            # Keep alive
            while ($job.State -eq "Running") {
                Start-Sleep -Seconds 30
                try {
                    $test = Invoke-WebRequest -Uri "$url/api/health" -TimeoutSec 10 -ErrorAction Stop
                } catch {
                    Write-Log "Tunnel dead, restarting..."
                    Stop-Job -Job $job -ErrorAction SilentlyContinue
                    Remove-Job -Job $job -Force -ErrorAction SilentlyContinue
                    break
                }
            }
        } else {
            Write-Log "Failed to get URL"
        }
        
        Stop-Job -Job $job -ErrorAction SilentlyContinue
        Remove-Job -Job $job -Force -ErrorAction SilentlyContinue
        
    } catch {
        Write-Log "Error: $($_.Exception.Message)"
    }
    
    Write-Log "Restarting in 10 seconds..."
    Start-Sleep -Seconds 10
}
