"use client";

// FR-15, FR-19 — where the shopper is, self-reported: floor, then a spot on it, the entrance by
// default; and the step-free switch. No positioning technology is used or implied.

import type { Store } from "@/lib/api";

export type Place = { level: number; node: string; stepFree: boolean };

export default function Where({
  store,
  place,
  onChange,
}: {
  store: Store;
  place: Place;
  onChange: (p: Place) => void;
}) {
  const floor = store.floors.find((f) => f.level === place.level) ?? store.floors[0];
  return (
    <section className="where" aria-label="Where you are">
      <label className="field">
        <span>Which floor are you on?</span>
        <select
          value={floor.level}
          onChange={(e) => {
            const next = store.floors.find((f) => f.level === Number(e.target.value)) ?? floor;
            onChange({ ...place, level: next.level, node: next.spots[0]?.node ?? store.entrance });
          }}
        >
          {store.floors.map((f) => (
            <option key={f.level} value={f.level}>
              Floor {f.level} — {f.name}
            </option>
          ))}
        </select>
      </label>
      <label className="field">
        <span>Where on that floor?</span>
        <select value={place.node} onChange={(e) => onChange({ ...place, node: e.target.value })}>
          {floor.spots.map((s) => (
            <option key={s.node} value={s.node}>
              {s.label}
            </option>
          ))}
        </select>
      </label>
      <label className="switch">
        <input
          type="checkbox"
          checked={place.stepFree}
          onChange={(e) => onChange({ ...place, stepFree: e.target.checked })}
        />
        <span>Step-free route (lifts, no stairs)</span>
      </label>
    </section>
  );
}
