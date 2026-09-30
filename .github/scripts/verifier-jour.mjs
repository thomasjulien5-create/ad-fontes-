/* ============================================================
   Ad Fontes — vérification quotidienne de préparation
   ------------------------------------------------------------
   Contrôle, pour une fenêtre de jours à venir, que chaque journée
   dispose de tout ce que la charte exige avant publication :
   lectures de la messe (latin et français), commentaire en quatre
   mouvements, trois points, résolution, et méditation complète.
   Les journées publiées sont validées : aucune mention de
   validation n'est plus recherchée.

   Le script n'invente rien : il constate ce qui manque et écrit
   un rapport JSON. L'envoi de l'alerte est fait à part.

   Sortie : rapport.json + code de retour 0 (rien à signaler)
            ou 1 (au moins une journée incomplète).
   ============================================================ */

import { readFileSync, writeFileSync, readdirSync } from "node:fs";
import { join } from "node:path";

const SOURCE = process.env.ADF_SOURCE || "donnees/jours";
const FENETRE = Number(process.env.ADF_FENETRE || 7); // jours vérifiés, aujourd'hui inclus
const FUSEAU = "Europe/Paris";

/* ---------- Chargement des données ----------
   Les journées vivent dans des fichiers mensuels donnees/jours/AAAA-MM.json,
   chargés à la demande par l'application ; on les réunit ici en un seul objet. */
function chargerJours(dossier) {
  const jours = {};
  for (const f of readdirSync(dossier).filter(f => /^\d{4}-\d{2}\.json$/.test(f)).sort())
    Object.assign(jours, JSON.parse(readFileSync(join(dossier, f), "utf8")));
  return jours;
}

/* ---------- Schéma exigé ----------
   Les Textes du jour donnent les lectures de la messe selon le Missel
   de 1962 : la Leçon ou l'Épître (et, aux Quatre-Temps, les leçons
   supplémentaires), puis l'Évangile. Chaque lecture porte le latin
   ET le français. */
const rempli = (v) => Array.isArray(v) ? v.some(x => String(x).trim()) : String(v ?? "").trim() !== "";

function verifierLecture(libelle, piece) {
  if (!piece || typeof piece !== "object") return `${libelle} : absente`;
  const manque = [];
  if (!rempli(piece.reference)) manque.push("référence");
  if (!rempli(piece.latin)) manque.push("latin");
  if (!rempli(piece.francais)) manque.push("français");
  return manque.length ? `${libelle} : ${manque.join(", ")} manquant(s)` : null;
}

function verifierJournee(cle, jour) {
  const manques = [];
  if (!jour) return ["journée absente du fichier de données"];

  const t = jour.textes;
  if (!t) manques.push("bloc « textes » absent");
  else {
    if (!t.liturgie?.nom) manques.push("jour liturgique non déterminé");
    const propre = t.propre;
    if (!propre) manques.push("lectures de la messe absentes");
    else {
      const premiere = propre.lecon ? ["Leçon", propre.lecon] : ["Épître", propre.epitre];
      for (const [libelle, piece] of [premiere, ...(propre.supplement ?? []).map((p, i) => [`Leçon ${i + 2}`, p]), ["Évangile", propre.evangile]]) {
        const e = verifierLecture(libelle, piece);
        if (e) manques.push(e);
      }
    }
    if ((t.commentaire?.sections?.length ?? 0) < 4) manques.push("commentaire des textes : les quatre mouvements ne sont pas au complet");
    if (!rempli(t.essentiel) || (t.essentiel?.length ?? 0) < 3) manques.push("textes : les 3 points ne sont pas au complet");
    if (!rempli(t.resolution)) manques.push("textes : résolution absente");
  }

  const m = jour.meditation;
  if (!m) manques.push("méditation absente (La Moelle)");
  else {
    if (!rempli(m.titre)) manques.push("méditation : titre absent");
    if (!rempli(m.texte)) manques.push("méditation : texte absent");
    if (!m.commentaire?.sections?.length) manques.push("méditation : commentaire absent");
    if (!rempli(m.essentiel) || (m.essentiel?.length ?? 0) < 3) manques.push("méditation : les 3 points ne sont pas au complet");
    if (!rempli(m.resolution)) manques.push("méditation : résolution absente");
  }
  return manques;
}

/* ---------- Fenêtre de dates, calée sur l'heure de Paris ---------- */
function cleParis(decalageJours = 0) {
  const maintenant = new Date();
  const d = new Date(maintenant.toLocaleString("en-US", { timeZone: FUSEAU }));
  d.setDate(d.getDate() + decalageJours);
  return [d.getFullYear(), String(d.getMonth() + 1).padStart(2, "0"), String(d.getDate()).padStart(2, "0")].join("-");
}

const JOURS = chargerJours(SOURCE);
const journees = [];
for (let i = 0; i < FENETRE; i++) {
  const cle = cleParis(i);
  const manques = verifierJournee(cle, JOURS[cle]);
  journees.push({ date: cle, prete: manques.length === 0, manques });
}

const incompletes = journees.filter(j => !j.prete);
const rapport = {
  genere_le: new Date().toISOString(),
  fuseau: FUSEAU,
  source: SOURCE,
  fenetre_jours: FENETRE,
  total_incompletes: incompletes.length,
  journees,
};
writeFileSync("rapport.json", JSON.stringify(rapport, null, 2), "utf8");

for (const j of journees) {
  console.log(j.prete ? `✓ ${j.date} — prête` : `✗ ${j.date} — ${j.manques.length} point(s) à traiter`);
  for (const m of j.manques) console.log(`    · ${m}`);
}
console.log(`\n${incompletes.length} journée(s) incomplète(s) sur ${FENETRE}.`);
process.exit(incompletes.length ? 1 : 0);
