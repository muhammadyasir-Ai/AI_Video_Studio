
import os
import json
import requests
from dotenv import load_dotenv

load_dotenv()

API_TOKEN = os.getenv("CLOUDFLARE_API_TOKEN")
ACCOUNT_ID = os.getenv("CLOUDFLARE_ACCOUNT_ID")

MODEL = "@cf/openai/gpt-oss-20b"

URL = (
    f"https://api.cloudflare.com/client/v4/accounts/"
    f"{ACCOUNT_ID}/ai/run/{MODEL}"
)

HEADERS = {
    "Authorization": f"Bearer {API_TOKEN}",
    "Content-Type": "application/json"
}


def generate_script(topic):

    prompt = f"""
Create a short, engaging English YouTube video about: {topic}

Create exactly 4 scenes.

Return ONLY valid JSON. Do not use Markdown or code fences.

Use this exact structure:

{{
    "title": "Video title",
    "description": "Short YouTube description",
    "scenes": [
        {{
            "scene_number": 1,
            "narration": "English voiceover for this scene",
            "image_prompt": "Detailed cinematic image generation prompt",
            "motion_prompt": "Detailed cinematic video motion prompt"
        }}
    ]
}}

Rules:
- Exactly 4 scenes.
- Each scene narration should contain 2 short sentences.
- Total narration should be approximately 40 to 60 seconds.
- Write natural, engaging English.
- Image prompts must describe visual details.
- Motion prompts must describe realistic camera and environmental movement.
- Keep all scenes visually consistent.
"""

    data = {
        "messages": [
            {
                "role": "user",
                "content": prompt
            }
        ],
        "max_tokens": 2500
    }

    print("\nGenerating your video script...")

    response = requests.post(
        URL,
        headers=HEADERS,
        json=data,
        timeout=180
    )

    response.raise_for_status()

    result = response.json()

    content = result["result"]["choices"][0]["message"]["content"]

    # Extract JSON if the model adds extra text
    start = content.find("{")
    end = content.rfind("}") + 1

    if start == -1 or end == 0:
        raise ValueError("AI did not return valid JSON.")

    project = json.loads(content[start:end])

    if len(project.get("scenes", [])) != 4:
        raise ValueError("AI did not generate exactly 4 scenes.")

    return project


def main():

    if not API_TOKEN or not ACCOUNT_ID:
        print("Cloudflare credentials missing in .env")
        return

    topic = input("Enter your YouTube video topic: ").strip()

    if not topic:
        print("Please enter a topic.")
        return

    try:
        project = generate_script(topic)

        os.makedirs("projects", exist_ok=True)

        output_file = "projects/project_data.json"

        with open(output_file, "w", encoding="utf-8") as file:
            json.dump(project, file, indent=4, ensure_ascii=False)

        print("\nScript generated successfully!")
        print("Title:", project["title"])
        print("Scenes:", len(project["scenes"]))
        print("Saved at:", output_file)

    except Exception as error:
        print("\nScript generation failed:")
        print(error)


if __name__ == "__main__":
    main()
