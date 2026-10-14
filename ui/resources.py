"""Built once per process, or once per browser session (hld.md §4.1, lld.md §11).

Services — the store, the search index and the distance matrices — are shared by every session
through ``st.cache_resource``; rebuilding them per click would spend NFR-05's budget before a
search began. Each session gets its own ``Journey``: its own checkpointer threads and its own
model client, so the model call budget is per session (constitution: public-deployment guard).
"""

import os
from pathlib import Path

import streamlit as st

from graph.journey import Journey
from graph.model import NoModel
from graph.model_factory import make_model
from graph.services import Services
from validation import load_store

REPO = Path(__file__).resolve().parents[1]


@st.cache_resource
def services() -> Services:
    folder = Path(os.environ.get("LOCATOR_STORE", REPO / "data" / "SBY-DEMO-001"))
    return Services.from_store(load_store(folder))


def model():
    return NoModel() if os.environ.get("LOCATOR_MODEL") == "off" else make_model()


def journey() -> Journey:
    if "journey" not in st.session_state:
        st.session_state.journey = Journey(services(), model())
    return st.session_state.journey
