# Quickstart: verifying the Phase 1 gate

```bash
uv sync --locked
scripts/check.sh                                   # everything, including all V- and W-tests
uv run python -m datagen --out /tmp/demo-check     # regenerate elsewhere
diff -r /tmp/demo-check data/SBY-DEMO-001          # expect no output
```

Load it by hand:

```bash
uv run python -c "from pathlib import Path; from validation import load_store; \
s = load_store(Path('data/SBY-DEMO-001')); print(len(s.products), len(s.nodes), s.warnings)"
```

Expect `180 314` and one warning, W-02 for Sparkling Water Lime 1l.

Break it on purpose: copy the folder, change one SKU in `products.csv` to begin with `0`, load the
copy — expect `products.csv row N: V-20 — …`.

In `docs/traceability.md`, every V- and W- row now lists its test, and AC-14 lists the refusal
tests.
