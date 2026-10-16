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
const OFFLINE =
  "No connection — a search needs signal. Suggestions and your basket still work; try again when you're back online.";
const SAVED = "locator:session";

type Asked = { query: string; answers: Record<string, string>[] };
type Tab = "search" | "basket" | "route";

// Where the shopper stands is for this visit (the tab's session); the basket is a shopping list,
// kept on the phone between visits until it is cleared (FR-30). Both are kept per store, and
// the store last chosen is remembered (FR-31): "basket:SBY-CITY-003", "place:SBY-CITY-003".
const KEEP: Record<string, () => Storage> = {
  place: () => sessionStorage,
  basket: () => localStorage,
  store: () => localStorage,
};

function load<T>(key: string, fallback: T): T {
  try {
    const raw =
      KEEP[key.split(":")[0]]().getItem(`${SAVED}:${key}`) ??
      sessionStorage.getItem(`${SAVED}:${key}`);
    return raw ? (JSON.parse(raw) as T) : fallback;
  } catch {
    return fallback;
  }
}

function save(key: string, value: unknown) {
  try {
    KEEP[key.split(":")[0]]().setItem(`${SAVED}:${key}`, JSON.stringify(value));
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
  const [sheet, setSheet] = useState<"store" | "where" | "scan" | null>(null);

  const [online, setOnline] = useState(true);

  // NFR-12 — weak in-store signal. The worker keeps the page and the store call, network first;
  // what this visit has already loaded is handed to it, so the first visit counts.
  useEffect(() => {
    const on = () => setOnline(navigator.onLine);
    on();
    window.addEventListener("online", on);
    window.addEventListener("offline", on);
    return () => {
      window.removeEventListener("online", on);
      window.removeEventListener("offline", on);
    };
  }, []);
  const keepOffline = useCallback(() => {
    if (!("serviceWorker" in navigator)) return;
    navigator.serviceWorker
      .register("/sw.js")
      .then(() => navigator.serviceWorker.ready)
      .then((reg) => {
        const loaded = performance.getEntriesByType("resource").map((r) => r.name);
        reg.active?.postMessage({ keep: [location.href, ...loaded] });
      })
      .catch(() => undefined); // no worker, no offline copy — the page works as before
  }, []);

  // FR-31 — open a store: its floors, its catalogue, and this phone's basket and start point for
  // it. Nothing from the store before is carried over — a basket is never routed in another
  // store (EC-75).
  const openStore = useCallback(
    (id?: string) => {
      setError(null);
      getStore(id)
        .catch(() => (id ? getStore() : Promise.reject())) // a store no longer offered: the default
        .then((s) => {
          keepOffline();
          const first = s.stores[0]?.id === s.id;
          const kept =
            load<Item[] | null>(`basket:${s.id}`, null) ??
            (first ? load<Item[]>("basket", []) : []);
          const saved = load<Place | null>(`place:${s.id}`, null);
          const known = saved && s.floors.some((f) => f.spots.some((p) => p.node === saved.node));
          setStore(s);
          setBasket(kept.map((i) => ({ ...i, qty: i.qty || 1 })));
          setPlace(known ? saved : { level: s.floors[0].level, node: s.entrance, stepFree: false });
          setView(null);
          setRouted(null);
          setAsked(null);
          setQuery("");
          setAdded(null);
          setTab("search");
          save("store", s.id);
        })
        .catch(() => setError(navigator.onLine ? APOLOGY : OFFLINE));
    },
    [keepOffline],
  );

  useEffect(() => openStore(load<string>("store", "") || undefined), [openStore]);

  useEffect(() => {
    if (store) save(`basket:${store.id}`, basket);
  }, [basket, store]);
  useEffect(() => {
    if (place && store) save(`place:${store.id}`, place);
  }, [place, store]);

  const where =
    place && store ? { store: store.id, start: place.node, step_free: place.stepFree } : null;

  const run = useCallback(async (call: () => Promise<View>, then: (v: View) => void) => {
    setBusy(true);
    setError(null);
    try {
      then(await call());
    } catch {
      setError(navigator.onLine ? APOLOGY : OFFLINE); // an apology, never a trace (AC-13)
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
      if (!place || !store) return;
      setAsked(null);
      setAdded(null);
      setSheet(null);
      setTab("search");
      run(
        () => scan(code, { store: store.id, start: place.node, step_free: place.stepFree }),
        (v) => {
          setView(v);
          setRouted(null);
        },
      );
    },
    [place, store, run],
  );

  const add = (rows: Row[]) => {
    const fresh = rows.filter((r) => !basket.some((i) => i.sku === r.sku));
    setBasket((b) => [
      ...b,
      ...fresh.map((r) => ({ sku: r.sku, label: r.label, qty: r.qty || 1 })),
    ]);
    setAdded(`Added ${fresh.length} to your basket.`);
  };

  const closeSheet = useCallback(() => setSheet(null), []);
  const shown = routed ?? view;
  const route = (routed ? routed.route : view?.route) ?? null;
  const inBasket = basket.map((i) => i.sku);
  const single = view ? view.available.length + view.unavailable.length === 1 : false;
  const ready = view
    ? view.available.filter((r) => view.addable.includes(r.sku) && !inBasket.includes(r.sku))
    : [];
  const floor = store?.floors.find((f) => f.level === place?.level);
  const spot = floor?.spots.find((s) => s.node === place?.node)?.label ?? "Entrance";

  return (
    <div className="app">
      <header className="bar">
        <div className="brand">
          <h1>Find it in store</h1>
          {store && (
            <button
              type="button"
              className="store"
              onClick={() => setSheet("store")}
              aria-label={`Store: ${store.name}. Change`}
            >
              {store.name} ▾
            </button>
          )}
        </div>
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
      {!online && (
        <p className="offline" role="status">
          No connection — suggestions and your basket still work.
        </p>
      )}

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

            {view?.split.map((cut) => (
              <p key={cut.from} className="split" role="status">
                Searched as: <b>{cut.into.join(" · ")}</b>{" "}
                <button
                  type="button"
                  className="link"
                  disabled={busy}
                  onClick={() => {
                    // quoted, it is searched as one item (FR-02)
                    const one = (asked?.query ?? query).replace(cut.from, `"${cut.from}"`);
                    setQuery(one);
                    ask({ query: one, answers: [] });
                  }}
                >
                  Search “{cut.from}” as one item
                </button>
              </p>
            ))}

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
                <div className="row">
                  {view.offer_add &&
                    (ready.length > 0 || (view.available.length === 0 && !single) ? (
                      <button
                        type="button"
                        className={view.route ? "secondary grow" : "primary grow"}
                        disabled={ready.length === 0} // EC-15: nothing available, nothing to add
                        onClick={() => add(ready)}
                      >
                        {single ? "Add to basket" : `Add ${ready.length} available to basket`}
                      </button>
                    ) : (
                      !added &&
                      view.available.length > 0 && (
                        <p className="caption grow">
                          {single
                            ? "It's in your basket."
                            : "Everything available is in your basket."}
                        </p>
                      )
                    ))}
                  {view.route && (
                    <button type="button" className="primary grow" onClick={() => setTab("route")}>
                      Show route
                    </button>
                  )}
                </div>
              </div>
            )}
            {shown?.degraded && <p className="caption">{shown.degraded}</p>}
          </section>
        )}

        {tab === "basket" && (
          <Basket
            items={basket}
            busy={busy || !where}
            onQty={(sku, qty) =>
              setBasket((b) => b.map((i) => (i.sku === sku ? { ...i, qty } : i)))
            }
            onRemove={(sku) => setBasket((b) => b.filter((i) => i.sku !== sku))}
            onClear={() => setBasket([])}
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
      {sheet === "store" && store && (
        <Sheet title="Which store?" onClose={closeSheet}>
          <fieldset>
            <legend className="sr-only">Store</legend>
            {store.stores.map((s) => (
              <label key={s.id} className="choice">
                <input
                  type="radio"
                  name="store"
                  value={s.id}
                  checked={s.id === store.id}
                  onChange={() => {
                    setSheet(null);
                    if (s.id !== store.id) openStore(s.id);
                  }}
                />
                <span>
                  {s.name} <span className="caption">· {s.floors} floors</span>
                </span>
              </label>
            ))}
          </fieldset>
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
