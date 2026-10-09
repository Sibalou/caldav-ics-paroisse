"""Tests rapides : python -m pytest -q"""
import csv
import sys
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import generer_calendrier as g  # noqa: E402

HERE = Path(__file__).resolve().parents[1]


def classer(titre):
    for motif, r in g.lire_regles(HERE / "regles.csv"):
        m = motif.search(titre)
        if m:
            return r["action"], m.expand(r["libelle"])
    return None, None


def test_noms_jamais_ecrits():
    action, lib = classer("Baptême de Salomé MOUNIER")
    assert (action, lib) == ("afficher", "Baptême")
    # mariages et funérailles : hors agenda paroissial (décision 2026-10-01)
    assert classer("Mariage de M. X et Mme Y")[0] == "exclure"
    assert classer("Funérailles de M. Georges  THIEBAUT")[0] == "exclure"


def test_decisions_2026_10_01():
    assert classer("Casa") == ("afficher", "Casa")
    assert classer("Case") == ("afficher", "Casa")
    assert classer("concert  eglise de ST hilaire") == ("afficher", "Concert")  # réintégré 2026-10-09
    assert classer("ass St Joseph")[0] == "afficher"  # retiré des exclusions 2026-10-09
    assert classer("Autre")[0] == "exclure" and classer("Temps De Prière")[0] == "exclure"
    assert classer("Groupe de prière")[0] == "afficher"
    assert classer("Père Pascal en Côte d'Ivoire")[0] == "afficher"
    assert classer("Visite du Pape en France")[0] == "afficher"
    assert classer("Semaine Sainte")[0] == "exclure"  # remplacé par l'Ordo


def test_routine_exclue_et_chrismale_conservee():
    assert classer("Messe")[0] == "exclure"
    assert classer("(P. YESSO) Messe")[0] == "exclure"
    assert classer("Messe Chrismale @Cathédrale") == ("afficher", "Messe Chrismale")


def test_dates_officielles_coherentes():
    with (HERE / "dates_officielles_2026-2027.csv").open(encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    for r in rows:
        d1, d2 = date.fromisoformat(r["date_debut"]), date.fromisoformat(r["date_fin"])
        assert d1 <= d2 and r["source"]
        assert r["style"] in g.STYLES or r["style"] in ("barre", "teinte", "")
    pacques = next(r for r in rows if r["libelle"] == "Pâques")
    assert date.fromisoformat(pacques["date_debut"]).weekday() == 6  # dimanche


def test_injection_formule_neutralisee():
    assert g.nettoyer_texte("=1+1").startswith("'")


def test_placement_pleine_hauteur_et_repetition(tmp_path):
    from openpyxl import load_workbook
    rap = g.Rapport()
    seul = g.Evt(date(2026, 9, 12), date(2026, 9, 13), "Rentrée Cté", "bleu", "ics")
    a = g.Evt(date(2026, 11, 9), date(2026, 11, 11), "Journée Paroisse", "bleu", "ics")
    b = g.Evt(date(2026, 11, 11), date(2026, 11, 11), "Éveil à la Foi", "bleu", "ics")
    f = g.Evt(date(2026, 11, 11), date(2026, 11, 11), "Armistice 1918", "jaune", "officiel")
    out = tmp_path / "t.xlsx"
    g.construire_xlsx(out, 2026, [seul, a, b, f], [], rap)
    ws = load_workbook(out).active
    merges = {str(m) for m in ws.merged_cells.ranges}
    assert "D37:D42" in merges  # 12 et 13 sept : un seul bloc de 6 lignes
    # Journée Paroisse (9-11 nov) : bloc fusionné 9-10 nov avec le texte ; le 11 nov, la couleur seule suffit
    assert ws.cell(4 + 3 * 8, 12).value == "Journée Paroisse"
    r = 4 + 3 * 10  # 11 nov : trois événements, le plus long en haut
    assert [ws.cell(r + k, 12).value for k in range(3)] == [None, "Armistice 1918", "Éveil à la Foi"]  # 3 événements : 1 ligne chacun


def test_garde_fou_noms_et_defaut():
    assert g.nom_possible("Communion Isabelle GUNGWELE")
    assert g.nom_possible("Obsèques de Mme Dupont")
    assert not g.nom_possible("Rencontre des CMP & CPAE du Diocèse @Visitation")
    assert g.nettoyer_titre("Semaine Epiphanie @Montagnieu") == "Semaine Epiphanie"


def test_multi_jours_fusionne_texte_une_fois(tmp_path):
    from openpyxl import load_workbook
    rap = g.Rapport()
    long = g.Evt(date(2026, 10, 20), date(2026, 10, 24), "Long", "violet", "ics")
    court = g.Evt(date(2026, 10, 22), date(2026, 10, 22), "Court", "or", "ics")
    out = tmp_path / "t.xlsx"
    g.construire_xlsx(out, 2026, [long, court], [], rap)
    ws = load_workbook(out).active
    col = 8  # octobre
    textes = [ws.cell(r, col).value for r in range(4 + 3 * 19, 4 + 3 * 24) if ws.cell(r, col).value]
    assert textes.count("Long") == 1 and textes.count("Court") == 1


def ics_test(tmp_path, evenements):
    lignes = ["BEGIN:VCALENDAR", "VERSION:2.0", "PRODID:-//test//FR"]
    for i, (titre, d1, d2) in enumerate(evenements):
        lignes += ["BEGIN:VEVENT", f"UID:{i}@test", f"SUMMARY:{titre}", f"DTSTART;VALUE=DATE:{d1}",
                   f"DTEND;VALUE=DATE:{d2}", "END:VEVENT"]
    lignes.append("END:VCALENDAR")
    f = tmp_path / "t.ics"
    f.write_text("\n".join(lignes), encoding="utf-8")
    return str(f)


def test_decalage_fin_detecte_et_corrige(tmp_path):
    # flux « décalé » : un événement d'un jour a DTEND = DTSTART + 2
    evts = [(f"E{i}", f"2026100{i}", f"2026100{i + 2}") for i in range(1, 7)]
    out, notes = g.lire_ics(ics_test(tmp_path, evts))
    assert out[0][1] == out[0][2] == date(2026, 10, 1) and notes
    # flux conforme RFC 5545 : un événement a une durée de 1 jour -> aucune correction
    evts2 = evts + [("Un jour", "20261010", "20261011")]
    out2, notes2 = g.lire_ics(ics_test(tmp_path, evts2))
    assert out2[0][2] == date(2026, 10, 2) and not notes2
    assert g.lire_ics(ics_test(tmp_path, evts), "0")[0][0][2] == date(2026, 10, 2)


def test_anomalie_fin_avant_debut(tmp_path):
    evts = [("Bizarre", "20261010", "20261010")] + [(f"E{i}", f"2026100{i}", f"2026100{i + 1}") for i in range(1, 6)]
    out, notes = g.lire_ics(ics_test(tmp_path, evts))
    assert out[0][1] == out[0][2] and any("Anomalie" in n for n in notes)


def test_ancrage_evenement_long_et_fusion(tmp_path):
    from openpyxl import load_workbook
    rap = g.Rapport()
    # « Pape » du 25 au 29/09 ; un événement le 26 et le 29 : le bloc du 25 rejoint les 2 premières lignes du 26
    pape = g.Evt(date(2026, 9, 25), date(2026, 9, 29), "Pape", "violet", "ics")
    x = g.Evt(date(2026, 9, 26), date(2026, 9, 26), "X", "or", "ics")
    y = g.Evt(date(2026, 9, 28), date(2026, 9, 28), "Y", "or", "ics")
    out = tmp_path / "t.xlsx"
    g.construire_xlsx(out, 2026, [pape, x, y], [], rap)
    ws = load_workbook(out).active
    merges = {str(m) for m in ws.merged_cells.ranges}
    r25, r26 = 4 + 3 * 24, 4 + 3 * 25
    assert f"D{r25}:D{r26 + 1}" in merges  # 25/09 entier + 2 premières lignes du 26/09
    assert ws.cell(r26 + 2, 4).value == "X"


def test_deux_evenements_une_ligne_chacun(tmp_path):
    from openpyxl import load_workbook
    rap = g.Rapport()
    a = g.Evt(date(2026, 10, 6), date(2026, 10, 6), "A", "bleu", "ics")
    b = g.Evt(date(2026, 10, 6), date(2026, 10, 6), "B", "or", "ics")
    out = tmp_path / "t.xlsx"
    g.construire_xlsx(out, 2026, [a, b], [], rap)
    ws = load_workbook(out).active
    r = 4 + 3 * 5
    assert [ws.cell(r + k, 8).value for k in range(3)] == ["A", "B", None]


def test_conflit_de_couleur_evenement_long(tmp_path):
    rap = g.Rapport()
    long = g.Evt(date(2027, 1, 3), date(2027, 1, 9), "Semaine", "bleu", "ics")
    court = g.Evt(date(2027, 1, 5), date(2027, 1, 5), "Court", "bleu", "ics")
    g.construire_xlsx(tmp_path / "t.xlsx", 2026, [long, court], [], rap)
    assert long.style != "bleu" and court.style == "bleu" and rap.recolores


def test_periode_teinte(tmp_path):
    from openpyxl import load_workbook
    rap = g.Rapport()
    out = tmp_path / "t.xlsx"
    g.construire_xlsx(out, 2026, [], [], rap, [("Avent", date(2026, 11, 29), date(2026, 12, 24))])
    ws = load_workbook(out).active
    r = 4 + 3 * 29  # 30/11 : colonne des jours de novembre = 9/10
    assert ws.cell(r, 9).fill.fgColor.rgb.endswith(g.TEINTE_PERIODE)
    assert ws.cell(4 + 3 * 28, 9).fill.fgColor.rgb.endswith(g.TEINTE_PERIODE)  # le dimanche 29/11 est rouge aussi


def test_evenement_traversant_cede_ses_lignes(tmp_path):
    from openpyxl import load_workbook
    rap = g.Rapport()
    long = g.Evt(date(2026, 10, 20), date(2026, 11, 20), "Long", "violet", "ics")
    petits = [g.Evt(date(2026, 11, 14), date(2026, 11, 14), n, c, "ics")
              for n, c in (("A", "or"), ("B", "vert"), ("C", "orange"))]
    out = tmp_path / "t.xlsx"
    g.construire_xlsx(out, 2026, [long] + petits, [], rap)
    ws = load_workbook(out).active
    r = 4 + 3 * 13
    assert [ws.cell(r + k, 12).value for k in range(3)] == ["A", "B", "C"]
    assert rap.suspendus == [(date(2026, 11, 14), "Long")] and not rap.debordements


def test_debordement_fusionne_les_textes_les_plus_courts(tmp_path):
    from openpyxl import load_workbook
    rap = g.Rapport()
    noms = ["Un très long libellé", "Autre long libellé ici", "CMP", "V & V"]
    evts = [g.Evt(date(2026, 10, 6), date(2026, 10, 6), n, "bleu", "ics") for n in noms]
    out = tmp_path / "t.xlsx"
    g.construire_xlsx(out, 2026, evts, [], rap)
    ws = load_workbook(out).active
    r = 4 + 3 * 5
    vals = [ws.cell(r + k, 8).value for k in range(3)]
    assert sorted(vals) == sorted(["Un très long libellé", "Autre long libellé ici", "CMP / V & V"])


def test_evenement_horodate_sur_deux_jours(tmp_path):
    f = tmp_path / "t.ics"
    f.write_text("BEGIN:VCALENDAR\nVERSION:2.0\nPRODID:-//t//FR\n"
                 "BEGIN:VEVENT\nUID:1\nSUMMARY:WE\nDTSTART:20261114T100000\nDTEND:20261115T160000\nEND:VEVENT\n"
                 "BEGIN:VEVENT\nUID:2\nSUMMARY:Soirée\nDTSTART:20261114T200000\nDTEND:20261115T010000\nEND:VEVENT\n"
                 "END:VCALENDAR\n", encoding="utf-8")
    out, _ = g.lire_ics(str(f))
    assert out[0][1:] == (date(2026, 11, 14), date(2026, 11, 15))
    assert out[1][1:] == (date(2026, 11, 14), date(2026, 11, 14))
