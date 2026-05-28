# Guide de configuration — caldav-ics-paroisse

## Étape 1 — Ajouter les GitHub Secrets

```powershell
gh secret set CALDAV_URL       --repo Sibalou/caldav-ics-paroisse
gh secret set CALDAV_USER      --repo Sibalou/caldav-ics-paroisse
gh secret set CALDAV_PASSWORD  --repo Sibalou/caldav-ics-paroisse
gh secret set CALDAV_CALENDARS --repo Sibalou/caldav-ics-paroisse
gh secret set CALENDAR_NAME    --repo Sibalou/caldav-ics-paroisse
```

| Secret | Exemple |
| --- | --- |
| `CALDAV_URL` | `https://caldav.example.com/user/` |
| `CALDAV_USER` | `mon.email@example.com` |
| `CALDAV_PASSWORD` | `monmotdepasse` |
| `CALDAV_CALENDARS` | `Agenda Principal,Messes,Événements` (vide = tous) |
| `CALENDAR_NAME` | `Agenda Paroisse` |

## Étape 2 — Premier run manuel

Le workflow crée automatiquement la branche `gh-pages` au premier run :

```powershell
gh workflow run sync.yml --repo Sibalou/caldav-ics-paroisse
gh run watch --repo Sibalou/caldav-ics-paroisse
```

## Étape 3 — Configurer GitHub Pages sur gh-pages

Une fois le premier run terminé (branche `gh-pages` créée) :

```powershell
gh api --method PUT `
  -H "Accept: application/vnd.github+json" `
  repos/Sibalou/caldav-ics-paroisse/pages `
  --field source[branch]=gh-pages `
  --field source[path]=/
```

Ou via l'UI : Settings → Pages → Source : `gh-pages` / `/ (root)` → Save

## Étape 4 — Vérifier

```powershell
gh api repos/Sibalou/caldav-ics-paroisse/pages --jq '.status, .html_url'
```

## Dépannage

```powershell
# Derniers runs
gh run list --repo Sibalou/caldav-ics-paroisse --workflow sync.yml

# Logs d'un run en échec
gh run view [RUN_ID] --repo Sibalou/caldav-ics-paroisse --log

# Secrets configurés
gh secret list --repo Sibalou/caldav-ics-paroisse

# Contenu de la branche gh-pages
gh api repos/Sibalou/caldav-ics-paroisse/git/trees/gh-pages --jq '.tree[].path'
```

## Domaine personnalisé (calendrier.saintemariedespeuples.org)

### Étape 1 — IONOS : supprimer la redirection existante

1. IONOS → **Domaines & SSL** → `saintemariedespeuples.org`
2. Onglet **Sous-domaines** → repérer `calendrier`
3. **Supprimer** l'entrée de redirection entièrement (pas juste la vider)

### Étape 2 — IONOS : créer le CNAME

Toujours dans **Sous-domaines** → **Ajouter un sous-domaine** :

| Champ | Valeur |
| --- | --- |
| Sous-domaine | `calendrier` |
| Type | `CNAME` |
| Cible | `sibalou.github.io` |
| TTL | `300` |

> La cible est `sibalou.github.io` sans chemin. GitHub résout vers le bon repo via le fichier `CNAME`.

### Étape 3 — Vérifier la propagation DNS

```powershell
# Doit retourner sibalou.github.io
Resolve-DnsName -Name calendrier.saintemariedespeuples.org -Type CNAME
```

**Attendre que le DNS soit propagé avant l'étape suivante** (risque de domain takeover sinon).

### Étape 4 — GitHub Pages : configurer le domaine personnalisé

1. GitHub → repo `caldav-ics-paroisse` → **Settings** → **Pages**
2. Champ **Custom domain** → `calendrier.saintemariedespeuples.org` → **Save**
3. Attendre le statut vert (vérification DNS GitHub, ~1-5 min)
4. Cocher **Enforce HTTPS** une fois le cert Let's Encrypt provisionné (~5-15 min)

### Étape 5 — Vérification complète

```powershell
# DNS
Resolve-DnsName -Name calendrier.saintemariedespeuples.org -Type CNAME

# TLS + Content-Type
$r = Invoke-WebRequest `
  -Uri "https://calendrier.saintemariedespeuples.org/calendrier.ics" `
  -Method Head
$r.StatusCode                  # 200
$r.Headers['Content-Type']     # text/calendar

# Validation
if ($r.Headers['Content-Type'] -like "*text/calendar*") { "OK" } else { "ERREUR Content-Type" }
```

## Modifier la fréquence

Dans `.github/workflows/sync.yml` :

```yaml
- cron: "0 */4 * * *"         # toutes les 4 heures
- cron: "0 7,12,18,21 * * *"  # 7h, 12h, 18h, 21h
- cron: "0 * * * *"           # toutes les heures
```
