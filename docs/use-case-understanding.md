# Planogram-Based Product Locator — Use Case Understanding

> **Historical — written before the build (2026-10-08), kept for its reasoning.** Its domain background still holds; its scoping now lives in the requirements. The current design is [`requirements.md`](requirements.md), [`hld.md`](hld.md), [`lld.md`](lld.md) and [`schema.md`](schema.md); what was built is in `specs/` and the code.

> Background on the domain. The build itself is scoped in
> `proposed-scope.md` — one store, synthetic data, one week. This document
> exists so the POC's design decisions are informed rather than arbitrary, and
> so the real-build implications can be answered if asked.

## 1. What a planogram actually is

A **planogram** is the shelf-level layout plan for a store: for every bay, shelf
and facing, which SKU sits there, how many facings it gets, and in what order.
It is a *merchandising* artefact — it exists so that stores can be set up
consistently and so that space can be sold to suppliers. It is produced by
space-planning tools (JDA/Blue Yonder Space Planning, Nielsen Spaceman,
Relex, Symphony RetailAI are the common ones in UK grocery).

Crucially: a planogram says **where a product is *supposed* to be**. It does not
say whether the product is physically there. That gap doesn't bite a POC with
synthetic data, but in a real deployment it is the single biggest source of
risk, and it drives most of the questions in `clarifying-questions.md`.

## 2. The use case as described

A shopper (or a colleague) searches for a product in a given store and gets,
in this order:

1. **Availability** — is it in stock in *this* store right now?
2. **Location** — where is it? (aisle / bay / shelf / facing)
3. **Route** — what is the optimal path from where they are to the product?

Example shape of the answer:

```
Search: "coca cola 500ml"

  Coca-Cola Classic 500ml                         £1.65
  ✅ In stock  (shelf stock: ~14)
  📍 Aisle 7  ·  Bay 3  ·  Shelf 2 (eye level)
  ➕ Also on promotion: Front-of-store end cap A2

  Route from your position (Entrance):
    Entrance → Main aisle → Aisle 7 (enter from front) → Bay 3
    ~45 m  ·  ~1 min walk
```

## 3. The three capabilities, decomposed

| Step | What it needs | Where it comes from |
|---|---|---|
| Search | Product catalogue + search index + synonym/typo handling | Product Master / PIM |
| Availability | Per-store stock position | Inventory / Stock service |
| Location | Planogram → store-specific location of a SKU | Space planning system |
| Route | Store floor layout as a navigable graph + a start position | Store layout / mapping |

Each of those four is a **separate upstream system** in a retailer the size of
Sainsbury's — which is exactly why the POC synthesises all four. In a real
build the work is mostly *integration and modelling*, not algorithms: the
routing is close to free (see the tiered answer in `solution-sketch.md`), and
the data is the hard part.

## 4. Two very different products hide behind the same description

This is the distinction that most changes the design, and it has to be settled
first:

**(a) Customer-facing "find it in store"**
- Goal: reduce shopper frustration, drive conversion.
- One product at a time, or a shopping list.
- Accuracy tolerance: "aisle 7" is good enough; being one bay out is fine.
- Hard part: indoor positioning for the shopper, and a UI that works on a
  phone with poor in-store signal.

**(b) Colleague-facing pick / replenishment tool**
- Goal: cut seconds per pick for online-order picking or shelf replenishment.
- Always a *multi-item list* (a customer order, or a replenishment run).
- Accuracy tolerance: much tighter — shelf and facing level matters.
- Hard part: route *sequencing* across 40–80 items, trolley constraints,
  chilled/frozen items last, crush order (don't put bananas under bleach).

These share a data layer but almost nothing in the UX or the optimisation
problem. (b) is where retailers usually get the ROI; (a) is where the demo
looks good — which, for a one-week POC, is the right trade. **The POC assumes
(a).** Confirm it, because if the real target is (b) the optimisation problem
changes completely.

## 5. Scope map — what "planogram" might also include

If the stakeholder said "planogram", the programme may be bigger than
navigation. Typical planogram-domain capabilities:

- Planogram authoring / space planning
- Planogram **compliance** (is the shelf set up as planned? usually image
  recognition on shelf photos)
- Range and assortment management per store cluster
- Space productivity analytics (sales per linear metre)
- Shelf-edge label generation
- **Product locator / in-store navigation ← what has been described**
- Gap / out-of-shelf detection

Navigation is a *consumer* of planogram data, not planogram management itself.
Worth confirming which of these is in scope, because "we own the planogram
system" and "we consume planogram data" are wildly different sized projects.
The POC consumes; it does not manage.
