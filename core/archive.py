"""Copies a finished video (with its script, subtitles and thumbnail) into final/archive/.

Scripts are not changed. The archive keeps each finished video even when a new run
overwrites final/final_video.mp4.
"""

import datetime
import shutil
import subprocess

from . import config as C
from .files import image_path, load_project, read_json, scene_numbers


def _rel(path):
    return path.relative_to(C.BASE_DIR).as_posix()


def probe_duration(path):
    """Video length in seconds using ffprobe (installed with FFmpeg). None if unavailable."""
    ffprobe = shutil.which("ffprobe")
    if not ffprobe or not path.exists():
        return None
    result = subprocess.run(
        [ffprobe, "-v", "error", "-show_entries", "format=duration",
         "-of", "default=noprint_wrappers=1:nokey=1", str(path)],
        capture_output=True, text=True,
    )
    try:
        return round(float(result.stdout.strip()), 2)
    except ValueError:
        timing = read_json(C.TIMING_FILE, {}) or {}
        return timing.get("total_duration")


def archive_final() -> dict:
    """Copy the current final video and its assets. Returns paths relative to the project."""
    C.ARCHIVE_DIR.mkdir(parents=True, exist_ok=True)
    stamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    base = C.ARCHIVE_DIR / f"video_{stamp}"
    counter = 1
    while base.with_suffix(".mp4").exists():
        base = C.ARCHIVE_DIR / f"video_{stamp}_{counter}"
        counter += 1

    video = base.with_suffix(".mp4")
    shutil.copy2(C.FINAL_FILE, video)

    result = {"video": _rel(video), "video_duration": probe_duration(video),
              "thumbnail": None, "script": None, "subtitles": None}

    project = load_project()
    numbers = scene_numbers(project)
    if numbers and image_path(numbers[0]).exists():
        thumb = base.with_suffix(".jpg")
        shutil.copy2(image_path(numbers[0]), thumb)
        result["thumbnail"] = _rel(thumb)
    if C.PROJECT_FILE.exists():
        script = base.with_suffix(".json")
        shutil.copy2(C.PROJECT_FILE, script)
        result["script"] = _rel(script)
    if C.SUBTITLE_FILE.exists():
        subs = base.with_suffix(".srt")
        shutil.copy2(C.SUBTITLE_FILE, subs)
        result["subtitles"] = _rel(subs)
    return result


def has_archived_copy_of_final() -> bool:
    """True if an archived video has the same size as the current final video."""
    if not C.FINAL_FILE.exists() or not C.ARCHIVE_DIR.exists():
        return False
    size = C.FINAL_FILE.stat().st_size
    return any(path.stat().st_size == size for path in C.ARCHIVE_DIR.glob("video_*.mp4"))
