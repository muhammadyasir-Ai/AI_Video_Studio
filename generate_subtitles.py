import os
import json
from faster_whisper import WhisperModel

TIMING_FILE = "projects/scene_timing.json"
OUTPUT_FILE = "subtitles/subtitles.srt"


def timestamp(seconds):
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    remaining_seconds = seconds % 60
    milliseconds = int((remaining_seconds % 1) * 1000)

    return (
        f"{hours:02}:{minutes:02}:"
        f"{int(remaining_seconds):02},{milliseconds:03}"
    )


def main():
    os.makedirs("subtitles", exist_ok=True)

    if not os.path.exists(TIMING_FILE):
        print(f"Timing file not found: {TIMING_FILE}")
        print("Run generate_voice.py first.")
        return

    with open(TIMING_FILE, "r", encoding="utf-8") as file:
        timing = json.load(file)

    scenes = timing.get("scenes", [])

    if not scenes:
        print("No scenes found in timing file.")
        return

    for scene in scenes:
        if not os.path.exists(scene["audio_file"]):
            print(f"Audio file not found: {scene['audio_file']}")
            return

    print("Loading Whisper model...")

    model = WhisperModel(
        "base",
        device="cpu",
        compute_type="int8"
    )

    captions = []

    for scene in scenes:
        number = scene["scene_number"]
        offset = scene["start"]
        scene_end = scene["end"]

        print(f"\nScene {number}: generating subtitles...")

        segments, info = model.transcribe(
            scene["audio_file"],
            beam_size=5
        )

        scene_captions = 0

        for segment in segments:
            text = segment.text.strip()

            if not text:
                continue

            # Shift to the scene's position in the full video.
            # The end is capped so a caption never runs into the next scene.
            start = offset + segment.start
            end = min(offset + segment.end, scene_end)

            captions.append((start, end, text))
            scene_captions += 1

        print(
            f"Scene {number}: {scene_captions} captions "
            f"(scene runs {scene['start']:.2f}s - {scene_end:.2f}s)"
        )

    # Written only after every scene succeeded, so a failed run
    # never leaves a half-built subtitles file behind.
    with open(OUTPUT_FILE, "w", encoding="utf-8") as file:
        for index, (start, end, text) in enumerate(captions, start=1):
            file.write(f"{index}\n")
            file.write(
                f"{timestamp(start)} --> "
                f"{timestamp(end)}\n"
            )
            file.write(f"{text}\n\n")

    print(f"\nSubtitles generated successfully! ({len(captions)} captions)")
    print(f"Saved at: {OUTPUT_FILE}")


if __name__ == "__main__":
    main()
