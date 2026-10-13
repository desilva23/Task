# Feature Specification: Project Scaffold and Guard Rails (Phase 0)

**Feature Branch**: none — work stays on `claude/planogram-store-navigation-czn7bh`

**Created**: 2026-10-13

**Status**: Draft

**Input**: User description: "Phase 0 — project scaffold and guard rails. Set up the project so
every later phase has somewhere to put code and tests, and so the constitution's mechanical rules
are enforced from the first commit."

Requirement and success-criterion IDs in this file are local to Phase 0 (`P0-…`), so they
cannot be confused with `FR-xx` in `docs/requirements.md`.

## User Scenarios & Testing *(mandatory)*

The people served by this phase are the **owner**, who reviews each phase at a gate, and the
**builder**, who writes the code. No shopper-facing behaviour exists yet.

### User Story 1 - One command says whether the project is healthy (Priority: P1)

The builder clones the repository on a machine whose default Python is not the pinned version,
runs one setup command and one check command, and gets a clear pass or fail covering lint,
formatting and every test.

**Why this priority**: every later phase depends on it. Without a reproducible environment and a
single check, no gate can be reviewed with confidence.

**Independent Test**: on a fresh clone, run the documented setup and check commands; they pass
with no manual steps, and the interpreter in use is the pinned version.

**Acceptance Scenarios**:

1. **Given** a fresh clone and a machine whose default Python is 3.14, **When** the builder runs
   the documented setup command, **Then** the environment is created on Python 3.12 exactly as
   recorded in the lock file.
2. **Given** a set-up environment, **When** the builder runs the check command, **Then** lint,
   format check and the full test suite all run and the command exits non-zero if any of them
   fails.
3. **Given** a file with a lint or formatting fault, **When** the check runs, **Then** it fails
   and names the file.

---

### User Story 2 - Architectural boundaries cannot be crossed silently (Priority: P1)

The constitution (Principle IV) says the deterministic core must never depend on the graph
runtime, a model client or the page framework. The owner wants that enforced by the test suite,
so a violation is caught on the commit that introduces it, not at review.

**Why this priority**: the fallbacks that make the system correct without a model (NFR-04) are
only honest if the core truly has no model dependency. A boundary that is only reviewed will
erode.

**Independent Test**: add a forbidden import to a file in each protected area; the suite fails
and names the file, the line and the rule. Remove it; the suite passes.

**Acceptance Scenarios**:

1. **Given** a module under `services/` that imports the graph runtime, a LangChain package, the
   page framework or a model client, **When** the suite runs, **Then** it fails naming the
   module, the line and the rule broken.
2. **Given** a module under `services/` that imports from `graph/`, **When** the suite runs,
   **Then** it fails.
3. **Given** any module outside `ui/` and `app.py` that imports the page framework, **When** the
   suite runs, **Then** it fails.
4. **Given** a module under `graph/nodes/` that imports from `services/`, **When** the suite runs,
   **Then** it passes — that direction is allowed.

---

### User Story 3 - A secret can never reach the public repository (Priority: P1)

The repository is public and the deployed app will use the owner's model-provider key. The owner
wants two layers of protection: the secret files are ignored by version control, and if one is
ever force-added the suite fails.

**Why this priority**: a leaked key is spent by strangers, and removing it from a public
history does not un-leak it.

**Independent Test**: create a local secrets file — it does not appear as a change to commit.
Force-add it — the suite fails and names it.

**Acceptance Scenarios**:

1. **Given** a local `.streamlit/secrets.toml` or `.env` file, **When** the builder checks what is
   to be committed, **Then** neither file is listed.
2. **Given** either file has been force-added to version control, at any directory depth, **When**
   the suite runs, **Then** it fails and names the tracked file.
3. **Given** a file named, for example, `.env.example` with no secret in it, **When** the suite
   runs, **Then** it is not flagged.

---

### User Story 4 - Every test is traced to the specification (Priority: P2)

The owner wants to see, for every requirement, acceptance criterion, edge case and validation
rule, which tests prove it — and to know that the list cannot go stale or cite an ID that does
not exist.

**Why this priority**: it is what makes a gate review fast: the owner reads the matrix, not the
test code. It ranks below P1 only because it reports on tests rather than protecting the code.

**Independent Test**: add a test with no traced ID — the suite fails. Add one citing `AC-99` — the
suite fails. Add one citing `AC-01` without regenerating the matrix — the suite fails. Regenerate
— the suite passes and the matrix shows the test against `AC-01`.

**Acceptance Scenarios**:

1. **Given** a test whose name and docstring contain no traced ID, **When** the suite is
   collected, **Then** collection fails and names the test.
2. **Given** a test citing an ID that is not defined in the specification — including the
   withdrawn `FR-03` — **When** the suite runs, **Then** it fails naming the test and the ID.
3. **Given** the committed matrix differs from what the current tests would produce, **When** the
   suite runs, **Then** it fails and states the command that regenerates it.
4. **Given** the matrix is current, **When** the owner opens it, **Then** every one of the 156
   defined IDs is listed with the tests that cite it, and IDs with no test yet are visibly marked.

---

### User Story 5 - The same checks run on every push (Priority: P3)

The owner wants the checks to run automatically on the public repository, on the pinned Python
version, so a gate never depends on the builder's machine.

**Why this priority**: valuable, but each check can already run locally; this phase's gate can be
reviewed from a local run while CI is first confirmed.

**Independent Test**: push the branch; the workflow runs setup, lint, format check and tests on
Python 3.12 and reports success.

**Acceptance Scenarios**:

1. **Given** a push to any branch, **When** CI runs, **Then** it performs exactly the checks of the
   local check command, from the lock file, on Python 3.12.
2. **Given** a failing check, **When** CI runs, **Then** the run is marked failed.

---

### Edge Cases

- **The system interpreter is 3.14.** The lock and environment must not drift to it; the pinned
  version is downloaded if absent.
- **An ID appears only in the docstring, or only in the test name.** Either counts.
- **A parametrised test.** The ID on the function applies to every case.
- **A test cites several IDs.** It appears in the matrix row of each.
- **An ID is mentioned in prose but not defined.** Only a register table row in its owning
  document defines an ID — `AC`/`FR`/`NFR` in `requirements.md`, `EC` in `hld.md`, `V`/`W` in
  `schema.md`. A mention elsewhere does not.
- **An import inside a function, or `from x import y` syntax.** Both are checked; the rule is
  about what a module depends on, wherever the statement sits.
- **An import built at run time from a string.** Not detected; this is accepted as the limit of a
  static check and recorded as an assumption.
- **A protected directory is still empty.** The boundary checks pass trivially and must still
  run, so the first violating file is caught.
- **Guard-rail tests themselves.** They prove constitution rules rather than a requirement — see
  P0-R09.

## Requirements *(mandatory)*

### Functional Requirements

- **P0-R01**: The project MUST declare its dependencies in a single dependency file with a
  committed lock file, and MUST pin the Python version to 3.12.
- **P0-R02**: The project MUST provide one documented command that runs lint, format check and the
  full test suite, and exits non-zero if any fails.
- **P0-R03**: The repository MUST contain the module layout of `lld.md` §1 — `app.py`,
  `config.py`, `errors.py`, `validation.py`, and the `ui/`, `graph/`, `graph/nodes/`,
  `services/`, `models/`, `data/` and `tests/{unit,integration,fixtures}/` areas — as empty
  placeholders with no behaviour.
- **P0-R04**: The suite MUST fail when any module under `services/` imports the graph runtime, any
  LangChain package, the page framework, or a model-provider client.
- **P0-R05**: The suite MUST fail when any module under `services/` imports from `graph/`.
- **P0-R06**: The suite MUST fail when any module other than those under `ui/` and `app.py`
  imports the page framework.
- **P0-R07**: Each boundary failure MUST name the module, the line and the rule.
- **P0-R08**: `.streamlit/secrets.toml` and `.env` MUST be ignored by version control, and the
  suite MUST fail if a file with either name is tracked at any depth.
- **P0-R09**: Every test MUST cite at least one traced ID in its name or docstring; collection MUST
  fail otherwise. Traced IDs are the specification IDs `AC`, `FR`, `NFR`, `EC`, `V` and `W`, plus
  constitution IDs of the form `CONST-<principle>` for tests that enforce the constitution itself
  (e.g. `CONST-IV` for the import rules, `CONST-SECRETS` for the secrets rule).
- **P0-R10**: The suite MUST fail when a test cites a specification ID that is not defined as a
  register row in its owning document, or a `CONST-` ID that names no principle or rule in the
  constitution.
- **P0-R11**: A committed traceability matrix MUST list every defined specification ID with the
  tests that cite it, mark IDs with no test, and list `CONST-` IDs separately. It MUST be produced
  by a command, never edited by hand.
- **P0-R12**: The suite MUST fail when the committed matrix differs from what the command would
  produce now, and the failure MUST state the command to run.
- **P0-R13**: A CI workflow MUST run the same checks as P0-R02, from the lock file, on Python 3.12,
  on every push and pull request.
- **P0-R14**: Phase 0 MUST NOT add store data, service logic, model calls or page content.

### Key Entities

- **Traced ID**: an identifier a test can cite. Either a specification ID, defined by a register
  row in exactly one design document, or a constitution ID naming a principle or rule.
- **Test**: a collected test case. Cites one or more traced IDs through its name or docstring.
- **Traceability matrix**: a generated document mapping each traced ID to the tests that cite it.
  It is the owner's view of coverage at each gate.
- **Boundary rule**: a pair of (area, forbidden dependency) from constitution Principle IV.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **P0-SC1**: From a fresh clone, setup plus the full check completes with two documented
  commands and no manual step, in under 3 minutes on a typical laptop with network access.
- **P0-SC2**: For each of the three boundary rules and the secrets rule, a deliberately planted
  violation makes the check fail — 4 out of 4 — and removing it makes the check pass.
- **P0-SC3**: 100% of collected tests cite at least one valid traced ID.
- **P0-SC4**: The matrix lists all 156 specification IDs — 27 AC, 24 FR, 11 NFR, 47 EC, 42 V and
  5 W — and a stale matrix is caught on every run.
- **P0-SC5**: The first CI run after the branch is pushed is green on Python 3.12.

## Assumptions

- The constitution fixes the toolchain, so this spec names it where needed: Python 3.12, `uv`
  with `uv.lock`, `ruff`, `pytest` (with `hypothesis` available), and GitHub Actions for CI since
  the repository is on GitHub.
- The project is an application, not an installable library; the layout sits at the repository
  root as `lld.md` §1 draws it.
- Constitution Principle III currently lists `AC`, `FR`, `NFR`, `EC` and `V`. P0-R09 adds `W`
  (schema warnings, which Phase 1 will test) and `CONST-` IDs for guard-rail tests. This is a
  MINOR amendment (1.0.0 → 1.1.0) made in this phase, with `CLAUDE.md` updated in the same
  change, as the constitution's governance section requires.
- The boundary checks are static. An import assembled from a string at run time is not
  detected; the codebase has no reason to do that, and review covers it.
- "Model-provider client" means `langchain_groq`, `groq`, `openai` and `anthropic` at minimum.
- CI first runs when the owner pushes the branch. Until then, the gate is reviewed from a local
  run; pushing to the public remote is the owner's decision.
- No runtime dependencies (LangGraph, Streamlit, scipy, …) are added in this phase. Each is added
  by the phase that first uses it, so the lock only ever holds what is exercised.
