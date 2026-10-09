#!/usr/bin/env python3
"""Génère le calendrier paroissial (xlsx + PDF + rapport de contrôle).

Principe : AUCUNE date n'est inventée ni calculée.
  - événements de la paroisse  -> flux ICS (Enoria) : tout est affiché sauf la liste d'exclusion de regles.csv
  - liturgie / fériés / scolaire -> dates_officielles_<saison>.csv (sources citées)
  - ajouts (KT, etc.)           -> ajouts_manuels.csv
Les noms de personnes (baptêmes, mariages, funérailles) ne sont jamais écrits.
"""
from __future__ import annotations

import argparse
import csv
import re
import subprocess
import sys
from collections import Counter, defaultdict
from dataclasses import dataclass, field
from datetime import date, datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

import requests
from icalendar import Calendar
from openpyxl import Workbook
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
from openpyxl.worksheet.pagebreak import Break

HERE = Path(__file__).resolve().parent
ICS_URL_DEFAUT = "https://calendrier.saintemariedespeuples.org/calendrier-interne.ics"
PARIS = ZoneInfo("Europe/Paris")
JOURS = ["L", "Ma", "Me", "J", "V", "S", "D"]
MOIS = ["SEPTEMBRE", "OCTOBRE", "NOVEMBRE", "DECEMBRE", "JANVIER", "FEVRIER",
        "MARS", "AVRIL", "MAI", "JUIN", "JUILLET", "AOUT"]
POLICE = "Calibri"

# style -> (fond, texte)
STYLES = {
    "jaune": ("FFFF00", "000000"), "rouge": ("C00000", "FFFFFF"),
    "rouge_vif": ("FF0000", "FFFFFF"), "or": ("FFC000", "000000"),
    "or_fonce": ("BF9000", "000000"), "orange": ("ED7D31", "000000"),
    "bleu": ("00B0F0", "000000"), "vert": ("00B050", "000000"),
    "violet": ("7030A0", "FFFFFF"), "gris": ("D0CECE", "000000"),
    "rose": ("F4B6C2", "000000"), "lavande": ("CDB4E8", "000000"),
    "turquoise": ("00B0A0", "000000"), "kaki": ("A9D18E", "000000"),
    "marine": ("2F5597", "FFFFFF"),
}
# Couleurs de remplacement pour un événement long dont la couleur est déjà prise par un événement simultané
COULEURS_ALT = ["rose", "lavande", "turquoise", "kaki", "marine", "or_fonce", "orange", "vert", "or", "bleu"]
TEINTE_PERIODE = "C00000"  # même rouge que les dimanches de l'Avent / du Carême
SEUIL_LONG = 4  # écart en jours (début→fin) à partir duquel un événement est « long » (5 jours et plus)
GRIS_DIMANCHE = "D9D9D9"
BLEU_VACANCES = "8EAADB"

# Référence : ce qui figurait dans le calendrier 2025-2026 (pour le contrôle des manques).
# (famille, motif sur les libellés affichés, statut connu de l'utilisateur)
REFERENCE_2025 = [
    ("KT", r"^KT", "Pas encore d'inscription (utilisateur, 2026-10-01) : à saisir dans ajouts_manuels.csv"),
    ("Temps fort KT / Retraite KT", r"(Temps FORT|RETRAITE) KT", "Dépend du KT : à saisir quand connu"),
    ("V & V", r"^V & V", ""),
    ("Prépa Mariage (soirées, WE)", r"^(Prépa Mariage|WE Prépa Mariage)", ""),
    ("J. Sexualité", r"^J\. Sexualité", ""),
    ("S. Réconciliation", r"Réconciliation", ""),
    ("1ère Communion", r"1ère Communion", ""),
    ("Dim. Baptême / Messe de Requiem", r"^Baptême", "Baptêmes explicites de l'ICS uniquement (funérailles non affichées, décision 2026-10-01)"),
    ("Journée Paroisse", r"^Journée Paroisse", ""),
    ("Installation du Curé", r"Installation", "Aucune cette année (utilisateur, 2026-10-01)"),
    ("Rentrée Paroissiale", r"^Rentrée Paroissiale", "Pas d'équivalence (décision utilisateur 2026-10-01) : « Rentrée Cté » est affichée telle qu'indiquée dans l'ICS"),
    ("Rentrée Co Rég.", r"Co R[ée]g", "Aucune cette année (utilisateur, 2026-10-01)"),
    ("J. Dioc. CMP", r"^J\. Dioc", "Pas d'équivalence (décision utilisateur 2026-10-01) : « Rencontre CMP & CPAE » est affichée telle qu'indiquée dans l'ICS"),
    ("WE Engagés / Frat / EAV ccn", r"(Engagés|Frat|Éveil)", ""),
    ("Célibataire ccn / Célibataire Épiphanie", r"Célibataire", "Aucune correspondance dans l'ICS (« Semaine Épiphanie » est un autre événement) : à confirmer"),
]


@dataclass
class Evt:
    debut: date
    fin: date  # inclusive
    libelle: str
    style: str
    origine: str  # ics | officiel | manuel
    nombre: int = 1


@dataclass
class Rapport:
    affiches: list = field(default_factory=list)
    exclus: Counter = field(default_factory=Counter)
    non_classes: dict = field(default_factory=lambda: defaultdict(list))
    ecarts: list = field(default_factory=list)
    debordements: list = field(default_factory=list)
    masques: list = field(default_factory=list)  # (date, raison) : titre jamais écrit (RGPD)
    suspendus: list = field(default_factory=list)  # (date, libellé) : événement long sans ligne ce jour-là (plus de 3 événements)
    hors_fenetre: int = 0
    notes_ics: list = field(default_factory=list)  # anomalies / corrections de dates de l'ICS
    recolores: list = field(default_factory=list)  # (libellé, ancienne, nouvelle couleur)


# ---------------------------------------------------------------- lecture ICS
def lire_ics(source: str, decalage: str = "auto"):
    """Retourne (événements [(titre, début, fin INCLUSE)], notes).

    RFC 5545 : DTEND d'un événement « journée entière » est EXCLUSIF. Si le flux ICS a été produit avec
    un +1 jour en trop (ancienne version de caldav_sync.py), aucun événement d'un seul jour n'a de durée 1 :
    `decalage="auto"` détecte ce cas (au moins 5 événements journée entière, aucun de durée 1) et corrige.
    `decalage` = "0" (aucune correction) ou "1" (forcer la correction d'un jour).
    """
    if source.startswith("https://"):
        r = requests.get(source, timeout=30)
        r.raise_for_status()
        data = r.content
    elif source.startswith("http://"):
        sys.exit("Refus : source ICS en http non chiffré.")
    else:
        data = Path(source).read_bytes()
    cal = Calendar.from_ical(data)
    brut = []  # (titre, début, fin exclusive ou None)
    for ev in cal.walk("VEVENT"):
        titre = re.sub(r"\s+", " ", str(ev.get("SUMMARY", ""))).strip()
        d0 = ev.get("DTSTART").dt
        if isinstance(d0, datetime):
            d0 = d0.astimezone(PARIS) if d0.tzinfo else d0
            debut = d0.date()
            fin_h = ev.get("DTEND").dt if ev.get("DTEND") else None
            if isinstance(fin_h, datetime):
                fin_h = fin_h.astimezone(PARIS) if fin_h.tzinfo else fin_h
                # horodaté sur plusieurs jours (ex. week-end 10h → 16h le lendemain) ; une fin avant 6h
                # (soirée qui déborde après minuit) ne compte pas comme un jour de plus
                jours = (fin_h.date() - debut).days
                if jours >= 1 and (fin_h.hour >= 6 or jours >= 2):
                    brut.append((titre, debut, ("horodate", fin_h.date())))
                    continue
            brut.append((titre, debut, None))
        else:
            f = ev.get("DTEND")
            brut.append((titre, d0, f.dt if f else None))
    notes = []
    durees = [(f - d).days for _, d, f in brut if isinstance(f, date)]
    if decalage == "auto":
        decale = len(durees) >= 5 and 1 not in durees
    else:
        decale = decalage == "1"
    if decale:
        notes.append("Fin des événements « journée entière » reculée d'un jour : le flux ICS porte un jour de trop "
                     "(aucun événement d'un seul jour n'a une durée de 1 jour ; correctif à faire dans caldav_sync.py). "
                     "Option --decalage-fin 0 pour désactiver.")
    out = []
    for titre, debut, f in brut:
        if f is None:
            fin = debut
        elif isinstance(f, tuple):  # horodaté : la date de fin est déjà le dernier jour
            fin = f[1]
        else:
            fin = f - timedelta(days=1 + (1 if decale else 0))
            if fin < debut:
                notes.append(f"Anomalie ICS : « {titre} » {debut:%d/%m/%Y} fin avant début ; limité au {debut:%d/%m/%Y}.")
                fin = debut
        out.append((titre, debut, fin))
    return out, notes


def lire_regles(chemin: Path):
    regles = []
    with chemin.open(encoding="utf-8", newline="") as f:
        for r in csv.DictReader(f):
            regles.append((re.compile(r["motif"], re.I), r))
    return regles


STYLE_DEFAUT = "bleu"
MOTS_MAJ_AUTORISES = {"CMP", "CPAE", "CCN", "LEM", "KT", "EAV", "WE", "AEP"}


def nettoyer_titre(titre: str) -> str:
    """Titre affiché par défaut : sans le lieu (« @Tigery »), espaces normalisés."""
    return re.sub(r"\s+", " ", re.sub(r"\s*@.*$", "", titre)).strip()


def nom_possible(titre: str) -> bool:
    """Garde-fou RGPD : un titre sans règle qui ressemble à un nom de personne n'est jamais écrit."""
    t = nettoyer_titre(titre)
    if re.search(r"\b(M\.|Mme|Mlle|Monsieur|Madame)\s", t):
        return True
    return any(len(m) >= 5 and m not in MOTS_MAJ_AUTORISES
               for m in re.findall(r"[A-ZÀ-ÖØ-Ý]{2,}", t))


def appliquer_regles(evts_ics, regles, debut_saison, fin_saison, rapport) -> list[Evt]:
    """Tout est affiché, sauf les règles « exclure » ; une règle « afficher » fixe libellé et couleur.
    Sans règle : affiché avec le titre nettoyé (relu dans le rapport, section 3), sauf nom de personne possible."""
    res: list[Evt] = []
    for titre, d1, d2 in evts_ics:
        if d2 < debut_saison or d1 > fin_saison:
            rapport.hors_fenetre += 1
            continue
        for motif, r in regles:
            m = motif.search(titre)
            if not m:
                continue
            if r["action"] == "exclure":
                rapport.exclus[(r["raison"], r["motif"])] += 1
            else:
                res.append(Evt(d1, d2, m.expand(r["libelle"]), r["style"], "ics"))
            break
        else:
            if nom_possible(titre):
                rapport.masques.append((d1, "nom de personne possible"))
            else:
                res.append(Evt(d1, d2, nettoyer_titre(titre), STYLE_DEFAUT, "ics"))
                rapport.non_classes[nettoyer_titre(titre)].append(d1)
    return res


def lire_officiel(chemin: Path):
    evts, vacances, periodes = [], [], []
    with chemin.open(encoding="utf-8", newline="") as f:
        for r in csv.DictReader(f):
            d1, d2 = date.fromisoformat(r["date_debut"]), date.fromisoformat(r["date_fin"])
            if r["categorie"] == "vacances":
                vacances.append((r["libelle"], d1, d2))
            elif r["categorie"] == "periode":
                periodes.append((r["libelle"], d1, d2))
            elif r["afficher"] == "oui":
                evts.append(Evt(d1, d2, r["libelle"], r["style"], "officiel"))
    return evts, vacances, periodes


def lire_manuel(chemin: Path) -> list[Evt]:
    evts = []
    if chemin.exists():
        with chemin.open(encoding="utf-8", newline="") as f:
            for r in csv.DictReader(f):
                if not (r.get("date_debut") or "").strip():
                    continue
                d1 = date.fromisoformat(r["date_debut"].strip())
                d2 = date.fromisoformat((r.get("date_fin") or r["date_debut"]).strip())
                st = (r.get("style") or "or").strip()
                if st not in STYLES:
                    sys.exit(f"Style inconnu dans ajouts_manuels.csv : {st}")
                evts.append(Evt(d1, d2, r["libelle"].strip(), st, "manuel"))
    return evts


def grouper_sacrements(evts: list[Evt]) -> list[Evt]:
    """Même libellé le même jour : « Baptême ×2 » ; les autres doublons sont fusionnés."""
    c: dict[tuple, Evt] = {}
    for e in evts:
        if e.debut == e.fin and e.origine == "ics":
            cle = (e.debut, e.libelle, e.style)
            if cle in c:
                if e.libelle == "Baptême":  # le nombre compte ; autres doublons (saisis plusieurs fois) : un seul
                    c[cle].nombre += 1
                continue
            c[cle] = Evt(e.debut, e.fin, e.libelle, e.style, e.origine)
        else:
            c[(e.debut, e.fin, e.libelle, id(e))] = e
    return list(c.values())


def nettoyer_texte(t: str) -> str:
    """Neutralise l'injection de formules Excel (=, +, -, @ en tête)."""
    return "'" + t if t[:1] in "=+-@" else t


# ---------------------------------------------------------------- écriture XLSX
def etaler(e: Evt):
    d = e.debut
    while d <= e.fin:
        yield d
        d += timedelta(1)


def resoudre_couleurs(evts: list[Evt], par_jour, rapport: Rapport):
    """Un événement long (≥ 5 jours, hors dates officielles) ne partage pas sa couleur avec un événement
    simultané (sinon on ne distingue plus les blocs) ; les événements courts restent lisibles grâce aux bordures."""
    longs = sorted((e for e in evts if (e.fin - e.debut).days >= SEUIL_LONG and e.origine != "officiel"),
                   key=lambda e: (-(e.fin - e.debut).days, e.debut, e.libelle))
    deja = {e.style for e in longs}  # couleurs déjà portées par un événement long : on les évite
    for e in longs:
        simultanes = {x.style for d in etaler(e) for x in par_jour.get(d, []) if x is not e}
        if e.style in simultanes:
            nouv = next((c for c in COULEURS_ALT if c not in simultanes and c not in deja), None)
            if nouv:
                rapport.recolores.append((e.libelle, e.style, nouv))
                e.style = nouv
                deja.add(nouv)


def construire_xlsx(chemin: Path, annee: int, evts: list[Evt], vacances, rapport: Rapport, periodes=()):
    wb = Workbook()
    ws = wb.active
    ws.title = "Calendrier"
    fin_s = f"{annee}-{annee + 1}"
    fin = Side(style="thin")
    epais = Side(style="medium")

    mois = [(annee, m) for m in range(9, 13)] + [(annee + 1, m) for m in range(1, 9)]
    jours_vacances = {d for _, d1, d2 in vacances
                      for d in (d1 + timedelta(n) for n in range((d2 - d1).days + 1))}
    jours_periode = {d for _, d1, d2 in periodes
                     for d in (d1 + timedelta(n) for n in range((d2 - d1).days + 1))}

    # colonnes : [jour sem][n°][séparateur][texte] x 12
    for i in range(12):
        c0 = 1 + 4 * i
        for off, w in enumerate((3.9, 3.9, 1.9, 15.9)):
            ws.column_dimensions[ws.cell(1, c0 + off).column_letter].width = w
    ws.row_dimensions[1].height = 40
    ws.row_dimensions[2].height = 20
    ws.row_dimensions[3].height = 30
    for r in range(4, 97):
        ws.row_dimensions[r].height = 20.1

    ws.merge_cells(start_row=1, start_column=1, end_row=1, end_column=48)
    t = ws.cell(1, 1, f"CALENDRIER PAROISSIAL {fin_s}")
    t.font = Font(name=POLICE, size=40, bold=True)
    t.alignment = Alignment(horizontal="center", vertical="center")

    # ligne 2 : légende des fonds (périodes, vacances)
    legende = []
    if periodes:
        legende.append("Fond rouge des jours : " + ", ".join(
            f"{n} ({d1:%d/%m} → {d2:%d/%m})" for n, d1, d2 in periodes))
    if vacances:
        legende.append("Bande bleue : vacances scolaires zone B")
    if legende:
        ws.merge_cells(start_row=2, start_column=1, end_row=2, end_column=48)
        lg = ws.cell(2, 1, "   ·   ".join(legende))
        lg.font = Font(name=POLICE, size=11, italic=True)
        lg.alignment = Alignment(horizontal="center", vertical="center")

    par_jour: dict[date, list[Evt]] = defaultdict(list)
    for e in evts:
        for d in etaler(e):
            par_jour[d].append(e)
    resoudre_couleurs(evts, par_jour, rapport)

    def ligne(j: int) -> int:
        return 4 + 3 * (j - 1)

    for i, (an, mo) in enumerate(mois):
        c0 = 1 + 4 * i
        ws.merge_cells(start_row=3, start_column=c0, end_row=3, end_column=c0 + 3)
        h = ws.cell(3, c0, MOIS[i])
        h.font = Font(name=POLICE, size=14, bold=True)
        h.alignment = Alignment(horizontal="center", vertical="center")
        for c in range(c0, c0 + 4):
            ws.cell(3, c).border = Border(top=fin, bottom=fin, left=epais if c == c0 else None)

        nb = (date(an + (mo == 12), mo % 12 + 1, 1) - date(an, mo, 1)).days
        for j in range(1, nb + 1):
            d = date(an, mo, j)
            r = ligne(j)
            dim = d.weekday() == 6
            for k in range(3):
                for off in range(4):
                    cel = ws.cell(r + k, c0 + off)
                    cel.border = Border(
                        top=fin if k == 0 else None, bottom=fin if k == 2 else None,
                        left=epais if off == 0 else None, right=fin if off == 3 else None)
                    if d in jours_periode and off < 2:
                        cel.fill = PatternFill("solid", fgColor=TEINTE_PERIODE)
                    elif dim:
                        cel.fill = PatternFill("solid", fgColor=GRIS_DIMANCHE)
                if d in jours_vacances:
                    ws.cell(r + k, c0 + 2).fill = PatternFill("solid", fgColor=BLEU_VACANCES)
            en_periode = d in jours_periode
            for off, val in ((0, JOURS[d.weekday()]), (1, j)):
                ws.merge_cells(start_row=r, start_column=c0 + off, end_row=r + 2, end_column=c0 + off)
                cel = ws.cell(r, c0 + off, val)
                cel.font = Font(name=POLICE, size=12, bold=en_periode, color="FFFFFF" if en_periode else None)
                cel.alignment = Alignment(horizontal="center", vertical="center")

    # --- événements : règles de placement
    #  - 1 événement : 3 lignes ; 2 événements : 1 ligne chacun (3e vide), sauf si l'un est multi-jours : 2 lignes
    #    pour lui ; 3 événements : 1 ligne chacun ; plus de 3 : les derniers regroupés en 3e ligne (rapport)
    #  - un événement multi-jours est ancré en haut ou en bas du jour pour que ses blocs se rejoignent d'un jour
    #    à l'autre (fusion), même quand d'autres événements s'intercalent
    #  - texte écrit une fois par mois (dans le plus grand bloc du mois) ; le reste = couleur seule
    debut_s, fin_s = date(annee, 9, 1), date(annee + 1, 8, 31)
    jours = [debut_s + timedelta(n) for n in range((fin_s - debut_s).days + 1)]

    def colonne(d: date) -> int:
        return 4 + 4 * mois.index((d.year, d.month))

    plan: dict[int, list] = {}
    objets: dict[int, Evt] = {}
    dernier: dict[int, tuple] = {}  # id -> (jour, le bloc de ce jour finit en bas de la case)

    def en_bas(e: Evt, d: date) -> bool:
        """Ancrage d'un événement multi-jours : en haut s'il vient de finir en bas la veille (les blocs se
        rejoignent), sinon en bas s'il continue le lendemain."""
        prev = dernier.get(id(e))
        if prev and prev[0] == d - timedelta(1) and prev[1]:
            return False
        return d < e.fin

    for d in jours:
        liste = sorted(par_jour.get(d, []),
                       key=lambda e: (-(e.fin - e.debut).days, e.origine != "officiel", e.debut, e.libelle))
        # plus de 3 événements : un événement long qui commence avant et finit après ce jour (ex. absence du
        # Père Pascal) cède ses lignes aux autres ; sa couleur continue de part et d'autre
        while len(liste) > 3:
            traversant = next((x for x in liste if x.debut < d < x.fin and x.origine != "officiel"), None)
            if traversant is None:
                break
            liste.remove(traversant)
            rapport.suspendus.append((d, traversant.libelle))
        while len(liste) > 3:  # on regroupe les deux événements au libellé le plus court : lisibilité maximale
            tries = sorted(range(len(liste)), key=lambda i: (len(liste[i].libelle), i))
            i, j = sorted(tries[:2])
            a, b = liste[i], liste[j]
            rapport.debordements.append((d, [a.libelle, b.libelle]))
            fusion = Evt(d, d, f"{a.libelle} / {b.libelle}", a.style, a.origine)
            liste = [x for k, x in enumerate(liste) if k not in (i, j)]
            liste.insert(i, fusion)
        n = len(liste)
        if n == 0:
            continue
        ancre = liste[0] if liste[0].fin > liste[0].debut else None
        if n == 1:
            pos = [(0, 3)]
        elif n == 2:
            if ancre:
                pos = [(1, 2), (0, 1)] if en_bas(ancre, d) else [(0, 2), (2, 1)]
            else:
                pos = [(0, 1), (1, 1)]
        else:
            if ancre and en_bas(ancre, d):
                pos = [(2, 1), (0, 1), (1, 1)]
            else:
                pos = [(0, 1), (1, 1), (2, 1)]
        for e, (off, h) in zip(liste, pos):
            plan.setdefault(id(e), []).append((d, off, h))
            objets[id(e)] = e
            dernier[id(e)] = (d, off + h == 3)

    for k, entrees in plan.items():
        e = objets[k]
        segs: list[list] = []  # [colonne, ligne début, ligne fin]
        for d, off, h in entrees:
            c, r1 = colonne(d), ligne(d.day) + off
            if segs and segs[-1][0] == c and segs[-1][2] == r1 - 1:
                segs[-1][2] = r1 + h - 1
            else:
                segs.append([c, r1, r1 + h - 1])
        avec_texte = {}
        for i, (c, r1, r2) in enumerate(segs):  # un seul bloc par mois porte le texte : le plus grand
            if c not in avec_texte or (r2 - r1) > (segs[avec_texte[c]][2] - segs[avec_texte[c]][1]):
                avec_texte[c] = i
        for i, (c, r1, r2) in enumerate(segs):
            ecrire_evt(ws, r1, r2, c, e, texte=(avec_texte[c] == i))

    for e in evts:
        if e.fin >= debut_s and e.debut <= fin_s:
            lib = e.libelle if e.fin == e.debut else f"{e.libelle} (→ {e.fin:%d/%m})"
            rapport.affiches.append((e.debut, lib, e.origine))

    ws.page_setup.orientation = "landscape"
    ws.page_setup.paperSize = 9
    ws.page_setup.fitToWidth = 1
    ws.page_setup.fitToHeight = 0  # hauteur libre : la coupure manuelle ci-dessous est respectée
    ws.sheet_properties.pageSetUpPr.fitToPage = True
    ws.print_options.horizontalCentered = True
    ws.print_area = "A1:AV96"
    ws.print_title_rows = "1:3"
    ws.row_breaks.append(Break(id=51))  # coupe après le 16 de chaque mois
    ws.page_margins.left = ws.page_margins.right = 0.3
    ws.page_margins.top = ws.page_margins.bottom = 0.4
    wb.save(chemin)


def ecrire_evt(ws, r1: int, r2: int, col: int, e: Evt, texte: bool = True):
    """Bloc coloré de r1 à r2 (fusionné si plusieurs lignes), bordé ; texte plus gros quand le bloc est haut."""
    fond, txt = STYLES[e.style]
    cote = Side(style="thin", color="000000")
    for r in range(r1, r2 + 1):
        cel = ws.cell(r, col)
        cel.fill = PatternFill("solid", fgColor=fond)
        cel.border = Border(left=cote, right=cote, top=cote if r == r1 else None, bottom=cote if r == r2 else None)
    if r2 > r1:
        ws.merge_cells(start_row=r1, start_column=col, end_row=r2, end_column=col)
    nb = r2 - r1 + 1
    taille = 11 if nb < 3 else 12 if nb < 6 else 13 if nb < 12 else 15
    cel = ws.cell(r1, col)
    if texte:
        lib = e.libelle + (f" ×{e.nombre}" if e.nombre > 1 else "")
        cel.value = nettoyer_texte(lib)
    cel.font = Font(name=POLICE, size=taille, bold=True, color=txt)
    cel.alignment = Alignment(horizontal="center", vertical="center",
                              wrap_text=nb >= 2, shrink_to_fit=nb < 2)


# ---------------------------------------------------------------- rapport
def ecrire_rapport(chemin: Path, annee: int, rapport: Rapport, ics_vacances, vacances_off):
    L = [f"# Rapport de contrôle - calendrier paroissial {annee}-{annee + 1}", ""]
    L += ["## 1. Événements affichés", "",
          "| Date | Libellé | Origine |", "|---|---|---|"]
    for d, lib, o in sorted(rapport.affiches):
        L.append(f"| {d:%d/%m/%Y} | {lib} | {o} |")
    L += ["", "## 2. Attendus (calendrier 2025-2026) non trouvés cette année", "",
          "À vérifier : rien n'est inventé ; ce qui manque reste vide.", "",
          "| Famille 2025-2026 | Présent ? | Statut connu |", "|---|---|---|"]
    libs = [lib for _, lib, _ in rapport.affiches]
    for fam, motif, statut in REFERENCE_2025:
        ok = any(re.search(motif, x, re.I) for x in libs)
        L.append(f"| {fam} | {'oui' if ok else '**NON**'} | {statut} |")
    L += ["", "## 3. Affichés par défaut (aucune règle) : à relire, ajouter une règle pour changer libellé/couleur ou exclure", "",
          "| Titre | Dates |", "|---|---|"]
    for titre, ds in sorted(rapport.non_classes.items(), key=lambda x: min(x[1])):
        L.append(f"| {titre} | {', '.join(f'{d:%d/%m/%Y}' for d in sorted(ds)[:6])}"
                 f"{' …' if len(ds) > 6 else ''} |")
    if not rapport.non_classes:
        L.append("| (aucun) | |")
    L += ["", "## 4. Écarts ICS / sources officielles", ""]
    for titre, d1, d2 in ics_vacances:
        for nom, o1, o2 in vacances_off:
            if o1 == d1 and nom.split()[-1].lower() in titre.lower():
                if o2 != d2:
                    L.append(f"- {titre} : ICS {d1:%d/%m} → {d2:%d/%m} ; officiel {o1:%d/%m} → {o2:%d/%m} "
                             f"(ICS décalé de {(d2 - o2).days} jour). **Officiel retenu.**")
    if rapport.ecarts:
        L += [f"- {x}" for x in rapport.ecarts]
    L += [f"- {x}" for x in rapport.notes_ics]
    for lib, ancien, nouveau in rapport.recolores:
        L.append(f"- Couleur modifiée : « {lib} » {ancien} → {nouveau} (événement long simultané à un autre de même couleur).")
    L += ["", "## 5. Jours avec plus de 3 événements (les deux libellés les plus courts regroupés sur une ligne)", ""]
    L += [f"- {d:%d/%m/%Y} : {', '.join(x)}" for d, x in rapport.debordements] or ["- (aucun)"]
    L += ["", "## 5a. Événement long sans ligne ce jour-là (plus de 3 événements ; sa couleur reprend le lendemain)", ""]
    L += [f"- {d:%d/%m/%Y} : {lib}" for d, lib in rapport.suspendus] or ["- (aucun)"]
    L += ["", "## 5b. Masqués par garde-fou (nom de personne possible : titre jamais écrit)", ""]
    L += [f"- {d:%d/%m/%Y}" for d, _ in sorted(rapport.masques)] or ["- (aucun)"]
    L += ["", "## 6. Événements ICS exclus par règle", "",
          "| Règle (raison) | Motif | Nombre |", "|---|---|---|"]
    for (raison, motif), n in sorted(rapport.exclus.items(), key=lambda x: -x[1]):
        L.append(f"| {raison} | `{motif}` | {n} |")
    L += ["", f"_Événements ICS hors de la saison : {rapport.hors_fenetre}._", ""]
    chemin.write_text("\n".join(L), encoding="utf-8")


# ---------------------------------------------------------------- principal
def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--annee", type=int, default=2026, help="année de rentrée (2026 = saison 2026-2027)")
    p.add_argument("--ics", default=ICS_URL_DEFAUT, help="URL https ou fichier .ics local")
    p.add_argument("--sortie", default=str(HERE / "sortie"), help="dossier de sortie")
    p.add_argument("--decalage-fin", choices=["auto", "0", "1"], default="auto",
                   help="correction de la fin des événements « journée entière » de l'ICS (auto : détectée)")
    p.add_argument("--sans-pdf", action="store_true")
    a = p.parse_args(argv)

    saison = f"{a.annee}-{a.annee + 1}"
    sortie = Path(a.sortie)
    sortie.mkdir(parents=True, exist_ok=True)
    debut_s, fin_s = date(a.annee, 9, 1), date(a.annee + 1, 8, 31)

    rap = Rapport()
    ics, notes = lire_ics(a.ics, a.decalage_fin)
    rap.notes_ics.extend(notes)
    evts = appliquer_regles(ics, lire_regles(HERE / "regles.csv"), debut_s, fin_s, rap)
    off, vac, per = lire_officiel(HERE / f"dates_officielles_{saison}.csv")
    evts = grouper_sacrements(evts) + off + lire_manuel(HERE / "ajouts_manuels.csv")

    ics_vac = [(t, d1, d2) for t, d1, d2 in ics if t.lower().startswith("vacances")]
    xlsx = sortie / f"Calendrier_paroissial_{saison}.xlsx"
    construire_xlsx(xlsx, a.annee, evts, vac, rap, per)
    rapport = sortie / f"rapport_controle_{saison}.md"
    ecrire_rapport(rapport, a.annee, rap, ics_vac, vac)
    print(f"OK  {xlsx}\nOK  {rapport}")

    if not a.sans_pdf:
        try:
            subprocess.run(["soffice", "--headless", "--convert-to", "pdf", "--outdir", str(sortie), str(xlsx)],
                           check=True, capture_output=True, timeout=180)
            print(f"OK  {xlsx.with_suffix('.pdf')}")
        except (FileNotFoundError, subprocess.SubprocessError):
            print("PDF non généré (LibreOffice introuvable) : ouvrir le .xlsx et exporter en PDF.")


if __name__ == "__main__":
    main()
