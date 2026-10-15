// Suggestions as the shopper types (FR-28, hld.md §4). The store's catalogue arrives once with
// GET /api/store and is matched here, on the phone — no keystroke reaches the server and no
// model is asked. Choosing one puts its label in the box: a label searches straight to that
// product, so the suggestion and the answer cannot disagree.

import type { Suggestion } from "@/lib/api";

export const MIN_CHARS = 2;
export const MAX_SHOWN = 6;

// The same separators the server splits a list on (lld.md §8.2), so the suggestion is for the
// item being typed now: "milk, bre" suggests bread, and leaves the milk alone.
const SEPARATOR = /[,;\n+]|\sand\s/gi;

const words = (text: string) =>
  text
    .toLowerCase()
    .normalize("NFKD")
    .replace(/[̀-ͯ]/g, "")
    .split(/[^a-z0-9%.]+/)
    .filter(Boolean);

/** Where the item being typed starts, and what it says so far. */
export function current(text: string): { start: number; term: string } {
  let start = 0;
  for (const m of text.matchAll(SEPARATOR)) start = (m.index ?? 0) + m[0].length;
  return { start, term: text.slice(start).trim() };
}

/** Products whose words begin with every word typed. First those whose name or a synonym starts
 *  with what was typed ("bre" → the breads), then those it names, then in stock, then the
 *  popular. Nothing until two characters; never more than six. */
export function suggest(products: Suggestion[], text: string): Suggestion[] {
  const { term } = current(text);
  const typed = words(term);
  if (term.length < MIN_CHARS || !typed.length) return [];
  const scored: [number, Suggestion][] = [];
  for (const p of products) {
    const name = words(p.label);
    const all = p.terms.flatMap(words).concat(name);
    if (!typed.every((t) => all.some((w) => w.startsWith(t)))) continue;
    const named = typed.every((t) => name.some((w) => w.startsWith(t)));
    const phrase = typed.join(" ");
    const leads = [p.label, ...p.terms].some((t) => words(t).join(" ").startsWith(phrase));
    scored.push([leads ? 0 : named ? 1 : 2, p]);
  }
  return scored
    .sort(
      ([a, p], [b, q]) =>
        a - b || Number(q.in_stock) - Number(p.in_stock) || q.popularity - p.popularity,
    )
    .slice(0, MAX_SHOWN)
    .map(([, p]) => p);
}

/** The text with the item being typed replaced by the chosen product's label. */
export function choose(text: string, label: string): string {
  const head = text.slice(0, current(text).start).trimEnd();
  return head ? `${head} ${label}` : label;
}
