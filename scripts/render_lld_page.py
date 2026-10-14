"""Regenerate docs/pages/locator-lld.html from docs/lld.md. Run from the repository root."""

import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).parent))
from pagegen import write  # noqa: E402

HEADER = """
<header class="prose">
  <div class="eyebrow">Low-level design · proof of concept</div>
  <h1>Product Locator LLD</h1>
  <p class="standfirst">Module layout, graph state, node contracts, algorithms and thresholds for the in-store product finder. Read after the HLD; the data formats live in the Schema document.</p>
  <div class="meta">
    <span><b>Stack</b> Python · LangGraph · FastAPI · Next.js · Vercel</span>
    <span><b>Nodes</b> 11, of which 3 call a model</span>
    <span><b>Interface</b> a Next.js page over a stateless API</span>
  </div>
</header>
"""
FOOTER = """
<footer>
  Low-level design · proof of concept · companion documents: Requirements, HLD, Schema
</footer>
"""

write("docs/pages/locator-lld.html", pathlib.Path("docs/lld.md").read_text(), HEADER, FOOTER)
