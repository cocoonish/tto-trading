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
import re
import sys

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
EVDS_KEY_FILE = os.path.join(BASE_DIR, ".evds_key")


def _anahtar_adaylari(base_dir):
    """Anahtar dosyası adayları — sıra tüm hatlarda AYNI (bkz. README, guncelle.py).

    <proje>/.evds_key → depo kökü/.evds_key → kardeş TCMBNetRezerv/.evds_key.
    Kök adayı olmadan, temiz bir klonda köke tek dosya koyan kullanıcının bu hattı
    düşüyordu; hatların yarısı kökü okurken yarısı okumuyordu.
    """
    p = os.path.abspath(base_dir)
    kok = os.path.dirname(os.path.dirname(p))          # …/TTO Trading
    return [os.path.join(p, ".evds_key"),
            os.path.join(kok, ".evds_key"),
            os.path.join(kok, "Aktarılacak Projeler", "TCMBNetRezerv", ".evds_key")]


def _dosyadan_anahtar(adaylar, uyar=None):
    """İlk okunabilir ve boş olmayan adaydaki anahtar; hiçbiri yoksa ''."""
    for yol in adaylar:
        if not os.path.exists(yol):
            continue
        try:
            with open(yol, encoding="utf-8") as f:
                a = f.read().strip()
        except OSError as e:
            if uyar:
                uyar(f"UYARI: {yol} okunamadı ({type(e).__name__}).")
            continue
        if a:
            return a
    return ""


EVDS_KEY_ADAYLARI = _anahtar_adaylari(BASE_DIR)

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
    anahtar = _dosyadan_anahtar(EVDS_KEY_ADAYLARI,
                                lambda m: print(m, file=sys.stderr))
    if anahtar:
        return anahtar
    if zorunlu:
        raise RuntimeError(
            "EVDS anahtari bulunamadi. Su iki yoldan birini kullanin:\n"
            "  1) export TTO_EVDS_KEY=<anahtar>   (Windows: set TTO_EVDS_KEY=…)\n"
            "  2) su dosyalardan BIRINE anahtari yazin (.gitignore'da):\n"
            + "".join(f"       {y}\n" for y in EVDS_KEY_ADAYLARI)
        )
    return ""


def gizle_anahtar(metin: str, anahtar: str = "") -> str:
    """Hata/log metnindeki ham anahtari maskele (requests istisna metnine gomer)."""
    anahtar = anahtar or (os.environ.get("TTO_EVDS_KEY") or "").strip()
    if anahtar and len(anahtar) >= 4:
        return metin.replace(anahtar, f"{anahtar[:2]}***{anahtar[-2:]}")
    return metin


# --------------------------------------------------------------------------- USD/TRY
# KARAR (09.09.2026, kullanıcı): USD/TRY Yahoo Finance'ten. Kaynak, kapsam
# ölçümü ve kapanmamış bar kuralı ortak/usdtry.py'de TEK tanım; bu hat yalnız
# köprü kurar. Önbellek hattın kendi klasöründe (data/cache, izlenmez).
USDTRY_ONBELLEK = os.path.join(BASE_DIR, "data", "cache", "usdtry_yahoo.csv")


def _ortak_usdtry():
    """ortak/usdtry — PYTHONPATH'te (sitecustomize) yoksa depo kökünden."""
    try:
        import usdtry  # noqa: F401
        return usdtry
    except ImportError:
        kok = os.path.dirname(os.path.dirname(BASE_DIR))
        sys.path.insert(0, os.path.join(kok, "ortak"))
        import usdtry
        return usdtry


def usdtry_serisi(start, uyar=print):
    """USD/TRY günlük kapanış (Yahoo Finance), `start` (GG-AA-YYYY, YYYY-AA-GG
    ya da tarih) sonrası. Kapsam yetmezse ya da ağ düşerse eldeki önbellek
    döner ve sebep `uyar` ile basılır; önbellek de yoksa hata."""
    import pandas as pd
    if isinstance(start, str) and re.fullmatch(r"\d{2}-\d{2}-\d{4}", start):
        start = pd.to_datetime(start, format="%d-%m-%Y").date()
    k = _ortak_usdtry().seri(bas=start, onbellek=USDTRY_ONBELLEK)
    for u in k.uyarilar:
        uyar("UYARI: " + u)
    s = k.seri.rename("USDTRY=X")
    return s


def usdtry_kunye(start):
    """ozet.json'a düşecek kaynak künyesi (kaynak adı, ilk/son gün, gözlem)."""
    import pandas as pd
    if isinstance(start, str) and re.fullmatch(r"\d{2}-\d{2}-\d{4}", start):
        start = pd.to_datetime(start, format="%d-%m-%Y").date()
    m = _ortak_usdtry()
    return m.kunye(m.seri(bas=start, onbellek=USDTRY_ONBELLEK))
