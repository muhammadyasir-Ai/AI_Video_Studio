"""Library items: finished videos that exist on disk."""

import datetime

from . import config as C
from .archive import has_archived_copy_of_final
from .files import image_path, load_project, scene_numbers
from .history import load_history


def _exists(rel_path) -> bool:
    return bool(rel_path) and (C.BASE_DIR / rel_path).exists()


def library_items() -> list:
    """Completed videos recorded by the GUI, plus a legacy final video made before the GUI existed."""
    items = [
        entry for entry in load_history()
        if entry.get("status") == "completed" and _exists(entry.get("video"))
    ]

    if C.FINAL_FILE.exists() and not has_archived_copy_of_final():
        project = load_project() or {}
        numbers = scene_numbers(project)
        thumb = image_path(numbers[0]) if numbers and image_path(numbers[0]).exists() else None
        modified = datetime.datetime.fromtimestamp(C.FINAL_FILE.stat().st_mtime)
        items.append({
            "id": "legacy-final",
            "label": "Earlier run",
            "topic": None,
            "title": project.get("title") or "Latest video",
            "status": "completed",
            "started_at": None,
            "finished_at": modified.isoformat(timespec="seconds"),
            "duration_seconds": None,
            "video": C.FINAL_FILE.relative_to(C.BASE_DIR).as_posix(),
            "video_duration": None,
            "thumbnail": thumb.relative_to(C.BASE_DIR).as_posix() if thumb else None,
            "script": C.PROJECT_FILE.relative_to(C.BASE_DIR).as_posix() if C.PROJECT_FILE.exists() else None,
            "subtitles": C.SUBTITLE_FILE.relative_to(C.BASE_DIR).as_posix() if C.SUBTITLE_FILE.exists() else None,
        })

    items.sort(key=lambda item: item.get("finished_at") or "", reverse=True)
    return items
