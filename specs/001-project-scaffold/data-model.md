# Data Model: Project Scaffold and Guard Rails (Phase 0)

No store data exists in this phase. These are the entities the guard rails reason about.

## TracedId

| Field | Meaning |
|---|---|
| `kind` | `AC`, `FR`, `NFR`, `EC`, `V`, `W` or `CONST` |
| `id` | canonical text — `AC-01`, `CONST-IV`, `CONST-SECRETS` |
| `source` | the document that defines it |

**Rules**
- A specification ID is defined only by a register row: a markdown table row whose first cell is
  the ID (bold allowed). A mention in prose does not define it — this is what rejects `FR-03`.
- Owning documents: `AC`/`FR`/`NFR` → `docs/requirements.md`; `EC` → `docs/hld.md`;
  `V`/`W` → `docs/schema.md`; `CONST` → `.specify/memory/constitution.md`.
- `CONST-` IDs are the numerals of the `### <numeral>.` principle headings, plus `SECRETS` for the
  bold **Secrets.** rule.
- Expected totals at the time of writing: 27 AC, 24 FR, 11 NFR, 47 EC, 42 V, 5 W = 156, plus
  8 CONST.

## Citation

A test's link to one or more TracedIds.

| Found in | Form | Example |
|---|---|---|
| test docstring | as written in the document | `"""AC-01 — exact name returns a match."""` |
| class docstring | as written; applies to every test in the class | `"""CONST-IV boundary rules."""` |
| test name | snake form, case-insensitive | `test_ac_01_exact_name`, `test_const_iv_services_clean` |

**Rules**: at least one citation per collected test; every cited ID must exist. A parametrised
test's citations apply to each case; the matrix lists the function once.

## TraceabilityMatrix

A generated markdown file, `docs/traceability.md`. One section per kind in the order
AC, FR, NFR, EC, V, W, CONST; one row per defined ID; the tests citing it as `file::function`
in sorted order, or `—` when none. A header line gives the count covered per kind. It contains no
timestamp, so regenerating an unchanged suite produces an identical file.

## BoundaryRule

| Rule name | Applies to | Forbidden |
|---|---|---|
| `services-no-runtime` | files under `services/` | `langgraph`, `langchain`, `langchain_*`, `streamlit`, `groq`, `openai`, `anthropic` |
| `services-not-graph` | files under `services/` | `graph` and anything below it |
| `streamlit-only-in-ui` | every `.py` file except under `ui/` and `app.py` | `streamlit` |

A module matches a forbidden name when it equals it or starts with it followed by a dot
(`langchain_groq` matches `langchain_*`; `graphviz` does not match `graph`). Relative imports
are resolved first, so `from .storegraph import …` in `services/` is `services.storegraph` and
passes, while `from .. import graph` climbs out and is caught. `tests/`, `scripts/`, `.venv/` and
`.specify/` are not scanned.

## Violation

`path:line rule-name: imported-module` — one line per offending import statement.
