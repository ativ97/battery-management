self.addEventListener('install', function(event) {
  event.waitUntil(
    caches.open('battery-sys-v1').then(function(cache) {
      return cache.addAll([
        '/',
        'app/static/manifest.json',
        'app/static/icon.svg'
      ]);
    })
  );
});

self.addEventListener('fetch', function(event) {
  event.respondWith(
    caches.match(event.request).then(function(response) {
      return response || fetch(event.request);
    })
  );
});