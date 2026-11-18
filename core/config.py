"""Paths, pipeline stages and constants. Nothing here reads secret values."""

import sys
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
PYTHON = sys.executable

PROJECT_FILE = BASE_DIR / "projects" / "project_data.json"
TIMING_FILE = BASE_DIR / "projects" / "scene_timing.json"
JOB_STATUS_FILE = BASE_DIR / "projects" / "job_status.json"
JOB_LOG_FILE = BASE_DIR / "projects" / "job_log.txt"
HISTORY_FILE = BASE_DIR / "projects" / "history.json"
ENV_FILE = BASE_DIR / ".env"

MODEL_FILE = BASE_DIR / "en_US-lessac-medium.onnx"
IMAGE_DIR = BASE_DIR / "output"
VOICE_DIR = BASE_DIR / "voiceovers"
NARRATION_FILE = VOICE_DIR / "narration.wav"
SUBTITLE_FILE = BASE_DIR / "subtitles" / "subtitles.srt"
CLIP_DIR = BASE_DIR / "video"
FINAL_DIR = BASE_DIR / "final"
FINAL_FILE = FINAL_DIR / "final_video.mp4"
ARCHIVE_DIR = FINAL_DIR / "archive"

# Stages in the order the pipeline must run them.
# "script" is the only stage that needs the topic; "scene" is derived from the script output.
STAGES = [
    {"key": "script", "title": "Script Generation", "script": "generate_script.py",
     "desc": "AI writes the title, scenes, narration and visual prompts."},
    {"key": "scene", "title": "Scene Processing", "script": None,
     "desc": "Checks that the script has valid scenes. Derived from the script step."},
    {"key": "images", "title": "Image Generation", "script": "generate_image.py",
     "desc": "One image per scene (Flux model on Cloudflare Workers AI)."},
    {"key": "voice", "title": "Voice Generation", "script": "generate_voice.py",
     "desc": "Offline narration per scene with Piper TTS, plus timing data."},
    {"key": "subs", "title": "Subtitle Generation", "script": "generate_subtitles.py",
     "desc": "Transcribes the narration with Whisper and writes an SRT file."},
    {"key": "clips", "title": "Video Clip Generation", "script": "generate_video.py",
     "desc": "Animates each image into a short clip with Wan 2.2. Slow step."},
    {"key": "final", "title": "Final Video Assembly", "script": "assemble_video.py",
     "desc": "Joins clips, narration and subtitles into one MP4 with FFmpeg."},
]
STAGE_BY_KEY = {stage["key"]: stage for stage in STAGES}
RUNNABLE_KEYS = [stage["key"] for stage in STAGES if stage["script"]]
