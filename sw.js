// Ad Fontes : la page est rechargée depuis le réseau quand il répond vite (les mises à jour
// apparaissent aussitôt) ; si le réseau tarde ou manque, la copie en cache s'affiche sans attendre
// et la nouvelle version, une fois arrivée, sert à l'ouverture suivante.
const CACHE = 'ad-fontes-v2';
const CORE = ['./', './index.html', './manifest.webmanifest', './icon-192.png', './icon-512.png', './apple-touch-icon.png'];
const DELAI = 2500; // ms accordées au réseau avant de servir la copie en cache
self.addEventListener('install', e => {
  e.waitUntil(caches.open(CACHE).then(c => c.addAll(CORE.map(u => new Request(u, { cache: 'reload' })))).then(() => self.skipWaiting()));
});
self.addEventListener('activate', e => {
  e.waitUntil(caches.keys().then(ks => Promise.all(ks.filter(k => k !== CACHE).map(k => caches.delete(k)))).then(() => self.clients.claim()));
});
self.addEventListener('fetch', e => {
  const req = e.request;
  if (req.method !== 'GET') return;
  const url = new URL(req.url);
  if (req.mode === 'navigate' || url.pathname.endsWith('/index.html')) {
    // « no-cache » : le navigateur revalide auprès du serveur au lieu de resservir une copie périmée.
    const net = fetch(url.origin + url.pathname, { cache: 'no-cache' }).then(r => {
      if (r && r.ok) { const cp = r.clone(); caches.open(CACHE).then(c => c.put('./index.html', cp)); }
      return r;
    });
    e.waitUntil(net.catch(() => {}));
    e.respondWith(caches.match('./index.html').then(hit => {
      if (!hit) return net;
      const lent = new Promise(res => setTimeout(() => res(hit), DELAI));
      return Promise.race([net.then(r => (r && r.ok ? r : hit)).catch(() => hit), lent]);
    }));
    return;
  }
  e.respondWith(caches.match(req).then(hit => {
    const net = fetch(req).then(r => { if (r && (r.ok || r.type === 'opaque')) { const cp = r.clone(); caches.open(CACHE).then(c => c.put(req, cp)); } return r; }).catch(() => hit);
    return hit || net;
  }));
});
