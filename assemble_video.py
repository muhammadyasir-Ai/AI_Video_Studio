import os
import json
import math
import shutil
import subprocess
import wave
from fractions import Fraction

TIMING_FILE = "projects/scene_timing.json"
AUDIO = "voiceovers/narration.wav"
SUBTITLES = "subtitles/subtitles.srt"
OUTPUT = "final/final_video.mp4"
TEMP_OUTPUT = "final/final_video.part.mp4"
WORK_DIR = "video/synced"
SIZE = 640

# Quality used for the in-between scene files (the final encode below
# keeps the original settings).
SCENE_ENCODE = [
    "-c:v", "libx264",
    "-preset", "ultrafast",
    "-crf", "12",
    "-pix_fmt", "yuv420p"
]


def run(command, label):
    result = subprocess.run(command)

    if result.returncode != 0:
        print(f"FFmpeg failed while {label}.")
        return False

    return True


def probe(path, entry):
    """Ask ffprobe for one value, e.g. 'stream=r_frame_rate'."""
    scope = ["-select_streams", "v:0"] if entry.startswith("stream=") else []

    result = subprocess.run(
        ["ffprobe", "-v", "error", *scope,
         "-show_entries", entry,
         "-of", "default=nw=1:nk=1", path],
        capture_output=True,
        text=True
    )

    values = result.stdout.split()

    if result.returncode != 0 or not values:
        raise ValueError(f"ffprobe could not read {entry} from {path}")

    return values[0]


def exact(value):
    # Decimal text -> exact fraction, so frame maths has no float error.
    return Fraction(str(value))


def build_scene(number, source, frames, fps, fps_text):
    """Make video/synced/scene_N_synced.mp4 with exactly `frames` frames.

    The clip plays forward, then in reverse, then repeats (ping-pong),
    so it can be stretched without a visible jump back to the start.
    """
    pingpong = os.path.join(WORK_DIR, f"scene_{number}_pingpong.mp4")
    repeat_list = os.path.join(WORK_DIR, f"scene_{number}_repeat.txt")
    synced = os.path.join(WORK_DIR, f"scene_{number}_synced.mp4")

    # 1) One forward + reverse cycle, already resized to 640x640.
    #    The reverse pass leaves out both end frames (they already appear
    #    in the forward pass), so no frame is shown twice in a row.
    graph = (
        f"[0:v]fps=fps={fps_text},"
        f"scale={SIZE}:{SIZE}:force_original_aspect_ratio=decrease,"
        f"pad={SIZE}:{SIZE}:(ow-iw)/2:(oh-ih)/2,"
        "setsar=1,split[fwd][rev_in];"
        "[rev_in]trim=start_frame=1,setpts=PTS-STARTPTS,"
        "reverse,trim=start_frame=1,setpts=PTS-STARTPTS[rev];"
        "[fwd][rev]concat=n=2:v=1:a=0[out]"
    )

    ok = run(
        ["ffmpeg", "-y", "-hide_banner", "-loglevel", "error",
         "-i", source,
         "-filter_complex", graph,
         "-map", "[out]", "-an",
         *SCENE_ENCODE, pingpong],
        f"building the ping-pong cycle for scene {number}"
    )

    if not ok:
        return None

    # 2) Repeat the cycle enough times and cut at the exact frame count.
    cycle_seconds = float(probe(pingpong, "format=duration"))
    needed_seconds = float(frames / fps)
    repeats = math.ceil(needed_seconds / cycle_seconds) + 1

    with open(repeat_list, "w", encoding="utf-8") as file:
        for _ in range(repeats):
            file.write(f"file 'scene_{number}_pingpong.mp4'\n")

    ok = run(
        ["ffmpeg", "-y", "-hide_banner", "-loglevel", "error",
         "-f", "concat", "-safe", "0",
         "-i", repeat_list,
         "-frames:v", str(frames), "-an",
         *SCENE_ENCODE, synced],
        f"matching scene {number} to its narration length"
    )

    return synced if ok else None


def main():
    for tool in ("ffmpeg", "ffprobe"):
        if shutil.which(tool) is None:
            print(f"{tool} not found. It is installed together with FFmpeg.")
            return

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

    sources = {}

    for scene in scenes:
        number = scene["scene_number"]
        sources[number] = f"video/scene_{number}.mp4"

    for path in list(sources.values()) + [AUDIO, SUBTITLES]:
        if not os.path.exists(path):
            print(f"File not found: {path}")
            return

    total = timing["total_duration"]

    # Make sure narration.wav belongs to this timing file.
    with wave.open(AUDIO, "rb") as wav:
        audio_seconds = wav.getnframes() / wav.getframerate()

    if abs(audio_seconds - total) > 0.05:
        print(
            f"narration.wav is {audio_seconds:.2f}s but the timing file "
            f"says {total:.2f}s. Run generate_voice.py again."
        )
        return

    os.makedirs("final", exist_ok=True)
    os.makedirs(WORK_DIR, exist_ok=True)

    try:
        fps = Fraction(probe(sources[scenes[0]["scene_number"]],
                             "stream=r_frame_rate"))
    except (ValueError, ZeroDivisionError) as error:
        print(error)
        return

    fps_text = f"{fps.numerator}/{fps.denominator}"

    print(f"Clip frame rate: {float(fps):g} fps")
    print(f"Narration length: {total:.3f}s\n")

    synced_files = []

    for scene in scenes:
        number = scene["scene_number"]

        # Frame counts come from the scene's start/end, so rounding
        # never builds up from one scene to the next.
        start_frame = round(exact(scene["start"]) * fps)
        end_frame = round(exact(scene["end"]) * fps)
        frames = end_frame - start_frame

        print(
            f"Scene {number}: {scene['duration']:.2f}s "
            f"-> {frames} frames (ping-pong)"
        )

        synced = build_scene(number, sources[number], frames, fps, fps_text)

        if synced is None:
            return

        synced_files.append(synced)

    concat_list = os.path.join(WORK_DIR, "final_concat.txt")

    with open(concat_list, "w", encoding="utf-8") as file:
        for synced in synced_files:
            file.write(f"file '{os.path.basename(synced)}'\n")

    print("\nJoining scenes, adding narration and subtitles...")

    command = [
        "ffmpeg", "-y", "-hide_banner", "-loglevel", "warning", "-stats",
        "-f", "concat", "-safe", "0",
        "-i", concat_list,
        "-i", AUDIO,
        "-vf",
        f"subtitles={SUBTITLES}:"
        "force_style='FontName=Arial,FontSize=18,"
        "PrimaryColour=&H00FFFFFF,OutlineColour=&H00000000,"
        "BorderStyle=1,Outline=2,Alignment=2,MarginV=35'",
        "-map", "0:v:0",
        "-map", "1:a:0",
        "-c:v", "libx264",
        "-preset", "ultrafast",
        "-pix_fmt", "yuv420p",
        "-c:a", "aac",
        "-b:a", "128k",
        "-t", f"{total:.3f}",
        "-movflags", "+faststart",
        TEMP_OUTPUT
    ]

    if not run(command, "creating the final video"):
        print("Your previous final video was not changed.")
        return

    # Only replace the old final video once the new one is complete.
    try:
        os.replace(TEMP_OUTPUT, OUTPUT)
    except OSError as error:
        print(f"Could not replace {OUTPUT}: {error}")
        print(f"The new video is saved at: {TEMP_OUTPUT}")
        print("Close the old video in any player, then run this again.")
        return

    print("\nFinal video created successfully!")
    print(f"Saved at: {OUTPUT}")

    try:
        final_seconds = float(probe(OUTPUT, "format=duration"))
        print(
            f"Video length: {final_seconds:.3f}s "
            f"(narration: {total:.3f}s)"
        )
    except ValueError:
        pass


if __name__ == "__main__":
    main()
