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

MEDAS_YENILE_GUN = 35   # Tarım-ÜFE aylık; ham dosya bundan eskiyse yeniden hasat denenir


def _eski(p, gun):
    import time
    return (not p.exists()) or (time.time() - p.stat().st_mtime) / 86400 > gun


def hasat_dene(mod, hedef):
    """MEDAS hasadı (Playwright). Ham dosya yoksa ZORUNLU; varsa ama eskiyse denenir,
    başarısız olursa (Playwright yok, TÜİK erişilemedi) eski dosyayla devam edilir —
    ama UYARI basılır. Eskiden yalnız dosya yoksa hasat yapılıyordu → Tarım-ÜFE ve
    madde fiyatları ilk hasat ayında donuyordu; tür kaması sessizce 1'e düşüyordu."""
    if not hedef.exists():
        calistir(mod)
        return
    if _eski(hedef, MEDAS_YENILE_GUN):
        print(f"\n===== {mod} (ham dosya {MEDAS_YENILE_GUN} günden eski, yeniden hasat deneniyor) =====")
        r = subprocess.run([sys.executable, str(SRC / mod)], cwd=str(SRC))
        if r.returncode != 0:
            print(f"UYARI: {mod} başarısız ({r.returncode}); ESKİ ham dosyayla devam: {hedef.name}")


if __name__ == "__main__":
    hasat_dene("medas_harvest.py", ROOT / "data/raw/medas_madde_fiyatlari.xls")
    hasat_dene("medas_tarim.py", ROOT / "data/raw/medas_tarim_ufe.xls")
    calistir("veri.py")
    calistir("analiz.py")
    calistir("grafikler.py")
    calistir("rapor.py")
    print("\nTamamlandı. Çıktılar: output/ (grafikler, seriler.xlsx, karşılaştırma, duyarlılık, değerlendirme notu)")
