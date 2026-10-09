# caldav-ics-paroisse

Synchronisation automatique CalDAV → fichiers `.ics` publics via GitHub Actions + GitHub Pages.

Regénéré toutes les 4 heures.

## URLs

| Calendrier | URL | Contenu |
| --- | --- | --- |
| **Public** | `https://calendrier.saintemariedespeuples.org/calendrier.ics` | Tous les événements sauf `#interne` et Locations de salle |
| **Interne** | `https://calendrier.saintemariedespeuples.org/calendrier-interne.ics` | Tous les événements sauf Locations de salle |

## Architecture

```text
GitHub Actions (cron toutes les 4h)
    ↓
caldav_sync.py
    ├── connexion CalDAV (credentials via GitHub Secrets)
    ├── récupère 6 calendriers (Locations de salle exclu)
    ├── merge tous les événements
    ├── vérifie DTEND journée entière (Enoria exporte déjà un DTEND exclusif RFC 5545 ; +1 jour seulement si DTEND <= DTSTART)
    ├── calendrier.ics         → filtre #interne + exclut les mois passés (cutoff = 1er du mois)
    └── calendrier-interne.ics → historique complet, conserve les #interne
    ↓
branche gh-pages uniquement (sources sur main, non publiées)
    ↓
GitHub Pages → domaine personnalisé calendrier.saintemariedespeuples.org
```

## Calendrier paroissial (Excel + PDF)

Le dossier [`calendrier_paroissial/`](calendrier_paroissial/README.md) génère le calendrier annuel (xlsx + PDF + rapport de contrôle) à partir du `calendrier-interne.ics`. Le workflow `calendrier.yml` le lance **chaque jour à 6h (heure de Paris)**, seulement si l'ICS publié, les règles ou le code ont changé, et publie le résultat dans `calendrier-paroissial/` sur gh-pages :

- `https://calendrier.saintemariedespeuples.org/calendrier-paroissial/Calendrier_paroissial_2026-2027.pdf` (et `.xlsx`, `rapport_controle_2026-2027.md`)
- Adresses fixes (toujours la saison en cours) : `https://calendrier.saintemariedespeuples.org/calendrier-paroissial/calendrier.pdf` et `.../calendrier.xlsx`
- Lancement manuel : onglet Actions → « Calendrier paroissial (xlsx + PDF) » → Run workflow (option « forcer »).
- Aucun secret n'est utilisé ; ces fichiers n'exposent que ce que l'ICS publié contient déjà (aucun nom de personne n'est écrit).

Lancement local :

```bash
python3 -m venv venv && source venv/bin/activate
pip install -r requirements.txt -r calendrier_paroissial/requirements.txt
python calendrier_paroissial/generer_calendrier.py
```

```powershell
python -m venv venv; venv\Scripts\activate
pip install -r requirements.txt -r calendrier_paroissial\requirements.txt
python calendrier_paroissial\generer_calendrier.py
```

## Setup

Voir [SETUP.md](SETUP.md) pour la configuration complète.

## Développement local

```powershell
uv venv .venv
.venv\Scripts\Activate.ps1
uv pip install -r requirements.txt
```

Copier `.env.example` en `.env` et renseigner les credentials :

```powershell
Copy-Item .env.example .env
# éditer .env avec vos identifiants CalDAV
uv run caldav_sync.py
```

## Abonnement calendrier

URL publique (à communiquer largement) :

```text
https://calendrier.saintemariedespeuples.org/calendrier.ics
```

URL interne (à communiquer aux membres uniquement) :

```text
https://calendrier.saintemariedespeuples.org/calendrier-interne.ics
```

Compatible iPhone, Google Calendar, Outlook, Thunderbird.
