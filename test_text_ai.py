
import os
import requests
from dotenv import load_dotenv

load_dotenv()

API_TOKEN = os.getenv("CLOUDFLARE_API_TOKEN")
ACCOUNT_ID = os.getenv("CLOUDFLARE_ACCOUNT_ID")

if not API_TOKEN or not ACCOUNT_ID:
    print("Error: Cloudflare credentials missing in .env")
    raise SystemExit

MODEL = "@cf/openai/gpt-oss-20b"

url = (
    f"https://api.cloudflare.com/client/v4/accounts/"
    f"{ACCOUNT_ID}/ai/run/{MODEL}"
)

headers = {
    "Authorization": f"Bearer {API_TOKEN}",
    "Content-Type": "application/json"
}

data = {
    "messages": [
        {
            "role": "user",
            "content": "Write one short sentence about nature."
        }
    ],
    "max_tokens": 100
}

print("Connecting to Cloudflare Text AI...")

try:
    response = requests.post(
        url,
        headers=headers,
        json=data,
        timeout=120
    )

    response.raise_for_status()
    result = response.json()

    print("Text AI connection successful!")

    ai_result = result.get("result", {})

    print("\nAI Response:")

    if isinstance(ai_result, dict):
        print(ai_result.get("response", ai_result))
    else:
        print(ai_result)

except requests.exceptions.RequestException as error:
    print("API request failed:", error)

    if error.response is not None:
        print(error.response.text)

except ValueError:
    print("Invalid JSON response:")
    print(response.text)
