#!/usr/bin/env python3
"""Canli ozet — Yahoo Finance'ten USD/TRY cekip ACT/365 deval hesaplar (tek seri, hizli)."""
import json, os, re
import pandas as pd
BASE = os.path.dirname(os.path.abspath(__file__))
from evds_ortak import usdtry_serisi, usdtry_kunye
# KARAR (09.09.2026): USD/TRY Yahoo Finance'ten (ortak/usdtry.py — kapsam ölçümlü,
# kapanmamış bar düşürülür). Seri işlem gününü taşır; EVDS gösterge kurundaki
# valör (ertesi iş günü) kayması ve tatil öncesi yarından ileri `_tarih` yok.
bas = (pd.Timestamp.today() - pd.Timedelta(days=160)).date()
s = usdtry_serisi(bas)
kunye = usdtry_kunye(bas)
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
        # Kaynak künyesi okura: hangi kaynak, seri hangi güne kadar, kaç gözlem.
        "kur_kaynak": kunye["kur_kaynak"], "kur_son": kunye["kur_son"],
        "kur_gozlem": kunye["kur_gozlem"],
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
