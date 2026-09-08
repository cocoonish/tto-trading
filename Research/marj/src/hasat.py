# -*- coding: utf-8 -*-
"""MEDAS ham dosya hasadı — TEK tanım, tek başına koşabilir.

NEDEN AYRI BİR ADIM (07.09.2026). Hattın hafif kipi yalnız `web_cikti.py` ve
`ozet_uret.py` koşuyordu; ikisi de `output/seriler.xlsx`i YALNIZ OKUR. Xlsx'i
yazan `rapor.py` ve onu besleyen `analiz.py` yalnız `run_all.py`den, yani TAM
kipten çağrılıyordu — ve tam kip cron'la ateşlenemiyor (`veri.yml` --tam yalnız
elle, üstelik hat listesi zorunlu). Sonuç ölçüldü: xlsx 26.08 04:31'den beri hiç
yeniden yazılmadı, hattın ana saati 07.2026'da dondu ve sayfada aynı anda üç
figür 08.2026, on üçü 07.2026 gösteriyordu. Ağustos TÜFE'si 03.09'da
yayımlandı, tetik ateşlendi, hat koştu — ve tetiği tükettiği hâlde ana saati
ilerletemedi.

Derleme zinciri hafif kipe alınırken hasat kapısı da GÖRÜNÜR bir adım olmalı:
`rapor.py`yi tek başına eklemek yeni bir ölü bağımlılık kurardı, çünkü
`data/raw/medas_tarim_ufe.xls` yalnız buradan tazeleniyor ve o dosya donduğunda
tür kaması sessizce 1'e düşüyor (endeks.py). "Bir dosya okunuyorsa onu üreten
adım hattın adım listesinde GÖRÜNMELİDİR" (CLAUDE.md).

Ağ ya da Playwright yoksa DÜŞMEZ: eski ham dosyayla devam eder ve uyarı basar.
Hasat, hattın geri kalanının önkoşulu değil — yalnız bir bacağının tazeliği.
"""
import pathlib
import subprocess
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
SRC = ROOT / "src"

MEDAS_YENILE_GUN = 35   # Tarım-ÜFE aylık; ham dosya bundan eskiyse yeniden hasat denenir


def _eski(p, gun):
    import time
    return (not p.exists()) or (time.time() - p.stat().st_mtime) / 86400 > gun


def calistir(mod):
    print(f"\n===== {mod} =====")
    r = subprocess.run([sys.executable, str(SRC / mod)], cwd=str(SRC))
    if r.returncode != 0:
        raise SystemExit(f"{mod} hata ile bitti ({r.returncode})")


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


def kos():
    hasat_dene("medas_harvest.py", ROOT / "data/raw/medas_madde_fiyatlari.xls")
    hasat_dene("medas_tarim.py", ROOT / "data/raw/medas_tarim_ufe.xls")


if __name__ == "__main__":
    kos()
