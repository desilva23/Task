"""The one-way import rules of constitution Principle IV, checked statically.

A violation reads ``path:line rule-name: module``. An import assembled from a string at run
time is not seen; the codebase has no reason to do that.
"""

import ast
from pathlib import Path

RUNTIME = ("langgraph", "langchain", "langchain_*", "streamlit", "groq", "openai", "anthropic")

SKIP_DIRS = {"tests", "scripts", "docs", "specs", "data", "notes", "__pycache__"}


def _in_services(rel: Path) -> bool:
    return rel.parts[0] == "services"


def _outside_ui(rel: Path) -> bool:
    return rel.parts[0] != "ui" and rel != Path("app.py")


# (rule name, which files it governs, forbidden module patterns)
RULES = [
    ("services-no-runtime", _in_services, RUNTIME),
    ("services-not-graph", _in_services, ("graph",)),
    ("streamlit-only-in-ui", _outside_ui, ("streamlit",)),
]


def _matches(module: str, pattern: str) -> bool:
    if pattern.endswith("_*"):
        return module.split(".")[0].startswith(pattern[:-1])
    return module == pattern or module.startswith(pattern + ".")


def _imported(tree: ast.AST, rel: Path):
    """Yield (line, [candidate module names]) for every import statement in the file."""
    package = list(rel.parts[:-1])  # what a level-1 relative import refers to
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                yield node.lineno, [alias.name]
        elif isinstance(node, ast.ImportFrom):
            if node.level:
                base = package[: len(package) - node.level + 1]
                stem = ".".join(base + ([node.module] if node.module else []))
            else:
                stem = node.module or ""
            names = [f"{stem}.{a.name}" if stem else a.name for a in node.names]
            yield node.lineno, ([stem] if stem else []) + names


def _files(root: Path):
    for path in sorted(root.rglob("*.py")):
        rel = path.relative_to(root)
        if any(part.startswith(".") or part in SKIP_DIRS for part in rel.parts[:-1]):
            continue
        yield rel, path


def find_violations(root: Path) -> list[str]:
    out = []
    for rel, path in _files(root):
        tree = ast.parse(path.read_text(), filename=str(rel))
        for line, candidates in sorted(_imported(tree, rel), key=lambda x: x[0]):
            for rule, governs, patterns in RULES:
                if not governs(rel):
                    continue
                hit = next(
                    (m for m in candidates for p in patterns if _matches(m, p)),
                    None,
                )
                if hit:
                    out.append(f"{rel.as_posix()}:{line} {rule}: {hit}")
                    break  # one line per offending statement — the first rule it breaks
    return out
