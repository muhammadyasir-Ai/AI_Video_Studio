import os
import json
import subprocess
import sys
import wave

PROJECT_FILE = "projects/project_data.json"
MODEL_FILE = "en_US-lessac-medium.onnx"
VOICE_DIR = "voiceovers"
OUTPUT_FILE = "voiceovers/narration.wav"
TIMING_FILE = "projects/scene_timing.json"

# Silence added at the end of every scene.
# It is counted in each scene's duration and in every later start time.
SILENCE_SECONDS = 0.4


def synthesize_scene(text, output_path):
    command = [
        sys.executable, "-m", "piper",
        "-m", MODEL_FILE,
        "-f", output_path,
        "--", text
    ]

    result = subprocess.run(command)

    return result.returncode == 0 and os.path.exists(output_path)


def add_silence(path, silence_seconds):
    """Append silence to a wav file.

    Returns ((channels, sample_width, sample_rate),
             speech_frames, silence_frames).
    """
    with wave.open(path, "rb") as wav:
        channels = wav.getnchannels()
        sample_width = wav.getsampwidth()
        sample_rate = wav.getframerate()
        speech_frames = wav.getnframes()
        audio = wav.readframes(speech_frames)

    if sample_width != 2:
        raise ValueError("Expected 16-bit PCM audio from Piper.")

    silence_frames = round(silence_seconds * sample_rate)
    silence = b"\x00" * (silence_frames * channels * sample_width)

    temp_path = path + ".tmp"

    with wave.open(temp_path, "wb") as wav:
        wav.setnchannels(channels)
        wav.setsampwidth(sample_width)
        wav.setframerate(sample_rate)
        wav.writeframes(audio + silence)

    os.replace(temp_path, path)

    return (channels, sample_width, sample_rate), speech_frames, silence_frames


def main():

    if not os.path.exists(PROJECT_FILE):
        print("Project data not found.")
        return

    if not os.path.exists(MODEL_FILE):
        print("Piper voice model not found.")
        return

    with open(PROJECT_FILE, "r", encoding="utf-8") as file:
        project = json.load(file)

    scenes = project.get("scenes", [])

    if not scenes:
        print("No narration found.")
        return

    os.makedirs(VOICE_DIR, exist_ok=True)

    print("Generating offline AI voiceover (one file per scene)...")

    processed = []
    audio_format = None

    for scene in scenes:
        number = scene["scene_number"]
        text = scene.get("narration", "").strip()

        if not text:
            print(f"Narration missing for scene {number}.")
            return

        scene_path = os.path.join(VOICE_DIR, f"scene_{number}.wav")

        print(f"\nScene {number}: generating voice...")

        if not synthesize_scene(text, scene_path):
            print(f"Voiceover generation failed for scene {number}.")
            return

        scene_format, speech_frames, silence_frames = add_silence(
            scene_path, SILENCE_SECONDS
        )

        if audio_format is None:
            audio_format = scene_format
        elif scene_format != audio_format:
            print(f"Scene {number} audio format differs from earlier scenes.")
            return

        processed.append({
            "number": number,
            "path": scene_path,
            "speech_frames": speech_frames,
            "silence_frames": silence_frames
        })

    channels, sample_width, sample_rate = audio_format

    # Combine the scene files into one narration track.
    # Only done after every scene succeeded, so a failed run never
    # leaves a half-built narration.wav behind.
    with wave.open(OUTPUT_FILE, "wb") as output:
        output.setnchannels(channels)
        output.setsampwidth(sample_width)
        output.setframerate(sample_rate)

        for item in processed:
            with wave.open(item["path"], "rb") as wav:
                output.writeframes(wav.readframes(wav.getnframes()))

    # Timing: counted in frames so nothing drifts, then converted to seconds.
    timing_scenes = []
    start_frames = 0

    for item in processed:
        total_frames = item["speech_frames"] + item["silence_frames"]

        timing_scenes.append({
            "scene_number": item["number"],
            "audio_file": item["path"].replace("\\", "/"),
            "speech_duration": round(item["speech_frames"] / sample_rate, 3),
            "silence_duration": round(item["silence_frames"] / sample_rate, 3),
            "duration": round(total_frames / sample_rate, 3),
            "start": round(start_frames / sample_rate, 3),
            "end": round((start_frames + total_frames) / sample_rate, 3)
        })

        start_frames += total_frames

    timing = {
        "sample_rate": sample_rate,
        "silence_seconds": SILENCE_SECONDS,
        "total_duration": round(start_frames / sample_rate, 3),
        "scenes": timing_scenes
    }

    os.makedirs(os.path.dirname(TIMING_FILE), exist_ok=True)

    with open(TIMING_FILE, "w", encoding="utf-8") as file:
        json.dump(timing, file, indent=4, ensure_ascii=False)

    print("\nVoiceover generated successfully!")

    for scene in timing_scenes:
        print(
            f"Scene {scene['scene_number']}: "
            f"speech {scene['speech_duration']:.2f}s + "
            f"silence {scene['silence_duration']:.2f}s = "
            f"{scene['duration']:.2f}s "
            f"(start {scene['start']:.2f}s)"
        )

    print(f"Total narration: {timing['total_duration']:.2f}s")
    print(f"Scene audio saved in: {VOICE_DIR}/")
    print(f"Combined narration saved at: {OUTPUT_FILE}")
    print(f"Timing saved at: {TIMING_FILE}")


if __name__ == "__main__":
    main()
