const CACHE_NAME = 'firstaid-v1';
const urlsToCache = [
  '/',
  '/static/css/style.css',
  '/static/images/icon_amb.webp'
];

// Install
self.addEventListener('install', (event) => {
  console.log('Service Worker: Installing...');
  event.waitUntil(
    caches.open(CACHE_NAME)
      .then((cache) => cache.addAll(urlsToCache))
  );
});

// Activate
self.addEventListener('activate', (event) => {
  console.log('Service Worker: Activated');
});

// Fetch
self.addEventListener('fetch', (event) => {
  event.respondWith(
    caches.match(event.request)
      .then((response) => response || fetch(event.request))
  );
});
