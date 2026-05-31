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
    ├── corrige DTEND journée entière (+1 jour : Enoria inclusif → RFC 5545 exclusif)
    ├── calendrier.ics         → filtre #interne + exclut les mois passés (cutoff = 1er du mois)
    └── calendrier-interne.ics → historique complet, conserve les #interne
    ↓
branche gh-pages uniquement (sources sur main, non publiées)
    ↓
GitHub Pages → domaine personnalisé calendrier.saintemariedespeuples.org
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
