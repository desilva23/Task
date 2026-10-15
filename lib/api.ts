// The four calls the page makes (lld.md §11). Every fact in a View was verified by the server
// before it was sent; the page only lays it out.

export type Spot = { label: string; node: string };
export type Floor = { level: number; name: string; spots: Spot[] };
export type Suggestion = {
  sku: string;
  label: string; // searches straight to this product
  terms: string[]; // name, brand and each synonym — what it answers to
  in_stock: boolean;
  popularity: number;
};
export type Store = { entrance: string; floors: Floor[]; products: Suggestion[] };

export type Option = { sku: string; label: string };
export type Question = { index: string; term: string; options: Option[] };
export type Row = { sku: string; label: string; statement: string; availability: string };
export type Pick = { n: number; node: string; label: string; where: string };
export type Plate = { level: number; name: string; svg: string; picks: Pick[] };

export type RouteView = {
  kind: "single" | "multi" | "none";
  message: string | null;
  directions: string[];
  excluded: string[];
  why: string | null;
  plates: Plate[];
};

export type View = {
  pending: { questions: Question[] } | null;
  notice: string | null;
  available: Row[];
  unavailable: Row[];
  notes: string[];
  addable: string[];
  offer_add: boolean;
  route: RouteView | null;
  degraded: string | null;
  split: { from: string; into: string[] }[]; // a list said without commas, cut into items
};

export type Where = { start: string; step_free: boolean };

export const APOLOGY = "Something went wrong on our side — please try your search again.";

async function call<T>(path: string, body?: object): Promise<T> {
  const response = await fetch(path, {
    method: body ? "POST" : "GET",
    headers: body ? { "Content-Type": "application/json" } : undefined,
    body: body ? JSON.stringify(body) : undefined,
  });
  if (!response.ok) throw new Error(APOLOGY); // the server's text is never shown raw
  return (await response.json()) as T;
}

export const getStore = () => call<Store>("/api/store");

export const search = (query: string, answers: Record<string, string>[], where: Where) =>
  call<View>("/api/search", { query, answers, ...where });

export const scan = (code: string, where: Where) => call<View>("/api/scan", { code, ...where });

export const planRoute = (skus: string[], where: Where) =>
  call<View>("/api/route", { skus, ...where });
