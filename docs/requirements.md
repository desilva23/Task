# Requirements Specification

**Project:** Multi-Floor Store Product Finder and Navigation Agent
**Version:** 1
Rendered: **https://claude.ai/artifact/3EX5yVGXaiUrGvMukseQbz** (private — share from the page's Share menu)

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
barcode scanning with the phone camera; product matching against a store catalogue; availability from a mock inventory;
location to floor, aisle, rack and shelf; shortest route from any start point,
across floors; one combined route for several products; step-free routing;
a single-page user interface.

**Out of scope:** voice input; live shopper positioning (beacons, Wi-Fi, QR);
integration with any real inventory, planogram or mapping system; payments,
loyalty and recommendations; shelf-compliance detection from photographs;
recognising a product from a photograph — the camera reads a barcode and
nothing else;
more than one store running concurrently; colleague workflows — order picking,
replenishment, shelf-edge tasks.

**Inputs:** one store folder holding four kinds of data — the **store map**
(walkable points, paths between them, and the stairs and lifts connecting
floors), the **product catalogue**, the **planogram** (which product
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
| **Shopper** | Find one or several products quickly; know before walking whether it is worth the trip | Yes |
| **Store colleague** | — | No |
| **Store data owner** | Onboard a new store by supplying its data files | Yes |

---

## 3. Constraints and assumptions

| ID | Constraint | Source |
|---|---|---|
| C-01 | Agentic framework is **LangGraph** | confirmed |
| C-02 | Implementation language is **Python** | confirmed |
| C-03 | User interface is a single **Streamlit** page | confirmed |
| C-04 | All store data is **synthetic**, and each store's files declare it | confirmed |
| C-05 | No integration with any live retailer system | confirmed |
| C-06 | Language models are served through **GroqCloud** | confirmed |
| C-07 | The application is deployed on **Streamlit Community Cloud** | confirmed |
| C-08 | The site is served over **HTTPS**. Camera access requires a secure context, so FR-03's camera does not work over plain HTTP, including on a local machine addressed by IP | confirmed |

| ID | Assumption | Status | If it later proves wrong |
|---|---|---|---|
| A-01 | Stock data is treated as current and correct; staleness is not modelled | confirmed | Availability needs a freshness indicator and an "unknown" state |
| A-02 | A product present in the planogram with non-zero stock counts as available | confirmed | — |
| A-03 | Demo store has **three floors**; the portability test store has two | confirmed | Floor count changes, and FR-17's ordering becomes more or less visible |
| A-04 | Catalogue of roughly 150–200 products is representative enough to demonstrate | confirmed | Search ranking needs re-tuning at real catalogue scale |
| A-05 | "Optimal" means shortest walking distance, not shortest time | confirmed | Edge weights become durations; floor transitions re-weighted |
| A-06 | The shopper uses the system as a **website in a mobile browser**, standing in the store. Nothing is installed | confirmed | An installed experience would change distribution, offline behaviour and device access |
| A-07 | The shopper's mobile browser can grant camera access and take a still photo the system can read an EAN-13 from. Where it cannot, FR-03 degrades to typed digits rather than failing | confirmed | Live decoding in the browser, which needs a custom component |

---

## 4. Functional requirements

### 4.1 Search and request handling

| ID | Requirement | Status |
|---|---|---|
| FR-01 | A shopper can find a product by typing its name | confirmed |
| FR-02 | A shopper can request **several products in one search**, separated by commas, semicolons, new lines or the word "and", without first building a basket | confirmed |
| FR-03 | A shopper can find a product by **scanning its barcode with the phone camera**. Where the camera is unavailable, unsupported or the shopper declines it, the same lookup is reachable by typing the digits | confirmed — withdrawn during review, reinstated by the owner 2026-10-14 |
| FR-04 | A request phrased in natural language resolves to real catalogue products — never to an invented one | confirmed |
| FR-05 | Where more than one product could match, the system **asks the shopper to choose** rather than selecting one | confirmed |
| FR-06 | Results are ordered so that products stocked at this store rank above products that are not | confirmed |

### 4.2 Availability

| ID | Requirement | Status |
|---|---|---|
| FR-07 | The system states whether each requested product is available | confirmed |
| FR-08 | "Not stocked at this branch" is distinguished from "stocked but sold out" — they are different answers to the shopper | confirmed |
| FR-09 | An unavailable product offers in-stock alternatives from the same category | confirmed |

### 4.3 Location

| ID | Requirement | Status |
|---|---|---|
| FR-10 | Location is given as **floor, aisle, rack and shelf** | confirmed |
| FR-11 | A product held in more than one place shows all of them; routing uses the nearest | confirmed |
| FR-12 | A product with no self-service location — service counter, locked cabinet — is identified as such rather than given a shelf | confirmed |

### 4.4 Routing

| ID | Requirement | Status |
|---|---|---|
| FR-13 | The system gives the **shortest walking route** from the shopper's position to the product | confirmed |
| FR-14 | A route may cross floors, using the **stairs and lifts** recorded in the store map | confirmed |
| FR-15 | The shopper sets their start point by selecting a floor and aisle; the entrance is only the default | confirmed |
| FR-16 | For several products the system gives **one combined route** visiting all of them, and lists any that are unavailable | confirmed |
| FR-17 | A combined route visits the floors in a fixed order, with one picking pass per floor | confirmed |
| FR-18 | A combined route ends at a checkout | confirmed |
| FR-19 | The shopper can request a **step-free route**, which crosses floors by lift and uses no stairs. Where no step-free path exists it says so rather than returning one with stairs in it | confirmed |
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
| FR-25 | A **different store works by replacing its data files only** — no code changes, including a store with a different number of floors | confirmed |

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
| AC-07 | FR-19 | A step-free request returns a route that uses lifts and no stairs, including across floors; where no step-free path exists it says so instead of returning one |
| AC-08 | FR-21, FR-22 | A search with three available and one unavailable item groups them, and the single action adds exactly three to the basket |
| AC-09 | FR-25, NFR-08 | A second store folder with a different floor count passes AC-01 to AC-08 with no code changes |
| AC-10 | NFR-01, NFR-02 | No location, distance or stock figure in any response differs from the store data; a deliberately corrupted claim is blocked before display |
| AC-11 | NFR-04 | With every model call forced to fail, each acceptance test above still returns a correct availability and a correct route |
| AC-12 | NFR-05 | Measured over repeated runs, one product completes inside 5 s and ten products inside 10 s |
| AC-13 | NFR-06 | Each hostile input in §7 is handled without an error page, a leaked file path, or a changed tool call |
| AC-14 | NFR-07 | Each malformed store fixture is rejected at load with a message naming the fault |
| AC-15 | NFR-11 | At a 390 px viewport the full journey completes with no horizontal page scroll, and the route on the floor map is legible without zooming |
| AC-16 | FR-12 | A counter product and a locked-cabinet product each return their counter or cabinet location with no shelf or facing value, and state that a colleague is required |
| AC-17 | FR-09 | An out-of-stock product returns at least one in-stock alternative from the same category; every candidate offered is itself in stock and compatible with the original's recorded dietary attributes; and where no compatible in-stock alternative exists it says so rather than offering an incompatible one |
| AC-18 | FR-04 | A natural-language request returns only SKUs present in `products.csv`; a model response carrying any field outside its schema — a product name, a SKU — is rejected before it can influence the result |
| AC-19 | FR-06 | For a term matching a ranged and an unranged product, the ranged one ranks first even when the unranged one has the higher text-match score |
| AC-20 | FR-08 | A product with `ranged=false` and a product with `ranged=true, shelf_qty=0` return different availability states, and the wording shown for each is different |
| AC-21 | FR-11 | A SKU with two placements returns both locations; from a start point nearer the second placement, the route targets the second |
| AC-22 | FR-20 | Every route is returned both as an ordered directions list and as a drawn floor-plate overlay, and the two describe the same sequence of points |
| AC-23 | FR-23 | Items added from three separate searches all appear in the basket, and the route planned from it visits every routable item regardless of which search added it |
| AC-24 | FR-24 | An out-of-stock item added individually appears in the basket marked not routable, is absent from the route, and its exclusion is stated in the output |
| AC-25 | NFR-03 | Across every response in the test suite, each mention of gluten free, nut free, vegan or halal corresponds to a product whose recorded attribute is `true`; a product with an empty attribute is shown as unknown and never described as having or lacking the property |
| AC-26 | NFR-09 | With every model call disabled, each ranked result's position is explained by the first ranking rule separating it from its neighbour, and each route's stop order is reproduced from its node path alone |
| AC-27 | NFR-10 | Read as plain text with the floor map removed, the directions list names every stop's floor, aisle, rack and shelf and every floor change; a step-free request also passes AC-07 |
| AC-28 | FR-03 | A scan of a catalogued product's barcode returns that exact product, with no choice prompt; with the camera declined, typing the same digits returns the same product; and a barcode that is valid but not in the catalogue says so rather than returning a nearest match |

---

## 7. Situations the system must handle

Required behaviours, not solutions. Each becomes a test case.

**Input** — empty, one character, extremely long · misspelled ("paracetomol",
"yoghurt") · non-English text, emoji, punctuation only · many items at once,
duplicated items, quantities ("2 x milk") · text that is not a product request ·
text written to subvert the system's instructions.

**Barcode scan** — camera permission declined, or revoked after one successful
scan · a browser with no camera · a damaged, creased or partly obscured barcode
that will not decode · a barcode decoded correctly but absent from this
catalogue · a barcode from something that is not a grocery product at all ·
mistyped digits · the page opened over plain HTTP, where the camera cannot
start.

**Matching** — synonyms and colloquial names ("coke", "nappies", "kitchen
roll") · several sizes or variants of the same product · a generic word that is
a category rather than a product ("milk", "dairy") · a product held in two
places at once · a product in the catalogue but absent from the planogram · a
product in the catalogue but not stocked at this branch.

**Start point** — the entrance; any other aisle; an unrecognised location ·
standing on a staircase or in a lift lobby · already standing at the
product.

**Routing** — same floor; different floor; every floor · a connector out of
out of service · step-free requested where no step-free path exists · a single item
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

## 8. Glossary

| Term | Meaning |
|---|---|
| **SKU** | The store's unique code for one exact product, including size and variant |
| **Planogram** | The shelf-level layout plan: which product sits on which shelf. It records where a product is *supposed* to be, which is not the same as where it is |
| **Bay / rack** | One section of a shelving unit within an aisle. "Rack" is used throughout this document |
| **Facing** | One product's frontage on a shelf. A product may hold several adjacent facings |
| **Ranged** | Carried by this particular branch. A product can be in the catalogue without being ranged here |
| **Connector** | A staircase or a lift joining two floors |
| **Step-free** | A route using no stairs — between floors, one that travels by lift |
