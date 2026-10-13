# Implementation Plan: Project Scaffold and Guard Rails (Phase 0)

**Branch**: `claude/planogram-store-navigation-czn7bh` (no feature branch) | **Date**: 2026-10-13 |
**Spec**: [spec.md](spec.md)

**Input**: Feature specification from `specs/001-project-scaffold/spec.md`

## Summary

Create an empty, reproducible Python 3.12 project in the `lld.md` §1 layout, with one check
command that runs lint, format and tests locally and in CI. The suite enforces the constitution
from the first commit: the three import boundaries, the secrets rule, and traceability — every
test cites a defined ID, and a generated matrix shows the owner which tests prove which ID.
Every check is built test-first, proven against planted violations before it is trusted on the
real tree.

## Technical Context

**Language/Version**: Python 3.12 (pinned; the machine default is 3.14)

**Primary Dependencies**: none at runtime in this phase. Development: `pytest`, `hypothesis`, `ruff`

**Storage**: files only — the generated matrix `docs/traceability.md`

**Testing**: pytest, with the built-in `pytester` fixture for testing the collection plugin

**Target Platform**: macOS for development; Linux for CI and Streamlit Community Cloud

**Project Type**: single application (one Streamlit page, later phases)

**Performance Goals**: full check under 30 s on an empty codebase; setup plus check under 3 min
on a fresh clone (P0-SC1)

**Constraints**: public repository — no secret is ever tracked; no runtime dependency added
before the phase that uses it

**Scale/Scope**: 156 specification IDs to trace; three boundary rules; one secrets rule

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | How this plan complies | Pass |
|---|---|---|
| I. Model never supplies a fact | No model code in this phase. The boundary rules that keep model clients out of `services/` are put in place here | ✅ |
| II. Unknown is not false | No data handling in this phase | ✅ n/a |
| III. Test-first, traced | Each guard is written as a failing test against a planted violation before the checker exists. Every test cites an ID, enforced at collection. Amendment 1.1.0 adds `W-` and `CONST-` IDs (research R8) | ✅ |
| IV. One-way imports | Implemented here, mechanically, as the principle requires | ✅ |
| V. Every model call has a fallback | No model calls | ✅ n/a |
| VI. Store loads completely or not at all | No store loading | ✅ n/a |
| VII. Proof-of-concept scale | Hand-rolled 40-line checkers over new dependencies; one script, no task runner; no runtime dependency | ✅ |
| Technology table | Python 3.12, uv + `uv.lock`, ruff, pytest + hypothesis — exactly as listed | ✅ |
| Secrets | `.gitignore` entries already committed; tracked-file test added here | ✅ |
| Gate | Phase ends at the owner's review; Phase 1 does not start before it | ✅ |

**Post-design re-check**: unchanged — the design adds no dependency, no runtime code and no
deviation. No entries in Complexity Tracking.

## Project Structure

### Documentation (this feature)

```text
specs/001-project-scaffold/
├── plan.md              # this file
├── research.md          # decisions R1–R8
├── data-model.md        # traced IDs, tests, matrix, boundary rules
├── quickstart.md        # how the owner verifies the gate
├── contracts/
│   ├── check-command.md     # scripts/check.sh behaviour
│   ├── trace-citations.md   # how a test cites an ID; what is valid
│   └── traceability-matrix.md  # scripts/trace_matrix.py and the file it writes
└── tasks.md             # /speckit-tasks output
```

### Source Code (repository root)

```text
pyproject.toml            uv project, package = false, Python ==3.12.*, ruff + pytest config
uv.lock
.python-version           3.12
conftest.py               loads tests.guards.trace_plugin
scripts/
  check.sh                ruff check · ruff format --check · pytest
  trace_matrix.py         writes / --check docs/traceability.md
.github/workflows/
  check.yml               uv sync --locked, then scripts/check.sh
docs/
  traceability.md         generated
app.py  config.py  errors.py  validation.py        empty placeholders (docstring only)
ui/__init__.py
graph/__init__.py   graph/nodes/__init__.py
services/__init__.py
models/__init__.py
data/.gitkeep
tests/
  __init__.py
  guards/
    __init__.py
    imports.py            boundary rules table + checker
    secret_files.py       tracked-secret finder
    spec_ids.py           register-row parser + CONST- IDs
    trace_plugin.py       collection-time citation check; matrix reporting mode
  unit/
    test_import_rules.py
    test_secret_files.py
    test_spec_ids.py
    test_trace_plugin.py
    test_traceability_matrix.py
  integration/__init__.py
  fixtures/.gitkeep
```

**Structure Decision**: the application layout of `lld.md` §1 at the repository root, unchanged.
The guard code lives under `tests/guards/` because it is test infrastructure: it must never be
imported by the application, and keeping it out of the application tree means the boundary
rules never have to exempt it.

## Complexity Tracking

No violations to justify.
