#!/usr/bin/env python3
"""Canli ozet — reer_analysis_data.csv + kaynak_damgasi.json'dan, internetsiz."""
import json, os, sys
import pandas as pd
BASE = os.path.dirname(os.path.abspath(__file__))
df = pd.read_csv(os.path.join(BASE, "reer_analysis_data.csv"), parse_dates=["Dönem"])
s = df.dropna(subset=["Deviation_10Y_Pct"]).iloc[-1]

# Kaynak damgasi: once main.py'nin yazdigi JSON, yoksa CSV'deki Kaynak sutunu.
# Boylece yayindaki sayinin EVDS'ten mi bayat Excel yedeginden mi geldigi gorunur.
damga = {}
damga_yolu = os.path.join(BASE, "kaynak_damgasi.json")
if os.path.exists(damga_yolu):
    damga = json.load(open(damga_yolu, encoding="utf-8"))
elif "Kaynak" in df.columns:
    damga = {"kaynak": str(df["Kaynak"].iloc[-1])}
else:
    print("UYARI: kaynak damgasi yok (kaynak_damgasi.json / CSV 'Kaynak' sutunu) — "
          "veri kaynagi bilinmiyor; main.py'yi yeniden kosturun.", file=sys.stderr)

kaynak = damga.get("kaynak", "bilinmiyor")

# Gecikme HER ZAMAN CSV'nin gercek son gozleminden, BUGUNE gore yeniden
# hesaplanir. Damgadaki gecikme_ay yazildigi anin degeridir; kopyalanirsa
# aylar sonra bile "1 ay gecikme / guncel" diye donmus halde yayinlanir.
_bugun = pd.Timestamp.today().normalize()
_son = s["Dönem"]
csv_son_gozlem = _son.strftime("%Y-%m")
gecikme_ay = (_bugun.year - _son.year) * 12 + (_bugun.month - _son.month)

# Damga ile CSV celisiyorsa CSV otoritedir (sayilar ondan geliyor); damga
# artik kalmis olabilir. Celiski sessiz gecmez.
csv_kaynak = str(df["Kaynak"].iloc[-1]) if "Kaynak" in df.columns else None
if csv_kaynak and kaynak != "bilinmiyor" and csv_kaynak != kaynak:
    print(f"UYARI: damga kaynagi ({kaynak}) ile CSV 'Kaynak' sutunu "
          f"({csv_kaynak}) uyusmuyor — CSV esas alindi.", file=sys.stderr)
    kaynak = csv_kaynak

damga_son = damga.get("son_gozlem")
if damga_son and damga_son != csv_son_gozlem:
    print(f"UYARI: kaynak damgasi ({damga_son}) ile CSV son gozlemi "
          f"({csv_son_gozlem}) uyusmuyor — damga bayat olabilir, CSV esas alindi.",
          file=sys.stderr)
    kaynak = "bilinmiyor"

# TAZELIK FAIL-CLOSED: damga yoksa/kaynak bilinmiyorsa "guncel" DEME.
# Esik main.py ile ayni (TAZELIK_ESIGI_AY = 2).
if kaynak == "bilinmiyor":
    tazelik = "bilinmiyor"
elif damga.get("bayat") or gecikme_ay > 2:
    tazelik = "bayat"
else:
    tazelik = "güncel"
ozet = {
    "_tarih": s["Dönem"].strftime("%m.%Y"),
    "donem": s["Dönem"].strftime("%B %Y").replace("January","Ocak").replace("February","Şubat").replace("March","Mart").replace("April","Nisan").replace("May","Mayıs").replace("June","Haziran").replace("July","Temmuz").replace("August","Ağustos").replace("September","Eylül").replace("October","Ekim").replace("November","Kasım").replace("December","Aralık"),
    "redk": round(float(s["Composite_REER"]), 1),
    "sapma10": round(float(s["Deviation_10Y_Pct"]), 1),
    "sapma5": round(float(s["Deviation_5Y_Pct"]), 1),
    "ppi10": round(float(s["PPI_Deviation_10Y_Pct"]), 1),
    "cpi10": round(float(s["CPI_Deviation_10Y_Pct"]), 1),
    # --- kaynak / tazelik damgasi ---
    "kaynak": kaynak,
    "kaynak_etiket": damga.get("kaynak_etiket",
                               {"evds": "TCMB EVDS",
                                "excel": "yerel Excel (yedek)"}.get(kaynak, "bilinmiyor")),
    "son_gozlem": csv_son_gozlem,
    "gecikme_ay": gecikme_ay,
    "tazelik": tazelik,
    "cekim": damga.get("cekim_zamani"),
}
if kaynak != "evds" or tazelik != "güncel":
    print(f"UYARI: ozet.json birincil kaynaktan gelmiyor veya bayat — "
          f"kaynak={kaynak}, son gozlem={ozet['son_gozlem']}, "
          f"gecikme={ozet['gecikme_ay']} ay.", file=sys.stderr)
json.dump(ozet, open(os.path.join(BASE, "ozet.json"), "w"), ensure_ascii=False, indent=1)
print(json.dumps(ozet, ensure_ascii=False))
