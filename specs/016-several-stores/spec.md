# Feature Specification: Several Stores (Phase 15)

**Branch**: none — committed to `main` (owner's rule, 2026-10-14) · **Created**: 2026-10-16

**Input**: "I need another store of synthetic data with five floors, so I can switch the store to
show this is scalable for all the stores." "More than one store running concurrently" had been
out of scope; the owner's request brings it in as FR-31. Proven by AC-36, and AC-01 to AC-08 on
every store.

## User Scenarios

1. **Given** the page, **When** the shopper taps the store name, **Then** "Which store?" lists
   Demo Superstore (3 floors), City Flagship (5) and Portability Test Store (2).
2. **Given** City Flagship chosen, **Then** the start point offers floors 0–4, "everyday
   shampoo" is on floor 3, and a route for dog food, shampoo and bananas clears floor 4 first and
   ends at a till (AC-36).
3. **Given** a basket in the demo store, **When** the shopper switches store and back, **Then**
   each store has its own basket and start point (EC-75).
4. **Given** an unknown store id, **Then** it is refused, never answered from another store
   (EC-74). **Given** a new folder under `data/`, **Then** it appears with no code change (EC-76).

## Requirements

- **P15-R01**: `datagen/variant.py` — one builder for "the demo catalogue in another building";
  the portability store and `datagen/city.py` are specs of it. The portability output is
  byte-for-byte unchanged.
- **P15-R02**: `data/SBY-CITY-003/` — generated, five floors, 36 aisles, its own shelf quantities.
- **P15-R03**: `api/index.py` — every store folder served; `store` on every request; per-store
  cached services; `stores` for the switcher.
- **P15-R04**: the page — store name in the header, "Which store?" sheet, basket and start point
  kept per store, floor buttons for any number of floors.
