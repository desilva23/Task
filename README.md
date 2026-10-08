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

## The short version

A user searches for a product and gets, in order: **is it in stock here**,
**where is it**, **how do I get to it**.

Four upstream systems are required — product catalogue, stock, planogram
location data, and store floor layout. The pathfinding is the easy part
(A* for one product, TSP for a list). The data availability and data accuracy
are the project.

**Start by asking:** is the user a shopper or a store colleague; does
machine-readable planogram and floor-plan data exist; and how do we know where
the user is standing.
