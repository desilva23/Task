"""Clarification, grouped results, and the basket gate (FR-05, FR-21 to FR-24)."""

import streamlit as st

from graph.templates import product_label
from ui.text import md
from ui.view import addable, group_results


def clarify(pending: dict) -> dict | None:
    """One choice per ambiguous term; the answer resumes the same thread on the next run."""
    st.subheader("Which did you mean?")
    with st.form("clarify_form", border=False):
        picks = {}
        for q in pending["questions"]:
            labels = {o["label"]: o["sku"] for o in q["options"]}
            choice = st.radio(f"“{md(q['term'])}”", list(labels), key=f"choose_{q['index']}")
            picks[q["index"]] = labels[choice]
        answered = st.form_submit_button("Continue", key="answer", type="primary", width="stretch")
    return picks if answered else None


def _add(skus: list[str]) -> None:
    basket = st.session_state.basket
    st.session_state.basket = basket + [s for s in skus if s not in basket]


def results(services, state: dict) -> None:
    if not state.get("results") and state.get("message"):
        st.info(md(state["message"]))  # a run that made no claim says why (EC-01, EC-10, EC-52)
        return
    groups = group_results(services, state)
    if groups.available:
        st.subheader("Available")
        for row in groups.available:
            st.markdown(f"- {md(row.statement)}")
    if groups.unavailable:
        st.subheader("Not available")
        for row in groups.unavailable:
            st.markdown(f"- {md(row.statement)}")
            st.button(
                f"Add {row.label} anyway (it won't be routed)",
                key=f"add_one_{row.sku}",
                on_click=_add,
                args=([row.sku],),
            )
    for note in groups.notes:
        st.markdown(f"- {md(note)}")
    ready = [s for s in addable(groups) if s not in st.session_state.basket]
    if len(groups.available) + len(groups.unavailable) > 1 or state.get("shape") != "term":
        if ready or not groups.available:
            st.button(
                f"Add {len(ready)} available to basket",
                key="add_available",
                on_click=_add,
                args=(ready,),
                disabled=not ready,  # EC-15: nothing available, nothing to add
                type="primary",
                width="stretch",
            )
        else:
            st.caption("Everything available is in your basket.")


def basket(services) -> bool:
    """FR-23 — what gets routed. Returns True when the shopper asks for the route."""
    if not st.session_state.basket:
        return False
    st.subheader(f"Basket ({len(st.session_state.basket)})")
    # pills wrap at phone width, where st.columns would stack every ✕ on its own line
    st.pills(
        "Tap an item to remove it",
        st.session_state.basket,
        format_func=lambda sku: f"✕ {product_label(services, sku)}",
        selection_mode="single",
        key="remove_pick",
        on_change=_remove,
    )
    return st.button("Plan my route", key="plan_route", type="primary", width="stretch")


def _remove() -> None:
    picked = st.session_state.get("remove_pick")
    st.session_state.basket = [s for s in st.session_state.basket if s != picked]
    st.session_state.remove_pick = None
