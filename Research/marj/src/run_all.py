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

Not: EVDS anahtarı TTO_EVDS_KEY / .evds_key'den okunur; cache data/cache altında (24 saat TTL).
"""
import pathlib, subprocess, sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
SRC = ROOT / "src"

def calistir(mod):
    print(f"\n===== {mod} =====")
    r = subprocess.run([sys.executable, str(SRC / mod)], cwd=str(SRC))
    if r.returncode != 0:
        raise SystemExit(f"{mod} hata ile bitti ({r.returncode})")

# HASAT KAPISI hasat.py'ye TAŞINDI (kopyalanmadı): derleme zinciri artık hafif
# kipte de koşuyor ve hasat kapısının o kipte de görünmesi gerekiyor. İki yerde
# iki tanım bir gün sessizce ayrışırdı.
from hasat import MEDAS_YENILE_GUN, hasat_dene  # noqa: F401,E402


if __name__ == "__main__":
    hasat_dene("medas_harvest.py", ROOT / "data/raw/medas_madde_fiyatlari.xls")
    hasat_dene("medas_tarim.py", ROOT / "data/raw/medas_tarim_ufe.xls")
    calistir("veri.py")
    calistir("analiz.py")
    calistir("grafikler.py")
    calistir("rapor.py")
    print("\nTamamlandı. Çıktılar: output/ (grafikler, seriler.xlsx, karşılaştırma, duyarlılık, değerlendirme notu)")
