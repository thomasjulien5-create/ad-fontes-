#!/usr/bin/env python3
"""Ad Fontes — contrôle des journées préparées (charte : .github/consignes/preparation-journee.md).

  python3 .github/scripts/controler-journees.py a-preparer --fenetre 30 [--max 3]
      Affiche, une par ligne, les dates de la fenêtre (aujourd'hui inclus, heure de Paris)
      dont la journée est absente ou incomplète, dans l'ordre, au plus --max.
  python3 .github/scripts/controler-journees.py valider AAAA-MM-JJ [AAAA-MM-JJ …]
      Vérifie les journées données dans donnees/jours/ ; code de retour 1 au moindre défaut.
  python3 .github/scripts/controler-journees.py fragment fichier.json [...]
      Même vérification sur des fragments { "AAAA-MM-JJ": {...} }.
"""
import json, re, sys
from datetime import datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

DOSSIER = Path("donnees/jours")
INTERDIT = re.compile(r"brouillon|ébauche|\bTODO\b|à vérifier|provisoire|placeholder|mise en page type", re.I)
MOELLE = "La Moelle de saint Thomas d’Aquin, R. P. Mézard, O.P., tome "

def plein(v): return bool(str(v or "").strip())

def defauts(j):
    err = []
    if not isinstance(j, dict): return ["journée absente"]
    t, m = j.get("textes") or {}, j.get("meditation") or {}
    l = t.get("liturgie") or {}
    for k in ("nom", "qualite", "classe", "couleur"):
        if not plein(l.get(k)): err.append(f"liturgie.{k} vide")
    if l.get("couleur") not in ("blanc", "rouge", "vert", "violet", "rose", "noir"): err.append("couleur inconnue")
    if not isinstance(l.get("commemoraisons"), list): err.append("commemoraisons doit être une liste")
    p = t.get("propre") or {}
    for nom, x in (("première lecture", p.get("lecon") or p.get("epitre")), ("évangile", p.get("evangile"))):
        if not isinstance(x, dict): err.append(f"{nom} absente"); continue
        for k in ("reference", "incipit"):
            if not plein(x.get(k)): err.append(f"{nom} : {k} vide")
        for k in ("latin", "francais"):
            if not x.get(k) or not all(plein(s) for s in x[k]): err.append(f"{nom} : {k} vide")
        if any("j" in s.lower() for s in x.get("latin") or []): err.append(f"{nom} : « j » dans le latin (écrire « i »)")
    v = t.get("verset") or {}
    if not plein(v.get("texte")) or not plein(v.get("ref")): err.append("verset incomplet")
    c = t.get("commentaire") or {}
    if c.get("mode") not in ("direct", "synthese"): err.append("commentaire.mode invalide")
    for k in ("portee", "verif"):
        if not plein(c.get(k)): err.append(f"commentaire.{k} vide")
    def sections(nom, secs, n):
        if len(secs) != n: err.append(f"{nom} : {len(secs)} sections au lieu de {n}")
        for s in secs:
            if not plein(s.get("titre")) or not s.get("paragraphes"): err.append(f"{nom} : section incomplète")
            if s.get("source") != "Saint Thomas d’Aquin": err.append(f"{nom} : source de section « {s.get('source')} »")
            u = (s.get("citation") or {}).get("url", "")
            if "corpusthomisticum" in u and "#" not in u: err.append(f"{nom} : citation sans ancre")
    def sources(nom, lst):
        if not lst: err.append(f"{nom} : sources vides")
        for s in lst or []:
            if not plein(s.get("label")) or not plein(s.get("detail")): err.append(f"{nom} : source incomplète")
            if "corpusthomisticum" in s.get("url", "") and "#" not in s["url"]: err.append(f"{nom} : URL du Corpus sans ancre")
    sections("textes", c.get("sections") or [], 4)
    for nom, d in (("textes", t), ("méditation", m)):
        if len(d.get("essentiel") or []) != 3 or not all(plein(x) for x in d.get("essentiel") or []): err.append(f"{nom} : 3 points")
        if not plein(d.get("resolution")): err.append(f"{nom} : résolution absente")
        sources(nom, d.get("sources"))
    fe = t.get("fete") or {}
    if fe.get("titre") not in ("Le sens de la fête", "Le saint du jour") or not plein(fe.get("texte")): err.append("encadré « fete » incomplet")
    if not plein(m.get("titre")) or len(m.get("texte") or []) < 2: err.append("méditation : titre ou texte absent")
    sections("méditation", (m.get("commentaire") or {}).get("sections") or [], 3)
    if not ((m.get("sources") or [{}])[0].get("label", "")).startswith(MOELLE): err.append("méditation : la première source doit être La Moelle")
    brut = json.dumps(j, ensure_ascii=False)
    for mo in INTERDIT.finditer(brut): err.append(f"mention interdite « {mo.group(0)} »")
    return err

def charger():
    jours = {}
    for f in sorted(DOSSIER.glob("[0-9][0-9][0-9][0-9]-[0-9][0-9].json")):
        jours.update(json.loads(f.read_text(encoding="utf-8")))
    return jours

def rapport(paires):
    ok = True
    for cle, j in paires:
        e = defauts(j); ok &= not e
        print(("✓ " if not e else "✗ ") + cle)
        for x in e: print("    · " + x)
    return 0 if ok else 1

def main(a):
    if not a: raise SystemExit(__doc__)
    if a[0] == "a-preparer":
        fenetre = int(a[a.index("--fenetre") + 1]) if "--fenetre" in a else 30
        maxi = int(a[a.index("--max") + 1]) if "--max" in a else 10**6
        jours, auj = charger(), datetime.now(ZoneInfo("Europe/Paris")).date()
        dates = [(auj + timedelta(days=i)).isoformat() for i in range(fenetre)]
        for d in [d for d in dates if defauts(jours.get(d))][:maxi]: print(d)
        return 0
    if a[0] == "valider":
        jours = charger(); return rapport([(d, jours.get(d)) for d in a[1:]])
    if a[0] == "fragment":
        return rapport([kv for f in a[1:] for kv in json.load(open(f, encoding="utf-8")).items()])
    raise SystemExit(__doc__)

if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
