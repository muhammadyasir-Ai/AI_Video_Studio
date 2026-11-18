"""Create New Video: topic input, validation, start generation, and script review."""

import streamlit as st

from core import config as C
from core.files import load_project, stage_done, write_json
from core.jobs import TOPIC_MAX, TOPIC_MIN, active_job, start_job

from .common import header


def _start(steps, topic, label, fresh):
    try:
        start_job(steps, topic=topic, label=label, fresh=fresh)
    except (ValueError, RuntimeError) as error:
        st.error(str(error))
        return
    st.toast("Generation started. Follow progress on the Pipeline page.", icon="🎬")
    st.rerun()


def render() -> None:
    header("Create New Video", "Enter a topic. The studio writes the script, then builds every part of the video.")

    job = active_job()
    project = load_project()
    if job:
        st.info("A video is being generated right now. Follow the progress on the Video Generation Pipeline page.")

    with st.container(border=True):
        st.subheader("1. Topic")
        topic = st.text_area(
            "Video topic",
            max_chars=TOPIC_MAX,
            height=90,
            placeholder="e.g. How solar panels turn sunlight into electricity",
            help=f"Between {TOPIC_MIN} and {TOPIC_MAX} characters. The AI uses it to write the script.",
        )
        cleaned = topic.strip()
        st.caption(f"{len(cleaned)} / {TOPIC_MAX} characters")

        col_new, col_continue = st.columns(2)
        if col_new.button("🎬 Generate video", type="primary", disabled=bool(job) or len(cleaned) < TOPIC_MIN,
                          width="stretch",
                          help="Writes a new script and rebuilds every step. The current final video is archived first."):
            _start(list(C.RUNNABLE_KEYS), cleaned, "New video", fresh=True)

        remaining = [key for key in C.RUNNABLE_KEYS if key != "script" and not stage_done(key, project)]
        if col_continue.button("▶️ Continue existing script", disabled=bool(job) or project is None,
                               width="stretch",
                               help="Runs only the steps that are not complete yet, using the saved script."):
            if not remaining:
                st.info("All steps are already complete.")
            else:
                _start(remaining, None, "Continue video", fresh=False)

    if project:
        with st.container(border=True):
            st.subheader("2. Review script")
            st.caption("Edit the title or narration here. Voiceover, subtitles and video must be run again "
                       "after changing narration.")
            with st.form("script_form"):
                title = st.text_input("Video title", value=project.get("title", ""), max_chars=120)
                narration_inputs = {}
                for scene in project.get("scenes", []):
                    number = scene["scene_number"]
                    narration_inputs[number] = st.text_area(
                        f"Scene {number} narration", value=scene.get("narration", ""), height=80,
                        key=f"narration_{number}")
                saved = st.form_submit_button("💾 Save changes", disabled=bool(job))
            if saved:
                if not title.strip():
                    st.error("The title cannot be empty.")
                elif any(not text.strip() for text in narration_inputs.values()):
                    st.error("Every scene needs narration text.")
                else:
                    project["title"] = title.strip()
                    for scene in project["scenes"]:
                        scene["narration"] = narration_inputs[scene["scene_number"]].strip()
                    write_json(C.PROJECT_FILE, project)
                    st.success("Saved. Run the voiceover and later steps again to update the video.")

            with st.expander("Visual prompts (read only)"):
                for scene in project.get("scenes", []):
                    st.markdown(f"**Scene {scene['scene_number']}**")
                    st.caption("Image prompt")
                    st.write(scene.get("image_prompt", ""))
                    st.caption("Motion prompt")
                    st.write(scene.get("motion_prompt", ""))
