import subprocess
import sys
from pathlib import Path

from tests.guards.spec_ids import defined_ids

REPO = Path(__file__).resolve().parents[2]
SCRIPT = REPO / "scripts" / "trace_matrix.py"
MATRIX = REPO / "docs" / "traceability.md"


def trace_matrix(*args: str) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, str(SCRIPT), *args], cwd=REPO, capture_output=True, text=True
    )


class TestTraceabilityMatrix:
    """CONST-III — the committed matrix is generated, complete and never stale."""

    def test_the_committed_matrix_is_current(self):
        result = trace_matrix("--check")
        assert result.returncode == 0, result.stdout + result.stderr

    def test_rendering_twice_gives_identical_output(self):
        first, second = trace_matrix("--stdout"), trace_matrix("--stdout")
        assert first.returncode == 0, first.stderr
        assert first.stdout == second.stdout

    def test_every_defined_id_has_a_row(self):
        text = MATRIX.read_text()
        missing = [i for i in defined_ids(REPO) if f"| {i} |" not in text]
        assert missing == []
