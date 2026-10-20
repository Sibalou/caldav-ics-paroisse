# Journal des décisions (pour reproduire à l'identique)

Chaque relance du script repart de trois fichiers, qui portent TOUTES les décisions :
`regles.csv` (filtrage et libellés de l'ICS), `dates_officielles_<saison>.csv` (liturgie, fériés, scolaire, sources citées)
et `ajouts_manuels.csv` (KT, etc.). Ne rien corriger à la main dans l'Excel : modifier ces fichiers et relancer.

## Décisions du 2026-10-01 (saison 2026-2027)

| Sujet | Décision |
| --- | --- |
| Source des événements | ICS Enoria interne (`calendrier.saintemariedespeuples.org/calendrier-interne.ics`) |
| Dates | Aucune date inventée ni calculée ; liturgie = Ordo CEF, fériés = service-public.gouv.fr, vacances = data.education.gouv.fr (Orléans-Tours, zone B) |
| Casa | Affiché « Casa » (caté des grands) ; « Case » dans l'ICS = faute de frappe |
| Concerts | ~~Non affichés~~ → affichés depuis le 2026-10-09 |
| Mariages, funérailles | Non affichés (liés à une personne ou un couple, hors agenda paroissial) |
| Baptêmes, 1ère communion | Affichés s'ils sont dans l'ICS (sans nom) |
| « ass St Joseph » | ~~Non retenu~~ → affiché depuis le 2026-10-09 |
| Visite du Pape, Père Pascal en Côte d'Ivoire | Affichés (dates de l'ICS) |
| Semaine Sainte | Affichée, dates de l'Ordo (Rameaux → samedi saint, 21→27/03/2027) ; l'ICS (22→29/03) incluait Pâques |
| Christ Roi, Jeudi saint, Vendredi saint | Ajoutés (Ordo CEF) |
| Pont de l'Ascension (07/05/2027) | Affiché |
| Vacances scolaires | Dates officielles ; l'ICS est décalé d'un jour (jour de reprise inclus) |
| Équivalences 2025-2026 | Aucune : « Rentrée Cté » et « Rencontre CMP & CPAE » sont affichés tels que dans l'ICS ; « Rentrée Paroissiale » et « J. Dioc. CMP » restent absents |
| KT | Pas encore d'inscription : à saisir dans `ajouts_manuels.csv` quand connu |
| Installation du curé, Rentrée Co Rég. | Aucune cette année |

## Relancer après ajout de nouvelles dates

1. Nouvelle date de paroisse dans Enoria : elle apparaît au prochain run (ICS régénéré toutes les 4 h) ; vérifier les « non classés » du rapport.
2. Date hors Enoria (KT...) : ajouter une ligne dans `ajouts_manuels.csv`.
3. Relancer `python generer_calendrier.py` (voir README), relire `rapport_controle_<saison>.md`, versionner les changements de CSV.

## 2026-10-08 — Mise en page des cases
- Événement seul sur le jour : toute la hauteur, fusion sur les jours consécutifs du même mois.
- Plusieurs événements : 1/3 + 2/3 (2) ou 1/3 chacun (3). (Le texte répété chaque jour est remplacé le 2026-10-09 : voir ci-dessous.)
- Plus de 3 : derniers regroupés dans la 3e ligne, listés dans le rapport (section 5).

## 2026-10-09 — Tout afficher sauf exclusions
- Logique inversée : tout événement de l'ICS est affiché, sauf la liste d'exclusion de `regles.csv` ; sans règle : titre nettoyé (sans « @lieu »), couleur bleue, listé au rapport (section 3).
- Exclusions conservées : messes, adorations, chapelets, laudes, « Autre » (jeudi 8h30), « Temps de prière » (Prière des mères), funérailles, mariages, et les dates remplacées par les sources officielles (vacances, fêtes, Avent, Carême, Cendres, Rameaux, Semaine Sainte, WE Ascension/Pentecôte).
- Retirés des exclusions : concerts (affichés « Concert », doublons fusionnés), groupes de prière, « ass St Joseph ».
- Catéchuménat : tout afficher. « Case » = faute de frappe de Casa (11/12/2026).
- Garde-fou RGPD : titre sans règle ressemblant à un nom de personne = masqué.
- Mise en page : événement multi-jours fusionné (texte plus gros, écrit une seule fois), le plus long en haut quand plusieurs événements.

## 2026-10-09 (suite) — Fins de dates, mise en page, périodes
- Cause des événements trop longs : `caldav_sync.py` ajoute +1 jour à tous les DTEND « journée entière » alors qu'Enoria exporte déjà une fin exclusive (captures Enoria : Rentrée Cté 12/09→12/09 ; Pentecôte Missionnaire 15→17/05). Le générateur détecte et corrige (`--decalage-fin auto`) en attendant le correctif amont.
- Mise en page : 2 événements un même jour = 1 ligne chacun (3e vide) ; multi-jours ancré haut/bas pour fusionner d'un jour à l'autre ; texte une fois par mois ; bordure fine par bloc.
- Couleurs : un événement long (≥ 5 jours) ne partage pas sa couleur avec un événement simultané ; Semaine Épiphanie = rose (règle) ; Semaine missionnaire recolorée automatiquement.
- Avent (29/11→24/12) et Carême (10/02→25/03) = périodes (fond rouge), dimanches de l'Avent et du Carême libellés (Ordo 2026-2027 CEF).
- Corrigé dans Enoria par l'utilisateur : Semaine missionnaire mondiale (11→18/10), Dimanche des Rameaux (21/03/2027). La suspension de l'absence du Père Pascal n'est plus nécessaire (20/10→20/11, sans chevauchement).

## 2026-10-09 (suite 2) — Rouge de la Semaine sainte
- Rameaux, Semaine Sainte, Jeudi saint, Vendredi saint et **Messe Chrismale** (semaine sainte) : tous dans le même rouge (`rouge`). Le rouge vif des Rameaux venait du modèle 2025-2026.
- Le générateur et ses données vivent désormais dans `caldav-ics-paroisse/calendrier_paroissial/` ; la copie du dépôt `diocese` est supprimée (doublon).
- Période Carême prolongée jusqu'au samedi saint (27/03/2027) : jour et date en rouge les 26 et 27/03 (demande utilisateur).
- WE de l'Ascension : affiché (ICS 06→09/05/2027, « WE Ascension »). WE de Pentecôte (15→17/05) toujours exclu : mêmes dates que « Pentecôte Miss. ccn ».
- Fêtes Enoria affichées : Notre-Dame de Velankanni (19/09/2026) et Saint Antoine (19/06/2027) de la communauté Tamoule, Divine Miséricorde (04/04/2027) ; les autres « Fête… » d'Enoria restent remplacées par les dates officielles. Transfiguration (06/08/2027, Ordo) ajoutée.
- Fêtes Enoria affichées (Tamoul, Divine Miséricorde) : en jaune (demande utilisateur 2026-10-09).

## 2026-10-20 — Palette par type (tri visuel)
Une couleur propre par type d'événement, teintes harmonisées (écart perceptuel ΔE ≥ 15 entre deux types). Modifier `regles.csv`, `dates_officielles_*.csv` ou `STYLES` du script, puis relancer.

| Type | Style | Fond |
|---|---|---|
| Avent, Carême (fond des jours jusqu'au 27/03), dimanches Avent/Carême, Cendres, Défunts | `violet` | 6A4C93 |
| Semaine sainte, Rameaux, Jeudi/Vendredi saint, Messe chrismale | `rouge` | A61E2E |
| Fêtes liturgiques (Noël, Pâques, Ascension, Pentecôte, Toussaint, Assomption, Christ Roi, Transfiguration, Annonciation, fêtes tamoules, Divine Miséricorde) | `jaune` | FFD23F |
| Fériés civils | `jaune_pale` | FFF1B8 |
| Père Pascal en Côte d'Ivoire | `gris` | 9AA0A6 |
| Visite du Pape | `ardoise` | 2B2D42 |
| Concerts | `turquoise` | 2A9D8F |
| Rentrée scolaire, pont de l'Ascension | `bleu_clair` | C6D9F1 |
| **CCN, Kion, Cté** (WE Frat, WE engagés, Pentecôte missionnaire, Rentrée Cté, Journée Paroisse, Journée Communautaire, tout titre contenant CCN / Kion / Cté) | `olive` | 7B8F2A |
| **CMP et Équipe pilote** | `menthe` | A8D672 |
| Reste du diocèse | `vert` | 3E8E5A |
| Éveil à la Foi | `cyan` | 22C3DB |
| Casa | `fuchsia` | E85D9C |
| Venez & Voyez | `brun` | 7A4E2D |
| Journée et Nuit d'adoration | `lavande` | D0B8F0 |
| Groupe de prière | `saumon` | F7BFA0 |
| 1ère communion, profession de foi, catéchisme | `or` | D79A3A |
| Catéchuménat | `or_fonce` | 9C6A12 |
| Préparation au mariage | `orange` | EE7B4D |
| Vie paroissiale (défaut) | `bleu` | 4F8FD8 |
| Semaine Épiphanie | `rose` | F4B6C2 |

- **Baptêmes exclus** (comme mariages et funérailles) : liés à une personne.
- « Kion » : aucun titre dédié dans l'ICS ; la règle générique reprend le titre tel quel (hors « @lieu »).
- `sable`, `ciel` et `rose` ne sont réservées à aucun type : elles servent à la recoloration automatique des événements longs (`COULEURS_ALT`).
- Remplace la palette précédente (Avent/Carême en rouge, violet du Pape et du Père Pascal, gris partagé, jaune des fêtes Enoria inchangé en tant que fête).
