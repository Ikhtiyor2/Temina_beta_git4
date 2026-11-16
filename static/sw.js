/* TeminaFit PWA Service Worker */
const CACHE_NAME = 'temina-fit-v1';
const STATIC_ASSETS = [
  '/static/manifest.json',
  '/static/icons/icon.svg',
  '/static/css/premium-styles.css',
  '/static/css/components.css',
  '/static/css/animations.css',
  '/static/js/core.js'
];

self.addEventListener('install', (event) => {
  event.waitUntil(
    caches.open(CACHE_NAME).then((cache) => {
      return cache.addAll(STATIC_ASSETS).catch(() => {});
    }).then(() => self.skipWaiting())
  );
});

self.addEventListener('activate', (event) => {
  event.waitUntil(
    caches.keys().then((keys) => {
      return Promise.all(
        keys.filter((k) => k !== CACHE_NAME).map((k) => caches.delete(k))
      );
    }).then(() => self.clients.claim())
  );
});

self.addEventListener('fetch', (event) => {
  const { request } = event;
  const url = new URL(request.url);
  if (url.origin !== location.origin) return;
  if (url.pathname.startsWith('/api/')) {
    event.respondWith(fetch(request));
    return;
  }
  if (url.pathname.match(/\.(css|js|svg|png|jpg|jpeg|webp|woff2?|ttf)(\?.*)?$/i)) {
    event.respondWith(
      caches.match(request).then((cached) => cached || fetch(request).then((res) => {
        const clone = res.clone();
        if (res.ok) caches.open(CACHE_NAME).then((c) => c.put(request, clone));
        return res;
      }))
    );
    return;
  }
  event.respondWith(fetch(request));
});
