"""The route, twice: the directions list — the accessible route (NFR-10) — and the floor plates
drawn from the same route (FR-20, AC-22)."""

import streamlit as st

from ui.floorplate import floor_plates


def route(services, state: dict) -> None:
    r = state.get("route")
    if not r:
        return
    st.subheader("Your route")
    if r["kind"] == "none":
        st.warning(r["message"])
        return
    st.markdown("\n".join(f"{i}. {line}" for i, line in enumerate(state["directions"], 1)))
    for item in r.get("excluded") or []:
        st.markdown(f"- {item['message']}")
    if r["kind"] == "multi":
        st.caption(
            "Why this order: the highest floor first, one pass per floor, ending at the checkouts."
        )
    plates = floor_plates(services, r)
    tabs = st.tabs([f"Floor {p.level}" for p in plates])
    for tab, plate in zip(tabs, plates, strict=True):
        with tab:
            # st.html drops inline SVG in Streamlit 1.65; markdown keeps it, data attributes
            # included. The SVG is ours, drawn from validated map data, with no free text in it.
            st.markdown(plate.svg, unsafe_allow_html=True)


def degraded_notice(state: dict) -> None:
    used = state.get("degraded") or []
    if used:
        names = ", ".join(n.replace("_", " ") for n in used)
        st.info(f"Plain wording: the language model wasn't used for {names}. Every fact above "
                "comes from the store data either way.")  # fmt: skip
