"""Tests de _fix_allday_dtend : python -m pytest -q tests"""
import os
import sys
from datetime import date, datetime
from pathlib import Path

os.environ.update(CALDAV_URL="https://exemple.invalid", CALDAV_USER="u",
                  CALDAV_PASSWORD="p", CALDAV_CALENDARS="a")
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import caldav_sync as s  # noqa: E402
from icalendar import Event  # noqa: E402


def evt(debut, fin):
    e = Event()
    e.add("SUMMARY", "Test")
    e.add("DTSTART", debut)
    e.add("DTEND", fin)
    return e


def test_dtend_exclusif_inchange():
    e = evt(date(2026, 9, 12), date(2026, 9, 13))  # événement d'un seul jour
    s._fix_allday_dtend(e)
    assert e["DTEND"].dt == date(2026, 9, 13)
    e = evt(date(2027, 5, 15), date(2027, 5, 18))  # 15 → 17 inclus
    s._fix_allday_dtend(e)
    assert e["DTEND"].dt == date(2027, 5, 18)


def test_dtend_invalide_ramene_a_un_jour():
    e = evt(date(2026, 9, 12), date(2026, 9, 12))
    s._fix_allday_dtend(e)
    assert e["DTEND"].dt == date(2026, 9, 13)


def test_evenement_horodate_inchange():
    e = evt(datetime(2026, 11, 14, 10), datetime(2026, 11, 15, 16))
    s._fix_allday_dtend(e)
    assert e["DTEND"].dt == datetime(2026, 11, 15, 16)
