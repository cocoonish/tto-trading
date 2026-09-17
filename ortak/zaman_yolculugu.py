# -*- coding: utf-8 -*-
"""Kapıları İLERİ BİR GÜNDE koşturmak için duvar saatini kaydırır.

NEDEN VAR. Bu depodaki en sinsi kusur sınıfı "donmuş girdi, canlı ölçü":
bir sınama fikstürü sabit bir tarih taşır, ölçüsü ise duvar saatini okur, ve
ikisinin arası büyüdükçe madde BİR GÜN kendiliğinden düşer. Kaynağı okuyarak
bulunamaz — hepsi BUGÜN yeşil geçer. 17.09.2026'da yayın kapısının ilk
basamağı böyle düştü (dört koşu), ve aynı gün OVP hattında 16.10'da
patlayacak bir eşi ölçüldü.

SESSİZ DEĞİL, İNERT. Modül `TTO_SAHTE_GUN` yoksa hiçbir şey yapmaz;
`ortak/sitecustomize.py` her hat alt sürecinde zaten yükleniyor (guncelle.py
PYTHONPATH'e ortak/ koyar), yani yeni bir mekanizma YOK — üretim yolu
değişmiyor.

ÜÇ ŞEYİ BİRDEN KAYDIRMAK ZORUNDA ve üçü de ÖLÇÜLEREK öğrenildi:

1. SIRA: freezegun pandas'tan ÖNCE başlatılırsa yorumlayıcı SEGFAULT verir
   (`datetime.date size changed` — freezegun datetime'ı Python alt sınıfıyla
   değiştiriyor, pandas'ın C uzantısı onu kabul etmiyor). Pandas varsa önce
   o yüklenir, saat sonra dondurulur.

2. PANDAS'IN KENDİ SAATİ: `pd.Timestamp.today()` C tarafından okunur ve
   freezegun ona dokunmaz. Dört hat kapısı saatini oradan okuyor; yamalanmazsa
   o kapılar ölçülmemiş olur ve "temiz" görünür.

3. DOSYA SAATİ: `ortak/tazelik.taze` dosyanın mtime'ını `now()` ile kıyaslar.
   Saati ileri alıp mtime'ı bırakmak, ŞİMDİ yazılan bir fikstür dosyasını
   bayat gösterir ve önbellek maddesi olan her kapı SAHTE BOMBA verir
   (YPMevduat'ta ölçüldü). Kör nokta iki yönlü: o gürültünün arkasında
   gerçek bir bomba da saklanabilir.
"""
from __future__ import annotations

import datetime as _dt
import os

DEGISKEN = "TTO_SAHTE_GUN"


def etkin() -> str | None:
    return (os.environ.get(DEGISKEN) or "").strip() or None


def _mtime_kaydir(fark_sn: float) -> None:
    """`os.stat`ı sarmalayıp dosya saatlerini aynı farkla öteler."""
    _os_stat = os.stat

    fark_ns = int(fark_sn * 1_000_000_000)

    def _stat(*a, **k):
        s = _os_stat(*a, **k)
        # NANOSANİYE ALANLARI DA TAŞINIR: düşürülürlerse None olurlar ve
        # `shutil.copystat` divmod(None, int) ile patlar — yani araç, ölçmek
        # istediği kapıyı KENDİ eliyle düşürür ve her tarihte "bomba" der.
        ek = {"st_atime": s.st_atime + fark_sn, "st_mtime": s.st_mtime + fark_sn,
              "st_ctime": s.st_ctime + fark_sn,
              "st_atime_ns": s.st_atime_ns + fark_ns,
              "st_mtime_ns": s.st_mtime_ns + fark_ns,
              "st_ctime_ns": s.st_ctime_ns + fark_ns,
              "st_blksize": s.st_blksize, "st_blocks": s.st_blocks,
              "st_rdev": s.st_rdev}
        return os.stat_result(
            (s.st_mode, s.st_ino, s.st_dev, s.st_nlink, s.st_uid, s.st_gid,
             s.st_size, int(s.st_atime + fark_sn), int(s.st_mtime + fark_sn),
             int(s.st_ctime + fark_sn)), ek)

    os.stat = _stat


def baslat() -> bool:
    """Saati kaydırır. Kaydıramazsa SESSİZCE GEÇMEZ — çağıran bilsin diye
    False döner; ölçülmemiş bir koşu, ölçülüp temiz çıkmışla aynı görünür."""
    gun = etkin()
    if not gun:
        return False
    hedef = _dt.datetime.fromisoformat(f"{gun}T12:00:00")
    fark = (hedef - _dt.datetime.now()).total_seconds()

    try:                                    # (1) pandas ÖNCE — bkz. başlık
        import pandas as pd
    except Exception:                       # noqa: BLE001
        pd = None

    from freezegun import freeze_time
    freeze_time(hedef).start()

    if pd is not None:                      # (2) pandas'ın kendi saati
        _T = pd.Timestamp
        pd.Timestamp.today = classmethod(lambda cls, tz=None: _T(hedef))
        pd.Timestamp.now = classmethod(lambda cls, tz=None: _T(hedef))

    _mtime_kaydir(fark)                     # (3) dosya saati
    return True
