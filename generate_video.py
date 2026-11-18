
import os
import json
import shutil
from gradio_client import Client, handle_file

PROJECT_FILE = "projects/project_data.json"
IMAGE_DIR = "output"
OUTPUT_DIR = "video"

NEGATIVE_PROMPT = (
    "static image, blurry, distorted, low quality, "
    "flickering, unnatural movement"
)


def main():
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    if not os.path.exists(PROJECT_FILE):
        print("Project data not found.")
        return

    with open(PROJECT_FILE, "r", encoding="utf-8") as file:
        project = json.load(file)

    scenes = project.get("scenes", [])

    if not scenes:
        print("No scenes found.")
        return

    print("Connecting to Wan 2.2...")

    client = Client("zerogpu-aoti/wan2-2-fp8da-aoti-faster")

    for scene in scenes:
        number = scene["scene_number"]

        image_file = os.path.join(
            IMAGE_DIR, f"scene_{number}.jpg"
        )

        output_path = os.path.join(
            OUTPUT_DIR, f"scene_{number}.mp4"
        )

        prompt = scene.get("motion_prompt", "")

        if not os.path.exists(image_file):
            print(f"Image not found: {image_file}")
            return

        if not prompt:
            print(f"Motion prompt missing for scene {number}")
            return

        # Skip already generated scenes
        if os.path.exists(output_path):
            print(f"Scene {number} already exists. Skipping...")
            continue

        print(f"\nGenerating video for scene {number}...")

        try:
            result = client.predict(
                input_image=handle_file(image_file),
                prompt=prompt,
                steps=6,
                negative_prompt=NEGATIVE_PROMPT,
                duration_seconds=3.5,
                guidance_scale=1,
                guidance_scale_2=1,
                seed=42,
                randomize_seed=True,
                api_name="/generate_video"
            )

            generated_video = result[0]

            if not generated_video:
                print(f"Scene {number} generation failed.")
                return

            shutil.copy2(generated_video, output_path)

            print(f"Scene {number} saved: {output_path}")

        except Exception as error:
            print(f"Scene {number} error: {error}")
            print("You can run the script again to resume.")
            return

    print("\nAll scene videos generated successfully!")


if __name__ == "__main__":
    main()
