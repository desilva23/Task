# Feature Specification: Portability, Performance, Hostile Input, Deployment (Phase 8)

**Feature Branch**: none — `claude/planogram-store-navigation-czn7bh` · **Created**: 2026-10-14 ·
**Status**: Draft

**Input**: "Phase 8 — portability store, performance, hostile input, deployment. Proven by AC-09,
AC-12, AC-13."

IDs here are local (`P8-…`).

## User Scenarios & Testing *(mandatory)*

### User Story 1 - A different store is only different files (Priority: P1)

**Acceptance Scenarios**:
1. **Given** `data/SBY-PORT-002` — two floors, 5-rack aisles, shared aisles, four tills — **Then**
   AC-01 to AC-08 pass against it exactly as against the demo store, with no code change (AC-09,
   FR-25, NFR-08).
2. **Given** `LOCATOR_STORE=data/SBY-PORT-002`, **Then** the page runs on it unchanged.

### User Story 2 - Fast enough in the hand (Priority: P1)

**Acceptance Scenarios**:
1. **Given** repeated runs, **Then** one product completes inside 5 s and ten products inside
   10 s (AC-12, NFR-05) — measured with the model off in CI, and with GroqCloud live on demand.

### User Story 3 - Nothing a shopper types can break it (Priority: P1)

**Acceptance Scenarios**:
1. **Given** each hostile input of `requirements.md` §7 — empty, one character, extremely long,
   misspelled, non-English, emoji, punctuation only, many and duplicated items, quantities, not a
   product request, text written to subvert the instructions — plus markup, path and query
   probes, **Then** the page shows no error page, no file path, no traceback and no secret, and
   the graph runs only its fixed nodes with the model asked only its three tasks (AC-13, NFR-06).
2. **Given** an unexpected failure inside the page, **Then** the shopper sees a short apology,
   never a stack trace.

### User Story 4 - Deployed (Priority: P1)

**Acceptance Scenarios**:
1. **Given** the owner's Streamlit Community Cloud account, **Then** the app deploys from the
   public repository with the key in the Cloud secrets field only, and a smoke journey works on
   the public URL (C-07).

## Requirements *(mandatory)*

- **P8-R01**: The generator builds `SBY-PORT-002` from the demo catalogue and stock with a
  different layout; the committed folder equals its output (`python -m datagen --store port`).
- **P8-R02**: One acceptance suite, parametrised over both store folders, proves AC-01 to AC-08.
- **P8-R03**: `MAX_QUERY_CHARS` caps a query on the page and in classification.
- **P8-R04**: The page catches unexpected errors and Streamlit's error details are off.
- **P8-R05**: A deployment guide for the owner; the app's store and model are chosen by
  environment, never by code change.

## Success Criteria *(mandatory)*

- **P8-SC1**: AC-09, AC-12, AC-13 pass; CI green.
- **P8-SC2**: The public URL serves a verified journey.

## Assumptions

- `schema.md` §8's portability sizes (143 / 160) could not be produced by this map's topology;
  they were authoring choices and are corrected to the store as built (125 / 140).
- Deployment is done by the owner in their own Streamlit account; Claude prepares and verifies.
