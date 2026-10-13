# Contract: the traceability matrix

```
uv run python scripts/trace_matrix.py          # regenerate docs/traceability.md
uv run python scripts/trace_matrix.py --check  # exit 1 if it would change; write nothing
uv run python scripts/trace_matrix.py --stdout # print it; write nothing
```

- Collects the suite without running it, then writes the matrix described in
  [data-model.md](../data-model.md#traceabilitymatrix).
- Deterministic: same tests and same documents → byte-identical file.
- `--check` failure message: `docs/traceability.md is stale — run: uv run python scripts/trace_matrix.py`.
- The test `tests/unit/test_traceability_matrix.py` runs `--check`, so a stale matrix fails the
  suite.
