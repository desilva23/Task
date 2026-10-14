# Feature Specification: Stock Alerts (Phase 11)

**Branch**: none — committed to `main` (owner's rule, 2026-10-14) · **Created**: 2026-10-14

**Input**: "I just need an alert to the store manager if the stock is very low, then another
alert once out of stock, by mail — we can use AgentMail." The rest of the colleague workflows
stay out of scope. Proven by AC-29.

## User Scenarios

1. **Given** a stock update that takes one product to 5 or fewer and another to 0, **Then** the
   manager gets one low-stock and one out-of-stock email, naming each product, units left and
   shelf (AC-29).
2. **Given** a product that stays low, recovers, or is not stocked here, **Then** nothing is sent
   (EC-56, EC-57); low → out sends only the out alert (EC-55).
3. **Given** alerts being switched on, **Then** one email lists everything already low, one
   everything out.
4. **Given** missing settings or a failing mail service, **Then** the job fails visibly and
   sends nothing, or sends once on re-run (EC-58, EC-59).

## Requirements

- **P11-R01**: `services/stock_alerts.py` — pure: `changes(before, after)`, `emails(...)`.
- **P11-R02**: `notify/run.py` — the job; `notify/mail.py` — AgentMail and dry-run senders.
- **P11-R03**: `.github/workflows/stock-alerts.yml` — on stock pushes to `main`, and by hand.
- **P11-R04**: Secrets only in GitHub; `agentmail` only in the `alerts` dependency group.

## Assumptions

- Stock changes arrive as new versions of `stock.csv` (A-08). A live feed would run the same
  comparison per update.
- One threshold for every product (`LOW_STOCK_UNITS = 5`), one recipient, one email per kind
  per update — the owner's recommended defaults.
