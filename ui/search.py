"""The header, where the shopper is, and the search box (FR-15, hld.md §4)."""

import streamlit as st

from config import MAX_QUERY_CHARS
from ui.view import floor_names, start_options


def header(services) -> None:
    st.title("Find it in store")


def where(services) -> tuple[str, bool]:
    """Floor, then aisle — the entrance by default. Self-reported; no positioning is used."""
    options, names = start_options(services), floor_names(services)
    floors = sorted(options)
    floor = st.selectbox(
        "Which floor are you on?",
        floors,
        format_func=lambda lv: f"Floor {lv} — {names[lv]}",
        key="start_floor",
    )
    labels = [label for label, _ in options[floor]]
    spot = st.selectbox("Where on that floor?", labels, key=f"start_spot_{floor}")
    step_free = st.toggle("Step-free route (lifts, no stairs)", key="step_free")
    return dict(options[floor])[spot], step_free


def search_box() -> str | None:
    with st.form("search_form", clear_on_submit=False, border=False):
        query = st.text_input(
            "What are you looking for?",
            key="query",
            placeholder="e.g. milk, bread, eggs — or 'something for a headache'",
            max_chars=MAX_QUERY_CHARS,
        )
        submitted = st.form_submit_button("Search", key="search", type="primary", width="stretch")
    return query if submitted and query.strip() else None
