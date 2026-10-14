"""Regenerate docs/pages/locator-hld.html from docs/hld.md. Run from the repository root.

The four drawn figures live in docs/pages/figures/; each takes the place of its section's ASCII
sketch, or follows the section's text."""

import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).parent))
from pagegen import write  # noqa: E402

FIGURES = {
    "## 2. System layers": ("hld-layers", "replace"),
    "### 3.2 Several products in one search": ("hld-query-shape", "end"),
    "### 3.3 Checking availability for all of them at once": ("hld-batch-sequence", "end"),
    "### 3.4 Batch results and the basket gate": ("hld-basket-gate", "replace"),
}
HEADER = """
<header class="prose">
  <div class="eyebrow">High-level design · proof of concept</div>
  <h1>Product Locator HLD</h1>
  <p class="standfirst">In-store product search, availability, location and optimal routing across a three-floor store, orchestrated with LangGraph behind a stateless API and served as a Next.js page on Vercel.</p>
  <div class="meta">
    <span><b>Requirements</b> in the specification, not here</span>
    <span><b>Scope</b> one store, synthetic data</span>
    <span><b>Stack</b> LangGraph · Python · FastAPI · Next.js · Vercel</span>
  </div>
</header>
"""
FOOTER = """
<footer>
  High-level design · proof of concept · one store, synthetic data · companion documents: Requirements, LLD, Schema
</footer>
"""

write(
    "docs/pages/locator-hld.html", pathlib.Path("docs/hld.md").read_text(), HEADER, FOOTER, FIGURES
)
