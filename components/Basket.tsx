"use client";

// FR-23, FR-30 — the basket accumulates across searches and is what gets routed. It lives in the
// page (the server keeps nothing between requests), with how many of each the shopper wants,
// and is kept on this phone between visits until it is cleared.

export type Item = { sku: string; label: string; qty: number };

export const MAX_QTY = 99;

export default function Basket({
  items,
  onQty,
  onRemove,
  onClear,
  onPlan,
  busy,
}: {
  items: Item[];
  onQty: (sku: string, qty: number) => void;
  onRemove: (sku: string) => void;
  onClear: () => void;
  onPlan: () => void;
  busy: boolean;
}) {
  return (
    <section className="pane-body basket" aria-label="Basket">
      <div className="route-head">
        <h2>Basket ({items.length})</h2>
        {items.length > 0 && (
          <button type="button" className="link" onClick={onClear}>
            Clear basket
          </button>
        )}
      </div>
      {items.length ? (
        <ul className="lines">
          {items.map((i) => (
            <li key={i.sku}>
              <span className="grow">{i.label}</span>
              <span className="stepper" role="group" aria-label={`How many ${i.label}`}>
                <button
                  type="button"
                  className="secondary"
                  aria-label={`One fewer ${i.label}`}
                  disabled={i.qty <= 1}
                  onClick={() => onQty(i.sku, i.qty - 1)}
                >
                  −
                </button>
                <output aria-live="polite">{i.qty}</output>
                <button
                  type="button"
                  className="secondary"
                  aria-label={`One more ${i.label}`}
                  disabled={i.qty >= MAX_QTY}
                  onClick={() => onQty(i.sku, i.qty + 1)}
                >
                  +
                </button>
              </span>
              <button
                type="button"
                className="secondary"
                onClick={() => onRemove(i.sku)}
                aria-label={`Remove ${i.label}`}
              >
                ✕
              </button>
            </li>
          ))}
        </ul>
      ) : (
        <p className="empty">
          Nothing here yet. Search for products, then add the ones in stock — they&apos;re collected
          here for one route, and kept on this phone until you clear them.
        </p>
      )}
      <button
        type="button"
        className="primary wide"
        onClick={onPlan}
        disabled={busy || !items.length}
      >
        Plan my route
      </button>
    </section>
  );
}
