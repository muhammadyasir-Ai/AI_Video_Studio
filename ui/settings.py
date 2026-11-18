"""Settings: read-only configuration, plus safe maintenance actions.

Credentials are only checked for presence, never displayed. .env is never written.
"""

import streamlit as st
from dotenv import dotenv_values

from core import config as C
from core.files import clear_generated_outputs
from core.history import clear_history
from core.jobs import active_job

from .common import header


def render() -> None:
    header("Settings", "Configuration and maintenance. Models and endpoints are set in the pipeline scripts.")

    env = dotenv_values(C.ENV_FILE)
    with st.container(border=True):
        st.subheader("Credentials")
        st.write("Cloudflare account ID: " + ("✅ configured" if env.get("CLOUDFLARE_ACCOUNT_ID") else "❌ missing"))
        st.write("Cloudflare API token: " + ("✅ configured" if env.get("CLOUDFLARE_API_TOKEN") else "❌ missing"))
        st.caption("Values come from .env and are never shown here. Edit .env by hand if needed.")

    with st.container(border=True):
        st.subheader("AI models and services (read only)")
        st.table({
            "Stage": ["Script", "Images", "Voiceover", "Subtitles", "Video clips", "Final assembly"],
            "Model or service": [
                "@cf/openai/gpt-oss-20b (Cloudflare Workers AI)",
                "@cf/black-forest-labs/flux-1-schnell (Cloudflare Workers AI)",
                "Piper en_US-lessac-medium (local, offline)",
                "faster-whisper 'base' on CPU (local)",
                "zerogpu-aoti/wan2-2-fp8da-aoti-faster (Hugging Face Space)",
                "FFmpeg and ffprobe (local)",
            ],
        })

    with st.container(border=True):
        st.subheader("Output locations (read only)")
        st.write(f"Project folder: `{C.BASE_DIR}`")
        for label, path in [("Script", C.PROJECT_FILE), ("Images", C.IMAGE_DIR), ("Voiceover", C.VOICE_DIR),
                            ("Subtitles", C.SUBTITLE_FILE), ("Clips", C.CLIP_DIR),
                            ("Final video", C.FINAL_FILE), ("Archive", C.ARCHIVE_DIR)]:
            st.write(f"{label}: `{path.relative_to(C.BASE_DIR).as_posix()}`")

    job_running = active_job() is not None
    with st.container(border=True):
        st.subheader("Maintenance")
        st.caption("Archived videos in final/archive are never deleted by these actions.")
        confirm_files = st.checkbox("I understand: delete current generated images, audio, subtitles and clips")
        if st.button("Clear current generated files", disabled=job_running or not confirm_files):
            clear_generated_outputs(keep_archive=True)
            st.toast("Current generated files deleted. Archive kept.", icon="🧹")
            st.rerun()

        confirm_history = st.checkbox("I understand: clear the generation history list (videos stay on disk)")
        if st.button("Clear history list", disabled=job_running or not confirm_history):
            clear_history()
            st.toast("History cleared.", icon="🧹")
            st.rerun()
        if job_running:
            st.info("A generation is running. Maintenance is disabled until it finishes.")
