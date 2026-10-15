from collections import Counter
from pathlib import Path

from tests.guards.spec_ids import defined_ids

REPO = Path(__file__).resolve().parents[2]


def fake_repo(root: Path, requirements="", hld="", schema="", constitution="") -> Path:
    for rel, text in [
        ("docs/requirements.md", requirements),
        ("docs/hld.md", hld),
        ("docs/schema.md", schema),
        (".specify/memory/constitution.md", constitution),
    ]:
        (root / rel).parent.mkdir(parents=True, exist_ok=True)
        (root / rel).write_text(text)
    return root


class TestSpecIds:
    """CONST-III — only IDs defined by a register row can be cited."""

    def test_the_real_documents_define_the_expected_totals(self):
        kinds = Counter(i.split("-")[0] for i in defined_ids(REPO))
        assert {k: kinds[k] for k in ("AC", "FR", "NFR", "C", "A", "EC", "V", "W")} == {
            "AC": 30,
            "FR": 27,
            "NFR": 11,
            "C": 9,
            "A": 9,
            "EC": 64,
            "V": 43,
            "W": 5,
        }

    def test_the_reinstated_fr_03_is_defined_by_its_row(self):
        """Withdrawn, then reinstated by the owner (2026-10-14) under the same ID."""
        ids = defined_ids(REPO)
        assert {"FR-01", "FR-02", "FR-03", "FR-04"} <= ids.keys()

    def test_each_id_records_its_owning_document(self):
        ids = defined_ids(REPO)
        assert ids["AC-01"] == "docs/requirements.md"
        assert ids["EC-38"] == "docs/hld.md"
        assert ids["V-01"] == "docs/schema.md"
        assert ids["CONST-IV"] == ".specify/memory/constitution.md"

    def test_constitution_ids_are_the_principles_and_the_secrets_rule(self):
        consts = sorted(i for i in defined_ids(REPO) if i.startswith("CONST-"))
        expected = ["I", "II", "III", "IV", "V", "VI", "VII", "SECRETS"]
        assert consts == sorted(f"CONST-{n}" for n in expected)

    def test_a_prose_mention_does_not_define_an_id(self, tmp_path):
        root = fake_repo(tmp_path, requirements="FR-07 is discussed here.\n| x | FR-08 |\n")
        assert defined_ids(root) == {}

    def test_a_first_cell_defines_it_bold_or_not(self, tmp_path):
        root = fake_repo(tmp_path, requirements="| FR-01 | a |\n| **NFR-02** | b |\n")
        assert defined_ids(root).keys() == {"FR-01", "NFR-02"}

    def test_an_id_counts_only_in_its_owning_document(self, tmp_path):
        root = fake_repo(tmp_path, requirements="| EC-01 | a |\n", hld="| AC-01 | b |\n")
        assert defined_ids(root) == {}

    def test_a_renamed_principle_heading_is_still_read_by_numeral(self, tmp_path):
        root = fake_repo(tmp_path, constitution="### II. Something New\n**Secrets.** text\n")
        assert defined_ids(root).keys() == {"CONST-II", "CONST-SECRETS"}
