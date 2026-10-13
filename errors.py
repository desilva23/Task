"""Error taxonomy (lld.md §12). Phase 1 adds the one error that refuses to start."""

from dataclasses import dataclass


@dataclass(frozen=True)
class Fault:
    """One broken rule: which rule, in which file, on which line (``None`` for whole-file)."""

    rule: str
    file: str
    row: int | None
    message: str

    def __str__(self) -> str:
        where = f"{self.file} row {self.row}" if self.row is not None else self.file
        return f"{where}: {self.rule} — {self.message}"


class StoreDataError(Exception):
    """A store folder failed validation. It is never served half-loaded (NFR-07)."""

    def __init__(self, faults: list[Fault]):
        self.faults = faults
        super().__init__("\n".join(str(f) for f in faults))

    @property
    def rules(self) -> set[str]:
        return {f.rule for f in self.faults}


class InvalidNodeError(KeyError):
    """A node ID that is not in the open graph. The start picker is built from the graph, so
    this is a bug, not shopper input (lld.md §12)."""


class UnreachableNodeError(Exception):
    """No path between two open nodes. Impossible after V-70 — a data bug if seen (EC-29)."""

    def __init__(self, source: str, target: str):
        self.source, self.target = source, target
        super().__init__(f"no path from {source} to {target}")
