"use client";

// FR-20 — the route twice: the directions, which are the accessible route (NFR-10), and the same
// route drawn on one floor plate per floor (AC-22). On one screen (NFR-11) the plate sits in its
// own frame, dragged like any map, and the directions are stepped through one at a time under
// it; each step shows its own floor. The whole list is one tap away, and is always in the page
// for a screen reader.

import { useEffect, useRef, useState } from "react";

import type { Pick, RouteView } from "@/lib/api";

const FLOOR = /floor (\d+)/gi;

/** The floor a step ends on — "Take the stairs up to floor 2" is on floor 2. */
function floorOf(step: string): number | null {
  const all = [...step.matchAll(FLOOR)];
  return all.length ? Number(all[all.length - 1][1]) : null;
}

export default function Route({ route, empty }: { route: RouteView | null; empty: string }) {
  const [step, setStep] = useState(0);
  const [shown, setShown] = useState(0);
  const [list, setList] = useState(false);
  const frame = useRef<HTMLDivElement>(null);

  const [tapped, setTapped] = useState<(Pick & { level: number }) | null>(null);

  const plates = route?.plates ?? [];
  const picks = plates.flatMap((p) => p.picks.map((k) => ({ ...k, level: p.level })));
  const line = route?.directions[step] ?? "";
  // The pin this step picks up: the step names the product (verified), or failing that its rack.
  const here = picks.find((k) => line.includes(k.label));
  useEffect(() => {
    const level = here ? here.level : floorOf(line);
    const i = plates.findIndex((p) => p.level === level);
    if (i >= 0) setShown(i);
  }, [here?.level, line, plates]); // eslint-disable-line react-hooks/exhaustive-deps
  // Open the map on this step's pin, pulsing — or the first pick on the floor, or the start —
  // rather than on the empty edge of the plan.
  useEffect(() => {
    const box = frame.current;
    if (!box) return;
    const at = /floor (\d+), aisle (\d+), rack (\d+)/i.exec(line);
    const node =
      here?.node ?? (at && `F${at[1]}-A${at[2].padStart(2, "0")}-R${at[3].padStart(2, "0")}`);
    box.querySelectorAll("[data-stop].current").forEach((el) => el.classList.remove("current"));
    const pin = node ? box.querySelector(`[data-stop][data-node="${node}"]`) : null;
    pin?.classList.add("current");
    const target = pin || box.querySelector("[data-stop]") || box.querySelector("[data-start]");
    if (!target) return;
    const t = target.getBoundingClientRect();
    const b = box.getBoundingClientRect();
    box.scrollTo({ top: box.scrollTop + t.top - b.top - box.clientHeight / 2, behavior: "smooth" });
  }, [here?.node, line, shown, list]); // eslint-disable-line react-hooks/exhaustive-deps

  if (!route) {
    return (
      <section className="pane-body route" aria-label="Route">
        <h2>Your route</h2>
        <p className="empty">{empty}</p>
      </section>
    );
  }
  if (route.kind === "none") {
    return (
      <section className="pane-body route" aria-label="Route">
        <h2>Your route</h2>
        <p className="callout warn">{route.message}</p>
      </section>
    );
  }
  const plate = plates[Math.min(shown, plates.length - 1)];
  const n = route.directions.length;
  const notes = [...route.excluded, ...(route.why ? [route.why] : [])];
  return (
    <section className="pane-body route" aria-label="Route">
      <div className="route-head">
        <h2>Your route</h2>
        {plates.length > 0 && (
          <div className="tabs" role="tablist" aria-label="Floor plans">
            {plates.map((p, i) => (
              <button
                key={p.level}
                type="button"
                role="tab"
                aria-selected={p === plate}
                className={p === plate ? "tab on" : "tab"}
                onClick={() => {
                  setShown(i);
                  setList(false);
                }}
              >
                Floor {p.level}
              </button>
            ))}
          </div>
        )}
      </div>

      {list || !plate ? (
        <ol className="directions frame">
          {route.directions.map((line, i) => (
            <li key={i} className={i === step ? "on" : undefined}>
              {line}
            </li>
          ))}
        </ol>
      ) : (
        // SVG drawn by the server from validated map data, with no free text in it (AC-13);
        // everything else on the page is rendered as text, never as markup.
        <div
          ref={frame}
          className="plate frame"
          role="tabpanel"
          aria-label={`Floor ${plate.level} — ${plate.name}`}
          dangerouslySetInnerHTML={{ __html: plate.svg }}
          onClick={(e) => {
            // a pin, or its line in the list under the plan: say what it is, go to its step
            const hit = (e.target as Element).closest("[data-stop], [data-pick]");
            const n = Number(hit?.getAttribute("data-stop") ?? hit?.getAttribute("data-pick"));
            const pick = plate.picks.find((k) => k.n === n);
            if (!pick) return;
            setTapped({ ...pick, level: plate.level });
            const i = route.directions.findIndex((d) => d.includes(pick.label));
            if (i >= 0) setStep(i);
          }}
        />
      )}

      {!list && (
        <ol className="sr-only" aria-label="Directions">
          {route.directions.map((line, i) => (
            <li key={i}>{line}</li>
          ))}
        </ol>
      )}

      <div className="step card">
        <p className="caption">
          Step {step + 1} of {n}
          {notes.length > 0 && <> · {notes.join(" ")}</>}
        </p>
        {tapped && (
          <p className="tapped" role="status">
            Pin {tapped.n}: <b>{tapped.label}</b> — {tapped.where}
          </p>
        )}
        <p className="now">{route.directions[step]}</p>
        <div className="row">
          <button
            type="button"
            className="secondary"
            disabled={step === 0}
            onClick={() => {
              setStep(step - 1);
              setTapped(null);
            }}
          >
            Back
          </button>
          <button type="button" className="secondary" onClick={() => setList(!list)}>
            {list ? "Map" : "All steps"}
          </button>
          <button
            type="button"
            className="primary grow"
            disabled={step >= n - 1}
            onClick={() => {
              setStep(step + 1);
              setTapped(null);
            }}
          >
            Next
          </button>
        </div>
      </div>
    </section>
  );
}
