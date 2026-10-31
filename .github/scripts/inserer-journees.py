#!/usr/bin/env python3
"""Ad Fontes — insère des journées préparées dans donnees/jours/AAAA-MM.json.

Usage : python3 .github/scripts/inserer-journees.py fragment.json [autre.json …]

Chaque fragment est un objet JSON { "AAAA-MM-JJ": { "textes": …, "meditation": … }, … }.
Les journées sont rangées dans le fichier du mois, triées par date, au format
des fichiers existants (indentation d'un espace, UTF-8, sans échappement).
Une journée déjà présente est remplacée.
"""

import json
import re
import sys
from pathlib import Path

DOSSIER = Path("donnees/jours")
CLE = re.compile(r"^\d{4}-\d{2}-\d{2}$")


def main(chemins):
    par_mois = {}
    for chemin in chemins:
        fragment = json.loads(Path(chemin).read_text(encoding="utf-8"))
        for cle, jour in fragment.items():
            if not CLE.match(cle):
                raise SystemExit(f"{chemin} : clé inattendue « {cle} »")
            if not isinstance(jour, dict) or "textes" not in jour or "meditation" not in jour:
                raise SystemExit(f"{chemin} : la journée {cle} doit avoir « textes » et « meditation »")
            par_mois.setdefault(cle[:7], {})[cle] = jour

    for mois, jours in sorted(par_mois.items()):
        fichier = DOSSIER / f"{mois}.json"
        donnees = json.loads(fichier.read_text(encoding="utf-8")) if fichier.exists() else {}
        donnees.update(jours)
        donnees = dict(sorted(donnees.items()))
        fichier.write_text(json.dumps(donnees, ensure_ascii=False, indent=1), encoding="utf-8")
        print(f"{fichier} : {', '.join(sorted(jours))}")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        raise SystemExit(__doc__)
    main(sys.argv[1:])
