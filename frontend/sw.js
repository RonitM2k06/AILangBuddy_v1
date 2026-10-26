// LingoBuddy no longer installs as an app. This worker only exists to remove the one browsers registered before: it deletes the old caches,
// unregisters itself and reloads any open tabs so they load straight from the server.
self.addEventListener("install", () => self.skipWaiting());
self.addEventListener("activate", (event) => {
  event.waitUntil((async () => {
    const keys = await caches.keys();
    await Promise.all(keys.filter((k) => k.startsWith("lingobuddy-static-")).map((k) => caches.delete(k)));
    await self.registration.unregister();
    const tabs = await self.clients.matchAll({ type: "window" });
    tabs.forEach((tab) => tab.navigate(tab.url));
  })());
});
