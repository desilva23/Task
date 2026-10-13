# Feature Specification: GroqCloud in the Three Model Nodes (Phase 6)

**Feature Branch**: none — `claude/planogram-store-navigation-czn7bh` · **Created**: 2026-10-13 ·
**Status**: Draft

**Input**: "Phase 6 — GroqCloud in the three model nodes; re-verify model IDs first. Proven by
AC-17, AC-25, NFR-04."

IDs here are local (`P6-…`).

**Re-verified 2026-10-13** (constitution technology table): `openai/gpt-oss-20b` and
`openai/gpt-oss-120b` are Production models on GroqCloud and support strict structured output;
strict mode requires every property in `required` and `additionalProperties: false`; structured
outputs support neither streaming nor tool use. Sources: console.groq.com/docs/structured-outputs,
console.groq.com/docs/models. LangChain's `with_structured_output(strict=True)` is reported broken
for gpt-oss (langchain#34155), so the request is sent directly.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - The real model, safely (Priority: P1)

The three model nodes call GroqCloud through the Phase 5 adapter: gpt-oss-20b to read sentences
and reword directions, gpt-oss-120b to choose a substitute. Every reply is schema-constrained by
Groq and validated again by our code.

**Acceptance Scenarios**:
1. **Given** a task, **Then** the request uses the configured model for it, strict `json_schema`
   output, the system prompt as instructions and the shopper's text only as user data, the
   per-call token cap, and the timeout.
2. **Given** a session that has used its call budget, **Then** further calls fail fast and the
   deterministic fallbacks answer (public-deployment guard).
3. **Given** no API key, **Then** the app runs entirely on the fallbacks and says so.
4. **Given** the key, **Then** it is never logged, printed, or written anywhere but the local
   secrets file or the Cloud secrets field.

### User Story 2 - Failure costs fluency, never correctness (Priority: P1)

**Acceptance Scenarios**:
1. **Given** a timeout, a 4xx/5xx, a reply cut off at the token cap, or unparseable JSON, **Then**
   the node falls back, records it in `degraded`, and the journey's facts are unchanged (NFR-04).

### User Story 3 - Alternatives that are safe (Priority: P1)

**Acceptance Scenarios**:
1. **Given** a sold-out product with compatible in-stock alternatives in its category, **Then**
   at least one is offered, and every one offered is in stock and keeps each dietary property the
   original is recorded to have, adding no allergen (AC-17, FR-09).
2. **Given** none exists, **Then** the answer says so and offers nothing incompatible (AC-17).
3. **Given** every sold-out and unranged product in the demo store, **Then** the above holds for
   all of them.

### User Story 4 - No dietary claim is ever invented (Priority: P1)

**Acceptance Scenarios**:
1. **Given** every response produced across the test suite's journeys, **Then** each mention of
   gluten free, nut free, vegan, vegetarian or halal belongs to a product whose recorded
   attribute is `true` — or is an explicit status line where an unrecorded attribute reads
   "not recorded", never yes or no (AC-25, NFR-03).
2. **Given** a model rewording that adds or drops a dietary word, **Then** verify blocks it.
3. **Given** a shopper who asks for a dietary property, **Then** each product shown states its
   recorded status for it.

## Requirements *(mandatory)*

- **P6-R01**: `GroqClient` implements `ModelClient` with `langchain-groq`'s `ChatGroq`, sending
  `response_format={"type": "json_schema", "json_schema": {name, strict: true, schema}}`.
- **P6-R02**: The schema sent is derived from the pydantic model: every property required,
  `additionalProperties: false`, undocumented constraint keywords stripped; our validation then
  enforces the full model.
- **P6-R03**: Per-call `max_tokens`, `timeout`, no client retries, low reasoning effort; a
  per-session call budget; a truncated reply (`finish_reason == "length"`) is a failure.
- **P6-R04**: Every failure raises `ModelUnavailableError` to the node.
- **P6-R05**: The key comes from the environment (Streamlit exports top-level secrets) or, for
  local runs, `.streamlit/secrets.toml`; absent, the model is `NoModel`.
- **P6-R06**: `verify` treats dietary words as claims: a reworded line must name exactly the
  dietary words of the fact line it rewords.
- **P6-R07**: When the shopper asked for dietary properties, each statement adds the recorded
  status for each: yes, no, or not recorded.
- **P6-R08**: Live tests against GroqCloud are marked `live` and run on demand only — never in CI,
  which has no key.

## Success Criteria *(mandatory)*

- **P6-SC1**: AC-17 and AC-25 pass; NFR-04 failure modes each proven with a fake transport.
- **P6-SC2**: With the owner's key, the live suite passes: each model node returns a valid reply
  from GroqCloud and journeys verify.
- **P6-SC3**: A one-product journey with the live model completes inside NFR-05's 5 s.

## Assumptions

- `reasoning_effort="low"` suits these short tasks; recorded in `config.py` and checked by the
  live suite.
- `temperature=0`, which was a Claude-only trap, is fine on Groq and makes rewording repeatable.
- The per-session budget is per `GroqClient`; Phase 7 creates one per browser session.
