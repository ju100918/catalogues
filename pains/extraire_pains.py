"""Récupère les ingrédients des pains listés dans urls.txt et produit pains_ingredients.xlsx.

Usage : python3 pains/extraire_pains.py [--refresh]

- urls.txt : une URL de produit par ligne (lignes vides et # ignorées).
- donnees.json : cache des fiches déjà extraites (clé = URL) ; --refresh les re-télécharge.
- saisie_manuelle.json : fiches saisies à la main (Coop, dont le site bloque les robots),
  même format que donnees.json.

Migros et Aldi sont lus avec Chromium (Playwright), Lidl directement depuis le HTML.
"""
import asyncio, datetime, html, json, os, re, sys
from bs4 import BeautifulSoup
from openpyxl import Workbook
from openpyxl.styles import Alignment, Font, PatternFill
from openpyxl.utils import get_column_letter
from playwright.async_api import async_playwright

ROOT = os.path.dirname(os.path.abspath(__file__))
CHROME = "/opt/pw-browsers/chromium-1194/chrome-linux/chrome"
UA = "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0 Safari/537.36"
COLS = ["enseigne", "marque", "produit", "denomination", "poids", "prix", "prix_100g", "ingredients",
        "allergenes", "traces", "origine", "categorie", "code_article", "url", "date_extraction"]


def clean(text):
    if not text:
        return None
    text = html.unescape(re.sub(r"<[^>]+>", "", text))
    text = re.sub(r"\s+", " ", text).strip()
    return re.sub(r"\s+([,.])", r"\1", text) or None


def enseigne(url):
    for k, v in {"migros.ch": "Migros", "coop.ch": "Coop", "aldi-suisse.ch": "Aldi", "lidl.ch": "Lidl"}.items():
        if k in url:
            return v
    return None


def prix_100g(prix, poids):
    m = re.match(r"(\d+(?:[.,]\d+)?)\s*(kg|g)\b", poids or "")
    if prix is None or not m:
        return None
    g = float(m.group(1).replace(",", ".")) * (1000 if m.group(2) == "kg" else 1)
    return round(prix / g * 100, 2)


async def migros(page, url):
    mid = re.search(r"/product/(\w+)", url).group(1)
    async with page.expect_response(lambda r: f"/product-display/public/v1/products/mgb/{mid}" in r.url,
                                    timeout=60000) as resp:
        await page.goto(url, wait_until="domcontentloaded", timeout=60000)
    d = await (await resp.value).json()
    info = d["productInformation"]["mainInformation"]
    offer = d.get("offer") or {}
    price = (offer.get("price") or {}).get("effectiveValue")
    origine = clean(info.get("origin"))
    return {"marque": d.get("brand"), "produit": clean(d.get("description") or d.get("name")),
            "poids": offer.get("quantity"), "prix": price,
            "ingredients": clean(info.get("ingredients")),
            "allergenes": clean(info.get("allergens")), "traces": clean(info.get("allergenIndication")),
            "origine": None if origine and "sur l’emballage" in origine else origine,
            "categorie": " > ".join(b["name"] for b in d.get("breadcrumb", [])), "code_article": mid}


async def aldi(page, url):
    await page.goto(url, wait_until="networkidle", timeout=60000)
    s = BeautifulSoup(await page.content(), "html.parser")
    prod = next(j for j in (json.loads(t.string) for t in s.find_all("script", type="application/ld+json"))
                if j.get("@type") == "Product")
    crumbs = next(j for j in (json.loads(t.string) for t in s.find_all("script", type="application/ld+json"))
                  if j.get("@type") == "BreadcrumbList")["itemListElement"]
    desc = clean(prod.get("description"))
    origine = re.match(r"Origine\s*:\s*([^.]+)\.\s*", desc)
    if origine:
        desc = desc[origine.end():]
    ingr, _, traces = desc.partition("Indications sur les allergènes:")
    poids = re.search(re.escape(prod["name"]) + r"\s+(\d+(?:[.,]\d+)?\s?k?g)\b", s.get_text(" ", strip=True))
    return {"marque": prod.get("brand", {}).get("name"), "produit": prod["name"],
            "poids": poids.group(1) if poids else None, "prix": float(prod["offers"]["price"]),
            "ingredients": ingr.strip() or None, "traces": traces.strip() or None,
            "origine": origine.group(1) if origine else None,
            "categorie": " > ".join(c["name"] for c in crumbs[2:-1]), "code_article": url.rsplit("-", 1)[-1]}


async def lidl(page, url):
    await page.goto(url, wait_until="domcontentloaded", timeout=60000)
    s = BeautifulSoup(await page.content(), "html.parser")
    col = s.select_one("div.col-left")
    texte = clean(" ".join(p.get_text(" ") for p in col.find_all("p", class_=False)))
    denom, _, ingr = texte.partition("Ingrédients:")
    if not ingr:
        denom, ingr = None, texte
    origine = re.search(r"\s*(?:Produit|Fabriqué|Origine)[^.]*?(?:en|:)\s*([^.]+)\.\s*$", ingr)
    if origine:
        ingr = ingr[:origine.start()]
    ingr, _, traces = ingr.partition("Peut contenir")
    poids = re.search(r"les\s+(\d+(?:[.,]\d+)?\s?k?g)\b", col.get_text(" "))
    return {"marque": None, "produit": s.find("meta", property="og:title")["content"].strip(),
            "denomination": denom.strip() or None, "poids": poids.group(1) if poids else None,
            "prix": float(s.find("meta", property="product:price:amount")["content"]),
            "ingredients": ingr.strip() or None, "traces": ("Peut contenir" + traces).strip() if traces else None,
            "origine": origine.group(1) if origine else None,
            "code_article": re.sub(r"\D", "", col.select_one("p.sku").get_text())}


async def fetch(urls):
    out = {}
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True, executable_path=CHROME,
                                          args=["--disable-blink-features=AutomationControlled"])
        ctx = await browser.new_context(locale="fr-CH", user_agent=UA)
        for url in urls:
            shop = enseigne(url)
            fn = {"Migros": migros, "Aldi": aldi, "Lidl": lidl}.get(shop)
            if not fn:
                print(f"IGNORÉ ({shop or 'enseigne inconnue'} : saisie manuelle requise) {url}")
                continue
            page = await ctx.new_page()
            try:
                r = await fn(page, url)
                r = {c: r.get(c) for c in COLS} | {"enseigne": shop, "url": url,
                                                    "date_extraction": datetime.date.today().isoformat()}
                out[url] = r
                print(f"OK  {shop:6} {r['produit']}" + ("" if r["ingredients"] else "  ⚠ pas d'ingrédients"))
            except Exception as e:
                print(f"ERREUR {url} : {type(e).__name__}: {e}")
            finally:
                await page.close()
        await browser.close()
    return out


def split_ingredients(text):
    """Découpe la liste aux virgules de premier niveau, en gardant l'ordre du site.

    Les virgules entre parenthèses/crochets (sous-ingrédients) et les virgules décimales
    (« 1,5% ») ne coupent pas ; la note de bas de liste (« * de l'agriculture biologique… »)
    est retirée.
    """
    text = re.split(r"\.\s+\*|\s\*+\s?(?:de l|issu|provenant)", text)[0].strip().rstrip(".")
    parts, cur, depth = [], "", 0
    for i, ch in enumerate(text):
        depth += 1 if ch in "([" else -1 if ch in ")]" else 0
        decimal = ch == "," and 0 < i < len(text) - 1 and text[i - 1].isdigit() and text[i + 1].isdigit()
        if ch == "," and depth == 0 and not decimal:
            parts.append(cur)
            cur = ""
        else:
            cur += ch
    parts.append(cur)
    return [p.strip() for p in parts if p.strip()]


def build_excel(rows):
    wb = Workbook()
    ws = wb.active
    ws.title = "Pains"
    lists = [split_ingredients(r.get("ingredients") or "") for r in rows]
    n = max(map(len, lists), default=0)
    ws.append(["Pain", "Supermarché", "Prix (CHF)", "Prix aux 100 g (CHF)"]
              + [f"Ingrédient {i}" for i in range(1, n + 1)])
    for r, ingr in zip(rows, lists):
        ws.append([r["produit"], r["enseigne"], r.get("prix"), prix_100g(r.get("prix"), r.get("poids"))] + ingr)
    style(ws, [40, 12, 10, 12] + [28] * n, wrap_cols=set(range(5, n + 5)))
    for row in ws.iter_rows(min_row=2):
        row[2].number_format = row[3].number_format = "0.00"

    wd = wb.create_sheet("Détails")
    wd.append(COLS)
    for r in rows:
        r["prix_100g"] = prix_100g(r.get("prix"), r.get("poids"))
        wd.append([r.get(c) for c in COLS])
    style(wd, [10, 18, 40, 30, 9, 9, 10, 100, 40, 50, 18, 40, 14, 50, 14], wrap_cols={8, 9, 10})
    for row in wd.iter_rows(min_row=2):
        row[5].number_format = row[6].number_format = "0.00"
        url = row[13]
        url.hyperlink, url.style = url.value, "Hyperlink"
    wb.save(os.path.join(ROOT, "pains_ingredients.xlsx"))


def style(ws, widths, wrap_cols):
    for c in ws[1]:
        c.font = Font(bold=True, color="FFFFFF")
        c.fill = PatternFill("solid", fgColor="E65C00")
        c.alignment = Alignment(wrap_text=True, vertical="center")
    for i, w in enumerate(widths, 1):
        ws.column_dimensions[get_column_letter(i)].width = w
    for row in ws.iter_rows(min_row=2):
        for c in row:
            c.alignment = Alignment(wrap_text=c.column in wrap_cols, vertical="top")
    ws.freeze_panes = "B2"
    ws.auto_filter.ref = ws.dimensions


def load(name):
    path = os.path.join(ROOT, name)
    return json.load(open(path, encoding="utf-8")) if os.path.exists(path) else {}


def main():
    refresh = "--refresh" in sys.argv
    urls = [l.strip() for l in open(os.path.join(ROOT, "urls.txt"), encoding="utf-8")
            if l.strip() and not l.startswith("#")]
    data = load("donnees.json")
    todo = [u for u in dict.fromkeys(urls) if refresh or u not in data]
    if todo:
        data.update(asyncio.run(fetch(todo)))
        json.dump(data, open(os.path.join(ROOT, "donnees.json"), "w", encoding="utf-8"),
                  ensure_ascii=False, indent=1)
    manual = load("saisie_manuelle.json")
    rows = [data[u] for u in dict.fromkeys(urls) if u in data] + list(manual.values())
    rows.sort(key=lambda r: (r["enseigne"], r["produit"] or ""))
    build_excel(rows)
    print(len(rows), "pains dans pains_ingredients.xlsx")


if __name__ == "__main__":
    main()
