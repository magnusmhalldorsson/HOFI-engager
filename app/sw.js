/* Offline shell for the recorder.

   Why this exists: a TA who opens the app in a room with bad Wi-Fi would otherwise
   get nothing at all -- the page itself has to come off the network every time. The
   recording work is entirely local, so failing to load is a pure loss.

   Deliberately NETWORK-FIRST, not cache-first. allocation.json says which cohort
   group takes the Thinking Lab first, and serving a stale copy of that would put a
   TA in the wrong room's block -- the one error the app is most careful about
   elsewhere. Freshness wins whenever the network can answer; the cache is a
   fallback for when it cannot.
*/
const CACHE = "hofi-v1";
const ASSETS = ["./", "./index.html", "./allocation.json", "./icon-180.png",
                "./manifest.webmanifest"];

self.addEventListener("install", e => {
  e.waitUntil(
    caches.open(CACHE)
      // Individually, so one missing asset cannot fail the whole install.
      .then(c => Promise.all(ASSETS.map(a => c.add(a).catch(() => null))))
      .then(() => self.skipWaiting())
  );
});

self.addEventListener("activate", e => {
  e.waitUntil(
    caches.keys()
      .then(ks => Promise.all(ks.filter(k => k !== CACHE).map(k => caches.delete(k))))
      .then(() => self.clients.claim())
  );
});

self.addEventListener("fetch", e => {
  const req = e.request;
  if (req.method !== "GET") return;
  if (new URL(req.url).origin !== self.location.origin) return;

  e.respondWith(
    fetch(req)
      .then(res => {
        if (res && res.ok) {
          const copy = res.clone();
          caches.open(CACHE).then(c => c.put(req, copy)).catch(() => {});
        }
        return res;
      })
      .catch(() => caches.match(req).then(hit => {
        if (hit) return hit;
        // A navigation with nothing cached for that exact URL still gets the app.
        // Anything else (allocation.json, say) is left to fail, because the app
        // already falls back to its own cached copy and must not be handed HTML.
        if (req.mode === "navigate") return caches.match("./index.html");
        return Response.error();
      }))
  );
});
