---
description: "Task list for Phase 6 — GroqCloud"
---

# Tasks: GroqCloud (Phase 6)

- [X] T001 Re-verify Groq model IDs and strict-mode rules; record sources in spec.md
- [X] T002 Add `langchain-groq`; confirm `ChatGroq.invoke` forwards `response_format`
- [X] T003 Write failing `tests/unit/test_groq_client.py` (request shape, strict schema, caps, budget, every failure mode, key handling) and `tests/integration/test_substitutes_and_dietary.py` (AC-17, AC-25, verify dietary claims)
- [X] T004 Implement `graph/groq_client.py`, `graph/model_factory.py`; dietary claims in verify; dietary status in statements
- [X] T005 Write `tests/live/test_groq_live.py` (marked `live`); run it once the owner has added the key
- [ ] T006 Regenerate the matrix; `scripts/check.sh` green; gate record
