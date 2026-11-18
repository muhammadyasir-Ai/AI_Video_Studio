
import os
import json
import base64
import requests
from dotenv import load_dotenv

load_dotenv()

API_TOKEN = os.getenv("CLOUDFLARE_API_TOKEN")
ACCOUNT_ID = os.getenv("CLOUDFLARE_ACCOUNT_ID")

if not API_TOKEN or not ACCOUNT_ID:
    print("Error: Credentials missing in .env")
    raise SystemExit

MODEL = "@cf/black-forest-labs/flux-1-schnell"

URL = (
    f"https://api.cloudflare.com/client/v4/accounts/"
    f"{ACCOUNT_ID}/ai/run/{MODEL}"
)

HEADERS = {
    "Authorization": f"Bearer {API_TOKEN}",
    "Content-Type": "application/json"
}


def generate_image(prompt, scene_number):

    data = {
        "prompt": prompt,
        "steps": 4
    }

    print(f"\nGenerating image for scene {scene_number}...")

    response = requests.post(
        URL,
        headers=HEADERS,
        json=data,
        timeout=180
    )

    response.raise_for_status()

    result = response.json()

    image_base64 = result.get("result", {}).get("image")

    if not image_base64:
        raise ValueError("Image data not found in API response.")

    image_bytes = base64.b64decode(image_base64)

    os.makedirs("output", exist_ok=True)

    image_path = f"output/scene_{scene_number}.jpg"

    with open(image_path, "wb") as file:
        file.write(image_bytes)

    print(f"Image saved: {image_path}")


def main():

    project_file = "projects/project_data.json"

    if not os.path.exists(project_file):
        print("Project data not found. Generate script first.")
        return

    with open(project_file, "r", encoding="utf-8") as file:
        project = json.load(file)

    scenes = project.get("scenes", [])

    if not scenes:
        print("No scenes found in project data.")
        return

    for scene in scenes:
        generate_image(
            scene["image_prompt"],
            scene["scene_number"]
        )

    print("\nAll scene images generated successfully!")


if __name__ == "__main__":
    main()
