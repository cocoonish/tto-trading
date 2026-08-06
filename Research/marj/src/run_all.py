# -*- coding: utf-8 -*-
"""
TCMB EN 24/17 replikasyonu — uçtan uca koşu.

Sıra:
  1. (Gerekliyse) MEDAS hasatları: python3 src/medas_harvest.py  ve  python3 src/medas_tarim.py
     (data/raw/medas_*.xls mevcutsa atlanır — ham dosyalar repo ile taşınabilir.)
  2. EVDS serilerini indir/önbellekten oku (veri.py).
  3. Endeksleri kur (endeks.py) ve doğrulama tablolarını üret (analiz.py).
  4. Grafik 1-14 (grafikler.py).
  5. Excel (rapor.py).

Not: EVDS anahtarı veri.py içindedir; cache data/cache altında.
"""
import pathlib, subprocess, sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
SRC = ROOT / "src"

def calistir(mod):
    print(f"\n===== {mod} =====")
    r = subprocess.run([sys.executable, str(SRC / mod)], cwd=str(SRC))
    if r.returncode != 0:
        raise SystemExit(f"{mod} hata ile bitti ({r.returncode})")

if __name__ == "__main__":
    if not (ROOT / "data/raw/medas_madde_fiyatlari.xls").exists():
        calistir("medas_harvest.py")
    if not (ROOT / "data/raw/medas_tarim_ufe.xls").exists():
        calistir("medas_tarim.py")
    calistir("veri.py")
    calistir("analiz.py")
    calistir("grafikler.py")
    calistir("rapor.py")
    print("\nTamamlandı. Çıktılar: output/ (grafikler, seriler.xlsx, karşılaştırma, duyarlılık, değerlendirme notu)")
