# caldav-ics-paroisse

Synchronisation automatique CalDAV → fichier `.ics` public via GitHub Actions + GitHub Pages.

Regénéré toutes les 4 heures. URL publique stable :

```text
https://calendrier.saintemariedespeuples.org/calendrier.ics
```

## Architecture

```text
GitHub Actions (cron toutes les 4h)
    ↓
caldav_sync.py
    ├── connexion CalDAV (credentials via GitHub Secrets)
    ├── récupère N calendriers
    ├── merge tous les événements
    └── filtre les événements contenant #interne dans DESCRIPTION
    ↓
calendrier.ics → branche gh-pages uniquement
(sources sur main, non publiées)
    ↓
GitHub Pages → URL publique stable
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
python caldav_sync.py
```

## Abonnement calendrier

URL à communiquer :

```text
https://calendrier.saintemariedespeuples.org/calendrier.ics
```

Compatible iPhone, Google Calendar, Outlook, Thunderbird.
