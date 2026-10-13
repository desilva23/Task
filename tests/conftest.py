"""Store fixtures: the demo store generated once, copied per test, and mutated in one place.

Every refusal test is a known-good store with exactly one fault — AC-14's "malformed store
fixture" — so there are no hand-kept fixture folders to drift.
"""

import csv
import io
import shutil
from pathlib import Path

import pytest

from datagen.build import STORE_ID, write_store
from errors import StoreDataError
from validation import load_store


class StoreFolder:
    def __init__(self, path: Path):
        self.path = path

    def rows(self, name: str) -> list[dict[str, str]]:
        return list(csv.DictReader(io.StringIO((self.path / name).read_text())))

    def header(self, name: str) -> list[str]:
        return (self.path / name).read_text().splitlines()[0].split(",")

    def write(self, name: str, rows: list[dict[str, str]], header: list[str] | None = None):
        out = io.StringIO()
        writer = csv.DictWriter(out, fieldnames=header or self.header(name), lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)
        (self.path / name).write_text(out.getvalue())

    def edit(self, file: str, where: dict[str, str], **changes: str) -> int:
        """Change the first row matching ``where``; return its line number (header = 1)."""
        rows = self.rows(file)
        for i, row in enumerate(rows):
            if all(row[k] == v for k, v in where.items()):
                row.update(changes)
                self.write(file, rows)
                return i + 2
        raise AssertionError(f"no row in {file} matches {where}")

    def edit_all(self, file: str, where: dict[str, str], **changes: str) -> None:
        rows = self.rows(file)
        hits = [r for r in rows if all(r[k] == v for k, v in where.items())]
        assert hits, f"no row in {file} matches {where}"
        for row in hits:
            row.update(changes)
        self.write(file, rows)

    def add(self, name: str, row: dict[str, str]) -> int:
        rows = self.rows(name)
        rows.append({k: row.get(k, "") for k in self.header(name)})
        self.write(name, rows)
        return len(rows) + 1

    def drop(self, name: str, where: dict[str, str]) -> None:
        rows = self.rows(name)
        kept = [r for r in rows if not all(r[k] == v for k, v in where.items())]
        assert len(kept) < len(rows), f"no row in {name} matches {where}"
        self.write(name, kept)

    def load(self):
        return load_store(self.path)

    def refusal(self) -> StoreDataError:
        with pytest.raises(StoreDataError) as caught:
            self.load()
        return caught.value

    def assert_refused(self, rule: str, file: str, row: int | None = None) -> StoreDataError:
        err = self.refusal()
        hits = [f for f in err.faults if f.rule == rule and f.file == file]
        assert hits, f"expected {rule} in {file}; got:\n{err}"
        if row is not None:
            assert row in {f.row for f in hits}, f"expected {rule} at {file} row {row}:\n{err}"
        return err


@pytest.fixture(scope="session")
def demo_folder(tmp_path_factory) -> Path:
    folder = tmp_path_factory.mktemp("generated") / STORE_ID
    write_store(folder)
    return folder


@pytest.fixture
def store(demo_folder, tmp_path) -> StoreFolder:
    copy = tmp_path / STORE_ID
    shutil.copytree(demo_folder, copy)
    return StoreFolder(copy)
