# Calendrier paroissial

Génère le calendrier paroissial annuel (même mise en page que 2025-2026) au format **Excel + PDF**, plus un **rapport de contrôle**.

**Règle d'or : aucune date n'est inventée ni calculée.**

| Donnée | Source |
| --- | --- |
| Événements de la paroisse | Flux ICS Enoria : **tout est affiché sauf la liste d'exclusion** de `regles.csv` (les règles « afficher » ne servent qu'à fixer libellé et couleur) |
| Liturgie, jours fériés, vacances scolaires | `dates_officielles_2026-2027.csv` (une source citée par ligne : Ordo CEF, service-public.gouv.fr, data.education.gouv.fr, académie d'Orléans-Tours, zone B) |
| KT et autres ajouts | `ajouts_manuels.csv` (à remplir à la main) |

## Installation (1 fois)

Avec [uv](https://docs.astral.sh/uv/) (environnement `.venv` à la racine du dépôt, ignoré par git).

Bash (Linux / macOS / Git Bash) :

```bash
uv venv .venv
uv pip install -r calendrier_paroissial/requirements.txt
```

PowerShell (Windows) :

```powershell
uv venv .venv
uv pip install -r calendrier_paroissial\requirements.txt
```

Pour le PDF, LibreOffice doit être installé (`soffice` dans le PATH ; Windows : `winget install TheDocumentFoundation.LibreOffice`). Sans lui, le script produit quand même le `.xlsx` ; export PDF possible avec Excel (voir plus bas). En ligne, le PDF est produit par GitHub Actions (LibreOffice installé dans le workflow).

## Lancement ultérieur

Depuis la racine du dépôt.

Bash :

```bash
.venv/Scripts/python.exe calendrier_paroissial/generer_calendrier.py --sortie calendrier_paroissial/sortie   # Windows
.venv/bin/python calendrier_paroissial/generer_calendrier.py --sortie calendrier_paroissial/sortie           # Linux / macOS
```

PowerShell :

```powershell
.venv\Scripts\python.exe calendrier_paroissial\generer_calendrier.py --sortie calendrier_paroissial\sortie
```

PDF sans LibreOffice (Windows, Excel installé) : exporter le `.xlsx` généré.

```powershell
$d = (Resolve-Path calendrier_paroissial\sortie).Path
$e = New-Object -ComObject Excel.Application; $e.Visible = $false; $e.DisplayAlerts = $false
$w = $e.Workbooks.Open("$d\Calendrier_paroissial_2026-2027.xlsx")
$w.ExportAsFixedFormat(0, "$d\Calendrier_paroissial_2026-2027.pdf")
$w.Close($false); $e.Quit()
```

Bash (Git Bash) : lancer la même commande via `powershell -NoProfile -Command '...'`.

Options utiles : `--ics <url https ou fichier>`, `--annee 2026` (saison 2026-2027), `--sortie <dossier>`, `--sans-pdf`.

Résultats dans `sortie/` : `Calendrier_paroissial_2026-2027.xlsx`, `.pdf`, `rapport_controle_2026-2027.md`.

Les décisions prises (ce qui est affiché, exclu, ou remplacé) sont consignées dans [`DECISIONS.md`](DECISIONS.md) pour pouvoir relancer à l'identique.

## Palette : une couleur par type

Teintes harmonisées, une par type d'événement (détail et codes hex dans [`DECISIONS.md`](DECISIONS.md), section 2026-10-20) :

| Type | Couleur |
| --- | --- |
| Avent, Carême (fond des jours), dimanches Avent/Carême, Cendres, Défunts | violet |
| Semaine sainte, Rameaux, Jeudi/Vendredi saint, Messe chrismale | rouge |
| Fêtes liturgiques / jours fériés civils | jaune / jaune pâle |
| Père Pascal en Côte d'Ivoire / Visite du Pape | gris / ardoise |
| CCN, Kion, Cté (dont Journées Paroisse) | olive |
| CMP et Équipe pilote | menthe |
| Éveil à la Foi / Casa / Venez & Voyez | cyan / fuchsia / brun |
| Sacrements et catéchisme / catéchuménat / prépa mariage | or / or foncé / orange |
| Diocèse / vie paroissiale (défaut, dont Journée Communautaire) | vert / bleu |
| Concerts / scolaire (rentrée, pont) | turquoise / bleu clair |

Pour changer la couleur d'un type : modifier le style dans `regles.csv` (ou `dates_officielles_*.csv`), ou la teinte dans `STYLES` de `generer_calendrier.py`.

## Publication en ligne (GitHub Actions)

Le workflow `.github/workflows/calendrier.yml` génère xlsx + PDF + rapport chaque jour à 6 h (heure de Paris) si l'ICS ou les règles ont changé, et publie sur `gh-pages` (`/calendrier.pdf`, `/calendrier.xlsx`). Pour le lancer à la demande (Bash et PowerShell, `gh` authentifié) :

```bash
gh workflow run calendrier.yml -f force=true
gh run list --workflow=calendrier.yml --limit 1
```

```powershell
gh workflow run calendrier.yml -f force=true
gh run list --workflow=calendrier.yml --limit 1
```

## Règle de mise en page des cases

- Un événement **seul** sur son jour occupe **toute la hauteur** de la case.
- **2 événements** le même jour : **1 ligne chacun**, la 3e reste vide ; **3 événements** : 1 ligne chacun. Exception : si l'un est multi-jours, il prend 2 lignes.
- Un événement **multi-jours** est **ancré en haut ou en bas** de la case pour que ses blocs se rejoignent d'un jour à l'autre et fusionnent, même quand d'autres événements s'intercalent (ex. Visite du Pape).
- Le texte n'est écrit **qu'une fois par mois** (dans le plus grand bloc du mois) : ailleurs, la couleur suffit ; un événement à cheval sur deux mois est donc nommé dans chaque mois.
- Chaque bloc est entouré d'un trait fin noir.
- **Couleurs** : un événement long (5 jours et plus) ne partage pas sa couleur avec un événement simultané ; il est recoloré (sable, ciel, rose) et signalé au rapport.
- **Périodes** (Avent, Carême) : fond violet sur les colonnes jour/numéro ; chaque dimanche porte son libellé (« 1er dim. de l'Avent »…). Légende en ligne 2.
- **Plus de 3** : les derniers sont regroupés dans la 3e ligne (signalé dans le rapport).

## Dates de fin de l'ICS

Dans un ICS, la fin (`DTEND`) d'un événement « journée entière » est **exclusive** (RFC 5545). Si le flux porte un jour de trop (cas constaté : aucun événement d'un seul jour n'a une durée de 1 jour), le générateur le détecte et corrige, et l'écrit au rapport (section 4). Option : `--decalage-fin auto|0|1`. La correction pérenne se fait dans `caldav_sync.py` (dépôt `caldav-ics-paroisse`).

## Lire le rapport de contrôle

1. **Événements affichés** : liste complète avec origine (ics / officiel / manuel).
2. **Attendus non trouvés** : ce qui figurait en 2025-2026 et manque cette année (KT, 1ère communion, etc.).
3. **Affichés par défaut** : événements sans règle (titre nettoyé, couleur bleue) ; ajouter une règle dans `regles.csv` pour changer libellé/couleur ou pour les exclure.
4. **Écarts ICS / officiel** : par exemple les vacances scolaires décalées d'un jour dans l'ICS (la date officielle est retenue).
5. **Plus de 3 événements le même jour** : les derniers sont regroupés dans la 3e ligne de la case (« A / B »).
6. **Exclus par règle** : messes, adorations (dont la Journée d'adoration), chapelets, laudes, groupes de prière, baptêmes, funérailles, mariages, etc.

## Ajouter le KT ou un événement ponctuel

Éditer `ajouts_manuels.csv` (colonnes `date_debut,date_fin,libelle,style`), puis relancer. Styles : `violet`, `rouge`, `jaune`, `jaune_pale`, `bleu`, `olive` (CCN / Kion / Cté), `cyan`, `saumon`, `lavande`, `turquoise`, `or`, `or_fonce`, `fuchsia`, `brun`, `orange`, `vert`, `menthe` (CMP), `gris`, `ardoise`, `bleu_clair`, `rose`, `sable`, `ciel` (palette par type : voir [`DECISIONS.md`](DECISIONS.md)).

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

- Les noms de personnes ne sont **jamais** écrits dans les fichiers produits : baptêmes, mariages et funérailles ne sont pas affichés (décisions du 2026-10-01 et du 2026-10-20).
- **Point d'attention** : le flux `calendrier-interne.ics` est joignable sans authentification à son URL et contient ces noms. Restreindre son accès (jeton, mot de passe, ou non publication) ou retirer ces événements du flux publié.
- Garde-fou : un événement sans règle dont le titre ressemble à un nom de personne (M./Mme, mot tout en majuscules de 5 lettres ou plus) n'est **jamais écrit** ; il est compté au rapport (section 5b) sans son titre.
- Aucun secret dans le dépôt. L'ICS est lu en HTTPS uniquement (l'URL `http://` est refusée).
- Les libellés venant de l'ICS sont neutralisés contre l'injection de formules Excel (`=`, `+`, `-`, `@`).
- Le dossier `sortie/` et les `.ics` sont ignorés par git.
