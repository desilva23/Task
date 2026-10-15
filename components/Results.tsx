"use client";

// FR-05 and FR-21 to FR-24 — the clarification, results grouped by availability, and the
// basket gate: one action moves only the available items. On one screen (NFR-11): results are
// short cards in the pane, and a question is asked one at a time.

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
  const [at, setAt] = useState(0);
  const q = questions[at];
  const last = at === questions.length - 1;
  return (
    <form
      className="card clarify"
      onSubmit={(e) => {
        e.preventDefault();
        if (last) onAnswer(picks);
        else setAt(at + 1);
      }}
    >
      <h2>Which did you mean?</h2>
      <fieldset key={q.index}>
        <legend>
          “{q.term}”
          {questions.length > 1 && (
            <span className="caption">
              {" "}
              · {at + 1} of {questions.length}
            </span>
          )}
        </legend>
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
      <div className="row">
        {at > 0 && (
          <button type="button" className="secondary" onClick={() => setAt(at - 1)}>
            Back
          </button>
        )}
        <button type="submit" className="primary grow" disabled={busy}>
          {last ? "Continue" : "Next"}
        </button>
      </div>
    </form>
  );
}

const BADGE: Record<string, [string, string]> = {
  in_stock: ["In stock", "ok"],
  sold_out: ["Sold out", "out"],
  not_ranged: ["Not sold here", "out"],
};

type Line = { key: string; row?: Row; note?: string };

export default function Results({
  view,
  basket,
  onAdd,
}: {
  view: View;
  basket: string[];
  onAdd: (rows: Row[]) => void;
}) {
  const lines: Line[] = [
    ...view.available.map((row) => ({ key: row.sku, row })),
    ...view.unavailable.map((row) => ({ key: row.sku, row })),
    ...view.notes.map((note) => ({ key: note, note })),
  ];
  if (!lines.length) return null;
  // Available first (FR-21), each a short card with its state up front. A search of a handful
  // of products fits the pane; a longer list scrolls inside it, never the page.
  return (
    <section className="results" aria-label="Results" aria-live="polite">
      <ul className="lines results-list">
        {lines.map(({ key, row, note }) => {
          const [badge, tone] = row ? (BADGE[row.availability] ?? ["", ""]) : ["Not found", "note"];
          const unavailable = row && !view.available.includes(row);
          return (
            <li key={key} className="result">
              <div className="result-head">
                {badge && <span className={`badge ${tone}`}>{badge}</span>}
                {row && row.qty > 1 && <span className="qty">{row.qty} ×</span>}
                {row?.price && <span className="price">{row.price}</span>}
              </div>
              <p>{row ? row.statement : note}</p>
              {row && row.tags.length > 0 && (
                // FR-29, NFR-03 — the record's own "yes", passed through; nothing is shown as "no"
                <ul className="tags" aria-label="Recorded as">
                  {row.tags.map((t) => (
                    <li key={t}>{t}</li>
                  ))}
                </ul>
              )}
              {row && unavailable && !basket.includes(row.sku) && (
                <button type="button" className="link" onClick={() => onAdd([row])}>
                  Add {row.label} anyway (it won&apos;t be routed)
                </button>
              )}
            </li>
          );
        })}
      </ul>
    </section>
  );
}
