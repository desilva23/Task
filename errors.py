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
