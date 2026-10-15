"use client";

// FR-23 — the basket accumulates across searches and is what gets routed. It lives in the page
// (the server keeps nothing between requests) and survives a refresh in session storage.

export type Item = { sku: string; label: string };

export default function Basket({
  items,
  onRemove,
  onPlan,
  busy,
}: {
  items: Item[];
  onRemove: (sku: string) => void;
  onPlan: () => void;
  busy: boolean;
}) {
  return (
    <section className="pane-body basket" aria-label="Basket">
      <h2>Basket ({items.length})</h2>
      {items.length ? (
        <ul className="lines">
          {items.map((i) => (
            <li key={i.sku}>
              <span>{i.label}</span>
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
          here for one route.
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
