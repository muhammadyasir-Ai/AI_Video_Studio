"""About page: what the studio does, how it works and who it is for."""

import streamlit as st

from .common import header


def render() -> None:
    header("About AI Video Studio", "Turn a single topic into a finished video, with AI doing the heavy lifting.")

    with st.container(border=True):
        st.subheader("What it does")
        st.write("AI Video Studio takes a topic and builds a complete short video: a script with scenes, "
                 "one image per scene, a natural-sounding voiceover, subtitles, animated clips and a final "
                 "video that joins everything together.")

    with st.container(border=True):
        st.subheader("How the pipeline works")
        for number, text in enumerate([
            "Script: AI writes the title, scenes, narration and visual prompts.",
            "Images: one image is created for each scene.",
            "Voiceover: narration is recorded offline with Piper, with timing for each scene.",
            "Subtitles: Whisper transcribes the narration into an SRT file.",
            "Video clips: each image is animated into a short clip with Wan 2.2.",
            "Final video: FFmpeg joins the clips, narration and subtitles into one MP4.",
        ], start=1):
            st.markdown(f"{number}. {text}")

    with st.container(border=True):
        st.subheader("Technology")
        st.write("Python · Streamlit · Cloudflare Workers AI · Piper TTS · faster-whisper · "
                 "Hugging Face Gradio · FFmpeg")

    with st.container(border=True):
        st.subheader("Created by")
        st.write("Muhammad Yasir · Computer Science graduate, KUST")
        st.caption("Version 1.0 · GUI built on top of the original command-line scripts, which still work unchanged.")
