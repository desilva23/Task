"use client";

// FR-05 and FR-21 to FR-24 — the clarification, results grouped by availability, and the
// basket gate: one action moves only the available items.

import { useState } from "react";

import type { Question, Row, View } from "@/lib/api";

export function Clarify({
  questions,
  onAnswer,
  busy,
}: {
  questions: Question[];
  onAnswer: (choice: Record<string, string>) => void;
  busy: boolean;
}) {
  const [picks, setPicks] = useState<Record<string, string>>(() =>
    Object.fromEntries(questions.map((q) => [q.index, q.options[0]?.sku ?? ""])),
  );
  return (
    <form
      className="card"
      onSubmit={(e) => {
        e.preventDefault();
        onAnswer(picks);
      }}
    >
      <h2>Which did you mean?</h2>
      {questions.map((q) => (
        <fieldset key={q.index}>
          <legend>“{q.term}”</legend>
          {q.options.map((o) => (
            <label key={o.sku} className="choice">
              <input
                type="radio"
                name={`choose-${q.index}`}
                value={o.sku}
                checked={picks[q.index] === o.sku}
                onChange={() => setPicks({ ...picks, [q.index]: o.sku })}
              />
              <span>{o.label}</span>
            </label>
          ))}
        </fieldset>
      ))}
      <button type="submit" className="primary wide" disabled={busy}>
        Continue
      </button>
    </form>
  );
}

function Statements({ rows }: { rows: Row[] }) {
  return (
    <ul className="statements">
      {rows.map((r) => (
        <li key={r.sku}>{r.statement}</li>
      ))}
    </ul>
  );
}

export default function Results({
  view,
  basket,
  onAdd,
}: {
  view: View;
  basket: string[];
  onAdd: (rows: Row[]) => void;
}) {
  const ready = view.available.filter((r) => view.addable.includes(r.sku) && !basket.includes(r.sku));
  return (
    <section className="results" aria-live="polite">
      {view.available.length > 0 && (
        <>
          <h2>Available</h2>
          <Statements rows={view.available} />
        </>
      )}
      {view.unavailable.length > 0 && (
        <>
          <h2>Not available</h2>
          <ul className="statements">
            {view.unavailable.map((r) => (
              <li key={r.sku}>
                {r.statement}
                {!basket.includes(r.sku) && (
                  <button type="button" className="link" onClick={() => onAdd([r])}>
                    Add {r.label} anyway (it won&apos;t be routed)
                  </button>
                )}
              </li>
            ))}
          </ul>
        </>
      )}
      {view.notes.length > 0 && (
        <ul className="statements notes">
          {view.notes.map((n) => (
            <li key={n}>{n}</li>
          ))}
        </ul>
      )}
      {view.offer_add &&
        (ready.length > 0 || view.available.length === 0 ? (
          <button
            type="button"
            className="primary wide"
            disabled={ready.length === 0} // EC-15: nothing available, nothing to add
            onClick={() => onAdd(ready)}
          >
            Add {ready.length} available to basket
          </button>
        ) : (
          <p className="caption">Everything available is in your basket.</p>
        ))}
    </section>
  );
}
