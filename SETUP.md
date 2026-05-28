# Guide de configuration — caldav-ics-paroisse

## Étape 1 — Créer le repo GitHub

```bash
gh repo create Sibalou/caldav-ics-paroisse \
  --public \
  --description "Sync CalDAV → ICS public via GitHub Actions + GitHub Pages"
```

## Étape 2 — Ajouter les GitHub Secrets

```bash
gh secret set CALDAV_URL       --repo Sibalou/caldav-ics-paroisse
gh secret set CALDAV_USER      --repo Sibalou/caldav-ics-paroisse
gh secret set CALDAV_PASSWORD  --repo Sibalou/caldav-ics-paroisse
gh secret set CALDAV_CALENDARS --repo Sibalou/caldav-ics-paroisse
gh secret set CALENDAR_NAME    --repo Sibalou/caldav-ics-paroisse
```

| Secret | Exemple |
|---|---|
| `CALDAV_URL` | `https://caldav.example.com/user/` |
| `CALDAV_USER` | `mon.email@example.com` |
| `CALDAV_PASSWORD` | `monmotdepasse` |
| `CALDAV_CALENDARS` | `Agenda Principal,Messes,Événements` (vide = tous) |
| `CALENDAR_NAME` | `Agenda Paroisse` |

## Étape 3 — Activer GitHub Pages

```bash
gh api \
  --method POST \
  -H "Accept: application/vnd.github+json" \
  /repos/Sibalou/caldav-ics-paroisse/pages \
  -f source='{"branch":"main","path":"/"}'
```

Ou via l'UI : Settings → Pages → Source : main / root → Save

## Étape 4 — Premier run manuel

```bash
gh workflow run sync.yml --repo Sibalou/caldav-ics-paroisse
gh run watch --repo Sibalou/caldav-ics-paroisse
```

## Étape 5 — Vérifier

```bash
curl -I https://sibalou.github.io/caldav-ics-paroisse/calendrier.ics
```

HTTP 200 = tout fonctionne.

## Dépannage

```bash
# Derniers runs
gh run list --repo Sibalou/caldav-ics-paroisse --workflow sync.yml

# Logs d'un run en échec
gh run view [RUN_ID] --repo Sibalou/caldav-ics-paroisse --log

# Secrets configurés
gh secret list --repo Sibalou/caldav-ics-paroisse

# Statut GitHub Pages
gh api /repos/Sibalou/caldav-ics-paroisse/pages --jq '.status, .html_url'
```

## Modifier la fréquence

Dans `.github/workflows/sync.yml` :

```yaml
- cron: "0 */4 * * *"         # toutes les 4 heures
- cron: "0 7,12,18,21 * * *"  # 7h, 12h, 18h, 21h
- cron: "0 * * * *"           # toutes les heures
```
