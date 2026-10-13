---
description: "Task list for Phase 0 — project scaffold and guard rails"
---

# Tasks: Project Scaffold and Guard Rails (Phase 0)

**Input**: Design documents from `specs/001-project-scaffold/`

**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/

**Tests**: required — constitution Principle III. Within each story, the test task comes first
and MUST be seen failing before the implementation task starts.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: can run in parallel (different files, no dependency on an unfinished task)
- **[Story]**: US1–US5 from spec.md

---

## Phase 1: Setup

- [X] T001 Create `pyproject.toml` (uv, `package = false`, `requires-python = "==3.12.*"`, dev group `pytest`, `hypothesis`, `ruff`; ruff `target-version = "py312"`, `line-length = 100`; pytest `pythonpath = ["."]`, `testpaths = ["tests"]`) and `.python-version` = `3.12`
- [X] T002 Run `uv lock` and `uv sync`; confirm `uv run python --version` is 3.12 and `uv.lock` is created
- [X] T003 [P] Create the empty layout from plan.md: `app.py`, `config.py`, `errors.py`, `validation.py` (docstring only), `ui/`, `graph/`, `graph/nodes/`, `services/`, `models/` (each `__init__.py` with a docstring), `data/.gitkeep`, `tests/__init__.py`, `tests/guards/__init__.py`, `tests/unit/__init__.py`, `tests/integration/__init__.py`, `tests/fixtures/.gitkeep`
- [X] T004 [P] Add `.venv/`, `__pycache__/`, `.pytest_cache/`, `.ruff_cache/`, `.hypothesis/` to `.gitignore`

---

## Phase 2: Foundational

- [X] T005 Amend `.specify/memory/constitution.md` to v1.1.0 — Principle III cites `W-` and `CONST-<principle>` IDs — and update the Conventions section of `CLAUDE.md` in the same change (research R8)

**Checkpoint**: an empty project that installs on 3.12.

---

## Phase 3: User Story 1 — one command says whether the project is healthy (P1) 🎯 MVP

**Goal**: `scripts/check.sh` runs lint, format and tests and fails on any of them.
**Independent test**: plant a lint fault; the script fails naming the file; remove it; it passes.

- [X] T006 [US1] Write `scripts/check.sh` per contracts/check-command.md (`set -euo pipefail`, three `uv run --locked` steps) and make it executable
- [X] T007 [US1] Verify by hand: plant an unused import in `config.py` → script fails naming it; remove → lint/format steps pass (pytest step reports no tests until US2)

---

## Phase 4: User Story 2 — architectural boundaries (P1)

**Goal**: the three Principle IV rules fail the suite with `path:line rule: module`.
**Independent test**: planted violations in a temp tree are each caught; the real tree is clean.

- [X] T008 [US2] Write failing tests in `tests/unit/test_import_rules.py` (class docstring `CONST-IV`): one planted violation per rule in `tmp_path` (incl. an import inside a function and a `from … import`), the allowed `graph/nodes → services` direction, `graphviz` not matching `graph`, a relative import inside `services/`, the message format, and the real repository tree reporting zero violations
- [X] T009 [US2] Implement `tests/guards/imports.py` — rules table and `find_violations(root) -> list[str]` per data-model.md — until T008 passes

---

## Phase 5: User Story 3 — secrets never reach the repository (P1)

**Goal**: a tracked `.env` or `secrets.toml` at any depth fails the suite.
**Independent test**: in a temp git repo, force-adding either file is caught; `.env.example` is not.

- [X] T010 [P] [US3] Write failing tests in `tests/unit/test_secret_files.py` (class docstring `CONST-SECRETS`): temp git repos with tracked `.env`, nested `a/.streamlit/secrets.toml`, harmless `.env.example`; a non-git directory fails with a reason; the real repository has none; both names are gitignored (`git check-ignore`)
- [X] T011 [US3] Implement `tests/guards/secret_files.py` — `tracked_secret_files(root) -> list[str]` via `git ls-files -z`, raising on a non-work-tree — until T010 passes

---

## Phase 6: User Story 4 — every test is traced (P2)

**Goal**: an untraced or wrongly traced test fails collection; a generated matrix shows coverage.
**Independent test**: the pytester cases in T012/T014 and the stale-matrix check.

- [X] T012 [P] [US4] Write failing tests in `tests/unit/test_spec_ids.py` (`CONST-III`): totals 27 AC / 24 FR / 11 NFR / 47 EC / 42 V / 5 W from the real documents; `FR-03` is not defined; a prose mention does not define an ID; bold IDs in a first cell do; `CONST-I`…`CONST-VII` and `CONST-SECRETS` are defined
- [X] T013 [US4] Implement `tests/guards/spec_ids.py` — `defined_ids(repo_root) -> dict[str, str]` (id → source) — until T012 passes
- [X] T014 [US4] Write failing tests in `tests/unit/test_trace_plugin.py` (`CONST-III`) using `pytester`: untraced test fails collection with `Untraced test:`; `FR-03` and `AC-99` fail with `Unknown ID`; docstring, snake-name and class-docstring citations pass; a parametrised test counts once
- [X] T015 [US4] Implement `tests/guards/trace_plugin.py` (citation extraction per contracts/trace-citations.md, collection-time check, reporting hook) and a root `conftest.py` that loads it — until T014 passes and the whole suite still collects
- [X] T016 [US4] Write failing test `tests/unit/test_traceability_matrix.py` (`CONST-III`): `scripts/trace_matrix.py --check` exits 0; it is deterministic (two runs, identical output); every defined ID has a row
- [X] T017 [US4] Implement `scripts/trace_matrix.py` per contracts/traceability-matrix.md; generate `docs/traceability.md`; T016 passes

---

## Phase 7: User Story 5 — the same checks on every push (P3)

- [X] T018 [US5] Confirm current major versions of `actions/checkout` and `astral-sh/setup-uv`, then write `.github/workflows/check.yml`: on `push` and `pull_request`, checkout, setup-uv, `uv sync --locked`, `scripts/check.sh`
- [ ] T019 [US5] Validate the workflow file parses as YAML; CI's first green run is confirmed after the owner pushes

---

## Phase 8: Polish

- [X] T020 Run `scripts/check.sh` from a fresh clone of the commit in a temp directory (P0-SC1), timing setup plus check
- [X] T021 Walk quickstart.md §3 plant-by-plant (P0-SC2) and record the results for the gate
- [X] T022 Update `CLAUDE.md` current state (Phase 0 complete, awaiting review) and `README.md` with the two commands

---

## Dependencies

- Setup (T001–T004) → Foundational (T005) → stories.
- US1 before US2–US4 (they are run through the check command).
- US2 and US3 are independent of each other.
- US4's plugin (T015) makes every test's citation mandatory, so T008/T010/T012 cite IDs from the
  start.
- T017 after every other test file exists, so the committed matrix is complete.
- US5 after US1 (it calls the same script).

## Parallel opportunities

- T003 ‖ T004; T010 ‖ T012 (different files, no shared code).

## Implementation strategy

Bottom-up, test-first, one story at a time, stopping at the Phase 0 gate for the owner's review
once T022 is done. Nothing is pushed without the owner's go-ahead.

## Gate record (2026-10-13)

- Fresh clone → `uv sync --locked` + `scripts/check.sh`: **5 s**, 45 passed, Python 3.12.13 (P0-SC1).
- Planted violations (P0-SC2): streamlit in `services/`, graph in `services/`, streamlit in
  `config.py`, tracked `.env`, untraced test, `FR-03` cited, stale matrix — **7 of 7 fail the
  check**; the clean tree passes again.
- CI (P0-SC5): not yet run — the branch has not been pushed.
