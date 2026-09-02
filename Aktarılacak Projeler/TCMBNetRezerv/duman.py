#!/usr/bin/env python3
"""TCMBNetRezerv duman sınaması — ağa çıkmaz, saniyeler sürer.

Hattın ölçüm katmanındaki sözleşmeleri sentetik veriyle sorar. Amaç bir
kusurun BİR KEZ düzeltilip ikinci kez geri gelmesini engellemek: burada
sınanan her madde, bir gün gerçekten yanlış yayımlanmış bir sayıdır.

Koşum:  python duman.py     (çıkış kodu 0 = geçti, 1 = düştü)
"""
from __future__ import annotations

import sys
import numpy as np
import pandas as pd

import altin_etkisi as ae

GECTI: list[str] = []
DUSTU: list[str] = []


def sina(ad: str, kosul: bool, ayrinti: str = "") -> None:
    (GECTI if kosul else DUSTU).append(ad if kosul else f"{ad} — {ayrinti}")
    print(f"  {'✓' if kosul else '✗'} {ad}" + (f"  ({ayrinti})" if ayrinti and not kosul else ""))


def _gunler(n: int) -> pd.DatetimeIndex:
    return pd.bdate_range("2026-01-05", periods=n)


# ---------------------------------------------------------------------------
# 1–5. Taşınan fiyat: ortadaki taşıma tatildir, sondaki taşıma kesintidir
# ---------------------------------------------------------------------------
# 27.08.2026'da ölçüldü: fiyat serisi 918 iş gününün 14'ünde taşınmıştı ve
# fiyat etkisinin SIFIR çıktığı günlerin tamamı (14/14) bu taşımalardan
# doğuyordu — gerçek bir kotasyonla ölçülmüş tek bir sıfır yoktu. Sayfa o
# sıfırı "günün fiyat etkisi 0,00 milyar dolar" diye yayımlıyordu.
print("\n▶ Ölçülemeyen fiyat günleri")

for ad, kaynaklar, beklenen in [
    ("ortadaki tek taşıma (tatil) korunur",
     ["agort03", "ffill", "agort03", "agort03"], [False, False, False, False]),
    ("uçtaki tek taşıma maskelenir",
     ["agort03", "agort03", "agort03", "ffill"], [False, False, True, True]),
    ("uçtaki iki taşıma maskelenir",
     ["agort03", "agort03", "ffill", "ffill"], [False, True, True, True]),
    ("taşıma yoksa hiçbir gün maskelenmez",
     ["agort03", "kap03", "agort03", "agort03"], [False, False, False, False]),
    ("hiç gerçek kotasyon yoksa hepsi maskelenir",
     ["ffill", "ffill", "ffill"], [True, True, True]),
]:
    k = pd.Series(kaynaklar, index=_gunler(len(kaynaklar)))
    m = ae.olculemeyen_fiyat_gunleri(k)
    sina(ad, list(m) == beklenen, f"beklenen {beklenen}, gelen {list(m)}")

# ---------------------------------------------------------------------------
# 6–8. Ayrıştırmanın kendisi
# ---------------------------------------------------------------------------
print("\n▶ Laspeyres ayrıştırması")

i = _gunler(4)
q = pd.Series([25.0, 25.0, 26.0, 26.0], index=i)
p = pd.Series([4000.0, 4100.0, 4100.0, 4100.0], index=i)
k = pd.Series(["agort03", "agort03", "agort03", "ffill"], index=i)

ham = ae.altin_fiyat_etkisi(q, p, None)   # maskesiz kıyas
v = q * p / 1000.0
kimlik = (ham["altin_fiyat_etkisi"] + ham["altin_miktar_etkisi"]
          - (v.shift(-1) - v)).abs().max()
sina("Γ + Λ = ΔV kimliği tutuyor", kimlik < 1e-9, f"artık {kimlik:.2e}")

maskeli = ae.altin_fiyat_etkisi(q, p, k)
sina("uçtaki taşımada fiyat etkisi BOŞ, sıfır değil",
     bool(maskeli["altin_fiyat_etkisi"].iloc[2:].isna().all()
          and float(ham["altin_fiyat_etkisi"].iloc[2]) == 0.0),
     "maskesiz hâlinde 0,00 yazılıyordu")
sina("maskesiz günler maskeden etkilenmiyor",
     bool((maskeli["altin_fiyat_etkisi"].iloc[:2]
           - ham["altin_fiyat_etkisi"].iloc[:2]).abs().max() < 1e-12))

# ΔQ = 0 iken Λ fiyattan bağımsızdır: ölçülebilen sıfır boşaltılmaz.
q2 = pd.Series([25.0, 25.0, 25.0, 25.0], index=i)
m2 = ae.altin_fiyat_etkisi(q2, p, k)
lam2 = m2["altin_miktar_etkisi"].iloc[:-1]     # son satır her zaman boş (L+1 yok)
sina("miktar kımıldamadıysa Λ sıfır kalır (boşalmaz)",
     bool(lam2.notna().all() and (lam2.abs() < 1e-12).all()),
     f"gelen {list(lam2)}")

# ---------------------------------------------------------------------------
# 9. Akım: ölçülemeyen Γ, net alımı da ölçülemez yapar
# ---------------------------------------------------------------------------
print("\n▶ Net döviz alımı")

sev = pd.Series([60.0, 61.0, 61.5, 62.0], index=i)
kamu = pd.Series([6.0, 6.0, 6.0, 6.0], index=i)
ak = ae.net_doviz_alimi(sev, kamu, maskeli["altin_fiyat_etkisi"],
                        maskeli["altin_miktar_etkisi"])
sina("fiyat etkisi boşsa net alım da boş",
     bool(ak["net_doviz_alimi"].iloc[2:].isna().all()
          and ak["net_doviz_alimi"].iloc[:2].notna().all()))

# ---------------------------------------------------------------------------
# 10. Uyarı metni: gerçekten olan şeyi anlatıyor mu?
# ---------------------------------------------------------------------------
print("\n▶ Uyarı metni")

u = ae.fiyat_tasima_tanisi(k)
sina("uçtaki taşıma görünür uyarı üretiyor", bool(u))
sina("uyarı 'boş bırakıldı' diyor, 'bu taşımaya dayanıyor' demiyor",
     bool(u) and "boş bırakıldı" in u[-1] and "dayanıyor" not in u[-1],
     u[-1] if u else "uyarı yok")

# ---------------------------------------------------------------------------
print(f"\n{'═' * 70}")
print(f"  {len(GECTI)} geçti · {len(DUSTU)} düştü")
if DUSTU:
    for d in DUSTU:
        print(f"  ✗ {d}")
    sys.exit(1)
print("  Duman sınaması temiz.")
