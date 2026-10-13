# Implementation Plan: The LangGraph Pipeline (Phase 5)

**Date**: 2026-10-13 | **Spec**: [spec.md](spec.md)

## Summary

Eleven nodes over the Phase 2–4 services, compiled with an `InMemorySaver` checkpointer, a
`ModelClient` adapter with a fake for tests, the clarify interrupt, deterministic templates, and
the verify gate. Three framework-free entry points for the page.

## Technical Context

Python 3.12 · new dependencies `langgraph` 1.2 (brings `langchain-core`), `pydantic` 2 — LangGraph
is C-01 · checkpointer `InMemorySaver` (verified exported in this release, with `delete_thread`) ·
`interrupt()` re-runs its node on resume, so clarify does nothing before it that is not repeatable.

## Constitution Check

| Principle | Compliance | Pass |
|---|---|---|
| I | Model output is validated against a schema with no fact fields, substitutes checked against the candidate set, and every claim verified against services before display | ✅ |
| II | `dietary_compatible` treats unknown as incompatible; templates never state a dietary property | ✅ |
| III | Tests first; AC-03/10/11/18 and EC-03/04/09/11/13/24/34/35/37/38/47 cited | ✅ |
| IV | `graph/nodes/*` import services; services import nothing from `graph`; no streamlit | ✅ |
| V | Each of the three model nodes has a named fallback, proven with the model off | ✅ |
| VII | Explicit edges; no tool-calling agent | ✅ |

## Project Structure

```text
models/llm.py            ParsedQuery, SubstituteChoice, RouteDescription (pydantic, extra=forbid)
errors.py                + ModelUnavailableError, GroundingError
graph/model.py           ModelClient protocol, NoModel, FakeModel
graph/services.py        Services bundle built from a Store
graph/state.py           JourneyState
graph/templates.py       result statements and directions — the deterministic wording
graph/routers.py         after_start, after_classify, after_resolve, after_availability, after_locations
graph/nodes/*.py         the eleven nodes
graph/build.py           build_graph(services, model, checkpointer)
graph/journey.py         run_query, resume, plan_route, ThreadSweeper (EC-34)
tests/integration/test_graph.py   AC-03, AC-11, AC-18, structure, two runs, EC cases
tests/integration/test_verify.py  AC-10
```

## Complexity Tracking

None.
