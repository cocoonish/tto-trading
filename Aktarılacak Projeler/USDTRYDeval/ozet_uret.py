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
def deval(n, kaydir=0):
    """n iş günü geriye giden ACT/365 yıllıklandırılmış devalüasyon.

    `kaydir` pencereyi geriye alır: 0 = bugün biten pencere, 1 = dün biten…
    Ortalama hesabı bunun üzerine kurulur ve TEK bir tanım kullanır — iki ayrı
    formül bir gün sessizce ayrışır."""
    i = -1 - kaydir
    p0, p1 = biz.iloc[i - n], biz.iloc[i]
    d = (biz.index[i] - biz.index[i - n]).days
    return round(((p1 / p0) ** (365 / d) - 1) * 100, 1)


# SON HAFTA ORTALAMASI — TEK GÜNLÜK OKUMANIN YANINDA.
#
# Yıllıklandırma bir GÜNLÜK fiyat farkını 365'e ölçekler, yani kotasyondaki
# küçük bir kayma orana büyük yansır. Valör farkı, tatil ve TCMB'nin ertesi gün
# kurunu bir gün önce ilan etmesi hep aynı sonucu doğurur: hız bir günde
# sıçramış ya da çökmüş görünür, oysa patikada bir şey değişmemiştir.
# 08.09.2026 bülteninde tam bu oldu — bir aylık hız tek günde 4,5 puan
# (%19,6 → %24,1) "arttı".
#
# Ortalama o gürültüyü söndürür ve AYNI ÖLÇÜNÜN penceresidir: son beş iş
# gününde biten beş ayrı yıllıklandırılmış oranın ortalaması. Hattın zaten
# yazdığı `hafta_son_ort` BURAYA GİRMEZ — o 1 HAFTALIK (5 iş günü) oranın
# haftalık ortalamasıdır; bir aylık hızın yanına yazmak iki farklı pencereyi
# aynı cümlede kıyaslamak olurdu.
HAFTA_IS_GUNU = 5


def deval_ort(n, gun=HAFTA_IS_GUNU):
    """Son `gun` iş gününde biten `n` iş günlük pencerelerin ortalaması."""
    degerler = [deval(n, k) for k in range(gun)]
    return round(sum(degerler) / len(degerler), 1)


ozet = {"_tarih": s.index[-1].strftime("%d.%m.%Y"), "kur": round(float(s.iloc[-1]), 2),
        "d1h": deval(5), "d1a": deval(21), "d3a": deval(63),
        # Ortalamanın penceresi ADIYLA yazılır: okur kaç günün ortalamasına
        # baktığını sayfada görmeli, dipnottan çıkarmak zorunda kalmamalı.
        "d1h_ort": deval_ort(5), "d1a_ort": deval_ort(21), "d3a_ort": deval_ort(63),
        "ort_pencere_gun": HAFTA_IS_GUNU}
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
