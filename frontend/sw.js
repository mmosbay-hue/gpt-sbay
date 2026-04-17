const CACHE = 'sbayai-v1';
const ASSETS = [
  '/chat',
  '/static/css/style.css',
  '/static/js/app.js',
  '/static/js/chat.js',
  '/static/js/sidebar.js',
  '/static/js/markdown.js',
  '/static/logo.svg',
  '/static/icons/icon-192.png',
];

self.addEventListener('install', e => {
  e.waitUntil(caches.open(CACHE).then(c => c.addAll(ASSETS)));
  self.skipWaiting();
});

self.addEventListener('activate', e => {
  e.waitUntil(caches.keys().then(keys =>
    Promise.all(keys.filter(k => k !== CACHE).map(k => caches.delete(k)))
  ));
  self.clients.claim();
});

self.addEventListener('fetch', e => {
  // Network first, fallback to cache
  if (e.request.url.includes('/api/')) return; // Don't cache API
  e.respondWith(
    fetch(e.request).then(res => {
      const clone = res.clone();
      caches.open(CACHE).then(c => c.put(e.request, clone));
      return res;
    }).catch(() => caches.match(e.request))
  );
});
