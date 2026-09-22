#!/usr/bin/env python3
"""Ad Fontes — envoi de l'alerte de préparation.

Lit rapport.json produit par verifier-jour.mjs et envoie un courriel
récapitulant ce qui manque. N'utilise que la bibliothèque standard :
aucune action tierce à épingler, aucune dépendance à installer.

Paramètres, tous fournis par des secrets du dépôt :
  SMTP_SERVEUR     hôte SMTP (ex. smtp.gmail.com)
  SMTP_PORT        465 (SSL) ou 587 (STARTTLS) — 465 par défaut
  SMTP_UTILISATEUR identifiant SMTP, sert aussi d'expéditeur
  SMTP_MOTDEPASSE  mot de passe ou mot de passe d'application
  DESTINATAIRE     adresse à prévenir
"""

import json
import os
import smtplib
import ssl
import sys
from email.message import EmailMessage

REQUIS = ["SMTP_SERVEUR", "SMTP_UTILISATEUR", "SMTP_MOTDEPASSE", "DESTINATAIRE"]


def corps(rapport):
    lignes = [
        "Ad Fontes — vérification quotidienne",
        "",
        f"{rapport['total_incompletes']} journée(s) incomplète(s) "
        f"sur les {rapport['fenetre_jours']} prochains jours.",
        "",
    ]
    for j in rapport["journees"]:
        if j["prete"]:
            continue
        lignes.append(f"— {j['date']}")
        lignes.extend(f"    · {m}" for m in j["manques"])
        lignes.append("")
    lignes += [
        "Rappel de la charte : les textes sont reproduits fidèlement et",
        "aucune référence n'est inventée. Une journée n'est publiable",
        "qu'une fois ses sources établies et le brouillon validé.",
        "",
        f"Rapport généré le {rapport['genere_le']} ({rapport['fuseau']}).",
    ]
    return "\n".join(lignes)


def main():
    manquants = [v for v in REQUIS if not os.environ.get(v)]
    if manquants:
        print(f"Secrets absents : {', '.join(manquants)} — alerte non envoyée.", file=sys.stderr)
        return 1

    with open("rapport.json", encoding="utf-8") as f:
        rapport = json.load(f)

    if rapport["total_incompletes"] == 0:
        print("Toutes les journées sont prêtes : pas d'alerte à envoyer.")
        return 0

    msg = EmailMessage()
    msg["Subject"] = (
        f"Ad Fontes — {rapport['total_incompletes']} journée(s) à préparer"
    )
    msg["From"] = os.environ["SMTP_UTILISATEUR"]
    msg["To"] = os.environ["DESTINATAIRE"]
    msg.set_content(corps(rapport))

    serveur = os.environ["SMTP_SERVEUR"]
    port = int(os.environ.get("SMTP_PORT", "465"))
    contexte = ssl.create_default_context()

    if port == 587:
        with smtplib.SMTP(serveur, port, timeout=30) as s:
            s.starttls(context=contexte)
            s.login(os.environ["SMTP_UTILISATEUR"], os.environ["SMTP_MOTDEPASSE"])
            s.send_message(msg)
    else:
        with smtplib.SMTP_SSL(serveur, port, context=contexte, timeout=30) as s:
            s.login(os.environ["SMTP_UTILISATEUR"], os.environ["SMTP_MOTDEPASSE"])
            s.send_message(msg)

    print(f"Alerte envoyée à {os.environ['DESTINATAIRE']}.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
