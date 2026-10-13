# Research: Project Scaffold and Guard Rails (Phase 0)

No item in the Technical Context was left as NEEDS CLARIFICATION — the constitution fixes the
toolchain. These are the design decisions the plan rests on.

## R1. Project shape: an application, not a package

- **Decision**: a uv project with `[tool.uv] package = false`, `requires-python = "==3.12.*"`,
  and a `.python-version` file reading `3.12`. Code sits at the repository root as `lld.md` §1
  draws it; pytest gets the root on its path through `pythonpath = ["."]`.
- **Rationale**: Streamlit Community Cloud runs `app.py` from the repository root and installs
  from `uv.lock`. Nothing is published to an index, so a build backend and `src/` layout add
  nothing. The pinned version stops uv choosing the machine's 3.14.
- **Alternatives**: `src/` layout with a build backend — rejected, no install target exists;
  `requirements.txt` — rejected, the constitution names one dependency file and `uv.lock`.

## R2. One check command

- **Decision**: `scripts/check.sh` runs, in order and stopping at the first failure,
  `ruff check .`, `ruff format --check .` and `pytest`, each through `uv run --locked`. CI calls
  the same script.
- **Rationale**: uv has no task runner. A script is the smallest thing that makes local and CI
  identical by construction — there is one list of checks, not two.
- **Alternatives**: a Makefile — rejected, an extra tool for three lines; a pytest-ruff plugin —
  rejected, a dependency to save one line, and lint failures would read as test failures.

## R3. Import boundary check

- **Decision**: a small `ast`-based checker in `tests/guards/imports.py`. It walks every `.py`
  file, reads every `import` and `from … import` node (at any depth, so imports inside functions
  count), and checks them against a table of three rules taken from constitution Principle IV.
  A violation reports `path:line rule-name: module`.
- **Rationale**: the rules are three lines of table; the checker is about forty lines with no
  dependency, and its message names the line (P0-R07). It is tested against planted violations
  in a temporary directory, so it is proven to catch each rule (P0-SC2) before it is trusted on
  the real tree.
- **Alternatives**: `import-linter` — rejected, a dependency and a config language for three
  rules, and its contracts are about packages, not "any file outside `ui/`".
- **Forbidden for `services/`**: `langgraph`, `langchain` and every `langchain_*`, `streamlit`,
  `groq`, `openai`, `anthropic`, and `graph`.

## R4. Secret-file check

- **Decision**: `tests/guards/secret_files.py` lists tracked files with `git ls-files -z` and
  flags any whose base name is `.env` or `secrets.toml`. If git is unavailable or the directory
  is not a work tree, the test **fails** with that reason rather than skipping.
- **Rationale**: matching on base name catches the file at any depth (spec edge case) and leaves
  `.env.example` alone. A skip would turn "could not check" into a silent pass.
- **Alternatives**: a pre-commit hook — rejected as the only layer, because hooks are local and
  optional; the suite runs in CI regardless.

## R5. Traceability: citing, validating, collecting

- **Decision**:
  - **Citing.** A test cites IDs in its docstring as written in the documents (`AC-01`,
    `CONST-IV`) or in its name in snake form (`test_ac_01_…`, `test_const_iv_…`). A test in a
    class also inherits IDs from the class docstring.
  - **Defined IDs.** Parsed from register rows — a markdown table row whose first cell is the
    ID: `AC`/`FR`/`NFR` from `docs/requirements.md`, `EC` from `docs/hld.md`, `V`/`W` from
    `docs/schema.md`. `CONST-` IDs are the principle numerals `I`–`VII` plus `SECRETS`, read
    from the constitution's headings so a renamed principle cannot pass silently.
  - **Enforcement.** A pytest plugin (`tests/guards/trace_plugin.py`, loaded from the root
    `conftest.py`) runs at collection. Any test with no ID, or with an undefined ID, fails
    collection with a list of offenders. Collection-time failure means a bad test can never
    run "green".
  - **The matrix.** `scripts/trace_matrix.py` runs `pytest --collect-only` with the plugin in a
    reporting mode, and writes `docs/traceability.md`. With `--check` it writes nothing and exits
    non-zero if the file would change, naming the command to run. A test calls it with `--check`.
- **Rationale**: generated, never edited, and checked on every run, so the matrix cannot drift
  — the same lesson as the LLD page that fell two versions behind its markdown. Reading the
  register rows (not any mention) is what rejects `FR-03`, which is withdrawn.
- **Alternatives**: pytest markers (`@pytest.mark.trace("AC-01")`) — rejected, easy to forget and
  invisible in a failing test's name; a hand-kept matrix — rejected, it drifts.

## R6. CI

- **Decision**: one GitHub Actions workflow, `.github/workflows/check.yml`, on `push` and
  `pull_request`: `actions/checkout`, `astral-sh/setup-uv`, `uv sync --locked`,
  `scripts/check.sh`. The Python version comes from `.python-version`; nothing else selects one.
  Action versions are pinned to a major tag and confirmed at implementation time.
- **Rationale**: the same script as local, the same lock, the same interpreter.
- **Alternatives**: a matrix over Python versions — rejected, only 3.12 is supported.

## R7. Dependencies added in this phase

- **Decision**: development group only — `pytest`, `hypothesis`, `ruff`. No runtime dependency.
- **Rationale**: each runtime library is added by the phase that first exercises it, so the lock
  never holds untested code (constitution Principle III).

## R8. Constitution amendment 1.0.0 → 1.1.0

- **Decision**: extend Principle III's list of citable IDs with `W-` and `CONST-<principle>`, and
  update `CLAUDE.md` in the same change.
- **Rationale**: a guard-rail test proves a constitution rule, not a requirement; forcing it to
  cite an unrelated NFR would make the matrix lie. Schema warnings get tested in Phase 1. Adding
  citable IDs materially expands guidance, so the bump is MINOR.
