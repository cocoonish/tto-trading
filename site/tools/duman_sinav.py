#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Sayfa sınavının KENDİ duman sınaması — ağa çıkmaz, saniyeler sürer.

NEDEN VAR. 2026-09-02'de yayın iş akışı arka arkaya altı kez düştü ve site
on iki saat donmuş kaldı; günün bülteni yayına hiç çıkmadı. Depoda hiçbir
dosya değişmemişti — DİBS hattının verisi tazelendi, iki değer bir sayfadaki
UYDURMA aritmetik örneğinin sabitleriyle tesadüfen çakıştı ve 2. ölçüt bunu
ihlal saydı. Yani sınavın hükmü, sınadığı şeyden bağımsız olarak değişti.

Yanlış alarm veren bir denetim, kapatılan bir denetimdir; üstelik bu denetim
yayının önünde durduğu için yanlış alarmı SİTEYİ DURDURUYOR. Bu yüzden
ölçütün hassasiyeti artık sentetik örneklerle sınanıyor: aşağıdaki her madde
bir gün gerçekten yaşanmış ya da yaşanabilecek bir çarpışmadır.

Koşum:  python site/tools/duman_sinav.py    (0 = geçti, 1 = düştü)
"""
from __future__ import annotations

import importlib.util
import pathlib
import sys

_YOL = pathlib.Path(__file__).resolve().with_name("sayfa_sinavi.py")
_spec = importlib.util.spec_from_file_location("sayfa_sinavi", _YOL)
_mod = importlib.util.module_from_spec(_spec)
sys.modules["sayfa_sinavi"] = _mod
_spec.loader.exec_module(_mod)          # main() yalnız __main__ altında koşar

deger_disi = _mod.deger_disi
ciplak_sayilar = _mod.ciplak_sayilar
ORNEK_AC, ORNEK_KAPA = _mod.ORNEK_AC, _mod.ORNEK_KAPA
MUAF_KALIP = _mod.MUAF_KALIP

GECTI: list[str] = []
DUSTU: list[str] = []


def sina(ad: str, kosul: bool, ayrinti: str = "") -> None:
    (GECTI if kosul else DUSTU).append(ad if kosul else f"{ad} — {ayrinti}")
    print(f"  {'✓' if kosul else '✗'} {ad}" + (f"  ({ayrinti})" if ayrinti and not kosul else ""))


def tara(mdx: str, ozet: dict) -> tuple[list[str], list[str]]:
    return ciplak_sayilar(deger_disi(mdx), ozet, set(MUAF_KALIP.findall(mdx)))


# ---------------------------------------------------------------------------
print("\n▶ Gerçek ihlal yakalanıyor mu (ölçüt zayıflamadı mı)")

e, u = tara("Bugün eğrinin üç aylık noktası 36,79 seviyesinde.", {"spot_3a": 36.79})
sina("çıplak ondalıklı ölçü ENGEL üretiyor", e == ["spot_3a=36,79"], f"gelen {e}")

e, u = tara('Bugün <Deger proje="x" anahtar="spot_3a" ondalik={2}>36,79</Deger> seviyesinde.',
            {"spot_3a": 36.79})
sina("<Deger> içindeki değer yakalanmıyor", not e and not u, f"gelen {e}")

e, u = tara("Yuvarlanmış hâli de sayılır: 36,8.", {"spot_3a": 36.79})
sina("bir ondalığa yuvarlanmış yazım da yakalanıyor", e == ["spot_3a=36,8"], f"gelen {e}")

# ---------------------------------------------------------------------------
print("\n▶ Örnek bloğu (uydurma sayılar taranmaz)")

ORNEK = ("{/* sinav-ornek: uydurma aritmetik */}\n"
         "Fiyatı 51,00 TL olsun; yıllık kupon oranı %36,8'dir.\n"
         "{/* /sinav-ornek */}\n")
e, u = tara(ORNEK, {"spot_3a": 36.79})
sina("örnek bloğunun İÇİ taranmıyor", not e and not u, f"gelen {e}")

e, u = tara(ORNEK + "\nGerçek ölçü ise bugün 36,79.", {"spot_3a": 36.79})
sina("örnek bloğunun DIŞI hâlâ taranıyor (blok sayfayı körleştirmiyor)",
     e == ["spot_3a=36,79"], f"gelen {e}")

sina("kapanmayan blok dengesizlik olarak görünüyor",
     len(ORNEK_AC.findall("{/* sinav-ornek: x */} ...")) == 1
     and len(ORNEK_KAPA.findall("{/* sinav-ornek: x */} ...")) == 0)

# ---------------------------------------------------------------------------
print("\n▶ Tam sayı ile ondalıklı ölçü ayrımı")

# 2026-09-02'yi düşüren tam çarpışma: sayım 51, metinde fiyat varsayımı 51,00 TL
e, u = tara("Fiyatı 51,00 TL olsun.", {"kimlik_cok_kaynakli": 51})
sina("tam sayı, ondalıklı yazımla ARANMIYOR (12 saatlik durmanın sebebi)",
     not e and not u, f"gelen engel={e} uyari={u}")

e, u = tara("Pencere 250 iş günü.", {"kimlik_api_n": 250})
sina("tam sayı kendi yazımıyla bulunursa UYARI, ENGEL değil",
     not e and u == ["kimlik_api_n=250"], f"gelen engel={e} uyari={u}")

e, u = tara("Kimlik 51 kaynakta sınandı.", {"kimlik_cok_kaynakli": 51})
sina("iki haneli sayım taranmıyor (çok yaygın)", not e and not u, f"gelen {e} {u}")

# ---------------------------------------------------------------------------
print("\n▶ İşaret")

e, u = tara("Haziran 2023 (−22,1).", {"d3a": 22.1})
sina("metindeki eksili sayı, POZİTİF değerle eşleşmiyor", not e, f"gelen {e}")

e, u = tara("Haziran 2023 (-22,1).", {"d3a": 22.1})
sina("ASCII eksi de aynı korumayı alıyor", not e, f"gelen {e}")

e, u = tara("Taşıma bugün −22,1 seviyesinde.", {"d3a": -22.1})
sina("gerçekten negatif değer, eksili yazımla yakalanıyor",
     e == ["d3a=−22,1"], f"gelen {e}")

# ---------------------------------------------------------------------------
print("\n▶ Kod ve formül taranmaz")

e, u = tara("`spot_3a = 36,79` satırı bir kod parçasıdır.", {"spot_3a": 36.79})
sina("satır içi kod taranmıyor", not e, f"gelen {e}")

e, u = tara("$y = 36{,}79$ formülü.", {"spot_3a": 36.79})
sina("KaTeX taranmıyor", not e, f"gelen {e}")

# ---------------------------------------------------------------------------
print("\n▶ Şekil saat defteri")

import datetime as _dt
YARIN = _dt.date.today() + _dt.timedelta(days=1)
sekil_saat_bulgulari = _mod.sekil_saat_bulgulari
MDX2 = ('<GrafikEmbed src="/projeler/x/a.html" />\n'
        '<GrafikEmbed src="/projeler/x/b.html" />\n')

e, u, n = sekil_saat_bulgulari(
    "x", {"_sekil_tarih": {"a.html": "2026-08-30", "b.html": "2026-09-03"}}, MDX2, YARIN)
sina("eksiksiz defter temiz geçiyor", not e and not u, f"engel={e} uyari={u}")
sina("gömülü figür sayısı doğru", n == 2, f"gelen {n}")

e, u, n = sekil_saat_bulgulari("x", {"_sekil_tarih": {"a.html": "2026-08-30"}}, MDX2, YARIN)
sina("defterde girdisi olmayan figür UYARI, ENGEL değil",
     not e and len(u) == 1 and "b.html" in u[0], f"engel={e} uyari={u}")

ileri = (YARIN + _dt.timedelta(days=3)).isoformat()
e, u, n = sekil_saat_bulgulari(
    "x", {"_sekil_tarih": {"a.html": ileri, "b.html": "2026-09-03"}}, MDX2, YARIN)
sina("yarından ileri şekil saati ENGEL",
     len(e) == 1 and "YARINDAN İLERİ" in e[0], f"engel={e}")

e, u, n = sekil_saat_bulgulari(
    "x", {"_sekil_tarih": {"a.html": None, "b.html": "2026-09-03"}}, MDX2, YARIN)
sina("None = 'ucu ölçülmedi' — engel değil, uyarı da değil",
     not e and not u, f"engel={e} uyari={u}")

e, u, n = sekil_saat_bulgulari(
    "x", {"_sekil_tarih": {"a.html": "dün", "b.html": "2026-09-03"}}, MDX2, YARIN)
sina("çözülemeyen tarih ENGEL", len(e) == 1 and "çözülemeyen" in e[0], f"engel={e}")

# ---------------------------------------------------------------------------
print(f"\n{'═' * 70}")
print(f"  {len(GECTI)} geçti · {len(DUSTU)} düştü")
if DUSTU:
    for d in DUSTU:
        print(f"  ✗ {d}")
    sys.exit(1)
print("  Sayfa sınavının duman sınaması temiz.")
