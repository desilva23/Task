# Quickstart: verifying the Phase 0 gate

**Prerequisites**: `uv` installed. Python 3.12 does not need to be installed — uv downloads it.

## 1. Set up and check

```bash
uv sync --locked
scripts/check.sh
```

Expect: three steps pass. `uv run python --version` prints `Python 3.12.x`.

## 2. Read the matrix

Open `docs/traceability.md`. Expect 156 specification rows, almost all marked `—` (no test yet —
later phases fill them), and the `CONST` section showing `CONST-IV` and `CONST-SECRETS` covered.

## 3. Prove each guard bites (optional — the suite already does this with planted files)

| Plant | Expect from `scripts/check.sh` |
|---|---|
| `import streamlit` in `services/__init__.py` | fails: `services/__init__.py:1 services-no-runtime: streamlit` |
| `from graph import nodes` in `services/__init__.py` | fails: `services-not-graph` |
| `import streamlit` in `config.py` | fails: `streamlit-only-in-ui` |
| `touch .env && git add -f .env` | fails naming `.env` (then `git rm --cached .env`) |
| a test with no ID in name or docstring | collection fails: `Untraced test: …` |
| a test whose docstring says `FR-03` | collection fails: `Unknown ID FR-03` |
| add a traced test without regenerating | fails: `docs/traceability.md is stale — run: …` |

Undo each plant before the next.

## 4. CI

After the owner pushes the branch, the **check** workflow runs on GitHub and should be green.
