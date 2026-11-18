"""Background pipeline runner. Started by core/jobs.py, not by the GUI directly.

Reads a JSON payload from stdin, runs each pipeline script in order with the
same arguments you would use in the terminal, and records progress in
projects/job_status.json. Output goes to projects/job_log.txt.
"""

import json
import os
import subprocess
import sys
import traceback
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

from core import config as C  # noqa: E402
from core.archive import archive_final  # noqa: E402
from core.files import read_json, write_json  # noqa: E402
from core.history import now_iso, record_job  # noqa: E402


def save(job, **changes):
    job.update(changes)
    write_json(C.JOB_STATUS_FILE, job)


def set_stage(status, key, state):
    stages = dict(status.get("stage_status", {}))
    stages[key] = state
    if key == "script":
        stages["scene"] = state if state != "completed" else "completed"
    save(status, stage_status=stages)


def run_script(stage, topic, log):
    env = {**os.environ, "PYTHONUNBUFFERED": "1", "PYTHONIOENCODING": "utf-8"}
    process = subprocess.Popen(
        [C.PYTHON, "-u", str(C.BASE_DIR / stage["script"])],
        cwd=C.BASE_DIR,
        stdin=subprocess.PIPE if topic is not None else subprocess.DEVNULL,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        encoding="utf-8",
        errors="replace",
        bufsize=1,
        env=env,
    )
    if topic is not None:
        process.stdin.write(topic + "\n")  # answers the script's input() prompt
        process.stdin.close()
    for line in process.stdout:
        log.write(line)
        log.flush()
    return process.wait()


def main() -> int:
    payload = json.loads(sys.stdin.buffer.read().decode("utf-8"))
    status = read_json(C.JOB_STATUS_FILE, {}) or {}
    status.update(runner_pid=os.getpid(), status="running")
    write_json(C.JOB_STATUS_FILE, status)

    steps = payload["steps"]
    topic = payload.get("topic")

    with open(C.JOB_LOG_FILE, "a", encoding="utf-8") as log:
        try:
            for key in steps:
                stage = C.STAGE_BY_KEY[key]
                save(status, current=key)
                set_stage(status, key, "running")
                log.write(f"\n=== {stage['title']} ({stage['script']}) ===\n")
                log.flush()

                code = run_script(stage, topic if key == "script" else None, log)
                if code != 0:
                    set_stage(status, key, "failed")
                    save(status, status="failed", finished_at=now_iso(),
                         error=f"{stage['title']} failed (exit code {code}). Check the log.")
                    record_job(status)
                    return 1
                set_stage(status, key, "completed")

            if "final" in steps and C.FINAL_FILE.exists():
                info = archive_final()
                save(status, **info)

            save(status, status="completed", finished_at=now_iso(), current=None, error=None)
            record_job(status)
            log.write("\nAll steps completed.\n")
            return 0
        except Exception as exc:  # keep the GUI informed about any unexpected failure
            log.write("\n" + traceback.format_exc())
            save(status, status="failed", finished_at=now_iso(),
                 error=f"Unexpected error: {exc}")
            record_job(status)
            return 1


if __name__ == "__main__":
    sys.exit(main())
