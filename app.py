"""AI Video Studio - Streamlit control panel.

Run with:  streamlit run app.py
The pipeline scripts (generate_*.py, assemble_video.py) are run exactly as
they are in the terminal, so the GUI and the command line always do the same work.
"""

import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

import streamlit as st
from dotenv import dotenv_values

BASE_DIR = Path(__file__).resolve().parent
PROJECT_FILE = BASE_DIR / "projects" / "project_data.json"
TIMING_FILE = BASE_DIR / "projects" / "scene_timing.json"
MODEL_FILE = BASE_DIR / "en_US-lessac-medium.onnx"
IMAGE_DIR = BASE_DIR / "output"
VOICE_DIR = BASE_DIR / "voiceovers"
NARRATION_FILE = VOICE_DIR / "narration.wav"
SUBTITLE_FILE = BASE_DIR / "subtitles" / "subtitles.srt"
CLIP_DIR = BASE_DIR / "video"
FINAL_FILE = BASE_DIR / "final" / "final_video.mp4"

# Each pipeline step: key, title, description, script to run.
STEPS = [
    {"key": "script", "title": "Script", "script": "generate_script.py",
     "desc": "AI writes the title, scenes, narration and visual prompts (Cloudflare Workers AI)."},
    {"key": "images", "title": "Scene images", "script": "generate_image.py",
     "desc": "Creates one image for every scene (Flux model on Cloudflare)."},
    {"key": "voice", "title": "Voiceover", "script": "generate_voice.py",
     "desc": "Offline narration for each scene using Piper TTS (no internet needed)."},
    {"key": "subs", "title": "Subtitles", "script": "generate_subtitles.py",
     "desc": "Transcribes the narration with Whisper and writes an SRT subtitle file."},
    {"key": "clips", "title": "Video clips", "script": "generate_video.py",
     "desc": "Animates each image into a short clip with Wan 2.2. This step is slow."},
    {"key": "final", "title": "Final video", "script": "assemble_video.py",
     "desc": "Joins clips, narration and subtitles into one final MP4 with FFmpeg."},
]
STEP_BY_KEY = {step["key"]: step for step in STEPS}

CSS = """
<style>
.hero {
    background: linear-gradient(135deg, #1F4E79 0%, #2E75B6 100%);
    color: #ffffff; padding: 26px 30px; border-radius: 16px; margin-bottom: 18px;
}
.hero h1 { color: #ffffff; margin: 0; font-size: 2.1rem; line-height: 1.2; }
.hero p { margin: 6px 0 0 0; opacity: 0.92; }
.badge {
    display: inline-block; padding: 3px 11px; border-radius: 999px;
    font-size: 0.78rem; font-weight: 600; white-space: nowrap;
}
.badge-done { background: #E6F4EA; color: #137333; }
.badge-todo { background: #EEF2F7; color: #44546A; }
.badge-blocked { background: #FFF4E5; color: #8A4B00; }
.step-title { font-weight: 700; font-size: 1.05rem; }
.muted { opacity: 0.75; font-size: 0.9rem; }
#MainMenu, footer { visibility: hidden; }
</style>
"""


# ---------- File helpers ----------

def load_project():
    if not PROJECT_FILE.exists():
        return None
    try:
        return json.loads(PROJECT_FILE.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return None


def load_timing():
    if not TIMING_FILE.exists():
        return None
    try:
        return json.loads(TIMING_FILE.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return None


def scene_numbers(project):
    if not project:
        return []
    return [scene["scene_number"] for scene in project.get("scenes", [])]


def image_path(number):
    return IMAGE_DIR / f"scene_{number}.jpg"


def clip_path(number):
    return CLIP_DIR / f"scene_{number}.mp4"


def all_exist(paths):
    return bool(paths) and all(path.exists() for path in paths)


def step_done(key, project):
    numbers = scene_numbers(project)
    if key == "script":
        return project is not None
    if key == "images":
        return all_exist([image_path(n) for n in numbers])
    if key == "voice":
        return NARRATION_FILE.exists() and TIMING_FILE.exists()
    if key == "subs":
        return SUBTITLE_FILE.exists()
    if key == "clips":
        return all_exist([clip_path(n) for n in numbers])
    if key == "final":
        return FINAL_FILE.exists()
    return False


def step_blockers(key, project):
    """Return a list of reasons why this step cannot run yet."""
    reasons = []
    numbers = scene_numbers(project)
    if key != "script" and project is None:
        reasons.append("Generate the script first.")
    if key == "voice" and not MODEL_FILE.exists():
        reasons.append("Piper model file (en_US-lessac-medium.onnx) is not in the project folder.")
    if key == "subs" and not NARRATION_FILE.exists():
        reasons.append("Generate the voiceover first.")
    if key == "clips" and not all_exist([image_path(n) for n in numbers]):
        reasons.append("Generate all scene images first.")
    if key == "final":
        if not NARRATION_FILE.exists():
            reasons.append("Voiceover is not generated yet.")
        if not SUBTITLE_FILE.exists():
            reasons.append("Subtitles are not generated yet.")
        if not all_exist([clip_path(n) for n in numbers]):
            reasons.append("Scene videos are not generated yet.")
        if not shutil.which("ffmpeg"):
            reasons.append("FFmpeg was not found on PATH.")
    return reasons


def reset_outputs():
    """Delete generated files only. Scripts and the Piper model are never touched."""
    for folder in (IMAGE_DIR, VOICE_DIR, CLIP_DIR):
        shutil.rmtree(folder, ignore_errors=True)
    for file in (SUBTITLE_FILE, FINAL_FILE, TIMING_FILE):
        file.unlink(missing_ok=True)


# ---------- Running pipeline scripts ----------

def run_step(step, topic=None):
    """Run one pipeline script and stream its output into a status box.

    Returns True when the script exits with code 0.
    """
    label = step["title"]
    command = [sys.executable, "-u", str(BASE_DIR / step["script"])]
    env = {**os.environ, "PYTHONUNBUFFERED": "1", "PYTHONIOENCODING": "utf-8"}

    with st.status(f"Running: {label}...", expanded=True) as status:
        log_box = st.empty()
        lines = []
        process = None
        try:
            process = subprocess.Popen(
                command,
                cwd=BASE_DIR,  # scripts use relative paths such as projects/ and output/
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
                lines.append(line.rstrip())
                log_box.code("\n".join(lines[-80:]), language="text")

            return_code = process.wait()
        finally:
            # If the user navigates away or the page reruns, do not leave the script running.
            if process is not None and process.poll() is None:
                process.kill()

        if return_code == 0:
            status.update(label=f"{label} complete", state="complete", expanded=False)
            return True
        status.update(label=f"{label} failed. Check the log above.", state="error", expanded=True)
        return False


# ---------- UI pieces ----------

def render_header(project, timing):
    st.markdown(
        """
        <div class="hero">
            <h1>🎬 AI Video Studio</h1>
            <p>Enter a topic and let AI create the script, images, voice, subtitles and video.</p>
        </div>
        """,
        unsafe_allow_html=True,
    )

    done = sum(step_done(step["key"], project) for step in STEPS)
    duration = f"{timing['total_duration']:.1f}s" if timing and "total_duration" in timing else "—"
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Project", (project or {}).get("title", "Not started")[:28])
    col2.metric("Scenes", len(scene_numbers(project)))
    col3.metric("Narration length", duration)
    col4.metric("Steps complete", f"{done} / {len(STEPS)}")


def render_sidebar():
    with st.sidebar:
        st.markdown("### ⚙️ System check")
        env = dotenv_values(BASE_DIR / ".env")
        checks = [
            ("Cloudflare credentials (.env)",
             bool(env.get("CLOUDFLARE_ACCOUNT_ID") and env.get("CLOUDFLARE_API_TOKEN"))),
            ("Piper voice model", MODEL_FILE.exists()),
            ("FFmpeg on PATH", bool(shutil.which("ffmpeg"))),
        ]
        for name, ok in checks:
            st.write(("✅ " if ok else "❌ ") + name)

        st.divider()
        st.markdown("### 🧹 Project files")
        st.caption("Delete old images, audio, subtitles and videos. "
                   "Scripts and the model will not be deleted.")
        confirm = st.checkbox("Yes, delete generated files")
        if st.button("Reset generated files", disabled=not confirm):
            reset_outputs()
            st.toast("Generated files deleted.", icon="🧹")
            st.rerun()

        st.divider()
        skip_done = st.toggle("Skip completed steps in pipeline", value=True)
        return skip_done


def render_create(project):
    with st.container(border=True):
        st.subheader("✍️ 1. Topic and script")
        topic = st.text_input(
            "Video topic",
            placeholder="e.g. AI in 2026: What It Can Really Do",
            key="topic",
        )
        if project:
            st.caption("Generating a new script means the images, audio, subtitles and video "
                       "must be generated again. Reset old files from the sidebar first if needed.")
        if st.button("Generate script", type="primary", disabled=not topic.strip()):
            if run_step(STEP_BY_KEY["script"], topic=topic.strip()):
                st.toast("Script is ready.", icon="✅")
                st.rerun()
        return topic.strip()


def render_pipeline(project, topic, skip_done):
    st.subheader("🛠️ Pipeline")
    pending = [s["key"] for s in STEPS if not (skip_done and step_done(s["key"], project))]

    col_a, col_b = st.columns([1, 3])
    if col_a.button("▶️ Run all steps", type="primary", disabled=not pending):
        if "script" in pending and not topic:
            st.warning("Please enter a topic above first.")
        else:
            for key in pending:
                blockers = step_blockers(key, load_project())
                if blockers:
                    st.error(f"{STEP_BY_KEY[key]['title']}: {blockers[0]}")
                    break
                if not run_step(STEP_BY_KEY[key], topic=topic if key == "script" else None):
                    break
            else:
                st.toast("Pipeline complete! 🎉", icon="🎬")
            st.rerun()
    col_b.caption(f"Remaining steps: {len(pending)}" if pending else "All steps are complete.")

    for index, step in enumerate(STEPS, start=1):
        key = step["key"]
        done = step_done(key, project)
        blockers = step_blockers(key, project)
        with st.container(border=True):
            info, action = st.columns([4, 1.4])
            with info:
                badge = ("<span class='badge badge-done'>Complete</span>" if done
                         else "<span class='badge badge-blocked'>Waiting</span>" if blockers
                         else "<span class='badge badge-todo'>Ready</span>")
                st.markdown(
                    f"<span class='step-title'>{index}. {step['title']}</span> &nbsp; {badge}",
                    unsafe_allow_html=True,
                )
                st.markdown(f"<span class='muted'>{step['desc']}</span>", unsafe_allow_html=True)
                if blockers:
                    st.caption("⏳ " + blockers[0])
            with action:
                label = "Run again" if done else "Run"
                needs_topic = key == "script" and not topic
                if st.button(label, key=f"run_{key}",
                             disabled=bool(blockers) or needs_topic,
                             use_container_width=True):
                    if run_step(step, topic=topic if key == "script" else None):
                        st.toast(f"{step['title']} complete.", icon="✅")
                        st.rerun()


def render_results(project):
    st.subheader("📦 Results")
    tab_script, tab_images, tab_voice, tab_subs, tab_final = st.tabs(
        ["📝 Script", "🖼️ Images", "🎙️ Voiceover", "💬 Subtitles", "🎬 Final video"]
    )

    with tab_script:
        if not project:
            st.info("Script is not generated yet.")
        else:
            st.markdown(f"#### {project.get('title', '')}")
            st.write(project.get("description", ""))
            st.markdown("##### Scenes (you can edit the narration)")
            with st.form("narration_form"):
                for scene in project.get("scenes", []):
                    number = scene["scene_number"]
                    st.text_area(f"Scene {number}", value=scene.get("narration", ""),
                                 key=f"narr_{number}", height=90)
                    with st.expander(f"Scene {number} visual prompts"):
                        st.caption("Image prompt")
                        st.write(scene.get("image_prompt", ""))
                        st.caption("Motion prompt")
                        st.write(scene.get("motion_prompt", ""))
                if st.form_submit_button("💾 Save narration"):
                    for scene in project.get("scenes", []):
                        scene["narration"] = st.session_state[f"narr_{scene['scene_number']}"]
                    PROJECT_FILE.write_text(json.dumps(project, ensure_ascii=False, indent=4),
                                            encoding="utf-8")
                    st.success("Saved. Start again from the voiceover step.")

    with tab_images:
        numbers = scene_numbers(project)
        if not numbers:
            st.info("Generate the script first.")
        else:
            columns = st.columns(3)
            for position, number in enumerate(numbers):
                with columns[position % 3]:
                    path = image_path(number)
                    if path.exists():
                        st.image(str(path), caption=f"Scene {number}", use_container_width=True)
                    else:
                        st.caption(f"Scene {number}: image not generated yet")

    with tab_voice:
        if NARRATION_FILE.exists():
            st.audio(NARRATION_FILE.read_bytes(), format="audio/wav")
            st.download_button("⬇️ Narration download", NARRATION_FILE.read_bytes(),
                               file_name="narration.wav", mime="audio/wav")
        else:
            st.info("Voiceover is not generated yet.")

    with tab_subs:
        if SUBTITLE_FILE.exists():
            text = SUBTITLE_FILE.read_text(encoding="utf-8")
            st.text_area("Subtitles (SRT)", value=text, height=320, disabled=True)
            st.download_button("⬇️ Subtitles download", text, file_name="subtitles.srt")
        else:
            st.info("Subtitles are not generated yet.")

    with tab_final:
        if FINAL_FILE.exists():
            video_bytes = FINAL_FILE.read_bytes()
            st.video(video_bytes)
            st.download_button("⬇️ Final video download", video_bytes,
                               file_name="final_video.mp4", mime="video/mp4", type="primary")
        else:
            st.info("Final video is not generated yet.")


def main():
    st.set_page_config(page_title="AI Video Studio", page_icon="🎬", layout="wide")
    st.markdown(CSS, unsafe_allow_html=True)

    skip_done = render_sidebar()
    project = load_project()
    render_header(project, load_timing())

    left, right = st.columns([1, 1.25], gap="large")
    with left:
        topic = render_create(project)
    with right:
        render_pipeline(project, topic, skip_done)

    st.divider()
    render_results(project)


if __name__ == "__main__":
    main()
