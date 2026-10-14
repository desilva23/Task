"""Find it in store — the one page (C-03). The graph runs in this process; there is no API.

Session state holds the search and route thread IDs and the basket draft; everything else is
read back from the checkpoint on each run, because Streamlit re-executes this script on every
interaction (lld.md §11, EC-36).
"""

import uuid

import streamlit as st

from ui import directions, resources, results, search

st.set_page_config(page_title="Find it in store", page_icon="🛒", layout="centered")

svc = resources.services()
journey = resources.journey()
ss = st.session_state
ss.setdefault("basket", [])
ss.setdefault("thread", None)
ss.setdefault("route_thread", None)
journey.sweep()  # EC-34

search.header(svc)
start, step_free = search.where(svc)
query = search.search_box()
if query:
    ss.thread, ss.route_thread = f"search-{uuid.uuid4().hex}", None
    journey.run_query(ss.thread, query, start_node=start, step_free=step_free)

shown = None
if ss.thread:
    outcome = journey.current(ss.thread)
    if outcome.pending:
        picks = results.clarify(outcome.pending)
        if picks is not None:
            journey.resume(ss.thread, picks)
            st.rerun()
    elif outcome.state:
        shown = outcome.state
        results.results(svc, shown)
        if shown.get("route") and not ss.route_thread:
            directions.route(svc, shown)

if results.basket(svc):
    ss.route_thread = f"route-{uuid.uuid4().hex}"
    journey.plan_route(ss.route_thread, ss.basket, start_node=start, step_free=step_free)
if ss.route_thread:
    shown = journey.current(ss.route_thread).state
    directions.route(svc, shown)

if shown:
    directions.degraded_notice(shown)
