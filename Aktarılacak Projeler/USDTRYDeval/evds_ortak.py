#!/usr/bin/env python3
"""USDTRYDeval hattinin ORTAK EVDS ayarlari — anahtar, uc nokta, sorgu penceresi.

Neden ayri modul:
  Bu klasordeki dort grafik scripti + ozet_uret.py ayni EVDS serisini ayni
  pencereyle cekmek zorunda; aksi halde sayfa metnindeki sayi ile hemen
  altindaki grafigin son gozlemi ayrisir (daha once tam olarak bu oldu).
  Sabitler her dosyada ayri ayri tanimlandiginda birini guncelleyip digerini
  unutmak kacinilmaz — o yuzden TEK KAYNAK burasi.

Anahtar:
  Kaynak koda ASLA gomulmez. Sirasiyla su iki yerden okunur:
    1) TTO_EVDS_KEY ortam degiskeni  (CI'da depo secret'i)
    2) bu klasordeki .evds_key dosyasi  (yerel; .gitignore'da)
  Ikisi de yoksa acik bir hata verilir — sessizce anahtarsiz istek atilmaz.
"""

import os
import sys

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
EVDS_KEY_FILE = os.path.join(BASE_DIR, ".evds_key")

EVDS_BASE = "https://evds3.tcmb.gov.tr/igmevdsms-dis"

# Sorgu bitisi bilerek ileri alinir: TCMB ertesi is gununun gosterge kurunu
# bugun (~15:30 TSI) yayimlar; endDate=bugun o kuru sistematik olarak disarida
# birakirdi. EVDS gelecek tarihli endDate icin yalnizca YAYIMLANMIS satirlari
# doner (uydurma/null satir uretmez — olculerek dogrulandi).
EVDS_ILERI_GUN = 5


def evds_anahtari(zorunlu: bool = True) -> str:
    """EVDS anahtarini ortam degiskeninden ya da yerel .evds_key dosyasindan oku."""
    anahtar = (os.environ.get("TTO_EVDS_KEY") or "").strip()
    if anahtar:
        return anahtar
    if os.path.exists(EVDS_KEY_FILE):
        try:
            with open(EVDS_KEY_FILE, encoding="utf-8") as f:
                anahtar = f.read().strip()
        except OSError as e:
            print(f"UYARI: {EVDS_KEY_FILE} okunamadi ({type(e).__name__}).",
                  file=sys.stderr)
            anahtar = ""
        if anahtar:
            return anahtar
    if zorunlu:
        raise RuntimeError(
            "EVDS anahtari bulunamadi. Su iki yoldan birini kullanin:\n"
            "  1) export TTO_EVDS_KEY=<anahtar>\n"
            f"  2) {EVDS_KEY_FILE} dosyasina anahtari yazin (.gitignore'da)"
        )
    return ""


def gizle_anahtar(metin: str, anahtar: str = "") -> str:
    """Hata/log metnindeki ham anahtari maskele (requests istisna metnine gomer)."""
    anahtar = anahtar or (os.environ.get("TTO_EVDS_KEY") or "").strip()
    if anahtar and len(anahtar) >= 4:
        return metin.replace(anahtar, f"{anahtar[:2]}***{anahtar[-2:]}")
    return metin
