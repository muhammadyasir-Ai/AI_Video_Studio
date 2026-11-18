"""Persistent generation history. Only records real runs started from this GUI."""

import datetime

from . import config as C
from .files import load_project, read_json, write_json


def now_iso() -> str:
    return datetime.datetime.now().isoformat(timespec="seconds")


def parse_time(value):
    try:
        return datetime.datetime.fromisoformat(value) if value else None
    except (TypeError, ValueError):
        return None


def seconds_between(start, end):
    start_dt, end_dt = parse_time(start), parse_time(end)
    if not start_dt or not end_dt:
        return None
    return max(0, round((end_dt - start_dt).total_seconds()))


def load_history() -> list:
    data = read_json(C.HISTORY_FILE, [])
    return data if isinstance(data, list) else []


def record_job(status: dict) -> None:
    """Store a finished, failed or cancelled job. Replaces an entry with the same id."""
    project = load_project() or {}
    entry = {
        "id": status.get("job_id"),
        "label": status.get("label", "Video generation"),
        "topic": status.get("topic"),
        "title": project.get("title") or status.get("topic") or "Untitled video",
        "status": status.get("status"),
        "started_at": status.get("started_at"),
        "finished_at": status.get("finished_at"),
        "duration_seconds": seconds_between(status.get("started_at"), status.get("finished_at")),
        "steps": status.get("steps", []),
        "failed_stage": status.get("current") if status.get("status") == "failed" else None,
        "error": status.get("error"),
        "video": status.get("video"),
        "video_duration": status.get("video_duration"),
        "thumbnail": status.get("thumbnail"),
        "script": status.get("script"),
        "subtitles": status.get("subtitles"),
    }
    items = [item for item in load_history() if item.get("id") != entry["id"]]
    items.insert(0, entry)
    write_json(C.HISTORY_FILE, items)


def clear_history() -> None:
    """Remove the history index only. Video files are kept."""
    C.HISTORY_FILE.unlink(missing_ok=True)
