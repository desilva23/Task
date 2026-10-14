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
  if (!items.length) return null;
  return (
    <section className="basket" aria-label="Basket">
      <h2>Basket ({items.length})</h2>
      <p className="caption">Tap an item to remove it</p>
      <ul className="chips">
        {items.map((i) => (
          <li key={i.sku}>
            <button type="button" className="chip" onClick={() => onRemove(i.sku)} aria-label={`Remove ${i.label}`}>
              ✕ {i.label}
            </button>
          </li>
        ))}
      </ul>
      <button type="button" className="primary wide" onClick={onPlan} disabled={busy}>
        Plan my route
      </button>
    </section>
  );
}
