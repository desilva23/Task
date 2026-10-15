"use client";

// Find it in store — the one page (C-03). The agent runs behind /api; this page holds what the
// server does not keep between requests: where the shopper is, the basket, and the answers to a
// clarification so far (hld.md §4.1).
//
// One screen, no page scroll (NFR-11): a header with where the shopper is, three panes — Search,
// Basket, Route — behind a tab bar at the bottom, and sheets over them for the start point and
// the barcode camera. Each pane fits the space it is given.

import { useCallback, useEffect, useState } from "react";

import Basket, { type Item } from "@/components/Basket";
import Results, { Clarify } from "@/components/Results";
import Route from "@/components/Route";
import Scanner from "@/components/Scanner";
import SearchBox from "@/components/SearchBox";
import Voice from "@/components/Voice";
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
type Tab = "search" | "basket" | "route";

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

function Sheet({
  title,
  onClose,
  children,
}: {
  title: string;
  onClose: () => void;
  children: React.ReactNode;
}) {
  useEffect(() => {
    const esc = (e: KeyboardEvent) => e.key === "Escape" && onClose();
    window.addEventListener("keydown", esc);
    return () => window.removeEventListener("keydown", esc);
  }, [onClose]);
  return (
    <div className="backdrop" onClick={onClose}>
      <div
        className="sheet"
        role="dialog"
        aria-modal="true"
        aria-label={title}
        onClick={(e) => e.stopPropagation()}
      >
        <div className="sheet-head">
          <h2>{title}</h2>
          <button type="button" className="secondary" aria-label="Close" onClick={onClose}>
            ✕
          </button>
        </div>
        {children}
      </div>
    </div>
  );
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
  const [listening, setListening] = useState(false);
  const [voiceNote, setVoiceNote] = useState<string | null>(null);
  const [added, setAdded] = useState<string | null>(null);
  const [tab, setTab] = useState<Tab>("search");
  const [sheet, setSheet] = useState<"where" | "scan" | null>(null);

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
    setAdded(null);
    setTab("search");
    run(
      () => search(next.query, next.answers, where),
      (v) => {
        setView(v);
        setRouted(null);
      },
    );
  };

  const onCode = useCallback(
    (code: string) => {
      if (!place) return;
      setAsked(null);
      setAdded(null);
      setSheet(null);
      setTab("search");
      run(
        () => scan(code, { start: place.node, step_free: place.stepFree }),
        (v) => {
          setView(v);
          setRouted(null);
        },
      );
    },
    [place, run],
  );

  const add = (rows: Row[]) => {
    const fresh = rows.filter((r) => !basket.some((i) => i.sku === r.sku));
    setBasket((b) => [...b, ...fresh.map((r) => ({ sku: r.sku, label: r.label }))]);
    setAdded(`Added ${fresh.length} to your basket.`);
  };

  const closeSheet = useCallback(() => setSheet(null), []);
  const shown = routed ?? view;
  const route = (routed ? routed.route : view?.route) ?? null;
  const inBasket = basket.map((i) => i.sku);
  const ready = view
    ? view.available.filter((r) => view.addable.includes(r.sku) && !inBasket.includes(r.sku))
    : [];
  const floor = store?.floors.find((f) => f.level === place?.level);
  const spot = floor?.spots.find((s) => s.node === place?.node)?.label ?? "Entrance";

  return (
    <div className="app">
      <header className="bar">
        <h1>Find it in store</h1>
        {place && (
          <button
            type="button"
            className="place"
            onClick={() => setSheet("where")}
            aria-label={`Where you are: floor ${place.level}, ${spot}${place.stepFree ? ", step-free" : ""}. Change`}
          >
            Floor {place.level} · {spot}
            {place.stepFree && " · step-free"} ▾
          </button>
        )}
      </header>

      <main className="pane">
        {tab === "search" && (
          <section className="pane-body search-pane" aria-label="Search">
            <form
              className="search"
              onSubmit={(e) => {
                e.preventDefault();
                setVoiceNote(null);
                (document.activeElement as HTMLElement | null)?.blur(); // the answer, not the keyboard
                if (query.trim()) ask({ query, answers: [] });
              }}
            >
              <label className="field" htmlFor="q">
                <span>What are you looking for?</span>
              </label>
              <div className="row">
                <div className="grow">
                  <SearchBox
                    value={query}
                    products={store?.products ?? []}
                    quiet={listening}
                    maxLength={MAX_QUERY_CHARS}
                    placeholder={
                      listening
                        ? "Listening — say what you're looking for"
                        : "e.g. milk, bread and eggs"
                    }
                    onChange={setQuery}
                    onPick={(text) => {
                      setQuery(text);
                      ask({ query: text, answers: [] }); // a label searches straight to its product
                    }}
                  />
                </div>
                <Voice
                  busy={busy || !where}
                  onListening={(on) => {
                    setListening(on);
                    if (on) setQuery("");
                  }}
                  onHearing={(text) => setQuery(text.slice(0, MAX_QUERY_CHARS))}
                  onHeard={(text) => {
                    const heard = text.slice(0, MAX_QUERY_CHARS);
                    setQuery(heard);
                    ask({ query: heard, answers: [] }); // the same search as typing it (AC-30)
                  }}
                  onMessage={setVoiceNote}
                />
              </div>
              <div className="row">
                <button type="submit" className="primary grow" disabled={busy || !where}>
                  {busy ? "Searching…" : "Search"}
                </button>
                <button
                  type="button"
                  className="secondary"
                  disabled={!where}
                  onClick={() => setSheet("scan")}
                >
                  Scan a barcode
                </button>
              </div>
            </form>

            {listening && (
              <p className="caption" role="status">
                Listening… tap the microphone again when you&apos;ve finished.
              </p>
            )}
            {voiceNote && (
              <p className="callout warn" role="status">
                {voiceNote}
              </p>
            )}
            {error && (
              <p className="callout error" role="alert">
                {error}
              </p>
            )}

            <div className="answer">
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
              ) : view ? (
                <Results view={view} basket={inBasket} onAdd={add} />
              ) : (
                <p className="empty">
                  Type a product, a list like “milk, bread and eggs”, or a sentence like “something
                  for a headache”. Or tap the microphone, or scan a barcode.
                </p>
              )}
            </div>

            {view && !view.pending && (
              <div className="actions">
                {added && (
                  <p className="caption" role="status">
                    {added}
                  </p>
                )}
                {view.offer_add &&
                  (ready.length > 0 || view.available.length === 0 ? (
                    <button
                      type="button"
                      className="primary wide"
                      disabled={ready.length === 0} // EC-15: nothing available, nothing to add
                      onClick={() => add(ready)}
                    >
                      Add {ready.length} available to basket
                    </button>
                  ) : (
                    !added && <p className="caption">Everything available is in your basket.</p>
                  ))}
                {view.route && (
                  <button type="button" className="primary wide" onClick={() => setTab("route")}>
                    Show route
                  </button>
                )}
              </div>
            )}
            {shown?.degraded && <p className="caption">{shown.degraded}</p>}
          </section>
        )}

        {tab === "basket" && (
          <Basket
            items={basket}
            busy={busy || !where}
            onRemove={(sku) => setBasket((b) => b.filter((i) => i.sku !== sku))}
            onPlan={() =>
              where &&
              run(
                () => planRoute(inBasket, where),
                (v) => {
                  setRouted(v);
                  setTab("route");
                },
              )
            }
          />
        )}

        {tab === "route" && (
          <Route
            key={route ? JSON.stringify(route.directions) : "none"}
            route={route}
            empty="Search for a product to see its route, or plan one for everything in your basket."
          />
        )}
      </main>

      <nav className="tabbar" role="tablist" aria-label="Sections">
        {(
          [
            ["search", "Search"],
            ["basket", `Basket (${basket.length})`],
            ["route", "Route"],
          ] as [Tab, string][]
        ).map(([id, label]) => (
          <button
            key={id}
            type="button"
            role="tab"
            aria-selected={tab === id}
            className={tab === id ? "on" : undefined}
            onClick={() => setTab(id)}
          >
            {label}
            {id === "route" && route && tab !== "route" && (
              <span className="dot" aria-label="ready" />
            )}
          </button>
        ))}
      </nav>

      {sheet === "where" && store && place && (
        <Sheet title="Where are you?" onClose={closeSheet}>
          <Where store={store} place={place} onChange={setPlace} />
          <button type="button" className="primary wide" onClick={closeSheet}>
            Done
          </button>
        </Sheet>
      )}
      {sheet === "scan" && (
        <Sheet title="Scan a barcode" onClose={closeSheet}>
          <Scanner onCode={onCode} busy={busy || !where} />
        </Sheet>
      )}
      {!store && !error && <p className="loading caption">Loading the store…</p>}
    </div>
  );
}
