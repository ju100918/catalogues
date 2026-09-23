"""Assemble les extractions par page (extraction/pNNN.json) en promotions_extraites.xlsx."""
import glob, json, os, re
from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill, Alignment
from openpyxl.utils import get_column_letter

ROOT = os.path.dirname(os.path.abspath(__file__))
SOURCES = {"extraction": "Migros-Wochenflyer-25-2026-f-VD.pdf"}

rows = []
for path in sorted(glob.glob(os.path.join(ROOT, "extraction", "p*.json"))):
    page = int(re.search(r"p(\d+)\.json$", path).group(1))
    for r in json.load(open(path, encoding="utf-8")):
        r["page"] = page
        r["fichier_source"] = SOURCES["extraction"]
        pi, pf = r.get("prix_initial"), r.get("prix_final")
        if pi is not None and pf is not None:
            r["rabais_montant"] = round(pi - pf, 2)
            r["rabais_pourcentage"] = round((pi - pf) / pi * 100, 1)
        else:
            r["rabais_montant"] = r["rabais_pourcentage"] = None
        rows.append(r)

rows.sort(key=lambda r: (r["fichier_source"], r["page"]))  # tri stable: ordre de lecture conservé

cols = [("fichier_source", "Fichier source"), ("page", "Page"), ("produit", "Produit"),
        ("categorie_pyramide", "Catégorie pyramide alimentaire"), ("provenance", "Provenance"),
        ("labels", "Labels"), ("type_offre", "Type d'offre"), ("prix_initial", "Prix initial (CHF)"),
        ("prix_final", "Prix final (CHF)"), ("rabais_montant", "Rabais (CHF)"),
        ("rabais_pourcentage", "Rabais (%)")]

wb = Workbook(); ws = wb.active; ws.title = "Promotions"
ws.append([h for _, h in cols])
for r in rows:
    ws.append([", ".join(r[k]) if k == "labels" and r[k] else (None if k == "labels" else r.get(k)) for k, _ in cols])

for c in ws[1]:
    c.font = Font(bold=True, color="FFFFFF"); c.fill = PatternFill("solid", fgColor="E65C00")
    c.alignment = Alignment(wrap_text=True, vertical="center")
widths = [36, 7, 70, 42, 26, 30, 42, 14, 14, 12, 11]
for i, w in enumerate(widths, 1):
    ws.column_dimensions[get_column_letter(i)].width = w
for row in ws.iter_rows(min_row=2):
    for c in row[7:10]: c.number_format = "0.00"
    row[10].number_format = "0.0"
ws.freeze_panes = "A2"; ws.auto_filter.ref = ws.dimensions
wb.save(os.path.join(ROOT, "promotions_extraites.xlsx"))
print(len(rows), "lignes")
