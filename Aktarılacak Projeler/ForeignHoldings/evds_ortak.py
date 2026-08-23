#!/usr/bin/env python3
"""ForeignHoldings hattının ORTAK EVDS ayarları — anahtar, uç nokta, seri kodları.

Neden ayrı modül:
  main.py (grafikleri üretir) ve ozet_uret.py (sayfa metnindeki canlı sayıları
  üretir) AYNI seriyi AYNI pencereyle çekmek zorunda; aksi hâlde sayfa
  metnindeki "son hafta" ile hemen altındaki grafiğin son gözlemi ayrışır.
  Sabitler iki dosyada ayrı tanımlanınca birini güncelleyip diğerini unutmak
  kaçınılmaz — o yüzden TEK KAYNAK burasıdır. (Aynı gerekçeyle kurulan kardeş
  modül: USDTRYDeval/evds_ortak.py)

Anahtar:
  Kaynak koda ASLA gömülmez. Sırasıyla şu iki yerden okunur:
    1) TTO_EVDS_KEY ortam değişkeni  (CI'da depo secret'ı)
    2) bu klasördeki .evds_key dosyası  (yerel; .gitignore'da)
  İkisi de yoksa açık bir hata verilir — sessizce anahtarsız istek atılmaz.

Uç nokta:
  Depodaki diğer EVDS hatlarıyla aynı: evds3 "igmevdsms-dis" REST servisi,
  anahtar `key` başlığında. (Eski `evds` PyPI paketi evds2'ye gider ve CI
  imajında kurulu değildir; bu yüzden doğrudan requests kullanılır.)
"""

import os
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

# TCMB Haftalık Menkul Kıymet İstatistikleri, veri grubu bie_mknethar.
# Her iki seri de "2. NET DEĞİŞİM" başlığı altındadır; yani STOK değil,
# fiyat ve kur etkisinden arındırılmış HAFTALIK NET İŞLEM (akım) verisidir.
#   TP.MKNETHAR.M7 → "2.1.1. Hisse Senedi"        (yurt içi piyasa, net değişim)
#   TP.MKNETHAR.M8 → "2.1.2. DİBS (Kesin Alım)"   (yurt içi piyasa, net değişim)
# Frekans: HAFTALIK(CUMA). Birim: milyon USD. Gerçek veri 11-09-2020'de başlar
# (EVDS daha eski tarihler için grubun diğer serileri yüzünden boş satır döner —
# bu satırlar sıfır DEĞİL, "veri yok"tur; fetcher onları atar).
EVDS_HISSE_SERIES = "TP.MKNETHAR.M7"
EVDS_DIBS_SERIES = "TP.MKNETHAR.M8"

# Serinin gerçek başlangıcı; daha erken bir tarih istemek yalnızca boş satır üretir.
EVDS_START = "01-09-2020"

# Sorgu bitişi bilerek ileri alınır: TCMB haftalık menkul kıymet istatistiklerini
# Cuma haftasını izleyen Perşembe yayımlar; endDate=bugün, yayımın düştüğü günde
# son haftayı sınırda dışarıda bırakabilir. EVDS gelecek tarihli endDate için
# yalnızca YAYIMLANMIŞ satırları döner (uydurma/boş satır üretmez).
EVDS_ILERI_GUN = 10


def evds_anahtari(zorunlu: bool = True) -> str:
    """EVDS anahtarını ortam değişkeninden ya da yerel .evds_key dosyasından oku."""
    anahtar = (os.environ.get("TTO_EVDS_KEY") or "").strip()
    if anahtar:
        return anahtar
    anahtar = _dosyadan_anahtar(EVDS_KEY_ADAYLARI,
                                lambda m: print(m, file=sys.stderr))
    if anahtar:
        return anahtar
    if zorunlu:
        raise RuntimeError(
            "EVDS anahtarı bulunamadı. Şu iki yoldan birini kullanın:\n"
            "  1) export TTO_EVDS_KEY=<anahtar>   (Windows: set TTO_EVDS_KEY=…)\n"
            "  2) şu dosyalardan BİRİNE anahtarı yazın (.gitignore'da):\n"
            + "".join(f"       {y}\n" for y in EVDS_KEY_ADAYLARI)
        )
    return ""


def gizle_anahtar(metin: str, anahtar: str = "") -> str:
    """Hata/log metnindeki ham anahtarı maskele (requests istisna metnine gömer)."""
    anahtar = anahtar or (os.environ.get("TTO_EVDS_KEY") or "").strip()
    if not anahtar and os.path.exists(EVDS_KEY_FILE):
        try:
            with open(EVDS_KEY_FILE, encoding="utf-8") as f:
                anahtar = f.read().strip()
        except OSError:
            anahtar = ""
    if anahtar and len(anahtar) >= 4:
        return metin.replace(anahtar, f"{anahtar[:2]}***{anahtar[-2:]}")
    return metin
