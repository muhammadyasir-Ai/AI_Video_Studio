"""Safe JSON helpers and file-based stage checks."""

import json
import os
import time
from pathlib import Path

from . import config as C


def read_json(path: Path, default=None):
    """Read JSON, retrying briefly because the background runner may be writing it."""
    for _ in range(3):
        try:
            return json.loads(Path(path).read_text(encoding="utf-8"))
        except FileNotFoundError:
            return default
        except json.JSONDecodeError:
            time.sleep(0.1)
        except OSError:
            time.sleep(0.1)
    return default


def write_json(path: Path, data) -> None:
    """Write JSON atomically so readers never see a half-written file."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_suffix(path.suffix + ".tmp")
    temp.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    # On Windows, os.replace fails while another process has the target open (for example
    # the GUI reading job_status.json). Retry for a few seconds instead of failing the job.
    for attempt in range(40):
        try:
            os.replace(temp, path)
            return
        except PermissionError:
            if attempt == 39:
                raise
            time.sleep(0.1)


def load_project():
    project = read_json(C.PROJECT_FILE)
    return project if isinstance(project, dict) else None


def scene_numbers(project):
    if not project:
        return []
    return [scene["scene_number"] for scene in project.get("scenes", []) if "scene_number" in scene]


def image_path(number):
    return C.IMAGE_DIR / f"scene_{number}.jpg"


def clip_path(number):
    return C.CLIP_DIR / f"scene_{number}.mp4"


def all_exist(paths):
    return bool(paths) and all(path.exists() for path in paths)


def stage_done(key, project):
    numbers = scene_numbers(project)
    if key == "script":
        return project is not None
    if key == "scene":
        return bool(numbers)
    if key == "images":
        return all_exist([image_path(n) for n in numbers])
    if key == "voice":
        return C.NARRATION_FILE.exists() and C.TIMING_FILE.exists()
    if key == "subs":
        return C.SUBTITLE_FILE.exists()
    if key == "clips":
        return all_exist([clip_path(n) for n in numbers])
    if key == "final":
        return C.FINAL_FILE.exists()
    return False


def stage_blockers(key, project):
    """Reasons a stage cannot run yet. An empty list means it can run."""
    reasons = []
    numbers = scene_numbers(project)
    if key != "script" and project is None:
        reasons.append("Generate the script first.")
    if key == "voice" and not C.MODEL_FILE.exists():
        reasons.append("Piper model file (en_US-lessac-medium.onnx) is missing from the project folder.")
    if key == "subs" and not C.NARRATION_FILE.exists():
        reasons.append("Generate the voiceover first.")
    if key == "clips" and not all_exist([image_path(n) for n in numbers]):
        reasons.append("Generate all scene images first.")
    if key == "final":
        if not C.NARRATION_FILE.exists():
            reasons.append("Voiceover is not generated yet.")
        if not C.SUBTITLE_FILE.exists():
            reasons.append("Subtitles are not generated yet.")
        if not all_exist([clip_path(n) for n in numbers]):
            reasons.append("Scene videos are not generated yet.")
    return reasons


def clear_generated_outputs(keep_archive: bool = True) -> None:
    """Delete generated pipeline files. Scripts, the model and .env are never touched."""
    import shutil

    for folder in (C.IMAGE_DIR, C.VOICE_DIR, C.CLIP_DIR):
        shutil.rmtree(folder, ignore_errors=True)
    for file in (C.SUBTITLE_FILE, C.FINAL_FILE, C.TIMING_FILE):
        file.unlink(missing_ok=True)
    if not keep_archive:
        shutil.rmtree(C.ARCHIVE_DIR, ignore_errors=True)
