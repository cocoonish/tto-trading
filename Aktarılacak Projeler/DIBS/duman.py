# -*- coding: utf-8 -*-
"""DİBS hattı duman sınaması — ağa çıkmaz, saniyeler sürer.

guncelle.py bu dosyayı hattın adımlarından ÖNCE koşturur; düşerse hat koşmaz.
Sınamada duran her madde bir gün gerçekten yanlış yayımlanmış (ya da yayını
durdurmuş) bir sayıdır.

08.09.2026 — SAYFANIN ADIYLA ÇAĞIRDIĞI ANAHTAR KOŞULLU ÜRETİLİYORDU. Dokuz yıl
düğümü o gün kurulamadı, `kiyas_*_9y_degisim_bp` çıpa gününün değerini
istediği için NaN çıktı ve `koy()` anahtarı ATLADI. Sayfa anahtarı adıyla
çağırıyor; yayın kapısı (sayfa sınavı 1) eksik anahtarı ENGEL saydı ve yayın
iş akışı arka arkaya üç kez düştü — günün bülteni saatlerce yayına çıkmadı.
Kural: sayfanın çağırdığı anahtar HER koşuda yazılır; ölçülebiliyorsa son dolu
günden ve kendi tarihiyle, ölçülemiyorsa boş ("—") — atlanmaz.
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

import numpy as np
import pandas as pd

BURASI = Path(__file__).resolve().parent
KOK = BURASI.parents[1]
sys.path.insert(0, str(BURASI))

SONUC: list[tuple[str, str]] = []


def sina(ad, fn):
    try:
        fn()
        SONUC.append(("✓", ad))
    except Exception as e:                                     # noqa: BLE001
        SONUC.append(("✗", f"{ad} — {type(e).__name__}: {e}"))


def _cerceve():
    gun = pd.bdate_range("2026-08-03", "2026-09-08")
    M = pd.DataFrame({"n2y": np.linspace(40.0, 38.0, len(gun)),
                      "n1y": np.linspace(41.0, 39.5, len(gun)),
                      "n9y": np.linspace(31.0, 30.5, len(gun))}, index=gun)
    return M


def _kiyas_son_dolu_gun():
    import ozet_uret as oz
    M = _cerceve()
    s_gun = pd.Timestamp("2026-09-08")
    g = pd.Timestamp("2026-08-10")
    # (1) çıpa dolu → değişim çıpaya kadar, bitiş çıpa günü
    r = oz.kiyas_degisim(M, s_gun, g, "n9y")
    assert r is not None
    bp, t1 = r
    assert t1 == s_gun, t1
    assert abs(bp - (M.loc[s_gun, "n9y"] - M.loc[g, "n9y"]) * 100) < 1e-9
    # (2) ÇIPA GÜNÜ BOŞ (08.09.2026 arızası) → son dolu gün alınır, bitiş o gün
    M2 = M.copy(); M2.loc[s_gun, "n9y"] = np.nan
    r = oz.kiyas_degisim(M2, s_gun, g, "n9y")
    assert r is not None, "çıpa günü boşken değişim ölçülemedi — anahtar düşer, yayın durur"
    bp2, t2 = r
    onceki = M2["n9y"].dropna().index[-1]
    assert t2 == onceki and t2 < s_gun, (t2, onceki)
    assert abs(bp2 - (M2.loc[onceki, "n9y"] - M2.loc[g, "n9y"]) * 100) < 1e-9
    # (3) son dolu gün TOLERANSIN DIŞINDA → None (bayat sayı basılmaz)
    M3 = M.copy(); M3.loc[M3.index > "2026-08-25", "n9y"] = np.nan
    assert oz.kiyas_degisim(M3, s_gun, g, "n9y") is None, \
        "on dört gün eski düğüm bugünün kıyası gibi yazılıyor"
    # (4) kıyas günü boş → None (başlangıç kaydırılmaz)
    M4 = M.copy(); M4.loc[g, "n9y"] = np.nan
    assert oz.kiyas_degisim(M4, s_gun, g, "n9y") is None
    # (5) tolerans sınırı kapsayıcı: tam ANLIK_TOLERANS_GUN gün eski düğüm kabul
    M5 = M.copy()
    sinir = s_gun - pd.Timedelta(days=oz.ANLIK_TOLERANS_GUN)
    M5.loc[M5.index > sinir, "n9y"] = np.nan
    r5 = oz.kiyas_degisim(M5, s_gun, g, "n9y")
    assert r5 is not None and (s_gun - r5[1]).days <= oz.ANLIK_TOLERANS_GUN


def _anahtar_atlanmaz():
    """Kıyas döngüsü ölçülemeyen değeri ATLAMAZ, boş yazar; bitişi damgalar.
    Kaynak metin sınanıyor: davranış koşturmadan, statik."""
    src = (BURASI / "ozet_uret.py").read_text(encoding="utf-8")
    i = src.index("# --- kıyas günleri")
    j = src.index("# --- ters eğri", i)
    blok = src[i:j]
    assert "kiyas_degisim(" in blok, "kıyas döngüsü ortak fonksiyonu kullanmıyor"
    assert 'O[f"{etiket}_{sonek}_degisim_bp"] = OLCULEMEDI' in blok, \
        "ölçülemeyen değişim boş yazılmıyor — anahtar düşer, yayın kapısı ENGEL üretir"
    assert 'O[f"{etiket}_{sonek}"] = OLCULEMEDI' in blok, "ölçülemeyen seviye boş yazılmıyor"
    assert '_degisim_bp_tarih"] = tr_tarih(t1)' in blok, \
        "değişimin bitiş günü damgalanmıyor — kaydırılmış uç çıpa günü gibi görünür"
    assert "float(M.loc[s_gun, kol])" not in blok, \
        "çıpa günü doğrudan okunuyor — boş düğümde NaN, anahtar düşer (08.09.2026)"
    import ozet_uret as oz
    assert oz.OLCULEMEDI == "—"


def _sayfa_anahtarlari():
    """Sayfaların bu hattan adıyla çağırdığı her anahtar, kıyas ailesindeyse
    döngünün ürettiği kalıba uymalı — sayfa yeni bir kıyas anahtarı çağırırsa
    burası onu adıyla söyler."""
    icerik = KOK / "site/src/content"
    if not icerik.exists():
        return
    kul: set[str] = set()
    for p in icerik.rglob("*.mdx"):
        kul |= set(re.findall(r'<Deger\s+proje="dibs-verim-egrisi"\s+anahtar="([^"]+)"',
                              p.read_text(encoding="utf-8")))
    kiyas = sorted(k for k in kul if k.startswith("kiyas_"))
    assert kiyas, "sayfa hiçbir kıyas anahtarı çağırmıyor — sınamanın hedefi değişmiş"
    kalip = re.compile(r"^kiyas_(1ay|3ay|1yil)(_(2y|1y|9y)(_degisim_bp)?)?$")
    uymayan = [k for k in kiyas if not kalip.match(k)]
    assert not uymayan, f"sayfa, döngünün üretmediği kıyas anahtarı çağırıyor: {uymayan}"


sina("kıyas değişimi: çıpa boşsa son dolu gün, kendi tarihiyle", _kiyas_son_dolu_gun)
sina("kıyas anahtarı atlanmaz, boş yazılır; bitiş damgalanır", _anahtar_atlanmaz)
sina("sayfanın çağırdığı kıyas anahtarları üretilen kalıpta", _sayfa_anahtarlari)

if __name__ == "__main__":
    for im, ad in SONUC:
        print(f"  {im} {ad}")
    dusen = [a for im, a in SONUC if im == "✗"]
    print(f"\n{len(SONUC) - len(dusen)}/{len(SONUC)} geçti")
    raise SystemExit(1 if dusen else 0)
