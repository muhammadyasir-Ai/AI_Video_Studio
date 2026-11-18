"""Background job control.

The pipeline runs in a detached process (core/runner.py), so a page refresh or a
Streamlit rerun never starts a second job or stops the first one. Progress is
read from projects/job_status.json.
"""

import datetime
import json
import os
import signal
import subprocess

from . import config as C
from .archive import archive_final, has_archived_copy_of_final
from .files import clear_generated_outputs, read_json, write_json
from .history import now_iso, parse_time, record_job

DETACHED_PROCESS = 0x00000008
CREATE_NEW_PROCESS_GROUP = 0x00000200
START_GRACE_SECONDS = 30
TOPIC_MIN, TOPIC_MAX = 5, 200


def read_status():
    return read_json(C.JOB_STATUS_FILE)


def _pid_alive(pid) -> bool:
    if not pid:
        return False
    if os.name == "nt":
        output = subprocess.run(["tasklist", "/FI", f"PID eq {pid}", "/NH"],
                                capture_output=True, text=True).stdout
        return f" {pid} " in output
    try:
        os.kill(pid, 0)  # on Linux/macOS signal 0 only checks that the process exists
    except ProcessLookupError:
        return False
    except PermissionError:
        return True
    return True


def _age_seconds(value) -> float:
    started = parse_time(value)
    if not started:
        return float("inf")
    return (datetime.datetime.now() - started).total_seconds()


def active_job():
    """Return the running job, or None. Marks a job as failed if its runner has disappeared."""
    status = read_status()
    if not status or status.get("status") != "running":
        return None
    pid = status.get("runner_pid")
    if pid is None and _age_seconds(status.get("started_at")) < START_GRACE_SECONDS:
        return status
    if pid is not None and _pid_alive(pid):
        return status
    status.update(status="failed", finished_at=now_iso(),
                  error="The background job stopped unexpectedly. Check the log and try again.")
    write_json(C.JOB_STATUS_FILE, status)
    record_job(status)
    return None


def _archive_unsaved_final():
    """Keep a copy of the current final video before a new run overwrites it."""
    if C.FINAL_FILE.exists() and not has_archived_copy_of_final():
        archive_final()


def validate_topic(topic: str) -> str:
    topic = (topic or "").strip()
    if not TOPIC_MIN <= len(topic) <= TOPIC_MAX:
        raise ValueError(f"Topic must be between {TOPIC_MIN} and {TOPIC_MAX} characters.")
    return topic


def start_job(step_keys, topic=None, label="Video generation", fresh=False):
    """Start a background job for the given stage keys.

    fresh=True clears old generated files first (used for a brand-new video).
    """
    if active_job():
        raise RuntimeError("Another job is already running. Wait for it to finish or stop it first.")
    unknown = [key for key in step_keys if key not in C.RUNNABLE_KEYS]
    if unknown:
        raise ValueError(f"Unknown stage: {unknown}")
    if topic is not None:
        topic = validate_topic(topic)

    if fresh:
        _archive_unsaved_final()
        clear_generated_outputs(keep_archive=True)

    job_id = datetime.datetime.now().strftime("%Y%m%d%H%M%S%f")
    status = {
        "job_id": job_id,
        "label": label,
        "topic": topic,
        "steps": list(step_keys),
        "status": "running",
        "started_at": now_iso(),
        "finished_at": None,
        "current": None,
        "error": None,
        "runner_pid": None,
        "stage_status": {key: "pending" for key in step_keys},
    }
    write_json(C.JOB_STATUS_FILE, status)
    C.JOB_LOG_FILE.write_text("", encoding="utf-8")

    options = {}
    if os.name == "nt":
        options["creationflags"] = CREATE_NEW_PROCESS_GROUP | DETACHED_PROCESS
    else:
        options["start_new_session"] = True

    payload = json.dumps({"job_id": job_id, "topic": topic, "steps": list(step_keys)})
    process = subprocess.Popen(
        [C.PYTHON, "-u", str(C.BASE_DIR / "core" / "runner.py")],
        cwd=C.BASE_DIR,
        stdin=subprocess.PIPE,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        **options,
    )
    process.stdin.write(payload.encode("utf-8"))
    process.stdin.close()

    status = read_status() or status
    status["runner_pid"] = process.pid
    write_json(C.JOB_STATUS_FILE, status)
    return status


def stop_job() -> bool:
    status = active_job()
    if not status:
        return False
    pid = status.get("runner_pid")
    if pid:
        if os.name == "nt":
            subprocess.run(["taskkill", "/PID", str(pid), "/T", "/F"], capture_output=True)
        else:
            try:
                os.killpg(os.getpgid(pid), signal.SIGTERM)
            except ProcessLookupError:
                pass
    status.update(status="cancelled", finished_at=now_iso(), error=None)
    write_json(C.JOB_STATUS_FILE, status)
    record_job(status)
    return True
