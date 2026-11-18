"""AI Video Studio: Streamlit entry point.

Run with:  streamlit run app.py
The pipeline still runs through the original scripts (generate_*.py, assemble_video.py).
"""

import streamlit as st

from core import config as C
from core.jobs import active_job
from ui import about, create, dashboard, history, library, pipeline, settings

st.set_page_config(page_title="AI Video Studio", page_icon="🎬", layout="wide",
                   initial_sidebar_state="expanded")

css_file = C.BASE_DIR / "assets" / "style.css"
if css_file.exists():
    st.markdown(f"<style>{css_file.read_text(encoding='utf-8')}</style>", unsafe_allow_html=True)

st.logo(str(C.BASE_DIR / "assets" / "logo.svg"), size="large")

pages = {
    "dashboard": st.Page(dashboard.render, title="Dashboard", url_path="dashboard", icon=":material/dashboard:", default=True),
    "create": st.Page(create.render, title="Create New Video", url_path="create-video", icon=":material/add_circle:"),
    "pipeline": st.Page(pipeline.render, title="Video Generation Pipeline", url_path="pipeline", icon=":material/account_tree:"),
    "library": st.Page(library.render, title="My Videos", url_path="my-videos", icon=":material/video_library:"),
    "history": st.Page(history.render, title="Generation History", url_path="history", icon=":material/history:"),
    "settings": st.Page(settings.render, title="Settings", url_path="settings", icon=":material/settings:"),
    "about": st.Page(about.render, title="About", url_path="about", icon=":material/info:"),
}
st.session_state["_pages"] = pages

navigation = st.navigation(list(pages.values()), position="sidebar")
navigation.run()

with st.sidebar:
    st.divider()
    job = active_job()
    if job:
        done = sum(1 for key in job.get("steps", []) if job.get("stage_status", {}).get(key) == "completed")
        st.markdown(f"🟣 **Generating** · {done}/{len(job.get('steps', []))} steps")
        st.page_link(pages["pipeline"], label="View progress", icon=":material/account_tree:")
    else:
        st.markdown("🟢 **Ready** · no job running")
    st.caption("Local studio · outputs stay in this project folder")
