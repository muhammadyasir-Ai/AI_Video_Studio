import os
import requests
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Get credentials
API_TOKEN = os.getenv("CLOUDFLARE_API_TOKEN")
ACCOUNT_ID = os.getenv("CLOUDFLARE_ACCOUNT_ID")

# Check credentials
if not API_TOKEN or not ACCOUNT_ID:
    print("Error: API Token or Account ID missing in .env")
    exit()

# Cloudflare API URL
url = f"https://api.cloudflare.com/client/v4/accounts/{ACCOUNT_ID}/ai/run/@cf/black-forest-labs/flux-1-schnell"

# Request headers
headers = {
    "Authorization": f"Bearer {API_TOKEN}",
    "Content-Type": "application/json"
}

# Test prompt
data = {
    "prompt": "A beautiful cinematic landscape with mountains at sunset, realistic photography"
}

# Send request
print("Connecting to Cloudflare Workers AI...")

response = requests.post(url, headers=headers, json=data)

if response.status_code == 200:
    print("Cloudflare API connection successful!")
    print("Image generation API is responding.")
else:
    print("API Error:", response.status_code)
    print(response.text)