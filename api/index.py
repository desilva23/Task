"""The HTTP API between the Next.js page and the agent (C-03, hld.md §4.1, lld.md §11).

One Vercel Python function. It is stateless: each request builds a journey on a fresh thread,
runs it, and deletes the thread before answering, so any request may land on any instance. The
store and its matrices are built once per instance, when the function starts. The page holds
the shopper's position, basket and clarification answers, and sends what a request needs.

This module is the only one that knows it is a web service.
"""

import csv
import logging
import os
import sys
import uuid
from functools import cache
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:  # the function runs from api/; the packages live at the root
    sys.path.insert(0, str(ROOT))

from fastapi import FastAPI, Request, Response  # noqa: E402
from fastapi.exceptions import RequestValidationError  # noqa: E402
from fastapi.responses import JSONResponse  # noqa: E402
from pydantic import BaseModel, Field  # noqa: E402

from config import MAX_CLARIFY_ROUNDS, MODEL_CALLS_PER_SESSION  # noqa: E402
from graph.journey import Journey  # noqa: E402
from graph.model import NoModel  # noqa: E402
from graph.model_factory import make_model  # noqa: E402
from graph.services import Services  # noqa: E402
from present.view import floor_names, page_view, start_options, suggestions  # noqa: E402
from validation import load_store  # noqa: E402

APOLOGY = "Something went wrong on our side — please try your search again."
BUDGET_COOKIE = "locator_model_calls"
MAX_INPUT_CHARS = 20_000  # far past MAX_QUERY_CHARS: the journey cuts and says so (NFR-06)
MAX_BASKET = 100

log = logging.getLogger("locator")
app = FastAPI(docs_url=None, redoc_url=None, openapi_url=None)


DATA = ROOT / "data"
DEFAULT_STORE = "SBY-DEMO-001"


@cache
def store_folders() -> dict[str, Path]:
    """FR-31, FR-25 — every store folder under data/, by its id. A new store is a new folder:
    it appears in the switcher with no code change. LOCATOR_STORE serves one folder alone."""
    if os.environ.get("LOCATOR_STORE"):
        folder = Path(os.environ["LOCATOR_STORE"])
        return {folder.name: folder}
    return {f.name: f for f in sorted(DATA.iterdir()) if (f / "store.csv").is_file()}


def default_store() -> str:
    folders = store_folders()
    return DEFAULT_STORE if DEFAULT_STORE in folders else next(iter(folders))


class UnknownStore(Exception):
    """EC-74 — a store id this deployment does not hold. Never answered from another store."""


@cache
def services(store_id: str | None = None) -> Services:
    """Built once per store per function instance, on that store's first request (NFR-05)."""
    store_id = store_id or default_store()
    folder = store_folders().get(store_id)
    if folder is None:
        raise UnknownStore(store_id)
    return Services.from_store(load_store(folder))


@cache
def store_list() -> list[dict]:
    """What the switcher offers: each store's id, name and floor count — read from two of its
    files, so listing stores never builds them; each is validated when it is first used. The
    default store first."""
    out = []
    for store_id, folder in store_folders().items():
        with (folder / "store.csv").open(encoding="utf-8") as f:
            info = {r["key"]: r["value"] for r in csv.DictReader(f)}
        with (folder / "map_nodes.csv").open(encoding="utf-8") as f:
            floors = {r["level"] for r in csv.DictReader(f)}
        out.append({"id": store_id, "name": info.get("store_name", store_id),
                    "floors": len(floors)})  # fmt: skip
    return sorted(out, key=lambda s: (s["id"] != default_store(), s["name"]))


# ── requests ─────────────────────────────────────────────────────────────────────────────────


class Where(BaseModel):
    store: str = Field("", max_length=32)  # FR-31 — which store; empty is the default one
    start: str = Field("", max_length=64)  # an unknown point falls back to the entrance
    step_free: bool = False


class SearchRequest(Where):
    query: str = Field(max_length=MAX_INPUT_CHARS)
    answers: list[dict[str, str]] = Field(default_factory=list, max_length=MAX_CLARIFY_ROUNDS)


class ScanRequest(Where):
    code: str = Field(max_length=64)


class RouteRequest(Where):
    skus: list[str] = Field(max_length=MAX_BASKET)


# ── the model budget — a courtesy limit, counted in a cookie (hld.md §4.1) ───────────────────


def _used(request: Request) -> int:
    try:
        return max(0, min(MODEL_CALLS_PER_SESSION, int(request.cookies.get(BUDGET_COOKIE, 0))))
    except ValueError:
        return 0


def _model(used: int):
    if os.environ.get("LOCATOR_MODEL") == "off":
        return NoModel()
    return make_model(budget=MODEL_CALLS_PER_SESSION - used)


def _journey_run(request: Request, response: Response, run, store: str = "") -> dict:
    svc = services(store or None)  # an unknown store is refused before any work (EC-74)
    used = _used(request)
    model = _model(used)
    journey, thread = Journey(svc, model), f"req-{uuid.uuid4().hex}"
    try:
        outcome = run(journey, thread)
        return page_view(svc, outcome.state, outcome.pending)
    finally:
        journey.forget(thread)  # nothing outlives its request (EC-34)
        calls = getattr(model, "calls", 0)
        if calls:
            response.set_cookie(BUDGET_COOKIE, str(used + calls), max_age=86_400,
                                httponly=True, secure=True, samesite="strict")  # fmt: skip


# ── endpoints ────────────────────────────────────────────────────────────────────────────────


@app.get("/api/store")
def store(store: str = "") -> dict:
    """What the position picker offers (FR-15), and the catalogue the search box suggests from
    (FR-28). Built from the store's files, so another store's folder offers its own floors, aisles
    and products with no code change (FR-25)."""
    svc = services(store[:32] or None)
    names = floor_names(svc)
    return {
        "id": svc.store.info.store_id,
        "name": svc.store.info.store_name,
        "stores": store_list(),  # FR-31 — the switcher
        "entrance": svc.engine.graph.entrance,
        "floors": [
            {
                "level": level,
                "name": names[level],
                "spots": [{"label": label, "node": node} for label, node in spots],
            }
            for level, spots in start_options(svc).items()
        ],  # fmt: skip
        "products": suggestions(svc),  # FR-28 — matched on the phone as the shopper types
    }


@app.post("/api/search")
def search(body: SearchRequest, request: Request, response: Response) -> dict:
    """FR-01, FR-02, FR-04, FR-05 — a search, with the answers to any clarification so far."""
    return _journey_run(request, response, lambda j, t: j.answer(
        t, body.query, body.answers, start_node=body.start, step_free=body.step_free),
        body.store)  # fmt: skip


@app.post("/api/scan")
def scan(body: ScanRequest, request: Request, response: Response) -> dict:
    """FR-03 — digits read by the page's camera or typed; checked again here (hld.md §3.5)."""
    return _journey_run(request, response, lambda j, t: j.run_scan(
        t, body.code, start_node=body.start, step_free=body.step_free), body.store)  # fmt: skip


@app.post("/api/route")
def route(body: RouteRequest, request: Request, response: Response) -> dict:
    """FR-16, FR-23 — the basket the page holds, routed. Routability is re-read from the store
    data, so a stale page can never be routed to an empty shelf (EC-17)."""
    skus = list(dict.fromkeys(body.skus))
    return _journey_run(request, response, lambda j, t: j.plan_route(
        t, skus, start_node=body.start, step_free=body.step_free), body.store)  # fmt: skip


# ── failures: an apology, never a trace (AC-13) ─────────────────────────────────────────────


@app.exception_handler(RequestValidationError)
def bad_request(request: Request, exc: RequestValidationError) -> JSONResponse:
    return JSONResponse({"error": "That request couldn't be read."}, status_code=422)


@app.exception_handler(UnknownStore)
def unknown_store(request: Request, exc: UnknownStore) -> JSONResponse:
    return JSONResponse({"error": "That store isn't available here."}, status_code=404)


@app.exception_handler(Exception)
def failed(request: Request, exc: Exception) -> JSONResponse:
    log.exception("request failed")
    return JSONResponse({"error": APOLOGY}, status_code=500)


if os.environ.get("LOCATOR_STATIC"):  # local runs and the browser tests: serve the built page too
    from fastapi.staticfiles import StaticFiles

    app.mount("/", StaticFiles(directory=os.environ["LOCATOR_STATIC"], html=True), name="page")
