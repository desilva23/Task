# Contract: the check command

```
scripts/check.sh
```

- Runs, in order, each through `uv run --locked`: `ruff check .`, `ruff format --check .`,
  `pytest`.
- Stops at the first failing step and exits with that step's non-zero status.
- Exits 0 only if all three pass.
- Takes no arguments. Extra pytest options are passed by running pytest directly.
- `--locked` makes a stale `uv.lock` an error rather than a silent re-resolve.
- CI runs exactly this script, after `uv sync --locked`.
