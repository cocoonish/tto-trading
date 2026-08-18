#!/usr/bin/env python3
"""Canli ozet — EVDS'ten USD/TRY cekip ACT/365 deval hesaplar (tek seri, hizli)."""
import json, os, re
from urllib.parse import urlencode
import pandas as pd, requests
BASE = os.path.dirname(os.path.abspath(__file__))
# Anahtar ve pencere ORTAK modulden; daha once anahtar baska bir scriptten
# regex'le okunuyordu (o dosya degisince sessizce kirilirdi) ve ileri-gun
# sabiti burada ayrica gomuluydu.
from evds_ortak import evds_anahtari, EVDS_ILERI_GUN, EVDS_BASE as EVDS
KEY = evds_anahtari()
bas = (pd.Timestamp.today() - pd.Timedelta(days=160)).strftime("%d-%m-%Y")
# Sorgu bitisi bilerek ileri: TCMB ertesi is gununun gosterge kurunu bugun yayimlar,
# endDate=bugun o kuru sistematik olarak disarida birakirdi. EVDS gelecek tarih icin
# bos doner. Grafik scriptleriyle AYNI pencere (EVDS_ILERI_GUN=5) — ozet.json ile
# grafikler ayni son gozleme dayansin.
son = (pd.Timestamp.today() + pd.Timedelta(days=EVDS_ILERI_GUN)).strftime("%d-%m-%Y")
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
# Grafik scriptlerinin yazdığı istatistik sidecar'ları (rejim eğimleri, haftalık ve
# aylık segment özetleri) sayfa metnine akar. Bunlar grafiklerle AYNI koşudan gelir;
# eksikse (script koşmadıysa) o anahtarlar düşer, sayfadaki statik yedek görünür.
for ad in ("istatistik_seg.json", "istatistik_hafta.json", "istatistik_ay.json"):
    yol = os.path.join(BASE, ad)
    if os.path.exists(yol):
        try:
            ozet.update(json.load(open(yol, encoding="utf-8")))
        except Exception as e:
            print(f"{ad} okunamadı: {e}")
json.dump(ozet, open(os.path.join(BASE, "ozet.json"), "w"), ensure_ascii=False, indent=1)
print(json.dumps(ozet, ensure_ascii=False))
