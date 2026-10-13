# Contract: loader and generator

## `validation.load_store(folder: Path) -> Store`

- Returns a `Store` only when every refusal passes. `Store.warnings` is a tuple of `Fault`
  records whose `rule` is a W- ID.
- Otherwise raises `errors.StoreDataError`, whose `faults` is a list of `Fault(rule, file, row,
  message)` and whose `str()` is one line per fault:

```
products.csv row 14: V-20 — sku '0123456' must be 7 digits and not begin with 0
map_edges.csv: V-70 — graph is not strongly connected: F0-CTR-01 cannot be reached from F0-ENTRANCE
```

- `row` is the line number in the file (header = 1), or `None` for file- and graph-level faults.
- Typed values: three-state booleans are `True | False | None`; `allergens_contains` is `None`
  (unknown), `()` (`none`), or a tuple of names; lists are tuples; IDs are `str`.

## `python -m datagen [--seed N] [--out DIR]`

- Default seed `20261013`, default out `data/SBY-DEMO-001`.
- Overwrites the six files; writes nothing else. Deterministic for a seed.
