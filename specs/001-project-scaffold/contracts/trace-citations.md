# Contract: how a test cites the specification

Every collected test cites at least one ID, or collection fails.

```python
def test_ac_01_exact_name_returns_match():          # cited in the name
    ...

def test_exact_name_returns_match():
    """AC-01, FR-01 — an exact product name is found."""   # cited in the docstring
    ...

class TestBoundaries:
    """CONST-IV — one-way imports."""                 # applies to every test below
    def test_services_clean(self): ...
```

Valid kinds: `AC`, `FR`, `NFR`, `EC`, `V`, `W` (two-digit numbers, as the documents write them)
and `CONST-<I…VII|SECRETS>`. An ID must be defined as a register row in its owning document —
see [data-model.md](../data-model.md).

**Collection failure output** lists each offender on its own line:

```
Untraced test: tests/unit/test_x.py::test_something — cite an ID in its name or docstring
Unknown ID FR-03 cited by tests/unit/test_y.py::test_barcode
```
