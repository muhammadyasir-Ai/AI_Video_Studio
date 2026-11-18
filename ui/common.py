"""Shared UI helpers: headers, badges and formatting."""

import datetime
import html

import streamlit as st

from core.history import parse_time

STATUS_BADGES = {
    "completed": ("Completed", "done"),
    "running": ("Running", "run"),
    "failed": ("Failed", "fail"),
    "cancelled": ("Cancelled", "wait"),
    "pending": ("Pending", "todo"),
}


def header(title: str, subtitle: str = "") -> None:
    st.markdown(
        f"<div class='page-head'><h1>{html.escape(title)}</h1>"
        f"<p>{html.escape(subtitle)}</p></div>",
        unsafe_allow_html=True,
    )


def badge(status: str) -> str:
    text, kind = STATUS_BADGES.get(status, (status.title(), "todo"))
    return f"<span class='badge badge-{kind}'>{html.escape(text)}</span>"


def empty_state(message: str) -> None:
    st.markdown(f"<div class='empty'>{html.escape(message)}</div>", unsafe_allow_html=True)


def fmt_seconds(value) -> str:
    if value is None:
        return "—"
    value = int(round(float(value)))
    hours, rest = divmod(value, 3600)
    minutes, seconds = divmod(rest, 60)
    if hours:
        return f"{hours}h {minutes}m {seconds}s"
    if minutes:
        return f"{minutes}m {seconds}s"
    return f"{seconds}s"


def fmt_time(value) -> str:
    dt = parse_time(value)
    return dt.strftime("%d %b %Y, %I:%M %p") if dt else "—"


def elapsed_since(value) -> str:
    started = parse_time(value)
    if not started:
        return "—"
    return fmt_seconds((datetime.datetime.now() - started).total_seconds())
