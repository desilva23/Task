"""Regenerate docs/pages/locator-requirements.html from docs/requirements.md. Run from the
repository root. The header's counts are read from the register rows, so they cannot go stale."""

import pathlib
import re
import sys

sys.path.insert(0, str(pathlib.Path(__file__).parent))
from pagegen import write  # noqa: E402

md = pathlib.Path("docs/requirements.md").read_text()
count = {k: len(set(re.findall(rf"^\| ({k}-\d+) \|", md, re.M))) for k in ("FR", "NFR", "C", "AC")}

HEADER = f"""
<header class="prose">
  <div class="eyebrow">Requirements specification · v1</div>
  <h1>Product Finder Requirements</h1>
  <p class="standfirst">Multi-floor store product finder and navigation agent. What the system must do, and how each requirement is verified.</p>
  <div class="meta">
    <span><b>Requirements</b> {count["FR"]} functional · {count["NFR"]} non-functional</span>
    <span><b>Constraints</b> {count["C"]}</span>
    <span><b>Acceptance criteria</b> {count["AC"]}</span>
  </div>
</header>
"""
FOOTER = f"""
<footer>
  Requirements specification · v1 · {count["FR"]} functional · {count["NFR"]} non-functional · {count["C"]} constraints · {count["AC"]} acceptance criteria · companion documents: HLD, LLD, Schema
</footer>
"""

write("docs/pages/locator-requirements.html", md, HEADER, FOOTER)
