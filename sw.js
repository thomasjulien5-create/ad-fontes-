// Ad Fontes : la page et les données (donnees/) sont rechargées depuis le réseau quand il répond vite
// (les mises à jour apparaissent aussitôt) ; si le réseau tarde ou manque, la copie en cache s'affiche
// sans attendre et la nouvelle version, une fois arrivée, sert à l'ouverture suivante.
// Les lots de données (journées par mois, psaumes et paraboles par dix) sont gardés dès leur premier
// chargement ; le mois en cours est mis en cache dès l'installation, pour lire la journée hors connexion.
const CACHE = 'ad-fontes-v5';
const CORE = ['./', './index.html', './manifest.webmanifest', './icon-192.png', './icon-512.png', './apple-touch-icon.png',
  './images/missel.webp', './images/thomas.webp', './images/david.webp', './images/jesus.webp',
  './images/banniere-portrait.webp', './images/banniere-paysage.webp', './images/somme.webp', './images/portrait.webp'];
const DELAI = 2500; // ms accordées au réseau avant de servir la copie en cache
function mois(decalage) {
  const d = new Date(); d.setDate(1); d.setMonth(d.getMonth() + decalage);
  return './donnees/jours/' + d.getFullYear() + '-' + String(d.getMonth() + 1).padStart(2, '0') + '.json';
}
self.addEventListener('install', e => {
  e.waitUntil(caches.open(CACHE).then(c => c.addAll(CORE.map(u => new Request(u, { cache: 'reload' })))
    // Mois en cours et suivant : un mois pas encore préparé (404) n'empêche pas l'installation.
    .then(() => Promise.all([mois(0), mois(1)].map(u => fetch(u, { cache: 'reload' }).then(r => r.ok && c.put(u, r)).catch(() => {})))))
    .then(() => self.skipWaiting()));
});
self.addEventListener('activate', e => {
  e.waitUntil(caches.keys().then(ks => Promise.all(ks.filter(k => k !== CACHE).map(k => caches.delete(k)))).then(() => self.clients.claim()));
});
// Réseau d'abord, avec la copie en cache si le réseau tarde plus de DELAI ou manque.
function reseauDabord(e, url, cle) {
  // « no-cache » : le navigateur revalide auprès du serveur au lieu de resservir une copie périmée.
  const net = fetch(url, { cache: 'no-cache' }).then(r => {
    if (r && r.ok) { const cp = r.clone(); caches.open(CACHE).then(c => c.put(cle, cp)); }
    return r;
  });
  e.waitUntil(net.catch(() => {}));
  e.respondWith(caches.match(cle).then(hit => {
    if (!hit) return net;
    const lent = new Promise(res => setTimeout(() => res(hit), DELAI));
    return Promise.race([net.then(r => (r && r.ok ? r : hit)).catch(() => hit), lent]);
  }));
}
self.addEventListener('fetch', e => {
  const req = e.request;
  if (req.method !== 'GET') return;
  const url = new URL(req.url);
  if (req.mode === 'navigate' || url.pathname.endsWith('/index.html')) return reseauDabord(e, url.origin + url.pathname, './index.html');
  if (url.origin === location.origin && url.pathname.includes('/donnees/')) return reseauDabord(e, url.origin + url.pathname, url.origin + url.pathname);
  e.respondWith(caches.match(req).then(hit => {
    const net = fetch(req).then(r => { if (r && (r.ok || r.type === 'opaque')) { const cp = r.clone(); caches.open(CACHE).then(c => c.put(req, cp)); } return r; }).catch(() => hit);
    return hit || net;
  }));
});
