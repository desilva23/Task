"use client";

// Find it in store — the one page (C-03). The agent runs behind /api; this page holds what the
// server does not keep between requests: where the shopper is, the basket, and the answers to a
// clarification so far (hld.md §4.1).

import { useCallback, useEffect, useState } from "react";

import Basket, { type Item } from "@/components/Basket";
import Results, { Clarify } from "@/components/Results";
import Route from "@/components/Route";
import Scanner from "@/components/Scanner";
import Where, { type Place } from "@/components/Where";
import {
  APOLOGY,
  type Row,
  type Store,
  type View,
  getStore,
  planRoute,
  scan,
  search,
} from "@/lib/api";

const MAX_QUERY_CHARS = 1000; // NFR-06 — the server cuts here too, and says so
const SAVED = "locator:session";

type Asked = { query: string; answers: Record<string, string>[] };

function load<T>(key: string, fallback: T): T {
  try {
    const raw = sessionStorage.getItem(`${SAVED}:${key}`);
    return raw ? (JSON.parse(raw) as T) : fallback;
  } catch {
    return fallback;
  }
}

function save(key: string, value: unknown) {
  try {
    sessionStorage.setItem(`${SAVED}:${key}`, JSON.stringify(value));
  } catch {
    /* private mode — the page still works, it just forgets on refresh */
  }
}

export default function Page() {
  const [store, setStore] = useState<Store | null>(null);
  const [place, setPlace] = useState<Place | null>(null);
  const [query, setQuery] = useState("");
  const [asked, setAsked] = useState<Asked | null>(null);
  const [view, setView] = useState<View | null>(null);
  const [routed, setRouted] = useState<View | null>(null);
  const [basket, setBasket] = useState<Item[]>([]);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    setBasket(load<Item[]>("basket", []));
    getStore()
      .then((s) => {
        setStore(s);
        const saved = load<Place | null>("place", null);
        const known = saved && s.floors.some((f) => f.spots.some((p) => p.node === saved.node));
        setPlace(known ? saved : { level: s.floors[0].level, node: s.entrance, stepFree: false });
      })
      .catch(() => setError(APOLOGY));
  }, []);

  useEffect(() => save("basket", basket), [basket]);
  useEffect(() => {
    if (place) save("place", place);
  }, [place]);

  const where = place ? { start: place.node, step_free: place.stepFree } : null;

  const run = useCallback(async (call: () => Promise<View>, then: (v: View) => void) => {
    setBusy(true);
    setError(null);
    try {
      then(await call());
    } catch {
      setError(APOLOGY); // an apology, never a trace (AC-13)
    } finally {
      setBusy(false);
    }
  }, []);

  const ask = (next: Asked) => {
    if (!where) return;
    setAsked(next);
    run(() => search(next.query, next.answers, where), (v) => {
      setView(v);
      setRouted(null);
    });
  };

  const onCode = useCallback(
    (code: string) => {
      if (!place) return;
      setAsked(null);
      run(() => scan(code, { start: place.node, step_free: place.stepFree }), (v) => {
        setView(v);
        setRouted(null);
      });
    },
    [place, run],
  );

  const add = (rows: Row[]) =>
    setBasket((b) => [
      ...b,
      ...rows.filter((r) => !b.some((i) => i.sku === r.sku)).map((r) => ({ sku: r.sku, label: r.label })),
    ]);

  const shown = routed ?? view;
  const route = routed ? routed.route : view?.route;

  return (
    <main>
      <h1>Find it in store</h1>
      {store && place ? (
        <Where store={store} place={place} onChange={setPlace} />
      ) : (
        !error && <p className="caption">Loading the store…</p>
      )}

      <form
        className="search"
        onSubmit={(e) => {
          e.preventDefault();
          if (query.trim()) ask({ query, answers: [] });
        }}
      >
        <label className="field">
          <span>What are you looking for?</span>
          <input
            type="search"
            enterKeyHint="search"
            maxLength={MAX_QUERY_CHARS}
            placeholder="e.g. milk, bread, eggs — or 'something for a headache'"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
          />
        </label>
        <button type="submit" className="primary wide" disabled={busy || !where}>
          {busy ? "Searching…" : "Search"}
        </button>
      </form>

      <Scanner onCode={onCode} busy={busy || !where} />

      {error && (
        <p className="callout error" role="alert">
          {error}
        </p>
      )}

      {view?.pending && asked ? (
        <Clarify
          key={asked.answers.length}
          questions={view.pending.questions}
          busy={busy}
          onAnswer={(choice) => ask({ ...asked, answers: [...asked.answers, choice] })}
        />
      ) : view?.notice ? (
        <p className="callout info" role="status">
          {view.notice}
        </p>
      ) : (
        view && <Results view={view} basket={basket.map((i) => i.sku)} onAdd={add} />
      )}

      <Basket
        items={basket}
        busy={busy || !where}
        onRemove={(sku) => setBasket((b) => b.filter((i) => i.sku !== sku))}
        onPlan={() => where && run(() => planRoute(basket.map((i) => i.sku), where), setRouted)}
      />

      {route && <Route key={JSON.stringify(route.directions)} route={route} />}

      {shown?.degraded && <p className="callout info">{shown.degraded}</p>}
    </main>
  );
}
