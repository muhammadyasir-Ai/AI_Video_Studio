"""My Videos: finished videos with search, sort, preview and download."""

import streamlit as st

from core import config as C
from core.files import read_json
from core.library import library_items

from .common import empty_state, fmt_seconds, fmt_time, header


def _abs(rel_path):
    return C.BASE_DIR / rel_path if rel_path else None


def _preview(item) -> None:
    video_path = _abs(item["video"])
    st.markdown(f"### {item.get('title', 'Untitled')}")
    cols = st.columns(3)
    cols[0].metric("Created", fmt_time(item.get("finished_at")))
    cols[1].metric("Duration", fmt_seconds(item.get("video_duration")))
    cols[2].metric("Status", "Completed")
    st.video(str(video_path))
    st.download_button("⬇️ Download video", video_path.read_bytes(),
                       file_name=video_path.name, mime="video/mp4", type="primary")
    st.caption(f"File location: {item['video']}")

    if item.get("script") and _abs(item["script"]).exists():
        with st.expander("Script"):
            data = read_json(_abs(item["script"]), {}) or {}
            st.write(data.get("description", ""))
            for scene in data.get("scenes", []):
                st.markdown(f"**Scene {scene.get('scene_number')}:** {scene.get('narration', '')}")
    if item.get("subtitles") and _abs(item["subtitles"]).exists():
        with st.expander("Subtitles"):
            text = _abs(item["subtitles"]).read_text(encoding="utf-8")
            st.code(text, language="text")
            st.download_button("⬇️ Download subtitles", text, file_name=_abs(item["subtitles"]).name)


def render() -> None:
    header("My Videos", "Every finished video, saved with its script and subtitles.")
    items = library_items()
    if not items:
        empty_state("No finished videos yet. Create your first video and it will appear here.")
        st.page_link(st.session_state["_pages"]["create"], label="Create a new video",
                     icon=":material/add_circle:")
        return

    left, right = st.columns([3, 1])
    query = left.text_input("Search", placeholder="Search by title or topic").strip().lower()
    order = right.selectbox("Sort", ["Newest first", "Oldest first", "Longest first"])

    filtered = [item for item in items
                if not query or query in (item.get("title") or "").lower()
                or query in (item.get("topic") or "").lower()]
    if order == "Oldest first":
        filtered = list(reversed(filtered))
    elif order == "Longest first":
        filtered.sort(key=lambda item: item.get("video_duration") or 0, reverse=True)

    if not filtered:
        empty_state("No videos match your search.")
        return

    selected_id = st.session_state.get("selected_video")
    columns = st.columns(3)
    for position, item in enumerate(filtered):
        with columns[position % 3]:
            with st.container(border=True):
                thumb = _abs(item.get("thumbnail"))
                if thumb and thumb.exists():
                    st.image(str(thumb), width="stretch")
                else:
                    empty_state("No thumbnail")
                st.markdown(f"**{item.get('title', 'Untitled')}**")
                st.markdown(
                    f"<span class='muted'>{fmt_time(item.get('finished_at'))} · "
                    f"{fmt_seconds(item.get('video_duration'))}</span>",
                    unsafe_allow_html=True,
                )
                st.caption("✅ Completed")
                if st.button("▶ Preview", key=f"preview_{item['id']}", width="stretch"):
                    st.session_state["selected_video"] = item["id"]
                    selected_id = item["id"]

    chosen = next((item for item in filtered if item["id"] == selected_id), None)
    if chosen:
        st.divider()
        _preview(chosen)
