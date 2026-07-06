import os
import json
import requests
import sys

print("=" * 50)
print("BG LABS TTS - Direct Vercel Deployment")
print("=" * 50)
print()

# Vercel API token (user needs to provide)
token = input("Enter your Vercel token (get from https://vercel.com/account/tokens): ").strip()

if not token:
    print("No token provided. Getting token...")
    print()
    print("Steps to get token:")
    print("1. Go to: https://vercel.com/account/tokens")
    print("2. Click 'Create Token'")
    print("3. Copy the token")
    print("4. Paste it here")
    sys.exit(1)

headers = {
    "Authorization": f"Bearer {token}",
    "Content-Type": "application/json"
}

# Read files
files = {}
for fname in ["main.py", "requirements.txt", "vercel.json"]:
    if os.path.exists(fname):
        with open(fname, "r") as f:
            files[fname] = f.read()

print("Creating deployment...")

# Create deployment
deploy_data = {
    "name": "bglabs-tts",
    "files": [
        {"file": fname, "data": data}
        for fname, data in files.items()
    ],
    "projectSettings": {
        "framework": None,
        "buildCommand": "pip install -r requirements.txt",
        "outputDirectory": "."
    },
    "target": "production"
}

resp = requests.post(
    "https://api.vercel.com/v13/deployments",
    headers=headers,
    json=deploy_data,
    timeout=60
)

if resp.status_code in [200, 201]:
    result = resp.json()
    url = f"https://{result.get('alias', [{}])[0].get('domain', result.get('url', 'unknown'))}"
    deploy_url = result.get("url", "unknown")
    
    print()
    print("=" * 50)
    print("DEPLOYED SUCCESSFULLY!")
    print("=" * 50)
    print()
    print(f"URL: https://{deploy_url}")
    print()
    print(f"Health: https://{deploy_url}/api/health")
    print(f"TTS API: https://{deploy_url}/api/tts/url")
    print()
    
    # Save URL
    with open("DEPLOYED_URL.txt", "w") as f:
        f.write(f"https://{deploy_url}")
    
    print("URL saved to DEPLOYED_URL.txt")
else:
    print(f"Error {resp.status_code}: {resp.text}")
