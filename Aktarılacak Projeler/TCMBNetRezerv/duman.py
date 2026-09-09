#!/usr/bin/env python3
"""TCMBNetRezerv duman sınaması — ağa çıkmaz, saniyeler sürer.

Hattın ölçüm katmanındaki sözleşmeleri sentetik veriyle sorar. Amaç bir
kusurun BİR KEZ düzeltilip ikinci kez geri gelmesini engellemek: burada
sınanan her madde, bir gün gerçekten yanlış yayımlanmış bir sayıdır.

Koşum:  python duman.py     (çıkış kodu 0 = geçti, 1 = düştü)
"""
from __future__ import annotations

import pathlib
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
# 11–13. Ons çapasının yaş eşiği: SAĞLIKLI hafta uyarı üretmemeli
# ---------------------------------------------------------------------------
# Çapa CUMA tarihlidir ve izleyen hafta (~+6 gün, Perşembe) yayımlanır; yani
# hiçbir yayım atlanmamışken bile çapanın yaşı bir sonraki yayım gününe kadar
# 13'e çıkar. Eşik 8 iken bu uyarı HER hafta Pazar–Çarşamba ateşliyordu ve
# uyarilar.json üzerinden sayfaya basılıyordu (09.09.2026'da ölçüldü: son çapa
# 28.08, ref 08.09, "11 gün önce, eşik 8"). Kapanamayan bir uyarı, yazarı
# bütün uyarıları görmezden gelmeye alıştırır — bu yüzden sağlıklı haftanın
# uyarı ÜRETMEMESİ de eşiğin sınanan bir özelliğidir.
print("\n▶ Ons çapasının yaş eşiği")

_CUMA = pd.Timestamp("2026-08-28")          # çapanın tarihi (Cuma)
_capalar = pd.DataFrame({"ons": [25.0], "kaynak": ["irfcl_pdf"]},
                        index=pd.DatetimeIndex([_CUMA], name="tarih"))
_bos_seri = pd.Series(dtype=float)


def _tazelik_uyarisi(ref: pd.Timestamp) -> list[str]:
    """Yalnız yaş uyarısını süzer: öbür tanılar boş girdiyle zaten susar."""
    u = ae.altin_tanilari(_capalar, _bos_seri, _bos_seri, pd.DataFrame(),
                          bugun=ref)
    return [x for x in u if x.startswith("ALTIN MİKTAR TAZELİĞİ")]


_carsamba = _CUMA + pd.Timedelta(days=12)   # izleyen haftanın Çarşamba'sı
sina("sağlıklı hafta (Cuma çapası + 12 gün) uyarı ÜRETMEZ",
     not _tazelik_uyarisi(_carsamba),
     f"eşik {ae.ONS_TASIMA_UYARI_GUN}, gelen {_tazelik_uyarisi(_carsamba)}")
sina("bir yayım atlanınca (17 gün) uyarı GELİR",
     bool(_tazelik_uyarisi(_CUMA + pd.Timedelta(days=17))),
     f"eşik {ae.ONS_TASIMA_UYARI_GUN} — atlanan yayım görünmüyor")
# Eşiğin kendisi de sınanır: sağlıklı haftanın 13'ü ile atlanan yayımın 20'si
# arasında kalmalı. Aksi hâlde iki maddeden biri sessizce anlamını yitirir.
sina("eşik sağlıklı hafta ile atlanan yayım ARASINDA",
     13 < ae.ONS_TASIMA_UYARI_GUN < 20,
     f"eşik {ae.ONS_TASIMA_UYARI_GUN}")

# ---------------------------------------------------------------------------
# 14–16. Özetin ETİKET/SAAT ayrımı
# ---------------------------------------------------------------------------
# 09.09.2026'da ölçüldü: sekiz özet alanı `GG.AA` yazımını `_tarih` sonekiyle
# taşıyordu. O sonek sözleşmede SAAT demek; bültenin karanlık denetimi de
# sayfadaki canlı değer bileşeni de alanı saat sanıp çözemiyor ve SESSİZCE
# atlıyordu — sekiz alan bayatlık denetiminin tamamen dışındaydı.
print("\n▶ Özet: etiket ile saat ayrı anahtarlar")

import json as _json
import os as _os
import re as _re

_ozet_kaynak = pathlib.Path(__file__).with_name("ozet_uret.py").read_text(encoding="utf-8")
sina("kısa gün yazımı `_etiket` anahtarına yazılıyor",
     'f"u{i}_etiket"' in _ozet_kaynak and 'f"ak_g{i}_etiket"' in _ozet_kaynak,
     "etiket yeniden `_tarih` sonekine döndü")
sina("`_tarih` alanları TAM yazımla (%d.%m.%Y) kuruluyor",
     not _re.search(r'_tarih"\]\s*=\s*r\["Tarih"\]\.strftime\("%d\.%m"\)',
                    _ozet_kaynak),
     "bir saat alanı yıl taşımıyor")

_ozet_yol = pathlib.Path(__file__).with_name("ozet.json")
if _ozet_yol.exists():
    _o = _json.loads(_ozet_yol.read_text(encoding="utf-8"))
    _cozulemeyen = [k for k, v in _o.items()
                    if k.endswith("_tarih") and isinstance(v, str)
                    and v != "-" and not _re.fullmatch(r"\d{2}\.\d{2}\.\d{4}", v)
                    and not _re.fullmatch(r"\d{2}\.\d{4}", v)]
    sina("özetteki her `_tarih` biçim sözleşmesine uyuyor",
         not _cozulemeyen, f"çözülemeyen: {_cozulemeyen}")

# ---------------------------------------------------------------------------
# 17. Haftalık yayım alınamazsa okur bunu GÖRÜR
# ---------------------------------------------------------------------------
# 09.09.2026'da ölçüldü: haftalık gözlem çekimi düştüğünde tek iz ekrana basılan
# bir satırdı; `uyarilar` listesi kodda SONRA kuruluyordu, yani hata ne uyarı
# kaydına ne sayfaya giriyordu. Bu bacak hattın en hassas çapasıdır (swap ve
# altın miktarı) ve donduğunda günlük seri sessizce aylık çapaya düşer.
print("\n▶ Haftalık yayım alınamazsa")

_net_kaynak = pathlib.Path(__file__).with_name("net_rezerv.py").read_text(encoding="utf-8")
_ekleme = _net_kaynak.find("uyarilar.append(pdf_uyarisi)")
_kurulum = _net_kaynak.find("uyarilar = tazelik_denetimi(")
sina("düşen haftalık çekim uyarı listesine giriyor",
     _ekleme > 0 and _kurulum > 0 and _ekleme > _kurulum,
     "hata yalnız ekrana basılıyor; okur görmüyor "
     f"(ekleme {_ekleme}, liste kurulumu {_kurulum})")

# ---------------------------------------------------------------------------
print(f"\n{'═' * 70}")
print(f"  {len(GECTI)} geçti · {len(DUSTU)} düştü")
if DUSTU:
    for d in DUSTU:
        print(f"  ✗ {d}")
    sys.exit(1)
print("  Duman sınaması temiz.")
