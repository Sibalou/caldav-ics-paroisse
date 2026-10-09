# Calendrier paroissial

Génère le calendrier paroissial annuel (même mise en page que 2025-2026) au format **Excel + PDF**, plus un **rapport de contrôle**.

**Règle d'or : aucune date n'est inventée ni calculée.**

| Donnée | Source |
| --- | --- |
| Événements de la paroisse | Flux ICS Enoria : **tout est affiché sauf la liste d'exclusion** de `regles.csv` (les règles « afficher » ne servent qu'à fixer libellé et couleur) |
| Liturgie, jours fériés, vacances scolaires | `dates_officielles_2026-2027.csv` (une source citée par ligne : Ordo CEF, service-public.gouv.fr, data.education.gouv.fr, académie d'Orléans-Tours, zone B) |
| KT et autres ajouts | `ajouts_manuels.csv` (à remplir à la main) |

## Installation (1 fois)

Bash (Linux / macOS) :

```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

PowerShell (Windows) :

```powershell
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
```

Pour le PDF, LibreOffice doit être installé (`soffice` dans le PATH). Sans lui, le script produit quand même le `.xlsx` (export PDF manuel depuis Excel).

## Lancement ultérieur

Bash :

```bash
source venv/bin/activate
python generer_calendrier.py
```

PowerShell :

```powershell
venv\Scripts\activate
python generer_calendrier.py
```

Options utiles : `--ics <url https ou fichier>`, `--annee 2026` (saison 2026-2027), `--sortie <dossier>`, `--sans-pdf`.

Résultats dans `sortie/` : `Calendrier_paroissial_2026-2027.xlsx`, `.pdf`, `rapport_controle_2026-2027.md`.

Les décisions prises (ce qui est affiché, exclu, ou remplacé) sont consignées dans [`DECISIONS.md`](DECISIONS.md) pour pouvoir relancer à l'identique.

## Règle de mise en page des cases

- Un événement **seul** sur son jour occupe **toute la hauteur** de la case.
- **2 événements** le même jour : **1 ligne chacun**, la 3e reste vide ; **3 événements** : 1 ligne chacun. Exception : si l'un est multi-jours, il prend 2 lignes.
- Un événement **multi-jours** est **ancré en haut ou en bas** de la case pour que ses blocs se rejoignent d'un jour à l'autre et fusionnent, même quand d'autres événements s'intercalent (ex. Visite du Pape).
- Le texte n'est écrit **qu'une fois par mois** (dans le plus grand bloc du mois) : ailleurs, la couleur suffit ; un événement à cheval sur deux mois est donc nommé dans chaque mois.
- Chaque bloc est entouré d'un trait fin noir.
- **Couleurs** : un événement long (5 jours et plus) ne partage pas sa couleur avec un événement simultané ; il est recoloré (rose, lavande, turquoise…) et signalé au rapport.
- **Périodes** (Avent, Carême) : fond rouge sur les colonnes jour/numéro ; chaque dimanche porte son libellé (« 1er dim. de l'Avent »…). Légende en ligne 2.
- **Plus de 3** : les derniers sont regroupés dans la 3e ligne (signalé dans le rapport).

## Dates de fin de l'ICS

Dans un ICS, la fin (`DTEND`) d'un événement « journée entière » est **exclusive** (RFC 5545). Si le flux porte un jour de trop (cas constaté : aucun événement d'un seul jour n'a une durée de 1 jour), le générateur le détecte et corrige, et l'écrit au rapport (section 4). Option : `--decalage-fin auto|0|1`. La correction pérenne se fait dans `caldav_sync.py` (dépôt `caldav-ics-paroisse`).

## Lire le rapport de contrôle

1. **Événements affichés** : liste complète avec origine (ics / officiel / manuel).
2. **Attendus non trouvés** : ce qui figurait en 2025-2026 et manque cette année (KT, 1ère communion, etc.).
3. **Affichés par défaut** : événements sans règle (titre nettoyé, couleur bleue) ; ajouter une règle dans `regles.csv` pour changer libellé/couleur ou pour les exclure.
4. **Écarts ICS / officiel** : par exemple les vacances scolaires décalées d'un jour dans l'ICS (la date officielle est retenue).
5. **Plus de 3 événements le même jour** : les derniers sont regroupés dans la 3e ligne de la case (« A / B »).
6. **Exclus par règle** : messes, adorations, chapelets, laudes, funérailles, mariages, etc.

## Ajouter le KT ou un événement ponctuel

Éditer `ajouts_manuels.csv` (colonnes `date_debut,date_fin,libelle,style`), puis relancer. Styles : `jaune`, `rouge`, `rouge_vif`, `or`, `or_fonce`, `orange`, `bleu`, `vert`, `violet`, `gris`, `rose`, `lavande`, `turquoise`, `kaki`, `marine`.

```csv
date_debut,date_fin,libelle,style
2026-11-15,2026-11-15,KT,or
```

## Nouvelle saison

Créer `dates_officielles_<annee>-<annee+1>.csv` à partir des mêmes sources (Ordo de l'année sur liturgie.catholique.fr, service-public.gouv.fr/F2405, jeu de données `fr-en-calendrier-scolaire`), puis lancer avec `--annee <annee>`.

## Tests

```bash
python -m pytest -q tests
```

```powershell
python -m pytest -q tests
```

## Sécurité et RGPD

- Les noms de personnes ne sont **jamais** écrits dans les fichiers produits : seul « Baptême » apparaît (avec un compteur si plusieurs le même jour) ; mariages et funérailles ne sont pas affichés (décision du 2026-10-01).
- **Point d'attention** : le flux `calendrier-interne.ics` est joignable sans authentification à son URL et contient ces noms. Restreindre son accès (jeton, mot de passe, ou non publication) ou retirer ces événements du flux publié.
- Garde-fou : un événement sans règle dont le titre ressemble à un nom de personne (M./Mme, mot tout en majuscules de 5 lettres ou plus) n'est **jamais écrit** ; il est compté au rapport (section 5b) sans son titre.
- Aucun secret dans le dépôt. L'ICS est lu en HTTPS uniquement (l'URL `http://` est refusée).
- Les libellés venant de l'ICS sont neutralisés contre l'injection de formules Excel (`=`, `+`, `-`, `@`).
- Le dossier `sortie/` et les `.ics` sont ignorés par git.
