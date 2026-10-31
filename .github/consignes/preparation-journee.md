# Ad Fontes — préparer une journée (Textes du jour et Méditation quotidienne)

Ce document fixe les règles en vigueur pour préparer une journée. Il sert à la
préparation manuelle comme à la génération nocturne (tâche planifiée de Claude Code à 3 h,
heure de Paris ; secours manuel : `.github/workflows/generation-nocturne.yml`).
Une journée n'est publiée que lorsqu'elle est **complète et vérifiée** : aucune
mention de brouillon, de travail en cours, de « à vérifier » ou de modèle ne doit
subsister dans les données publiées.

## 1. Où écrire

- Une journée = une clé `AAAA-MM-JJ` dans `donnees/jours/AAAA-MM.json` (un fichier par
  mois, objet JSON trié par date, indentation de 1 espace, UTF-8, apostrophes typographiques `’`).
- Le schéma est celui des journées déjà publiées (voir octobre 2026 pour des exemples complets) :

```
"AAAA-MM-JJ": {
  "textes": {
    "liturgie": { "nom", "qualite", "classe", "couleur", "commemoraisons": [] },
    "propre": { "lecon"? , "supplement"?: [], "epitre"?, "evangile" },
        // chaque lecture : { "titre"?, "reference", "incipit", "note"?, "latin": [], "francais": [] }
    "verset": { "texte", "ref" },
    "commentaire": { "mode": "direct" | "synthese", "portee", "verif", "sections": [4 sections] },
    "essentiel": [3 phrases], "resolution": "…", "sources": [{ "label", "detail", "url" }],
    "fete": { "titre": "Le sens de la fête" | "Le saint du jour", "texte": "…" }
  },
  "meditation": {
    "titre", "texte": [], "reserve"?: "…",
    "commentaire": { "sections": [3 sections] },
    "essentiel": [3 phrases], "resolution": "…", "sources": [...]
  }
}
```

- Dans les textes, `**gras**` met une proposition en valeur, `*italique*` marque les citations
  de l'Écriture dans la méditation.
- Contrôle : `python3 .github/scripts/controler-journees.py fragment <fichier>` avant insertion
  (`.github/scripts/inserer-journees.py`), puis `valider AAAA-MM-JJ` ; `verifier-jour.mjs` (7 h) doit passer.

## 2. Textes du jour

### Liturgie (fiche)
- **Missel romain de 1962, rubriques de 1960**, d'après les données libres du projet
  Divinum Officium (`web/www/missa/Latin/…` et `web/www/missa/Francais/…`,
  calendrier `web/www/Tabulae/Kalendaria/`). Les communs de la messe (C2, C4, C8…) sont dans
  `web/www/horas/{Latin,Francais}/Commune/` (sections [Introitus], [Lectio], [Evangelium]…). Le site divinumofficium.com est protégé :
  lire les fichiers du dépôt GitHub `DivinumOfficium/divinum-officium` (raw.githubusercontent.com).
- `nom` en français (« Saint Martin », « Mardi de la XXIIIe semaine après la Pentecôte »),
  `qualite` (« Évêque et Confesseur », « Férie », « Dimanche »…), `classe` (« Ire classe »…
  « IVe classe »), `couleur` parmi blanc, rouge, vert, violet, rose, noir.
- `commemoraisons` : les commémoraisons de la messe selon les rubriques de 1960
  (saint d'un jour empêché par un dimanche, commémoraison simple, dimanche empêché par une fête de Ire classe, férie privilégiée de l'Avent).
- Féries : messe du dimanche précédent. Samedis libres : férie (comme le 31 octobre 2026).
- Le dimanche après l'Épiphanie reporté en novembre suit la règle des rubriques
  (avec 26 dimanches après la Pentecôte : XXIVe = Ve après l'Épiphanie, XXVe = VIe,
  le dernier dimanche prenant la messe du XXIVe).

### Lectures
- Épître (ou Leçon) et Évangile **en latin** (texte du missel, Divinum Officium, accents conservés)
  **et en français** dans la **Bible Crampon 1923**, relevée sur Wikisource
  (`https://fr.wikisource.org/w/index.php?title=Bible_Crampon_1923/<Livre>&action=render`),
  sans les appels de note `[n]`, en gardant les crochets propres à la Crampon (`[Dieu]`).
- Latin : texte du missel avec « i » à la place de « j » (Iesus, eius), accents et æ/œ conservés.
- `incipit` : formule liturgique traduite du missel (« Mes frères : », « En ce temps-là : »,
  « Mes bien-aimés : »…). Lorsque le missel s'écarte du texte biblique (début abrégé,
  conclusion liturgique, versets omis), le signaler dans `note`, et traduire « par Ad Fontes »
  les seuls mots liturgiques absents de la Crampon.
- `verset` : un verset de l'Évangile du jour (sinon de l'Épître), cité exactement d'après la Crampon.

### Encadré `fete`
- « Le sens de la fête » (fêtes du Seigneur, de la Vierge, dimanches, féries, défunts…) ou
  « Le saint du jour » (fête d'un saint) : un paragraphe d'environ 120 à 180 mots, appuyé sur
  le propre de la messe (introït, collecte…) et les leçons du bréviaire (Divinum Officium,
  `web/www/horas/Francais/Sancti/` ou `Latin`), sans rien inventer.

### Commentaire en quatre mouvements (≈ 350 mots en tout, comme les journées publiées)
1. L'Épître (ou la Leçon), 2. L'Évangile, 3. Ce que l'Épître et l'Évangile disent ensemble,
4. À la lumière de la fête (ou du temps liturgique). Titres de la forme
« L’Épître : … », « L’Évangile : … », « Ce que l’Épître et l’Évangile disent ensemble : … »,
« À la lumière de la fête : … » (ou « du jour », « du temps de l’Avent »…).
- **Saint Thomas d'abord** : `source` = « Saint Thomas d’Aquin » pour chaque section ;
  commentaires bibliques (Super Matthaeum, Super Ioannem, épîtres de saint Paul, Isaïe, Jérémie,
  Job, Psaumes…), Catena aurea (pour Marc et Luc, en précisant qu'elle recueille les Pères),
  Sommes, Questions disputées, sermons. Une section par paragraphe, une à deux citations
  (`citation` : `texte`, `ref`, `url`) au plus.
- `mode` : « direct » si saint Thomas commente directement les passages lus ; « synthese »
  s'il faut composer à partir d'autres œuvres (ou pour varier quand la même messe revient en semaine).
- `portee` : « Épître, Colossiens 1, 9-14, et Évangile, Matthieu 24, 15-35 ».
- `verif` : « Textes relus : … » — liste exacte de ce qui a été lu.
- Quand la même messe revient plusieurs jours de suite, chaque jour a un commentaire
  différent (autres versets, autres œuvres de saint Thomas).

### Trois points et résolution
- `essentiel` : trois phrases brèves, mémorisables, tirées réellement du commentaire.
- `resolution` : un acte concret, réalisable aujourd'hui, qui découle des trois points.

### Sources (`sources`)
- Chaque œuvre de saint Thomas citée : label « Saint Thomas d’Aquin, <titre latin>, cap. x, lect. y »
  (ou « Somme théologique, II-II, q. 82, a. 3 »), detail précisant « Commentaire direct de l’Épître »
  ou le sujet, « texte latin, Corpus Thomisticum (…) ; traduction d’Ad Fontes »,
  **url avec l'ancre du paragraphe** (`https://www.corpusthomisticum.org/sth3082.html#42575`).
  Les ancres sont les numéros entre crochets (`[42575]`) des pages du Corpus : les relever
  dans la page, ne jamais les deviner. Fichiers utiles du Corpus : Somme `sth1…` (I), `sth2…` (I-II),
  `sth3…` (II-II), `sth4…` (III), nommés d'après la première question du lot (voir l'index
  `iopera.html`) ; Super Matthaeum `cma…`/`cml…` ; Super Ioannem `cih…` ; Catena aurea `cmt`, `cmc`,
  `clc`, `cjo` ; épîtres `cro`, `c1c`, `c2c`, `cgl`, `cep`, `cpl` (Philippiens), `ccl`… ;
  `cph` est In Ieremiam ; In Symbolum `csv` ; In orationem dominicam `csu…`.
- Le missel (fichier Divinum Officium du jour, classe, couleur, collecte citée), le bréviaire si
  l'encadré s'en sert, la Crampon (une source par lecture, URL Wikisource du livre).

## 3. Méditation quotidienne : La Moelle de saint Thomas d’Aquin

- R. P. Mézard, O.P., traduction « par un religieux du même Ordre », P. Lethielleux, 1930,
  exemplaire de la Bibliothèque Saint Libère sur archive.org :
  tome I `la-moelle-de-saint-thomas-d-aquin-tome-1-000000942` (de l'Avent au Sacré-Cœur),
  tome II `la-moelle-de-saint-thomas-d-aquin-tome-2-000000990` (du 1er juillet à l'Avent).
- **Suivre la table de l'ouvrage** : les méditations sont datées (« 3 Novembre. »). Du 1er juillet
  au samedi qui précède l'Avent, tome II à la date du jour ; à partir du premier dimanche de
  l'Avent, tome I à la date du jour (le tome I commence au 27 novembre). Après la Septuagésime,
  suivre l'Avis du tome I (reprendre la série qui commence ce dimanche-là).
- **Transcrire sur les images du scan** (PDF d'archive.org, une page de PDF par page imprimée,
  rendue avec `pdftoppm`), l'OCR d'archive.org étant très fautif. Texte intégral, dans l'ordre,
  sans coupe ; corriger seulement les erreurs manifestes de numérisation ou d'impression.
  Conserver la division de l'ouvrage (`**I**`, `1°`, `a)`…), les citations de l'Écriture en
  `*italique*`, et la référence finale imprimée en italique entre parenthèses
  (`*(Sur saint Jean, c. VI.)*`), en dernier paragraphe.
- `titre` : le titre de l'ouvrage, orthographe moderne et majuscules sobres.
- **Vérifier la référence imprimée** sur le Corpus Thomisticum. Si le texte appartient à une
  œuvre que le Corpus range parmi les douteux ou les apocryphes (par ex. l'Expositio in Canticum
  attribuée à Gilles de Rome, certains opuscules), le dire dans `reserve` et n'appuyer le
  commentaire que sur des œuvres authentiques. Si la référence est inexacte, donner la bonne
  dans les sources.

### Commentaire de la méditation (trois sections, ≈ 270 mots en tout)
- Trois paragraphes qui approfondissent la méditation **par d'autres textes authentiques de
  saint Thomas** (Somme, commentaires, Questions disputées), une citation au plus, `source` =
  « Saint Thomas d’Aquin ». Puis trois points et une résolution, comme pour les textes.
- Sources : en premier, La Moelle avec tome et pages
  (« La Moelle de saint Thomas d’Aquin, R. P. Mézard, O.P., tome II, p. 261-263 », detail
  identique aux journées précédentes, url archive.org du tome) ; puis la référence imprimée
  par l'ouvrage vérifiée sur le Corpus Thomisticum ; puis chaque texte cité dans le commentaire.

## 4. Exigences de vérification

- Aucune citation, référence, ancre ou page n'est donnée sans avoir été lue à la source.
- Les traductions de saint Thomas sont faites par Ad Fontes et signalées comme telles.
- Aucune mention de brouillon, d'ébauche, de validation en attente, de « TODO », de modèle.
- Style : français soigné, phrases nettes, pas de jargon ; « saint Thomas », « saint Paul ».
