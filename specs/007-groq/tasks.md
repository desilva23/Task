---
description: "Task list for Phase 6 — GroqCloud"
---

# Tasks: GroqCloud (Phase 6)

- [X] T001 Re-verify Groq model IDs and strict-mode rules; record sources in spec.md
- [X] T002 Add `langchain-groq`; confirm `ChatGroq.invoke` forwards `response_format`
- [X] T003 Write failing `tests/unit/test_groq_client.py` (request shape, strict schema, caps, budget, every failure mode, key handling) and `tests/integration/test_substitutes_and_dietary.py` (AC-17, AC-25, verify dietary claims)
- [X] T004 Implement `graph/groq_client.py`, `graph/model_factory.py`; dietary claims in verify; dietary status in statements
- [X] T005 Write `tests/live/test_groq_live.py` (marked `live`); run it once the owner has added the key
- [X] T006 Regenerate the matrix; `scripts/check.sh` green; gate record

## Gate record (2026-10-14)

- `scripts/check.sh`: 297 passed (4 live deselected). AC-17, AC-25 and NFR-04 proven; CI green.
- **Live, against GroqCloud with the owner's key** (`uv run pytest -m live`): 4/4 pass —
  strict parse valid; one-product journey verified in 0.57 s with no mismatch (NFR-05);
  substitutes chosen from the safe list; a sentence reaches real products.
- Meaning-style queries with the live model: **5/6, none confidently wrong** (keyword search alone
  3/6). Answers the owner's semantic-search question with the model in place.
- Found live and fixed:
  1. gpt-oss invented category names ("pharmacy", "over the counter"). The understand schema now
     lists only this store's department and category names; Groq and our validation both reject
     anything else. Both fields accept any real name and the node files each correctly, because
     the model mixed department and category.
  2. "something for a headache" (4 words) never reached the model — `NL_WORD_THRESHOLD` 4 → 3.
  3. Intermittent live failures were Groq's free-tier limit — 8,000 tokens/minute on gpt-oss-20b
     — not a code fault; every 429 fell back correctly.
- Measured cost per call: understand ≈ 1,000 tokens, describe ≈ 360.
- Process note: the GroqClient tests were written first but first run after the module existed;
  red-before-green was then confirmed by removing the module (fails) and restoring it (passes).
- **Decision for the owner:** on the free tier the public app supports roughly 6–8 model-assisted
  searches a minute across all users; beyond that answers fall back (still correct, plainer).
  Options: accept that for the demo, or move the Groq account to a paid tier before deploying.
