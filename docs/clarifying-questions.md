# Clarifying Questions for the Stakeholder

Ordered by how much the answer changes the design. The P0 questions are
genuinely blocking — you cannot size or architect this without them. Each one
says *why* it matters, so you can explain yourself if asked.

---

## P0 — Blocking. Ask these first.

### 1. Who is the user: a shopper, or a store colleague?
*Why it matters:* a customer "find it in store" feature and a colleague
pick-path tool share a data layer but have different UX, different accuracy
requirements, and a completely different optimisation problem (single
destination vs. sequencing 40–80 stops). Colleague tools also don't need
consumer-grade indoor positioning, which removes the hardest part of the build.

### 2. Where does the planogram / location data come from, and in what form?
*Why it matters:* nothing works without it. Specifically:
- Which system of record? (Blue Yonder / Spaceman / Relex / in-house?)
- Is there an API, or is it a nightly file/extract?
- What is the granularity — aisle only, or aisle → bay → shelf → facing?
- Is it per-store, or per store *cluster* with stores deviating in practice?

*If the answer is "we don't have it yet"* then the first phase of this project
is a location data model and a way to populate it, and navigation is phase 2.
That changes the plan completely, so establish it now.

### 3. How is the store floor layout represented today?
*Why it matters:* this determines whether pathfinding is a two-day job or a
two-month job.
- A navigable graph (nodes + edges) → pathfinding is straightforward.
- Coordinates / CAD / DWG floor plans → needs a conversion pipeline to a graph.
- Only a PDF or a JPEG of the store map → someone has to digitise every store
  by hand. For ~600+ Sainsbury's stores that is a programme in itself.

Ask explicitly: **does a machine-readable store layout exist, for how many
stores, and who owns it?**

### 4. How do we know where the user is standing?
*Why it matters:* "optimal path" is meaningless without a start point. Options,
cheapest first:
- Assume the entrance (works, ships immediately, mediocre UX)
- User taps their current aisle on a map
- Scan a QR code on the aisle marker (cheap, surprisingly effective)
- BLE beacons / Wi-Fi RTT / UWB (real indoor positioning, real cost, real
  hardware rollout per store)

**Recommendation to put forward:** start with entrance + QR aisle markers. It
delivers 80% of the value with zero hardware. Treat beacons as a later phase.

### 5. What does "availability" mean, and how fresh is it?
*Why it matters:* this is where the product loses user trust fastest.
- Source system for stock? Real-time or batch?
- Is it *shelf* stock or *total* store stock (including back-room)? Telling a
  shopper something is available when it's on a pallet in the warehouse is
  worse than saying nothing.
- What refresh latency is acceptable — minutes, hours, overnight?
- Do we show a number ("3 left"), a band ("low stock"), or a boolean?

**Suggest:** show a band, not a number. Exact counts are almost always wrong
and invite complaints.

### 6. One product, or a whole shopping list?
*Why it matters:* single product = shortest path (Dijkstra/A*, trivial).
A list = a Travelling Salesman Problem over the store graph, with extra
constraints (chilled last, heavy items first, one-way aisles). Completely
different engineering effort. Do not let this be ambiguous.

---

## P1 — Needed before detailed design.

### 7. How many stores, and how different are they?
Every store having its own layout and its own planogram deviations is the normal
case in UK grocery (a Local vs. a Superstore vs. a Hybrid are nothing alike).
Ask: pilot in one store, or multi-store from day one? Multi-store means store
layout becomes a managed, versioned data asset with an ownership model.

### 8. What happens when a product is in more than one place?
Very common and frequently forgotten: a SKU sits in its home planogram bay
*and* on a promotional end cap, a seasonal gondola, a front-of-store dump bin,
and the meal-deal chiller. Does the system show all locations, the nearest one,
or the one most likely to be stocked? This affects the data model (one-to-many
SKU→location), not just the UI.

### 9. How does search work — and what do people actually type?
Real queries are "coke", "nappies size 4", "that gluten free bread",
"paracetomol" (misspelled). Ask:
- Is there an existing product search service to reuse, or are we building one?
- Do we need synonyms, misspelling tolerance, brand vs. generic, category
  browse as well as search?
- Barcode scan as an input?

### 10. How is location data kept correct over time?
Shelves get re-set — typically on a seasonal or quarterly range change, and
ad hoc for promotions. Ask:
- When a planogram changes, how and when does our data update?
- Who is accountable when the data is wrong?
- Do we need a "report wrong location" feedback loop from users? (Strongly
  recommend one — it is the cheapest data-quality mechanism available.)

### 11. Does the route include the checkout, or the entrance/exit flow?
And are there constraints to respect: one-way aisles, staff-only areas,
step-free routes for accessibility, trolley-width restrictions, locked
cabinets (spirits, baby formula) that require a colleague?

### 12. What does "optimal" mean to them?
Shortest distance? Fastest time? Fewest turns? Least congested? Avoiding the
pick-path of other colleagues? Get a definition, because it becomes the
objective function.

---

## P2 — Worth raising to show you've thought ahead.

13. **Out of stock behaviour** — do we offer substitutes / alternatives, or
    just say no? Suggesting a substitute turns a dead end into a sale.
14. **Connectivity** — in-store mobile signal is often poor, especially in
    chilled aisles and basements. Does this need to work offline, with a cached
    store map and planogram?
15. **Accessibility** — screen reader support, step-free routing, high
    contrast. For a UK retailer this is a legal consideration, not a nice-to-have.
16. **Channel** — native app, mobile web, in-store kiosk, colleague handheld
    device, or several? Affects positioning options and effort significantly.
17. **Scale and SLA** — expected searches/second at peak (Saturday lunchtime),
    target response time. Pathfinding on a precomputed graph is fast; be sure
    nobody expects per-request route recomputation at 10k rps without caching.
18. **Success metric** — what number proves this worked? Reduced "where is X"
    colleague interruptions? Basket size? Pick rate (items/hour)? Without this
    the project has no finish line.
19. **Personalisation / loyalty** — is Nectar data or purchase history in play,
    e.g. "your usual" or a route built from a reorder list?
20. **Is this build or buy?** Products exist in this space (Dor Technologies,
    Pointr, Oriient, Mapsted, Aisle411 historically). Worth asking whether a
    vendor evaluation has already happened or is expected.

---

## The one-paragraph version to open with

> My understanding is this is a planogram-driven product locator: a user
> searches for a product, sees whether it's in stock in that store, sees its
> aisle/bay/shelf location, and gets the optimal route to it. Before I design
> anything I need four things pinned down. First, is the user a shopper or a
> store colleague — because a colleague picking a 60-item online order is a
> route-sequencing problem, not a shortest-path one. Second, where does the
> planogram location data come from, at what granularity, and via API or file.
> Third, does a machine-readable store floor layout exist, and for how many
> stores, or do we need to digitise it. Fourth, how do we establish the user's
> starting position — my recommendation is to assume the entrance and add QR
> codes on aisle markers before we consider any beacon hardware. I also need to
> know whether "available" means shelf stock or total store stock, and how
> stale that figure is allowed to be.

That covers the real unknowns and signals that you understand where the
difficulty actually sits.
