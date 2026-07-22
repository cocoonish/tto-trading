#!/usr/bin/env python3
"""Canli ozet — EVDS'ten USD/TRY cekip ACT/365 deval hesaplar (tek seri, hizli)."""
import json, os, re
from urllib.parse import urlencode
import pandas as pd, requests
BASE = os.path.dirname(os.path.abspath(__file__))
kaynak = open(os.path.join(BASE, "usdtry_deval_plotly.py")).read()
KEY = re.search(r'EVDS_KEY\s*=\s*"([^"]+)"', kaynak).group(1)
EVDS = "https://evds3.tcmb.gov.tr/igmevdsms-dis"
bas = (pd.Timestamp.today() - pd.Timedelta(days=160)).strftime("%d-%m-%Y")
son = pd.Timestamp.today().strftime("%d-%m-%Y")
p = {"series": "TP.DK.USD.A.YTL", "startDate": bas, "endDate": son, "type": "json"}
r = requests.get(f"{EVDS}/{urlencode(p)}", headers={"key": KEY}, timeout=30)
df = pd.DataFrame(r.json()["items"])
df["Tarih"] = pd.to_datetime(df["Tarih"], format="%d-%m-%Y")
col = "TP_DK_USD_A_YTL"
df[col] = pd.to_numeric(df[col], errors="coerce")
s = df.dropna(subset=[col]).set_index("Tarih")[col].sort_index()
# Grafik scriptleriyle AYNI taban: gunluk interpolasyon + hafta ici gunler.
# Ham gozlem uzerinden n-adim geri gitmek resmi tatillerde pencereyi kaydirir
# (or. 15 Temmuz) ve sayfa metnini grafiklerle celiskiye dusurur.
biz = s.asfreq("D").interpolate(method="time")
biz = biz[biz.index.dayofweek < 5]
def deval(n):
    p0, p1 = biz.iloc[-1 - n], biz.iloc[-1]
    d = (biz.index[-1] - biz.index[-1 - n]).days
    return round(((p1 / p0) ** (365 / d) - 1) * 100, 1)
ozet = {"_tarih": s.index[-1].strftime("%d.%m.%Y"), "kur": round(float(s.iloc[-1]), 2),
        "d1h": deval(5), "d1a": deval(21), "d3a": deval(63)}
json.dump(ozet, open(os.path.join(BASE, "ozet.json"), "w"), ensure_ascii=False, indent=1)
print(json.dumps(ozet, ensure_ascii=False))
