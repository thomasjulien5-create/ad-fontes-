#!/usr/bin/env python3
"""Ad Fontes — production automatique des Textes du jour et de la Méditation.

Sans IA : le script ne rédige rien, il assemble des textes existants.

Pour chaque date :
  1. Divinum Officium (rubriques de 1960) donne le jour liturgique retenu
     — fête, classe, couleur, commémoraisons — et les lectures de la messe :
     références de la Leçon ou de l'Épître et de l'Évangile, avec leur latin
     (le texte du Missel, c'est-à-dire la Vulgate).
     Le site étant fermé aux requêtes automatiques, on exécute son propre
     programme à partir de son dépôt public (voir divinum-officium-jour.pl).
     Les noms français des fêtes viennent de noms-1962.json (ceux de Divinum
     Officium sont incomplets) ; ceux du temporal sont composés ici.
  2. Le français est pris, verset par verset, dans la Bible Crampon 1923
     publiée sur Wikisource.
  3. La méditation est lue dans donnees/moelle.json, le fichier extrait des
     deux tomes de La Moelle de saint Thomas d'Aquin, rangé par jour
     liturgique (voir lire_moelle).

Les commentaires, les trois points et la résolution restent préparés à part :
le script n'y touche pas. Il ne remplace jamais une journée déjà écrite ; il
ajoute seulement ce qui manque (la journée entière, ou son bloc « textes »
ou « meditation » s'il est absent).

Utilisation :
  python3 .github/scripts/generer-jours.py                  # 30 jours à partir d'aujourd'hui (Paris)
  python3 .github/scripts/generer-jours.py --jours 10
  python3 .github/scripts/generer-jours.py --date 2026-11-02 --afficher   # une date, sans rien écrire

Variables d'environnement :
  ADF_DIVINUM_OFFICIUM  dossier du dépôt Divinum Officium (défaut : .cache/divinum-officium)

Pour l'essayer sur son poste : installer le module CGI de Perl (paquet libcgi-pm-perl),
puis récupérer Divinum Officium comme le fait .github/workflows/generation-quotidienne.yml.

Un jour que le script ne sait pas établir sûrement (Passion de la Semaine sainte, verset
que la Crampon numérote autrement, pièce manquante chez Divinum Officium) n'est pas écrit,
ou sa lecture reste sans français ; tout est signalé dans le bilan de l'action.
"""

import argparse
import datetime
import html
import json
import os
import re
import shutil
import subprocess
import sys
import time
import unicodedata
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path
from zoneinfo import ZoneInfo

RACINE = Path(__file__).resolve().parents[2]
DOSSIER_JOURS = RACINE / "donnees" / "jours"
FICHIER_MOELLE = RACINE / "donnees" / "moelle.json"
DOSSIER_DO = Path(os.environ.get("ADF_DIVINUM_OFFICIUM", RACINE / ".cache" / "divinum-officium"))
SONDE_DO = Path(__file__).resolve().parent / "divinum-officium-jour.pl"
VERSION_DO = "Rubrics 1960 - 1960"
FUSEAU = ZoneInfo("Europe/Paris")
AGENT = "AdFontes-textes-du-jour/1.0 (https://github.com/thomasjulien5-create/ad-fontes-)"
API_WIKISOURCE = "https://fr.wikisource.org/w/api.php"
CRAMPON = "Bible Crampon 1923"


class Echec(Exception):
    """Une donnée ne peut pas être établie sûrement : on n'écrit rien pour ce bloc."""


def sans_accents(s):
    return "".join(c for c in unicodedata.normalize("NFD", s) if unicodedata.category(c) != "Mn")


# ============================================================
#  Livres de la Bible : abréviation de Divinum Officium →
#  (nom affiché, page Wikisource de la Crampon, livre du Nouveau Testament ?)
# ============================================================
LIVRES = {}
for abreviations, nom, page, nt in [
    ("Gen", "Genèse", "Genèse", False),
    ("Exod Ex", "Exode", "Exode", False),
    ("Lev Levit", "Lévitique", "Lévitique", False),
    ("Num", "Nombres", "Nombres", False),
    ("Deut", "Deutéronome", "Deutéronome", False),
    ("Jos Josue", "Josué", "Josué", False),
    ("Judic Jdc", "Juges", "Juges", False),
    ("Ruth", "Ruth", "Ruth", False),
    ("1Reg 1Sam", "I Samuel (I Rois)", "1 Samuel", False),
    ("2Reg 2Sam", "II Samuel (II Rois)", "2 Samuel", False),
    ("3Reg 1Kgs", "I Rois (III Rois)", "1 Rois", False),
    ("4Reg 2Kgs", "II Rois (IV Rois)", "2 Rois", False),
    ("1Par 1Chr", "I Chroniques", "1 Chroniques", False),
    ("2Par 2Chr", "II Chroniques", "2 Chroniques", False),
    ("1Esdr Esdr", "Esdras", "Esdras", False),
    ("2Esdr Neh", "Néhémie (II Esdras)", "Néhémie", False),
    ("Tob", "Tobie", "Tobie", False),
    ("Judith Jdt", "Judith", "Judith", False),
    ("Esth", "Esther", "Esther", False),
    ("Job", "Job", "Job", False),
    ("Prov", "Proverbes", "Proverbes", False),
    ("Eccl Eccles", "Ecclésiaste", "Ecclésiaste", False),
    ("Cant", "Cantique des cantiques", "Cantique", False),
    ("Sap", "Sagesse", "Sagesse", False),
    ("Eccli Sir", "Ecclésiastique", "Ecclésiastique", False),
    ("Is Isa Isai", "Isaïe", "Isaïe", False),
    ("Jer", "Jérémie", "Jérémie", False),
    ("Lam Thren", "Lamentations", "Lamentations", False),
    ("Bar", "Baruch", "Baruch", False),
    ("Ezech Ez", "Ézéchiel", "Ézéchiel", False),
    ("Dan", "Daniel", "Daniel", False),
    ("Osee Os", "Osée", "Osée", False),
    ("Joel", "Joël", "Joël", False),
    ("Amos", "Amos", "Amos", False),
    ("Abd", "Abdias", "Abdias", False),
    ("Jon Jonas Jonae", "Jonas", "Jonas", False),
    ("Mich", "Michée", "Michée", False),
    ("Nah", "Nahum", "Nahum", False),
    ("Hab", "Habacuc", "Habacuc", False),
    ("Soph", "Sophonie", "Sophonie", False),
    ("Agg", "Aggée", "Aggée", False),
    ("Zach", "Zacharie", "Zacharie", False),
    ("Mal Malach", "Malachie", "Malachie", False),
    ("1Mach", "I Machabées", "1 Machabées", False),
    ("2Mach", "II Machabées", "2 Machabées", False),
    ("Matt Mt", "Matthieu", "Matthieu", True),
    ("Marc Mc Mk", "Marc", "Marc", True),
    ("Luc Lc Lk", "Luc", "Luc", True),
    ("Joann Joannes Joh Jo Jn John", "Jean", "Jean", True),
    ("Act Acts", "Actes des Apôtres", "Actes", True),
    ("Rom", "Romains", "Romains", True),
    ("1Cor", "I Corinthiens", "1 Corinthiens", True),
    ("2Cor", "II Corinthiens", "2 Corinthiens", True),
    ("Gal", "Galates", "Galates", True),
    ("Eph Ephes", "Éphésiens", "Éphésiens", True),
    ("Phil Philipp", "Philippiens", "Philippiens", True),
    ("Col", "Colossiens", "Colossiens", True),
    ("1Thess", "I Thessaloniciens", "1 Thessaloniciens", True),
    ("2Thess", "II Thessaloniciens", "2 Thessaloniciens", True),
    ("1Tim", "I Timothée", "1 Timothée", True),
    ("2Tim", "II Timothée", "2 Timothée", True),
    ("Tit", "Tite", "Tite", True),
    ("Phlm Philem", "Philémon", "Philémon", True),
    ("Heb Hebr", "Hébreux", "Hébreux", True),
    ("Jac Jas Jc", "Jacques", "Jacques", True),
    ("1Pet 1Petri", "I Pierre", "1 Pierre", True),
    ("2Pet 2Petri", "II Pierre", "2 Pierre", True),
    ("1Joann 1Joannes 1Joannnes 1John 1Jo", "I Jean", "1 Jean", True),
    ("2Joann 2John", "II Jean", "2 Jean", True),
    ("3Joann 3John", "III Jean", "3 Jean", True),
    ("Jud Judae", "Jude", "Jude", True),
    ("Apoc Apc", "Apocalypse", "Apocalypse", True),
]:
    for a in abreviations.split():
        LIVRES[a.lower()] = (nom, page, nt)
SAPIENTIAUX = {"Proverbes", "Ecclésiaste", "Cantique des cantiques", "Sagesse", "Ecclésiastique"}


def lire_reference(ref):
    """« 1 Cor 1:4-8 » ou « Mich 7:14; 7:16; 7:18-20 » → (livre, [(chap, v1, chap2, v2), …])."""
    ref = sans_accents(ref).replace("æ", "ae").strip().rstrip(".")
    m = re.match(r"^((?:[1-4]\.?\s*)?[A-Za-z]+)\.?\s+(.+)$", ref)
    if not m:
        raise Echec(f"référence illisible : {ref}")
    abr = re.sub(r"[\s.]", "", m.group(1)).lower()
    livre = LIVRES.get(abr) or LIVRES.get(re.sub(r"^(\d?)i(?=[aeiou])", r"\1j", abr))  # Ioann → Joann
    if not livre:
        raise Echec(f"livre inconnu : {m.group(1)} ({ref})")
    # « Act 1, 15-26 » : la virgule sépare parfois le chapitre du verset.
    passages = ";".join(p if ":" in p else re.sub(r"^\s*(\d+)\s*,\s*", r"\1:", p, count=1)
                        for p in m.group(2).split(";"))
    morceaux, chap = [], None
    for part in re.split(r"[;,]\s*", passages):
        part = part.strip()
        if not part:
            continue
        pm = re.match(r"^(?:(\d+):)?(\d+)[a-d]?(?:\s*-\s*(?:(\d+):)?(\d+)[a-d]?)?$", part)
        if not pm:
            raise Echec(f"passage illisible : {part} ({ref})")
        if pm.group(1):
            chap = int(pm.group(1))
        if chap is None:
            raise Echec(f"chapitre manquant : {ref}")
        v1 = int(pm.group(2))
        chap2 = int(pm.group(3)) if pm.group(3) else chap
        v2 = int(pm.group(4)) if pm.group(4) else v1
        morceaux.append((chap, v1, chap2, v2))
        chap = chap2
    if not morceaux:
        raise Echec(f"référence vide : {ref}")
    return livre, morceaux


def reference_francaise(livre, morceaux):
    """(livre, morceaux) → « I Corinthiens 1, 4-8 », « Michée 7, 14. 16. 18-20 », « II Corinthiens 10, 17-18 ; 11, 1-2 »."""
    groupes, courant, chap_courant = [], [], None
    for c1, v1, c2, v2 in morceaux:
        if c1 != c2:
            if courant:
                groupes.append(f"{chap_courant}, " + ". ".join(courant))
                courant = []
            groupes.append(f"{c1}, {v1} – {c2}, {v2}")
            chap_courant = None
            continue
        if c1 != chap_courant and courant:
            groupes.append(f"{chap_courant}, " + ". ".join(courant))
            courant = []
        chap_courant = c1
        courant.append(f"{v1}-{v2}" if v2 != v1 else f"{v1}")
    if courant:
        groupes.append(f"{chap_courant}, " + ". ".join(courant))
    return f"{livre[0]} " + " ; ".join(groupes)


# ============================================================
#  Divinum Officium
# ============================================================
# Jours à plusieurs messes : celle que l'on retient (Divinum Officium prend la première par défaut).
MESSE_RETENUE = {"Sancti/12-25": 3,        # Noël : messe du jour
                 "Tempora/Quad6-4r": 2}    # Jeudi saint : messe du soir, in Cena Domini


def interroger_do(date, messe=None):
    dossier = DOSSIER_DO / "web" / "cgi-bin" / "missa"
    if not (dossier / "missa.pl").exists():
        raise SystemExit(f"Divinum Officium introuvable dans {DOSSIER_DO} (variable ADF_DIVINUM_OFFICIUM).")
    sonde = dossier / "adf-jour.pl"
    if not sonde.exists() or sonde.read_bytes() != SONDE_DO.read_bytes():
        shutil.copyfile(SONDE_DO, sonde)
    requete = urllib.parse.urlencode({
        "date1": date.strftime("%m-%d-%Y"),
        "version": VERSION_DO,
        "lang2": "Francais",
        "command": "praySancta Missa",
        **({"missanumber": messe} if messe else {}),
    })
    env = dict(os.environ, QUERY_STRING=requete, REQUEST_METHOD="GET")
    r = subprocess.run(["perl", "adf-jour.pl"], cwd=dossier, env=env, capture_output=True, timeout=120)
    if r.returncode != 0 or not r.stdout:
        raise Echec(f"Divinum Officium : échec pour {date} — {r.stderr.decode('utf-8', 'replace')[-500:]}")
    info = json.loads(r.stdout.decode("utf-8"))
    base = fichier_do(info.get("gagnant", ""))
    if messe is None and base in MESSE_RETENUE:
        return interroger_do(date, MESSE_RETENUE[base])
    return info


def fichier_do(chemin):
    """« Sancti/12-25m1.txt » → « Sancti/12-25 » (sans extension ni numéro de messe)."""
    return re.sub(r"m\d+$", "", chemin.removesuffix(".txt"))


def texte_brut(fragment):
    t = re.sub(r"<br\s*/?>", "\n", fragment, flags=re.I)
    t = re.sub(r"<[^>]+>", "", t)
    t = html.unescape(t).replace(" ", " ")
    return [re.sub(r"\s+", " ", l).strip() for l in t.split("\n")]


def cellules_latines(page):
    """Les pièces de la colonne latine, avec leur titre rouge (Lectio, Evangelium…).
    Aux Quatre-Temps, une même cellule enchaîne plusieurs pièces (Lectio, Graduale, Oratio…)."""
    cellules = []
    for ligne in re.findall(r"<TR>(.*?)</TR>", page, flags=re.S | re.I):
        tds = re.findall(r"<TD[^>]*>(.*?)</TD>", ligne, flags=re.S | re.I)
        if not tds:
            continue
        morceaux = re.split(r"<FONT SIZE='\+1' COLOR=\"red\"><B><I>(.*?)</I></B></FONT>", tds[0], flags=re.S | re.I)
        for i in range(1, len(morceaux) - 1, 2):
            cellules.append((texte_brut(morceaux[i])[0].strip(), morceaux[i + 1]))
    return cellules


RE_REF = re.compile(r"<FONT COLOR=\"red\"><I>((?:[1-4]\.? ?)?[A-ZÆ][^\W\d_]+\.? \d+ ?[:,] ?\d[^<]*)</I></FONT>")


def lecture_de_cellule(td, evangile):
    """Référence et texte latin d'une cellule Lectio ou Evangelium de la page de la messe."""
    manque = re.search(r"\S+ is missing!|\w+ missing!", td)
    if manque:
        raise Echec(f"Divinum Officium : pièce introuvable dans ses données ({manque.group(0)})")
    refs = list(RE_REF.finditer(td))
    if not refs:
        raise Echec("référence absente d'une lecture de Divinum Officium")
    m = refs[-1] if evangile else refs[0]
    if evangile and re.search(r"P[aá]ssio D[oó]mini", " ".join(texte_brut(td[:m.start()]))):
        # Semaine sainte : Divinum Officium ne donne ici que la fin de la Passion.
        raise Echec("jour de la Passion (Semaine sainte) : lectures à préparer à la main")
    lignes = [l for l in texte_brut(td[m.end():]) if l]
    corps = []
    for l in lignes:
        if re.match(r"^(℟\.|R\.|S\.|℣\.)", l):
            break
        corps.append(l)
    if not corps:
        raise Echec("texte latin vide")
    return m.group(1).strip(), [" ".join(corps)]


def lectures_do(page):
    lectures, evangile = [], None
    for titre, td in cellules_latines(page):
        if re.match(r"^Passio", titre):
            # Semaine sainte : la Passion est chantée en une pièce à part, l'Évangile n'en garde que la fin.
            raise Echec("jour de la Passion (Semaine sainte) : lectures à préparer à la main")
        if re.match(r"^Lectio", titre):
            lectures.append(lecture_de_cellule(td, False))
        elif titre == "Evangelium":
            evangile = lecture_de_cellule(td, True)
    if not lectures or not evangile:
        raise Echec("lectures de la messe introuvables dans la page de Divinum Officium")
    return lectures, evangile


# ---------- Noms, classe, couleur ----------
NOMS = {k: v for k, v in json.loads((Path(__file__).resolve().parent / "noms-1962.json").read_text("utf-8")).items()
        if not k.startswith("_")}
NOMS_INCONNUS = set()  # fichiers de Divinum Officium absents de noms-1962.json, signalés dans le bilan

ROMAINS = ["", "I", "II", "III", "IV", "V", "VI", "VII", "VIII", "IX", "X", "XI", "XII", "XIII", "XIV", "XV",
           "XVI", "XVII", "XVIII", "XIX", "XX", "XXI", "XXII", "XXIII", "XXIV", "XXV", "XXVI", "XXVII", "XXVIII"]
JOURS = ["Dimanche", "Lundi", "Mardi", "Mercredi", "Jeudi", "Vendredi", "Samedi"]
# Titres latins du temporal qui sont des fêtes (Divinum Officium les range dans Tempora).
FETES_DU_TEMPORAL = [
    (r"Sanct\w* Famili", "Sainte Famille de Jésus, Marie et Joseph"),
    (r"Sanctissimi Nominis Jesu", "Très Saint Nom de Jésus"),
    (r"Sanctissimæ Trinitatis|Sanctissimae Trinitatis", "Très Sainte Trinité"),
    (r"Corporis Christi", "Fête-Dieu"),
    (r"Cordis Domini", "Sacré-Cœur de Jésus"),
    (r"^In Ascensione Domini", "Ascension de Notre-Seigneur"),
]
QUATRE_TEMPS = {"Adv": "de l’Avent", "Quad": "du Carême", "Pasc": "de Pentecôte", "Pent": "de septembre"}


def ordinal(n):
    return f"{ROMAINS[n]}er" if n == 1 else f"{ROMAINS[n]}e"


def ordinal_f(n):
    return f"{ROMAINS[n]}re" if n == 1 else f"{ROMAINS[n]}e"


def paques(annee):
    """Dimanche de Pâques (comput grégorien)."""
    a, b, c = annee % 19, annee // 100, annee % 100
    d, e = divmod(b, 4)
    f = (b + 8) // 25
    g = (b - f + 1) // 3
    h = (19 * a + b - d - g + 15) % 30
    i, k = divmod(c, 4)
    l = (32 + 2 * e + 2 * i - h - k) % 7
    m = (a + 11 * h + 22 * l) // 451
    mois, jour = divmod(h + l - 7 * m + 114, 31)
    return datetime.date(annee, mois, jour + 1)


def nom_temporal(fichier, latin, date):
    """Nom français d'un jour du temporal, d'après son fichier Divinum Officium (« Tempora/Pent18-4 »)
    et son titre latin (pour les Quatre-Temps et les fêtes)."""
    for motif, nom in FETES_DU_TEMPORAL:
        if re.search(motif, latin, re.I):
            return nom, ""
    m = re.match(r"^Tempora/(Adv|Nat|Epi|Quadp|Quad|Pasc|PentEpi|Pent)(\d+)(?:-(\d))?", fichier)
    if not m:
        return None
    temps, n, j = m.group(1), int(m.group(2)), int(m.group(3) or date.isoweekday() % 7)
    jour = JOURS[j]
    if re.search(r"Quat+uor Temporum", latin, re.I):
        saison = "Pasc" if temps == "Pasc" else ("Pent" if temps.startswith("Pent") else temps)
        return f"{jour} des Quatre-Temps {QUATRE_TEMPS.get(saison, '')}".strip(), "Férie des Quatre-Temps"
    qualite = "Dimanche" if j == 0 else "Férie"
    if temps == "Adv":
        return (f"{ordinal(n)} dimanche de l’Avent" if j == 0 else f"{jour} de la {ordinal_f(n)} semaine de l’Avent"), qualite
    if temps == "Nat":
        if fichier.startswith("Tempora/Nat1-0"):
            return "Dimanche dans l’octave de la Nativité", "Dimanche"
        if 26 <= n <= 31:
            return f"{ordinal(n - 24)} jour dans l’octave de la Nativité", ""
        return "Férie du temps de Noël", "Férie"
    if temps == "Epi":
        return (f"{ordinal(n)} dimanche après l’Épiphanie" if j == 0 else f"{jour} de la {ordinal_f(n)} semaine après l’Épiphanie"), qualite
    if temps == "Quadp":
        nom = ["", "Septuagésime", "Sexagésime", "Quinquagésime"][n]
        if n == 3 and j == 3:
            return "Mercredi des Cendres", "Férie"
        if n == 3 and j > 3:
            return f"{jour} après les Cendres", "Férie"
        return (f"Dimanche de la {nom}" if j == 0 else f"{jour} de la semaine de la {nom}"), qualite
    if temps == "Quad":
        if n <= 4:
            return (f"{ordinal(n)} dimanche de Carême" if j == 0 else f"{jour} de la {ordinal_f(n)} semaine de Carême"), qualite
        if n == 5:
            return ("Dimanche de la Passion" if j == 0 else f"{jour} de la semaine de la Passion"), qualite
        return ("Dimanche des Rameaux" if j == 0 else f"{jour} saint"), qualite
    if temps == "Pasc":
        if n == 0:
            return ("Dimanche de Pâques" if j == 0 else ("Samedi in albis" if j == 6 else f"{jour} de Pâques")), ("Dimanche" if j == 0 else "")
        if n == 1 and j == 0:
            return "Dimanche in albis", "Dimanche"
        if n == 5 and j in (1, 2, 3):
            return ("Vigile de l’Ascension" if j == 3 else f"{jour} des Rogations"), qualite
        if (n == 5 and j > 4) or (n == 6 and j < 6):
            return ("Dimanche après l’Ascension" if j == 0 else f"{jour} après l’Ascension"), qualite
        if n == 6 and j == 6:
            return "Vigile de la Pentecôte", ""
        if n == 7:
            return ("Dimanche de la Pentecôte" if j == 0 else f"{jour} de la Pentecôte"), ("Dimanche" if j == 0 else "")
        return (f"{ordinal(n)} dimanche après Pâques" if j == 0 else f"{jour} de la {ordinal_f(n)} semaine après Pâques"), qualite
    # Après la Pentecôte : semaine réelle, comptée depuis la Pentecôte (les messes des dimanches
    # après l'Épiphanie reportées, et celle du dernier dimanche, gardent leur rang dans l'année).
    pentecote = paques(date.year) + datetime.timedelta(days=49)
    semaine = (date - pentecote).days // 7
    noel = datetime.date(date.year, 12, 25)
    avent = noel - datetime.timedelta(days=(noel.isoweekday() % 7 or 7) + 21)  # Ier dimanche de l'Avent
    if 1 <= (avent - date).days <= 7:
        nom = (f"{ordinal(semaine)} et dernier dimanche après la Pentecôte" if j == 0
               else f"{jour} de la {ordinal_f(semaine)} et dernière semaine après la Pentecôte")
    else:
        nom = f"{ordinal(semaine)} dimanche après la Pentecôte" if j == 0 else f"{jour} de la {ordinal_f(semaine)} semaine après la Pentecôte"
    if temps == "PentEpi":
        qualite = f"{qualite} — messe du {ordinal(n)} dimanche après l’Épiphanie"
    return nom, qualite


def nom_et_qualite(info, date):
    """Nom de la fête et qualité (« Confesseur », « Férie »…), en français."""
    fichier = fichier_do(info.get("gagnant", ""))
    if fichier in NOMS:
        return tuple(NOMS[fichier])
    if fichier.startswith("Tempora/"):
        t = nom_temporal(fichier, info["titre_latin"], date)
        if t:
            return t
    NOMS_INCONNUS.add(f"{fichier} ({info['titre_latin']})")
    fr = info.get("office_francais") or ""
    if fr and fr != info.get("office_latin"):
        nom, _, qualite = fr.partition(", ")
        return nom, qualite
    return info["titre_latin"], ""


def classe(info):
    m = re.search(r"~.*?\b([IV]+)\. classis", info.get("entete", ""))
    if not m:
        raise Echec(f"classe introuvable : {info.get('entete')}")
    return f"{ordinal_f(ROMAINS.index(m.group(1)))} classe"


COULEURS = {"green": "vert", "purple": "violet", "red": "rouge", "grey": "noir", "black": "blanc", "blue": "blanc"}


def couleur(info):
    if re.match(r"Tempora/(Adv3-0|Quad4-0)", info.get("gagnant", "")):
        return "rose"
    return COULEURS.get(info.get("couleur"), "blanc")


def en_commemoraison(nom, qualite):
    """[« Saint Hilarion », « Abbé »] → « saint Hilarion, abbé »."""
    nom = re.sub(r"^(Saint|Sainte|Saints|Saintes|Les|Le|La)\b", lambda m: m.group(1).lower(), nom)
    return f"{nom}, {qualite.lower().replace('l’église', 'l’Église')}" if qualite else nom


def commemoraisons(info, date):
    sortie = []
    for c in info.get("commemoraisons", []):
        fichier = fichier_do(c.get("fichier", ""))
        if fichier in NOMS:
            texte = en_commemoraison(*NOMS[fichier])
        elif fichier.startswith("Tempora/") and nom_temporal(fichier, c.get("latin", ""), date):
            nom = nom_temporal(fichier, c.get("latin", ""), date)[0]
            texte = nom if re.match(r"^[IVX]+(?:er|e)\b", nom) else nom[0].lower() + nom[1:]
        else:
            NOMS_INCONNUS.add(f"{fichier} ({c.get('latin')})")
            texte = c.get("francais") or c.get("latin") or ""
        if texte and texte not in sortie:
            sortie.append(texte)
    return sortie


# ============================================================
#  Bible Crampon 1923, sur Wikisource
# ============================================================
_LIVRES_CRAMPON = {}


def wikisource(page):
    params = urllib.parse.urlencode({"action": "parse", "page": page, "prop": "text", "format": "json",
                                     "formatversion": "2", "redirects": "1"})
    for essai in range(6):
        try:
            req = urllib.request.Request(f"{API_WIKISOURCE}?{params}", headers={"User-Agent": AGENT})
            with urllib.request.urlopen(req, timeout=60) as r:
                d = json.loads(r.read().decode("utf-8"))
            if "error" in d:
                raise Echec(f"Wikisource : {d['error'].get('info')} ({page})")
            return d["parse"]["text"]
        except urllib.error.HTTPError as e:
            if e.code not in (429, 500, 502, 503, 504):
                raise Echec(f"Wikisource : HTTP {e.code} ({page})")
            attente = int(e.headers.get("Retry-After") or 0) or 5 * (essai + 1)
        except (urllib.error.URLError, TimeoutError) as e:
            attente = 5 * (essai + 1)
            print(f"  … Wikisource injoignable ({e}), nouvel essai dans {attente} s", file=sys.stderr)
        time.sleep(attente)
    raise Echec(f"Wikisource ne répond pas ({page})")


def versets_crampon(page):
    """Page d'un livre → {(chap, verset): (morceaux de texte, début de paragraphe ?)}.
    Un verset a plusieurs morceaux quand un paragraphe (ou une strophe) s'ouvre en son milieu."""
    if page in _LIVRES_CRAMPON:
        return _LIVRES_CRAMPON[page]
    h = wikisource(f"{CRAMPON}/{page}")
    time.sleep(1)  # courtoisie envers l'API
    for fin in ('class="references"', "mw-references-wrap", "<!--"):
        if fin in h:
            i = h.index(fin)
            h = h[:h.rfind("<", 0, i) if fin != "<!--" else i]  # couper avant la balise qui porte la marque
    # Retirer notes, numéros de page et de verset, numéros et sommaires de chapitre.
    h = re.sub(r"<sup[^>]*class=\"reference\"[^>]*>.*?</sup>", "", h, flags=re.S)
    h = re.sub(r"<sup class=\"verset-num\".*?</sup>", "", h, flags=re.S)
    h = re.sub(r"<span[^>]*class=\"pagenum[^\"]*\"[^>]*>\s*</span>", "", h)
    h = re.sub(r"<div class=\"alineanegatif\".*?</div>", "", h, flags=re.S)
    h = re.sub(r"<div style=\"margin-left[^\"]*\"><a href=\"#Sommaire\">.*?</div>", "", h, flags=re.S)
    # Paragraphes et strophes → ¶ ; simples retours à la ligne des vers → espace.
    h = re.sub(r"<br\s*/?>\s*(?:<br\s*/?>\s*)+", " ¶ ", h)
    h = re.sub(r"</?(?:p|div|dl|dd|blockquote)\b[^>]*>", " ¶ ", h)
    h = re.sub(r"<br\s*/?>", " ", h)
    decoupe = re.split(r"<span id=\"(\d+)-(\d+)\">", h)
    versets, debut = {}, True
    for i in range(1, len(decoupe) - 2, 3):
        chap, v = int(decoupe[i]), int(decoupe[i + 1])
        t = html.unescape(re.sub(r"<[^>]+>", "", decoupe[i + 2])).replace("\u00a0", " ")
        morceaux = [re.sub(r"\s+([,.])", r"\1", re.sub(r"\s+", " ", m)).strip() for m in t.split("¶")]
        pleins = [m for m in morceaux if m]
        if pleins:
            versets[(chap, v)] = (pleins, debut or not morceaux[0])
        debut = not morceaux[-1] if pleins else debut
    if not versets:
        raise Echec(f"aucun verset lu dans la Crampon : {page}")
    _LIVRES_CRAMPON[page] = versets
    return versets


def numero_crampon(page, c, v):
    """La Crampon suit l'hébreu là où la Vulgate découpe autrement les chapitres."""
    if page == "Joël":
        if c == 2 and v >= 28:
            return 3, v - 27
        if c == 3:
            return 4, v
    if page == "Malachie" and c == 4:
        return 3, v + 18
    if page == "1 Rois":
        if c == 4 and v >= 21:
            return 5, v - 20
        if c == 5:
            return 5, v + 14
    return c, v


def texte_crampon(livre, morceaux):
    """Versets demandés, regroupés selon les paragraphes et strophes de la Crampon."""
    versets = versets_crampon(livre[1])
    paragraphes, courant = [], []

    def clore():
        if courant:
            paragraphes.append(" ".join(courant))
            courant.clear()

    for c1, v1, c2, v2 in morceaux:
        c, v = c1, v1
        while (c, v) <= (c2, v2):
            cle = numero_crampon(livre[1], c, v)
            if cle not in versets:
                if c < c2 and numero_crampon(livre[1], c + 1, 1) in versets:
                    c, v = c + 1, 1
                    continue
                raise Echec(f"verset absent de la Crampon : {livre[1]} {c}, {v}")
            textes, nouveau = versets[cle]
            if nouveau:
                clore()
            for n, t in enumerate(textes):
                if n:
                    clore()
                courant.append(t)
            v += 1
        # Un passage sauté (« 14. 16. 18-20 ») ouvre un nouveau paragraphe.
        clore()
    return paragraphes


INCIPITS = [
    (r"^In illo tempore", "En ce temps-là :"),
    (r"^In diebus illis", "En ces jours-là :"),
    (r"^Fratres", "Mes frères :"),
    (r"^Carissimi", "Mes bien-aimés :"),
    (r"^Carissime", "Mon bien-aimé :"),
    (r"^Dilectissimi", "Mes bien-aimés :"),
    (r"^Filioli", "Mes petits enfants :"),
    (r"^Haec dicit Dominus Deus", "Voici ce que dit le Seigneur Dieu :"),
    (r"^Haec dicit Dominus", "Voici ce que dit le Seigneur :"),
]


def incipit(latin, livre):
    l = sans_accents(latin).replace("æ", "ae").replace("Æ", "Ae")
    for motif, fr in INCIPITS:
        if re.match(motif, l, re.I):
            return fr
    if livre[0] in SAPIENTIAUX:
        return "Lecture du livre de la Sagesse."
    return None


def piece(ref_do, latin, titre=None):
    livre, morceaux = lire_reference(ref_do)
    p = {}
    if titre:
        p["titre"] = titre
    p["reference"] = reference_francaise(livre, morceaux)
    p["latin"] = latin
    try:
        p["francais"] = texte_crampon(livre, morceaux)
    except Echec as e:
        # Le reste de la journée est sûr : on garde la lecture (référence, latin) et on signale le manque,
        # que la vérification de 7 h relèvera aussi.
        p["francais"] = []
        p["_manque"] = f"{p['reference']} : {e}"
    inc = incipit(latin[0], livre)
    # Pas d'incipit si la Crampon commence déjà ainsi (« En ces jours-là, Pierre… »).
    if inc and not (p["francais"] and sans_accents(p["francais"][0]).lower().startswith(sans_accents(inc.rstrip(" :.")).lower())):
        p["incipit"] = inc
    return p, livre


ORDINAUX_LECONS = ["Première", "Deuxième", "Troisième", "Quatrième", "Cinquième", "Sixième"]


def propre(lectures, evangile):
    pieces = [piece(ref, latin) for ref, latin in lectures]
    sortie = {}
    derniere, livre = pieces[-1]
    if livre[2]:
        derniere["titre"] = "Épître"
        sortie["epitre"] = derniere
        lecons = pieces[:-1]
    else:
        lecons = pieces
    lecons = [p for p, _ in lecons]
    if len(lecons) == 1 and "epitre" not in sortie:
        lecons[0]["titre"] = "Leçon"
    else:
        for i, p in enumerate(lecons):
            p["titre"] = f"{ORDINAUX_LECONS[i]} leçon" if i < len(ORDINAUX_LECONS) else "Leçon"
    if lecons:
        sortie["lecon"] = lecons[0]
        if lecons[1:]:
            sortie["supplement"] = lecons[1:]
    ev, _ = piece(*evangile)
    sortie["evangile"] = ev
    # Ordre des clés conforme aux journées préparées à la main.
    ordre = ("titre", "reference", "incipit", "latin", "francais", "_manque")
    ranger = lambda p: {k: p[k] for k in ordre if k in p}
    return {k: ([ranger(p) for p in sortie[k]] if k == "supplement" else ranger(sortie[k]))
            for k in ("lecon", "supplement", "epitre", "evangile") if k in sortie}


def textes_du_jour(date):
    info = interroger_do(date)
    nom, qualite = nom_et_qualite(info, date)
    lectures, evangile = lectures_do(info["html"])
    liturgie = {"nom": nom, "qualite": qualite, "classe": classe(info), "couleur": couleur(info),
                "commemoraisons": commemoraisons(info, date)}
    if not qualite:
        del liturgie["qualite"]
    pr = propre(lectures, evangile)
    manques = [p.pop("_manque") for p in [pr.get("lecon"), *pr.get("supplement", []), pr.get("epitre"), pr.get("evangile")]
               if p and "_manque" in p]
    fichier = info.get("gagnant", "")
    livres = []
    for p in [pr.get("lecon"), *pr.get("supplement", []), pr.get("epitre"), pr.get("evangile")]:
        if p:
            livres.append(p["reference"])
    sources = [
        {"label": f"Missel romain de 1962 : {nom}",
         "detail": "Jour liturgique, classe, couleur, commémoraisons et texte latin des lectures d’après Divinum Officium (rubriques de 1960).",
         "url": f"https://github.com/DivinumOfficium/divinum-officium/blob/master/web/www/missa/Latin/{fichier}" if fichier else "https://www.divinumofficium.com/"},
        {"label": "Bible Crampon 1923 (Wikisource)",
         "detail": "Texte français des lectures : " + " ; ".join(livres) + ".",
         "url": "https://fr.wikisource.org/wiki/Bible_Crampon_1923"},
    ]
    return {"liturgie": liturgie, "propre": pr, "sources": sources}, info, manques


# ============================================================
#  La Moelle de saint Thomas d'Aquin
# ============================================================
def lire_moelle():
    """donnees/moelle.json : { "meditations": { clé: {titre, texte:[], sources:[], reserve?} } }.

    Les clés reprennent le rangement des deux tomes :
      « MM-JJ »     — les méditations datées (« 1er octobre » → « 10-01 ») ;
      « Quadp1-0 »… — les jours du temps mobile (de la Septuagésime au temps
                      pascal), notés comme dans Divinum Officium : semaine
                      (Adv, Epi, Quadp, Quad, Pasc, Pent + numéro), tiret,
                      jour (0 = dimanche … 6 = samedi).
    Pour une date, la méditation du temps mobile l'emporte si elle existe,
    sinon celle de la date civile.
    """
    if not FICHIER_MOELLE.exists():
        return {}
    return json.loads(FICHIER_MOELLE.read_text("utf-8")).get("meditations", {})


def meditation_du_jour(moelle, date, info):
    jour_semaine = (date.weekday() + 1) % 7
    cles = []
    if info and info.get("temporal"):
        cles.append(f"{info['temporal']}-{jour_semaine}")
    cles.append(date.strftime("%m-%d"))
    for cle in cles:
        if cle in moelle:
            m = moelle[cle]
            sortie = {"titre": m["titre"], "texte": m["texte"]}
            if m.get("reserve"):
                sortie["reserve"] = m["reserve"]
            if m.get("sources"):
                sortie["sources"] = m["sources"]
            return sortie, cle
    return None, cles


# ============================================================
#  Fichiers mensuels
# ============================================================
def charger_mois(mois):
    f = DOSSIER_JOURS / f"{mois}.json"
    return json.loads(f.read_text("utf-8")) if f.exists() else {}


def ecrire_mois(mois, jours):
    f = DOSSIER_JOURS / f"{mois}.json"
    ordonne = {k: jours[k] for k in sorted(jours)}
    f.write_text(json.dumps(ordonne, ensure_ascii=False, indent=1) + "\n", "utf-8")


def principal():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--jours", type=int, default=30, help="nombre de jours à couvrir, aujourd'hui inclus (défaut : 30)")
    ap.add_argument("--depuis", help="première date (AAAA-MM-JJ) ; défaut : aujourd'hui, heure de Paris")
    ap.add_argument("--date", help="une seule date (AAAA-MM-JJ)")
    ap.add_argument("--afficher", action="store_true", help="afficher le résultat sans rien écrire")
    args = ap.parse_args()

    if args.date:
        dates = [datetime.date.fromisoformat(args.date)]
    else:
        debut = datetime.date.fromisoformat(args.depuis) if args.depuis else datetime.datetime.now(FUSEAU).date()
        dates = [debut + datetime.timedelta(days=i) for i in range(args.jours)]

    moelle = lire_moelle()
    mois_charges, modifies, bilan = {}, set(), {"ajoutes": [], "incomplets": [], "echecs": []}

    for date in dates:
        cle, mois = date.isoformat(), date.strftime("%Y-%m")
        jours = mois_charges.setdefault(mois, charger_mois(mois))
        existant = jours.get(cle, {})
        besoin_textes = args.afficher or not existant.get("textes")
        besoin_medit = args.afficher or not existant.get("meditation")
        if not (besoin_textes or besoin_medit):
            continue

        nouveau, remarques, info = {}, [], None
        if besoin_textes:
            try:
                nouveau["textes"], info, manques = textes_du_jour(date)
                remarques += [f"français à établir — {m}" for m in manques]
            except Echec as e:
                remarques.append(f"textes : {e}")
        if besoin_medit:
            if info is None:
                try:
                    info = interroger_do(date)
                except Echec as e:
                    remarques.append(f"calendrier : {e}")
            med, cles = meditation_du_jour(moelle, date, info)
            if med:
                nouveau["meditation"] = med
            else:
                remarques.append(f"méditation : aucune entrée dans {FICHIER_MOELLE.relative_to(RACINE)} ({' ou '.join(cles)})")

        if args.afficher:
            print(json.dumps({cle: nouveau}, ensure_ascii=False, indent=1))
            for r in remarques:
                print(f"  ! {r}", file=sys.stderr)
            continue

        if nouveau:
            fusion = dict(existant)
            for bloc, contenu in nouveau.items():
                fusion.setdefault(bloc, contenu)
            jours[cle] = {k: fusion[k] for k in ("textes", "meditation") if k in fusion} | {k: v for k, v in fusion.items() if k not in ("textes", "meditation")}
            modifies.add(mois)
            nom = fusion.get("textes", {}).get("liturgie", {}).get("nom", "?")
            bilan["ajoutes"].append(f"{cle} — {nom} ({', '.join(nouveau)})")
            print(f"✓ {cle} — {nom} : {', '.join(nouveau)} ajouté(s)")
        for r in remarques:
            (bilan["incomplets"] if nouveau else bilan["echecs"]).append(f"{cle} — {r}")
            print(f"  ! {cle} — {r}")

    for mois in sorted(modifies):
        ecrire_mois(mois, mois_charges[mois])
        print(f"→ donnees/jours/{mois}.json écrit")

    if not args.afficher:
        print(f"\n{len(bilan['ajoutes'])} journée(s) complétée(s) ; {len(bilan['incomplets']) + len(bilan['echecs'])} point(s) non résolu(s).")
        for n in sorted(NOMS_INCONNUS):
            print(f"  ! nom français absent de noms-1962.json : {n}")
        sortie = os.environ.get("GITHUB_STEP_SUMMARY")
        if sortie:
            with open(sortie, "a", encoding="utf-8") as f:
                f.write("## Textes du jour et méditations\n\n")
                if NOMS_INCONNUS:
                    bilan["noms"] = [f"{n} : à ajouter à .github/scripts/noms-1962.json" for n in sorted(NOMS_INCONNUS)]
                for titre, cle in (("Ajouts", "ajoutes"), ("Incomplets", "incomplets"), ("Échecs", "echecs"), ("Noms français manquants", "noms")):
                    if bilan.get(cle):
                        f.write(f"### {titre}\n\n" + "".join(f"- {l}\n" for l in bilan[cle]) + "\n")
                if not any(bilan.values()):
                    f.write("Rien à ajouter : les journées à venir sont déjà en place.\n")


if __name__ == "__main__":
    principal()
