"""Generation History: only real runs recorded by this GUI."""

import streamlit as st

from core.history import load_history

from .common import badge, empty_state, fmt_seconds, fmt_time, header


def render() -> None:
    header("Generation History", "Every run started from this studio, with its result.")
    history = load_history()
    if not history:
        empty_state("No runs recorded yet. History starts with your first generation.")
        return

    options = ["All", "completed", "failed", "cancelled"]
    choice = st.selectbox("Filter by status", options)
    rows = [entry for entry in history if choice == "All" or entry.get("status") == choice]
    if not rows:
        empty_state("No runs with this status.")
        return

    st.dataframe(
        [{
            "Title": entry.get("title", "Untitled"),
            "Status": entry.get("status", ""),
            "Started": fmt_time(entry.get("started_at")),
            "Duration": fmt_seconds(entry.get("duration_seconds")),
            "Video": entry.get("video") or "—",
        } for entry in rows],
        width="stretch",
        hide_index=True,
    )

    st.markdown("#### Details")
    for entry in rows:
        with st.expander(f"{entry.get('title', 'Untitled')} · {entry.get('status', '')}"):
            st.markdown(badge(entry.get("status", "pending")), unsafe_allow_html=True)
            st.write(f"**Topic:** {entry.get('topic') or '—'}")
            st.write(f"**Started:** {fmt_time(entry.get('started_at'))}")
            st.write(f"**Finished:** {fmt_time(entry.get('finished_at'))}")
            st.write(f"**Generation time:** {fmt_seconds(entry.get('duration_seconds'))}")
            if entry.get("failed_stage"):
                st.write(f"**Failed at:** {entry['failed_stage']}")
            if entry.get("error"):
                st.error(entry["error"])
            if entry.get("video"):
                st.write(f"**Output file:** {entry['video']}")
