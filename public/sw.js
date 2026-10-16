// The offline layer (NFR-12). Network first, always: online, every request goes to the network
// and a fresh deploy is what the shopper gets; the copy kept here answers only when the network
// does not. The page, its scripts and the store call (floors, aisles, the catalogue the
// suggestions match) are kept; a search, scan or route needs the server and is never answered
// from here — the page says it needs a connection (EC-72).
const CACHE = "find-it-v1";
const KEEP_API = "/api/store";

self.addEventListener("install", (event) => {
  self.skipWaiting();
  event.waitUntil(caches.open(CACHE).then((c) => c.addAll(["/", "/manifest.webmanifest"])));
});

self.addEventListener("activate", (event) => {
  event.waitUntil(
    caches
      .keys()
      .then((keys) => Promise.all(keys.filter((k) => k !== CACHE).map((k) => caches.delete(k))))
      .then(() => self.clients.claim()),
  );
});

// What the page loaded before this worker was running: kept now, so the first visit counts.
self.addEventListener("message", (event) => {
  const urls = (event.data && event.data.keep) || [];
  event.waitUntil(
    caches
      .open(CACHE)
      .then((c) => Promise.all(urls.filter(keepable).map((u) => c.add(u).catch(() => undefined)))),
  );
});

function keepable(href) {
  const url = new URL(href, self.location.origin);
  if (url.origin !== self.location.origin) return false;
  return !url.pathname.startsWith("/api/") || url.pathname === KEEP_API;
}

self.addEventListener("fetch", (event) => {
  const req = event.request;
  if (req.method !== "GET" || !keepable(req.url)) return; // searches go straight to the network
  event.respondWith(
    fetch(req)
      .then((res) => {
        if (res.ok) {
          const copy = res.clone();
          caches.open(CACHE).then((c) => c.put(req, copy));
        }
        return res;
      })
      .catch(() =>
        caches
          .match(req) // the exact URL: each store's call is kept as its own (FR-31)
          .then((hit) => hit || (req.mode === "navigate" ? caches.match("/") : Response.error())),
      ),
  );
});
