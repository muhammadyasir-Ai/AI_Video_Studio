"""Dashboard: real statistics from project files and job history only."""

import collections
import datetime
import shutil

import streamlit as st
from dotenv import dotenv_values

from core import config as C
from core.files import load_project, stage_done
from core.history import load_history
from core.jobs import active_job
from core.library import library_items

from .common import badge, empty_state, fmt_seconds, fmt_time, header


def _folder_size(path) -> int:
    if not path.exists():
        return 0
    return sum(file.stat().st_size for file in path.rglob("*") if file.is_file())


def _fmt_bytes(value: float) -> str:
    for unit in ("B", "KB", "MB", "GB"):
        if value < 1024:
            return f"{value:.1f} {unit}"
        value /= 1024
    return f"{value:.1f} TB"


def _health_checks():
    env = dotenv_values(C.ENV_FILE)
    return [
        ("Cloudflare credentials", bool(env.get("CLOUDFLARE_ACCOUNT_ID") and env.get("CLOUDFLARE_API_TOKEN"))),
        ("Piper voice model", C.MODEL_FILE.exists()),
        ("FFmpeg", bool(shutil.which("ffmpeg"))),
        ("Script ready", load_project() is not None),
    ]


def _activity_chart(history):
    today = datetime.date.today()
    days = [today - datetime.timedelta(days=offset) for offset in range(6, -1, -1)]
    counts = collections.Counter()
    for entry in history:
        started = entry.get("started_at")
        if started:
            counts[started[:10]] += 1
    data = {day.strftime("%d %b"): counts.get(day.isoformat(), 0) for day in days}
    st.bar_chart(data, height=220, color="#8B5CF6")


def render() -> None:
    header("Dashboard", "Your AI video studio at a glance.")

    job = active_job()
    history = load_history()
    items = library_items()
    completed = sum(1 for entry in history if entry.get("status") == "completed")
    failed = sum(1 for entry in history if entry.get("status") == "failed")

    cols = st.columns(4)
    cols[0].metric("Total videos", len(items))
    cols[1].metric("Completed generations", completed)
    cols[2].metric("Running now", 1 if job else 0)
    cols[3].metric("Failed generations", failed)

    left, right = st.columns([1.6, 1], gap="large")
    with left:
        with st.container(border=True):
            st.subheader("Welcome")
            st.write("Type a topic and the studio will write a script, create scene images, "
                     "record a voiceover, add subtitles, generate clips and assemble one final video.")
            st.page_link(st.session_state["_pages"]["create"], label="Create a new video",
                         icon=":material/add_circle:")

        with st.container(border=True):
            st.subheader("Recent generations")
            if not history:
                empty_state("No generations yet. Create your first video to see it here.")
            else:
                for entry in history[:5]:
                    cols = st.columns([3, 1.2, 1.6])
                    cols[0].markdown(f"**{entry.get('title', 'Untitled')}**  \n"
                                     f"<span class='muted'>{fmt_time(entry.get('started_at'))}</span>",
                                     unsafe_allow_html=True)
                    cols[1].markdown(badge(entry.get("status", "pending")), unsafe_allow_html=True)
                    cols[2].markdown(f"<span class='muted'>{fmt_seconds(entry.get('duration_seconds'))}</span>",
                                     unsafe_allow_html=True)

        with st.container(border=True):
            st.subheader("Activity, last 7 days")
            _activity_chart(history)

    with right:
        with st.container(border=True):
            st.subheader("Pipeline health")
            for name, ok in _health_checks():
                st.markdown(("🟢 " if ok else "🔴 ") + name)
            st.caption("Credential values are never shown.")

        with st.container(border=True):
            st.subheader("Storage")
            project_size = sum(_folder_size(folder) for folder in
                               (C.IMAGE_DIR, C.VOICE_DIR, C.CLIP_DIR, C.FINAL_DIR))
            free = shutil.disk_usage(C.BASE_DIR).free
            st.metric("Project files", _fmt_bytes(project_size))
            st.caption(f"Free disk space on this drive: {_fmt_bytes(free)}")

        with st.container(border=True):
            st.subheader("Current project")
            project = load_project()
            if project:
                st.write(f"**{project.get('title', 'Untitled')}**")
                done = sum(stage_done(key, project) for key in ("images", "voice", "subs", "clips", "final"))
                st.progress(done / 5, text=f"{done} of 5 build steps complete")
            else:
                empty_state("No project yet.")
