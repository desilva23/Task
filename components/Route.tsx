"use client";

// FR-20 — the route twice: the directions list, which is the accessible route (NFR-10), and the
// same route drawn on one floor plate per floor (AC-22).

import { useState } from "react";

import type { RouteView } from "@/lib/api";

export default function Route({ route }: { route: RouteView }) {
  const [shown, setShown] = useState(0);
  if (route.kind === "none") {
    return (
      <section className="route">
        <h2>Your route</h2>
        <p className="callout warn">{route.message}</p>
      </section>
    );
  }
  const plate = route.plates[Math.min(shown, route.plates.length - 1)];
  return (
    <section className="route">
      <h2>Your route</h2>
      <ol className="directions">
        {route.directions.map((line, i) => (
          <li key={i}>{line}</li>
        ))}
      </ol>
      {route.excluded.length > 0 && (
        <ul className="statements">
          {route.excluded.map((m) => (
            <li key={m}>{m}</li>
          ))}
        </ul>
      )}
      {route.why && <p className="caption">{route.why}</p>}
      {route.plates.length > 0 && (
        <div className="plates">
          <div className="tabs" role="tablist" aria-label="Floor plans">
            {route.plates.map((p, i) => (
              <button
                key={p.level}
                type="button"
                role="tab"
                aria-selected={p === plate}
                className={p === plate ? "tab on" : "tab"}
                onClick={() => setShown(i)}
              >
                Floor {p.level}
              </button>
            ))}
          </div>
          {/* SVG drawn by the server from validated map data, with no free text in it (AC-13);
              everything else on the page is rendered as text, never as markup. */}
          <div className="plate" role="tabpanel" aria-label={`Floor ${plate.level} — ${plate.name}`}
               dangerouslySetInnerHTML={{ __html: plate.svg }} />
        </div>
      )}
    </section>
  );
}
