# Feature Specification: Review Improvements (Phase 14)

**Branch**: none — committed to `main` (owner's rule, 2026-10-14) · **Created**: 2026-10-16

**Input**: the owner chose items 1–7 of the improvement list after the development-day review:
spoken lists without commas; "coke" landing on a sold-out product; spend limits; the current
step's pin; price and diet tags; quantities and a kept basket; weak in-store signal.

## User Scenarios

1. **Given** "milk bread chicken" spoken, **Then** three items are searched and the page says
   "Searched as: milk · bread · chicken", with one tap to search it as one item (AC-32).
   "chocolate milk", "free range eggs" are never cut (EC-68); "wheat bread" is not (EC-69).
2. **Given** "coke", **Then** the shopper is asked which — Classic, Zero or Diet (EC-70).
3. **Given** the public site, **Then** the owner sets a Groq spend limit and a Vercel rate limit
   of 60 API calls a minute per IP (steps in `docs/deploy.md`; the firewall could not be created
   through the API before it is opened once in the dashboard).
4. **Given** a route, **Then** the current step's pin pulses, and a tapped pin names its product
   and jumps to its step.
5. **Given** any result, **Then** it shows its price and only the dietary tags its record
   confirms (AC-33, EC-71).
6. **Given** "2 x baked beans", **Then** the basket holds 2, − and + change it, and it is kept on
   the phone between visits until cleared (AC-34).
7. **Given** no signal after one visit, **Then** the page, suggestions and basket work and a
   search says it needs a connection; the page installs to the home screen (AC-35, EC-72, EC-73).
