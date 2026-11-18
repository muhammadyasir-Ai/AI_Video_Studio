"""Video Generation Pipeline: live stage status from real job state and output files."""

import streamlit as st

from core import config as C
from core.files import load_project, stage_blockers, stage_done
from core.jobs import active_job, read_status, start_job, stop_job

from .common import badge, elapsed_since, empty_state, header

STAGE_LABELS = {"pending": "Pending", "running": "Running", "completed": "Completed", "failed": "Failed"}


def _tail_log(lines: int = 40) -> str:
    if not C.JOB_LOG_FILE.exists():
        return ""
    text = C.JOB_LOG_FILE.read_text(encoding="utf-8", errors="replace").splitlines()
    return "\n".join(text[-lines:])


def _stage_state(key, project, job, status):
    if job and key in job.get("stage_status", {}):
        return job["stage_status"][key]
    if status and status.get("status") == "failed" and key in status.get("stage_status", {}):
        return status["stage_status"][key]
    return "completed" if stage_done(key, project) else "pending"


@st.fragment(run_every=3)
def _pipeline_body():
    project = load_project()
    job = active_job()
    status = read_status()

    if job:
        steps = job.get("steps", [])
        finished_count = sum(1 for key in steps if job.get("stage_status", {}).get(key) == "completed")
        current = job.get("current")
        title = C.STAGE_BY_KEY[current]["title"] if current in C.STAGE_BY_KEY else "Starting"
        with st.container(border=True):
            st.subheader(f"Running: {job.get('label', 'Video generation')}")
            st.progress(finished_count / max(len(steps), 1),
                        text=f"{title} · {finished_count} of {len(steps)} steps done · elapsed {elapsed_since(job.get('started_at'))}")
            if st.button("⏹ Stop generation", type="secondary"):
                stop_job()
                st.toast("Generation stopped.", icon="⏹")
                st.rerun(scope="app")
            with st.expander("Live log", expanded=True):
                st.code(_tail_log() or "Waiting for output...", language="text")
    elif status and status.get("status") in ("failed", "cancelled"):
        if status["status"] == "failed":
            st.error(f"Last run failed. {status.get('error') or ''}")
        else:
            st.warning("Last run was stopped by you.")
        with st.expander("Last run log"):
            st.code(_tail_log(200) or "No log.", language="text")
    elif status and status.get("status") == "completed" and C.FINAL_FILE.exists():
        st.success("Last run completed. Find the video on the My Videos page.")

    remaining = [key for key in C.RUNNABLE_KEYS if key != "script" and not stage_done(key, project)]
    if st.button("▶️ Run remaining steps", disabled=bool(job) or project is None or not remaining,
                 help="Runs every step that is not complete yet, in order."):
        try:
            start_job(remaining, label="Remaining steps")
        except (ValueError, RuntimeError) as error:
            st.error(str(error))
        else:
            st.rerun(scope="app")

    for index, stage in enumerate(C.STAGES, start=1):
        key = stage["key"]
        state = _stage_state(key, project, job, status)
        blockers = stage_blockers(key, project) if state != "completed" else []
        with st.container(border=True):
            info, action = st.columns([4, 1.3])
            with info:
                st.markdown(f"**{index}. {stage['title']}**  {badge(state)}", unsafe_allow_html=True)
                st.markdown(f"<span class='muted'>{stage['desc']}</span>", unsafe_allow_html=True)
                if state == "failed" and status and status.get("error"):
                    st.error(status["error"])
                elif blockers and state == "pending":
                    st.caption("⏳ " + blockers[0])
            with action:
                if stage["script"] is None:
                    st.caption("Automatic")
                elif key == "script":
                    st.page_link(st.session_state["_pages"]["create"], label="Write script",
                                 icon=":material/edit:")
                else:
                    if st.button("Run this stage", key=f"stage_{key}",
                                 disabled=bool(job) or bool(blockers) or state == "completed",
                                 width="stretch"):
                        try:
                            start_job([key], label=stage["title"])
                        except (ValueError, RuntimeError) as error:
                            st.error(str(error))
                        else:
                            st.rerun(scope="app")


def render() -> None:
    header("Video Generation Pipeline", "Follow each stage. Progress comes from the real background job.")
    if not any(stage["script"] for stage in C.STAGES):
        empty_state("No pipeline stages configured.")
    _pipeline_body()
