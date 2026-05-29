"""
caldav_sync.py — Récupère N calendriers CalDAV, merge, filtre #interne, écrit calendrier.ics
Produit deux fichiers :
  - calendrier.ics         : événements publics (filtre #interne actif)
  - calendrier-private.ics : tous les événements (filtre #interne désactivé)
Conçu pour tourner dans GitHub Actions → les .ics sont commités sur gh-pages (GitHub Pages)
"""

import os
import sys
import logging
from datetime import date, datetime, timedelta, timezone

import caldav
from icalendar import Calendar
from dotenv import load_dotenv

load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)
log = logging.getLogger(__name__)

CALDAV_URL      = os.environ["CALDAV_URL"]
CALDAV_USER     = os.environ["CALDAV_USER"]
CALDAV_PASSWORD = os.environ["CALDAV_PASSWORD"]

CALDAV_CALENDARS = [
    c.strip()
    for c in os.getenv("CALDAV_CALENDARS", "").split(",")
    if c.strip()
]

FILTER_KEYWORD          = os.getenv("FILTER_KEYWORD", "#interne")
OUTPUT_FILENAME         = os.getenv("OUTPUT_FILENAME", "calendrier.ics")
OUTPUT_FILENAME_PRIVATE = os.getenv("OUTPUT_FILENAME_PRIVATE", "calendrier-private.ics")
EXCLUDE_CALENDARS = [
    c.strip()
    for c in os.getenv("EXCLUDE_CALENDARS", "").split(",")
    if c.strip()
]

def connect_caldav() -> caldav.DAVClient:
    log.info("Connexion CalDAV : %s", CALDAV_URL)
    return caldav.DAVClient(url=CALDAV_URL, username=CALDAV_USER, password=CALDAV_PASSWORD)

def get_calendars(client: caldav.DAVClient) -> list:
    principal = client.principal()
    all_cals = principal.calendars()
    log.info("Calendriers disponibles : %s", [c.name for c in all_cals])
    if not CALDAV_CALENDARS:
        log.info("Aucun filtre → inclusion de tous (%d)", len(all_cals))
        selected = list(all_cals)
    else:
        selected = [c for c in all_cals if c.name in CALDAV_CALENDARS]
        missing = set(CALDAV_CALENDARS) - {c.name for c in selected}
        if missing:
            log.warning("Calendriers introuvables : %s", missing)
    if EXCLUDE_CALENDARS:
        selected = [
            c for c in selected
            if not any(excl.lower() in c.name.lower() for excl in EXCLUDE_CALENDARS)
        ]
        log.info("Après exclusion : %d calendrier(s) retenus", len(selected))
    return selected

def fetch_events(calendars: list) -> list:
    all_events = []
    for cal in calendars:
        try:
            events = cal.events()
            log.info("  %s : %d événements récupérés", cal.name, len(events))
            all_events.extend(events)
        except Exception as exc:
            log.error("Erreur lecture '%s' : %s", cal.name, exc)
    return all_events

def is_internal(component) -> bool:
    description = component.get("DESCRIPTION", "")
    return FILTER_KEYWORD.lower() in str(description).lower() if description else False

def _fix_allday_dtend(component) -> None:
    """Corrige DTEND des événements journée entière quand DTEND <= DTSTART.

    Certains serveurs CalDAV stockent DTEND = DTSTART au lieu de DTSTART + 1 jour,
    ce qui fait afficher l'événement comme finissant la veille dans les apps calendrier.
    """
    dtstart = component.get("DTSTART")
    if dtstart is None:
        return
    dt = dtstart.dt
    if not (isinstance(dt, date) and not isinstance(dt, datetime)):
        return  # pas un événement journée entière
    dtend = component.get("DTEND")
    if dtend is None:
        return
    dtend_dt = dtend.dt
    if isinstance(dtend_dt, date) and not isinstance(dtend_dt, datetime):
        if dtend_dt <= dt:
            component["DTEND"].dt = dt + timedelta(days=1)

def build_ics(caldav_events: list, skip_internal: bool = True, calendar_name: str = None) -> bytes:
    merged = Calendar()
    merged.add("PRODID", "-//Paroisse CalDAV Sync//FR")
    merged.add("VERSION", "2.0")
    merged.add("CALSCALE", "GREGORIAN")
    merged.add("METHOD", "PUBLISH")
    merged.add("X-WR-CALNAME", calendar_name or os.getenv("CALENDAR_NAME", "Agenda Paroisse"))
    merged.add("X-WR-TIMEZONE", "Europe/Paris")
    kept = filtered = 0
    for dav_event in caldav_events:
        try:
            cal_obj = Calendar.from_ical(dav_event.data)
            for component in cal_obj.walk():
                if component.name == "VEVENT":
                    if skip_internal and is_internal(component):
                        filtered += 1
                    else:
                        _fix_allday_dtend(component)
                        merged.add_component(component)
                        kept += 1
        except Exception as exc:
            log.error("Erreur parsing événement : %s", exc)
    log.info("Conservés : %d | Filtrés (%s) : %d", kept, FILTER_KEYWORD, filtered)
    return merged.to_ical()

def main():
    log.info("=== Démarrage sync CalDAV → ICS [%s] ===", datetime.now(timezone.utc).isoformat())
    try:
        client    = connect_caldav()
        calendars = get_calendars(client)
        if not calendars:
            log.error("Aucun calendrier trouvé, arrêt.")
            sys.exit(1)
        events = fetch_events(calendars)
        calendar_name = os.getenv("CALENDAR_NAME", "Agenda Paroisse")

        ics_public = build_ics(events, skip_internal=True, calendar_name=calendar_name)
        with open(OUTPUT_FILENAME, "wb") as f:
            f.write(ics_public)
        log.info("Fichier public écrit : %s", OUTPUT_FILENAME)

        ics_private = build_ics(events, skip_internal=False, calendar_name=calendar_name + " — Complet")
        with open(OUTPUT_FILENAME_PRIVATE, "wb") as f:
            f.write(ics_private)
        log.info("Fichier complet écrit : %s", OUTPUT_FILENAME_PRIVATE)

        log.info("=== Sync terminée avec succès ===")
    except Exception as exc:
        log.exception("Erreur fatale : %s", exc)
        sys.exit(1)

if __name__ == "__main__":
    main()
