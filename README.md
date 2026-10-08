# Planogram-Based Product Locator — Discovery Notes

Pre-build discovery for the in-store product search / location / navigation use
case (Sainsbury's as the reference retailer).

Nothing here is a commitment to a design. The purpose is to go into the
stakeholder conversation with a clear understanding, the right questions, and a
straw man to react to.

## Contents

| Document | Purpose |
|---|---|
| [`docs/use-case-understanding.md`](docs/use-case-understanding.md) | What a planogram is, the use case restated, and the two very different products hiding behind it |
| [`docs/clarifying-questions.md`](docs/clarifying-questions.md) | Questions for the stakeholder, prioritised P0/P1/P2, each with why it matters |
| [`docs/solution-sketch.md`](docs/solution-sketch.md) | Straw-man data model, store graph, algorithms, phasing and risks |
| [`docs/genai-opportunities.md`](docs/genai-opportunities.md) | Where Gen AI genuinely fits, where it must not be used, the grounded tool-use architecture, and the guardrails |

## The short version

A user searches for a product and gets, in order: **is it in stock here**,
**where is it**, **how do I get to it**.

Four upstream systems are required — product catalogue, stock, planogram
location data, and store floor layout. The data availability and data accuracy
are the project; the routing is the easy part, and mostly needs less algorithm
than expected — see the tiered answer in `solution-sketch.md`.

**Start by asking:** is the user a shopper or a store colleague; does
machine-readable planogram and floor-plan data exist; and how do we know where
the user is standing.

**On Gen AI:** it belongs in two specific places — understanding how people
actually phrase a search, and detecting where the shelf no longer matches the
planogram. It does not belong anywhere near computing a route or asserting
where a product is. The model interprets and explains; the systems of record
supply every fact.
