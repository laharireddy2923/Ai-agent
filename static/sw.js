const CACHE_NAME = 'finance-agent-v1';
const urlsToCache = [
  '/',
  '/login',
  '/signup',
  '/static/css/style.css',
  '/static/js/app.js',
  '/static/js/theme.js',
  '/static/manifest.json'
];

self.addEventListener('install', (event) => {
  event.waitUntil(
    caches.open(CACHE_NAME).then((cache) => {
      return cache.addAll(urlsToCache);
    })
  );
});

self.addEventListener('fetch', (event) => {
  event.respondWith(
    caches.match(event.request).then((response) => {
      return response || fetch(event.request);
    })
  );
});
