"""Which IDs exist. A specification ID is defined only by a register row — a markdown table
row whose first cell is the ID — in the one document that owns its kind. A mention in prose
defines nothing, so a withdrawn requirement stops being citable the moment its row goes."""

import re
from pathlib import Path

OWNERS = {
    "docs/requirements.md": ("AC", "FR", "NFR", "C", "A"),
    "docs/hld.md": ("EC",),
    "docs/schema.md": ("V", "W"),
}
CONSTITUTION = ".specify/memory/constitution.md"

ROW = re.compile(r"^\|\s*\**([A-Z]+-\d+)\**\s*\|", re.M)
PRINCIPLE = re.compile(r"^### ([IVX]+)\. ", re.M)
SECRETS_RULE = "**Secrets.**"


def defined_ids(root: Path) -> dict[str, str]:
    """Every citable ID mapped to the document that defines it."""
    ids = {}
    for doc, kinds in OWNERS.items():
        text = (root / doc).read_text()
        for found in ROW.findall(text):
            if found.split("-")[0] in kinds:
                ids[found] = doc
    text = (root / CONSTITUTION).read_text()
    for numeral in PRINCIPLE.findall(text):
        ids[f"CONST-{numeral}"] = CONSTITUTION
    if SECRETS_RULE in text:
        ids["CONST-SECRETS"] = CONSTITUTION
    return ids
