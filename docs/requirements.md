# Requirements Specification

**Project:** Multi-Floor Store Product Finder and Navigation Agent
**Version:** 1
Rendered: **https://claude.ai/artifact/3EX5yVGXaiUrGvMukseQbz** (private — share from the page's Share menu)

> **What this document is, and is not.** It states *what* the system must do and
> how each requirement will be shown to be met. It contains no architecture, no
> algorithms, no data schemas and no technology choices beyond the constraints
> in §3 — those belong in the HLD, the LLD and the Schema document.
>
> That separation is deliberate. A requirement that names a technique cannot be
> challenged without re-opening the design, and a design that hides inside a
> requirement never gets reviewed.

---

## 1. Overview

Shoppers in a large multi-floor store lose time hunting for products and cannot
tell from the shelf whether an item is stocked at that branch. This system takes
one or more typed product requests and returns, for each, whether it is
available, exactly where it sits, and the shortest walking route to reach it —
including floor changes.

It is built as an agentic system in which language models interpret and phrase,
and deterministic tools supply every fact. It must work on any store by
replacing the store data, with no code changes.

**In scope:** typed requests (single, several at once, natural language);
product matching against a store catalogue; availability from a mock inventory;
location to floor, aisle, rack and shelf; shortest route from any start point,
across floors; one combined route for several products; step-free routing; a
single-page user interface.

**Out of scope:** voice input; live shopper positioning (beacons, Wi-Fi, QR);
integration with any real inventory, planogram or mapping system; payments,
loyalty and recommendations; shelf-compliance detection from photographs; more
than one store running concurrently; colleague workflows — order picking,
replenishment, shelf-edge tasks.

**Inputs:** one store folder holding four kinds of data — the **store map**
(walkable points, paths between them, and the stairs, escalators and lifts
connecting floors), the **product catalogue**, the **planogram** (which product
sits on which shelf) and the **stock position**. File format and structure are
specified in the Schema document, not here — the map may take more than one
file, since a graph does not fit a single table.

**Done when:** a shopper's request returns the correct availability, the correct
location and a provably shortest route — including from a start point other than
the entrance, and across floors; every fact in every answer has been checked
against the store data before it is shown; and a second, differently shaped
store works with no code changes.

---

## 2. Users

| Actor | Needs | In scope |
|---|---|---|
| **Shopper** | Find one or several products quickly; know before walking whether it is worth the trip | Yes — the primary user |
| **Store colleague** | — | **No.** Not a user of this system. Colleague workflows are out of scope and not planned |
| **Store data owner** | Onboard a new store by supplying four files | Yes — FR-25 exists for this actor |

---

## 3. Constraints and assumptions

| ID | Constraint | Source |
|---|---|---|
| C-01 | Agentic framework is **LangGraph** | confirmed |
| C-02 | Implementation language is **Python** | confirmed |
| C-03 | User interface is a single **Streamlit** page | confirmed |
| C-04 | All store data is **synthetic** and is stated as such wherever shown | confirmed |
| C-05 | No integration with any live retailer system | confirmed |

| ID | Assumption | Status | If it later proves wrong |
|---|---|---|---|
| A-01 | Stock data is treated as current and correct; staleness is not modelled | confirmed | Availability needs a freshness indicator and an "unknown" state |
| A-02 | A product present in the planogram with non-zero stock counts as available | confirmed | — |
| A-03 | Demo store has **three floors**; the portability test store has two | confirmed | Floor count changes, and FR-17's ordering becomes more or less visible |
| A-04 | Catalogue of roughly 150–200 products is representative enough to demonstrate | confirmed | Search ranking needs re-tuning at real catalogue scale |
| A-05 | "Optimal" means shortest walking distance, not shortest time | confirmed | Edge weights become durations; floor transitions re-weighted |
| A-06 | The shopper uses the system as a **website in a mobile browser**, standing in the store. Nothing is installed | confirmed | An installed experience would change distribution, offline behaviour and device access |

**Why three floors costs almost nothing.** The catalogue and the planogram do
not grow with floor count. The same roughly 180 products still sit somewhere;
three floors simply spreads them across more aisles, so the row counts are
unchanged. Only the **map** grows — in the order of 150 walkable points to 220,
plus the extra paths and one more floor plate to draw.

Three floors is worth that, because it is the smallest store in which **FR-17**
is a real decision rather than a formality. With two floors, "visit the floors
in a fixed order, one pass each" reduces to "upstairs, then downstairs" — the
rule still has to be built, and still stops a shopper being sent up and down
repeatedly, but nothing in a demo shows whether it works.

The **portability store therefore has two floors**. What AC-09 proves is that
the store's shape lives in the data rather than the code, and a differently
shaped store proves that whether it is larger or smaller. Two floors is also the
cheaper second store to author.

---

## 4. Functional requirements

### 4.1 Search and request handling

| ID | Requirement | Status |
|---|---|---|
| FR-01 | A shopper can find a product by typing its name | confirmed |
| FR-02 | A shopper can request **several products in one search**, separated by commas, semicolons, new lines or the word "and", without first building a basket | confirmed |
| FR-03 | A shopper can find a product by entering its barcode | assumed |
| FR-04 | A request phrased in natural language resolves to real catalogue products — never to an invented one | confirmed |
| FR-05 | Where more than one product could match, the system **asks the shopper to choose** rather than selecting one | confirmed |
| FR-06 | Results are ordered so that products stocked at this store rank above products that are not | confirmed |

### 4.2 Availability

| ID | Requirement | Status |
|---|---|---|
| FR-07 | The system states whether each requested product is available | confirmed |
| FR-08 | "Not stocked at this branch" is distinguished from "stocked but sold out" — they are different answers to the shopper | confirmed |
| FR-09 | An unavailable product offers in-stock alternatives from the same category | assumed |

### 4.3 Location

| ID | Requirement | Status |
|---|---|---|
| FR-10 | Location is given as **floor, aisle, rack and shelf** | confirmed |
| FR-11 | A product held in more than one place shows all of them; routing uses the nearest | confirmed |
| FR-12 | A product with no self-service location — service counter, locked cabinet — is identified as such rather than given a shelf | assumed |

### 4.4 Routing

| ID | Requirement | Status |
|---|---|---|
| FR-13 | The system gives the **shortest walking route** from the shopper's position to the product | confirmed |
| FR-14 | A route may cross floors, using the lifts, escalators and stairs recorded in the store map | confirmed |
| FR-15 | The shopper sets their start point by selecting a floor and aisle; the entrance is only the default | confirmed |
| FR-16 | For several products the system gives **one combined route** visiting all of them, and lists any that are unavailable | confirmed |
| FR-17 | A combined route visits the floors in a fixed order, with one picking pass per floor | confirmed |
| FR-18 | A combined route ends at a checkout | confirmed |
| FR-19 | The shopper can request a **step-free route** that avoids stairs and escalators | confirmed |
| FR-20 | A route is presented both as step-by-step directions and drawn on a floor map | confirmed |

### 4.5 Basket

| ID | Requirement | Status |
|---|---|---|
| FR-21 | Results of a multi-product search are **grouped by availability, in-stock first** | confirmed |
| FR-22 | A **single action moves only the available items** into the basket | confirmed |
| FR-23 | The basket accumulates items across separate searches, and is what gets routed | confirmed |
| FR-24 | An unavailable item may be added to the basket individually, but is marked as not routable and left out of the route | confirmed |

### 4.6 Portability

| ID | Requirement | Status |
|---|---|---|
| FR-25 | A **different store works by replacing the four data files only** — no code changes, including a store with a different number of floors | confirmed |

---

## 5. Non-functional requirements

| ID | Area | Requirement |
|---|---|---|
| NFR-01 | Correctness | Availability, location, distance and directions are taken only from the store data. **No fact in any answer is generated by a language model.** |
| NFR-02 | Verification | Every factual claim in a response is checked against the store data **before it is shown**. A claim that fails the check is never displayed. |
| NFR-03 | Safety | No generated text asserts that a product is gluten free, nut free, vegan or halal. Such claims come only from a recorded product attribute, passed through unaltered. An unrecorded attribute reads as unknown, never as absent. |
| NFR-04 | Reliability | If a language model is unavailable, slow, or returns malformed output, the system still answers using deterministic rules. The answer may be less fluent; it is never less correct. |
| NFR-05 | Performance | Under **5 seconds** for one product; under **10 seconds** for ten products. |
| NFR-06 | Input safety | Empty, over-long, non-English, duplicated and deliberately malicious input is handled safely. Shopper text cannot alter which tools run, nor reach files or commands. |
| NFR-07 | Data integrity | Invalid or inconsistent store data is rejected when the store is loaded, not discovered during a shopper's request. |
| NFR-08 | Portability | A differently shaped store passes the same acceptance tests with no code changes. |
| NFR-09 | Explainability | Why a product ranked where it did, and why a route took the order it did, can both be explained without reference to a model. |
| NFR-10 | Accessibility | Step-free routing is available, and route directions are usable by a screen reader. |
| NFR-11 | Mobile layout | The interface is usable at phone width — roughly 390 px — in a mobile browser: no horizontal page scrolling, controls reachable one-handed, and the floor map legible without pinch-zoom. |

**NFR-02 is the one that shapes the system.** Requiring every claim to be
checked against the store data before display is stronger than requiring the
facts to come from tools. It means a verification step is part of the required
behaviour, not an implementation nicety — and it gives the whole design a
testable definition of "correct" rather than a promise.

---

## 6. Acceptance criteria

Each row is a test that can pass or fail. A requirement with no row here is not
finished being written.

| ID | Verifies | Passes when |
|---|---|---|
| AC-01 | FR-01, FR-07, FR-10 | A known product returns its recorded availability and its exact floor, aisle, rack and shelf |
| AC-02 | FR-02, FR-16 | "milk, bread, eggs" returns three separate results in one response, then one route covering all three |
| AC-03 | FR-05 | A deliberately ambiguous term returns a choice prompt, and the chosen option resolves without re-entering the other terms |
| AC-04 | FR-13 | The returned route distance equals the shortest distance computed independently from the store map for the same pair of points |
| AC-05 | FR-14, FR-17, FR-18 | A basket spanning all three floors returns a route that visits each floor once, in the specified order, ending at a checkout |
| AC-06 | FR-15 | The same product requested from two different start points returns two different, each-correct routes |
| AC-07 | FR-19 | A step-free request returns a route using no stairs or escalators; where none exists, it says so instead of returning one |
| AC-08 | FR-21, FR-22 | A search with three available and one unavailable item groups them, and the single action adds exactly three to the basket |
| AC-09 | FR-25, NFR-08 | A second store folder with a different floor count passes AC-01 to AC-08 with no code changes |
| AC-10 | NFR-01, NFR-02 | No location, distance or stock figure in any response differs from the store data; a deliberately corrupted claim is blocked before display |
| AC-11 | NFR-04 | With every model call forced to fail, each acceptance test above still returns a correct availability and a correct route |
| AC-12 | NFR-05 | Measured over repeated runs, one product completes inside 5 s and ten products inside 10 s |
| AC-13 | NFR-06 | Each hostile input in §7 is handled without an error page, a leaked file path, or a changed tool call |
| AC-14 | NFR-07 | Each malformed store fixture is rejected at load with a message naming the fault |
| AC-15 | NFR-11 | At a 390 px viewport the full journey completes with no horizontal page scroll, and the route on the floor map is legible without zooming |

**AC-11 is the test that earns the architecture.** It is the only one that
proves NFR-01 and NFR-04 rather than asserting them. If every model call can be
switched off and the system still returns the right aisle and the right route,
then the claim that models never supply facts is demonstrated. If it cannot, the
claim is decoration.

---

## 7. Situations the system must handle

Required behaviours, not solutions. Each becomes a test case.

**Input** — empty, one character, extremely long · misspelled ("paracetomol",
"yoghurt") · non-English text, emoji, punctuation only · many items at once,
duplicated items, quantities ("2 x milk") · text that is not a product request ·
text written to subvert the system's instructions.

**Matching** — synonyms and colloquial names ("coke", "nappies", "kitchen
roll") · several sizes or variants of the same product · a generic word that is
a category rather than a product ("milk", "dairy") · a product held in two
places at once · a product in the catalogue but absent from the planogram · a
product in the catalogue but not stocked at this branch.

**Start point** — the entrance; any other aisle; an unrecognised location ·
standing on a staircase, escalator or in a lift lobby · already standing at the
product.

**Routing** — same floor; different floor; every floor · a connector out of
service · step-free requested where no step-free path exists · a single item
submitted as a multi-product request · chilled and frozen items that should be
collected last.

**Several products** — spread across all floors · one unavailable; all
unavailable · one ambiguous while the others resolve cleanly · a list long
enough to need a cap.

**Data and system failures** — store map with an unreachable point, a missing
point, or duplicate identifiers · planogram referring to a product or a location
that does not exist · a model returning malformed output, or declining the
request · a tool failing or timing out · a wrong aisle or a wrong distance
caught before the shopper sees it · a shopper abandoning a choice prompt and
never returning.

---

## 8. Open questions

| ID | Question | Why it matters now |
|---|---|---|
| OQ-01 | **Confirm the intended user is a shopper.** | The whole specification assumes it. If the intended user is a store colleague, this document needs rewriting rather than extending — it is a different problem, not a later phase |
| OQ-02 | ~~Two floors or three in the demo store?~~ — **resolved: three**, with two for the portability store | Closed. Reasoning recorded in §3 |
| OQ-03 | ~~Which single-page framework?~~ — **resolved: Streamlit** | Closed. Recorded rather than deleted, with the consequences below |
| OQ-04 | Does FR-05 ask a question, or show a ranked list to tap? | A shopper on a phone may prefer tapping one of six breads to answering a question. Changes what gets built |
| OQ-05 | Is FR-09 wanted at all? | Substitutes are a commercial nice-to-have and the first thing to cut under time pressure |
| OQ-06 | Approved model platform, data residency, and whether shopper-facing generated text is permitted | May require the colleague-facing version first |
| OQ-07 | How are age-restricted and locked-cabinet products handled? (FR-12) | Needs an "ask a colleague" outcome rather than a route |
| OQ-08 | What number proves this worked? | Without a success metric the project has no finish line |

### OQ-03 resolved — Streamlit, calling the agent in-process

There is no HTTP layer. The page invokes the compiled agent directly in the same
process, which removes the whole API surface and roughly a day of plumbing. The
HLD's layer stack loses its API tier and the LLD's API contracts cease to exist.

**What this costs:** no other client can consume the system. That is an accepted
trade for a one-week proof of concept. Because the design keeps the
orchestration and service layers free of any web dependency, putting a service
in front of the same agent later changes nothing below the page.

**What this requires of the design** — detail belongs in the HLD and LLD, but
the decision carries three consequences worth recording here:

1. The page re-executes on every interaction, so the store graph, search index
   and distance matrices must be built **once and cached** rather than per
   interaction.
2. The clarification pause in FR-05 is served by **re-invoking the agent with
   the shopper's answer on the next page run**, not by a second HTTP call.
3. The search box must **commit on submit** rather than on each keystroke, or
   NFR-05's budget is spent re-running the agent while the shopper is still
   typing.

---

## 9. Glossary

| Term | Meaning |
|---|---|
| **SKU** | The store's unique code for one exact product, including size and variant |
| **Planogram** | The shelf-level layout plan: which product sits on which shelf. It records where a product is *supposed* to be, which is not the same as where it is |
| **Bay / rack** | One section of a shelving unit within an aisle. "Rack" is used throughout this document |
| **Facing** | One product's frontage on a shelf. A product may hold several adjacent facings |
| **Ranged** | Carried by this particular branch. A product can be in the catalogue without being ranged here |
| **Connector** | A lift, escalator or staircase joining two floors |
| **Step-free** | A route using no stairs and no escalators |

---

## 10. Differences from the peer specification

Recorded so they are resolved deliberately rather than discovered late. "Peer
spec" is the Multi-Floor Store Product Finder requirements dated 9 October 2026.

| Topic | Peer spec | This document | Why |
|---|---|---|---|
| **Location depth** | Floor, aisle, shelf | Floor, aisle, **rack**, shelf (FR-10) | Rack-level addressing was asked for directly. Without it an aisle is 20 m long and the distance is not honest |
| **Floors** | Two | Three, with two as the portability test (A-03) | Three is the smallest store in which FR-17 is a real decision. The two-floor store becomes the portability test, so the peer spec's shape is still covered |
| **Route terminus** | Not specified | Ends at a checkout (FR-18) | Confirmed separately. Makes it a complete shopping trip and places chilled items naturally last |
| **Floor order** | Not specified | Fixed, one pass per floor (FR-17) | Confirmed separately. A distance-only optimiser sends shoppers up and down repeatedly |
| **Basket** | Not present | FR-21 to FR-24 | Grouping results by availability and moving only the in-stock items means no route is ever planned to an empty shelf |
| **Front end** | Streamlit | Streamlit (C-03) | **Aligned.** An earlier choice here was a service plus a static page; settled in favour of Streamlit, so no HTTP layer exists |
| **Framework** | "Agentic", five named agents | LangGraph (C-01) | Named explicitly as a constraint. The agent decomposition is an HLD matter, not a requirement |
| **Verification** | A Verifier agent | NFR-02, a behaviour | **Adopted from the peer spec.** Stated as required behaviour so it can be tested, rather than as a component that might be dropped |
| **Step-free** | FR-8, confirmed | FR-19, confirmed | **Adopted.** It had been an open question here; it should not have been |
| **Portability** | FR-9 plus an NFR | FR-25 plus NFR-08 | **Adopted.** A requirement worth having, and AC-09 makes it testable |
| **Performance** | 5 s / 10 s | Same (NFR-05) | **Adopted.** Concrete targets beat "fast" |
| **Prompt injection** | Named in security | NFR-06 | **Adopted.** Shopper text reaches a model, so this is a real surface |
