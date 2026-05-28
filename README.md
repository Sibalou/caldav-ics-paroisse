# caldav-ics-paroisse

Synchronisation automatique CalDAV → fichier `.ics` public via GitHub Actions + GitHub Pages.

Regénéré toutes les 4 heures. URL publique stable :

```
https://sibalou.github.io/caldav-ics-paroisse/calendrier.ics
```

## Architecture

```
GitHub Actions (cron toutes les 4h)
    ↓
caldav_sync.py
    ├── connexion CalDAV (credentials via GitHub Secrets)
    ├── récupère N calendriers
    ├── merge tous les événements
    └── filtre les événements contenant #interne dans DESCRIPTION
    ↓
calendrier.ics commité dans le repo
    ↓
GitHub Pages → URL publique stable
```

## Setup

Voir [SETUP.md](SETUP.md) pour la configuration complète.

## Abonnement calendrier

URL à communiquer :

```
https://sibalou.github.io/caldav-ics-paroisse/calendrier.ics
```

Compatible iPhone, Google Calendar, Outlook, Thunderbird.
