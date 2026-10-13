"""Collection-time traceability (constitution Principle III).

Every collected test must cite at least one defined ID — in its docstring as the documents
write it (``AC-01``, ``CONST-IV``), in its name in snake form (``test_ac_01_…``), or through its
class or module docstring. Collection fails otherwise, so a test that proves nothing can never run green.

With ``--trace-report=PATH`` the citations are written as JSON for ``scripts/trace_matrix.py``.
"""

import json
import re
from pathlib import Path

import pytest

from tests.guards.spec_ids import defined_ids

REPO = Path(__file__).resolve().parents[2]

DOC_SPEC = re.compile(r"\b(AC|FR|NFR|C|A|EC|V|W)-(\d{2})\b")
DOC_CONST = re.compile(r"\bCONST-(SECRETS|[IVX]+)\b")
NAME_SPEC = re.compile(r"(?:^|_)(ac|fr|nfr|c|a|ec|v|w)_(\d{2})(?=_|$)", re.I)
NAME_CONST = re.compile(r"(?:^|_)const_(secrets|[ivx]+)(?=_|$)", re.I)


def citations(item: pytest.Item) -> list[str]:
    name = getattr(item, "originalname", item.name)
    found = {f"{k.upper()}-{n}" for k, n in NAME_SPEC.findall(name)}
    found |= {f"CONST-{c.upper()}" for c in NAME_CONST.findall(name)}
    owners = ("function", "cls", "module")  # a class or module docstring covers its tests
    for owner in (getattr(item, o, None) for o in owners):
        doc = getattr(owner, "__doc__", None) or ""
        found |= {f"{k}-{n}" for k, n in DOC_SPEC.findall(doc)}
        found |= {f"CONST-{c}" for c in DOC_CONST.findall(doc)}
    return sorted(found)


def function_id(item: pytest.Item) -> str:
    return item.nodeid.split("[", 1)[0]  # one entry per function, not per parameter


def pytest_addoption(parser):
    parser.addoption("--trace-report", default=None, help="write test → cited IDs as JSON")


def pytest_collection_modifyitems(session, config, items):
    known = defined_ids(REPO)
    report, errors = {}, []
    for item in items:
        cited = citations(item)
        name = function_id(item)
        if not cited:
            errors.append(f"Untraced test: {name} — cite an ID in its name or docstring")
        errors += [f"Unknown ID {i} cited by {name}" for i in cited if i not in known]
        report[name] = cited
    if errors:
        raise pytest.UsageError("\n".join(dict.fromkeys(errors)))
    path = config.getoption("--trace-report")
    if path:
        Path(path).write_text(json.dumps(report, indent=1, sort_keys=True) + "\n")
