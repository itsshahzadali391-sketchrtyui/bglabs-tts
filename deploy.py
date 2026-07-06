import os
import json
import subprocess
import sys

print("=" * 50)
print("BG LABS TTS - Vercel Deployment")
print("=" * 50)
print()

# Check if vercel is available
try:
    result = subprocess.run(['npx', '--yes', 'vercel', '--version'], 
                          capture_output=True, text=True, timeout=30)
    print("Vercel CLI available")
except:
    print("Installing Vercel CLI...")
    subprocess.run(['npm', 'install', '-g', 'vercel'], check=True)

print()
print("Starting deployment...")
print()

# Deploy
try:
    result = subprocess.run(
        ['npx', '--yes', 'vercel', '--yes', '--prod'],
        capture_output=True, text=True, timeout=300
    )
    
    if result.returncode == 0:
        # Extract URL from output
        for line in result.stdout.split('\n'):
            if 'https://' in line and '.vercel.app' in line:
                url = line.strip()
                print(f"DEPLOYED: {url}")
                
                # Save URL
                with open('DEPLOYED_URL.txt', 'w') as f:
                    f.write(url)
                
                print()
                print(f"Your permanent URL: {url}")
                print(f"Health check: {url}/api/health")
                print(f"TTS API: {url}/api/tts/url")
                break
        else:
            print("Output:", result.stdout)
    else:
        print("Error:", result.stderr)
except Exception as e:
    print(f"Deployment failed: {e}")
    print()
    print("Manual steps:")
    print("1. Go to: https://vercel.com")
    print("2. Sign up/Login")
    print("3. Import Git Repository")
    print("4. Select: bglabs-tts")
    print("5. Deploy!")
