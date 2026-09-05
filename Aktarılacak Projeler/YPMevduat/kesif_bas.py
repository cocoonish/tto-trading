#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Keşif: hpbitablo serilerinin GERÇEK başlangıcı nerede?

NEDEN. Hattın "yapısal sıfır" hükmünün bütün dayanağı, bir bacağın serinin
İLK gözleminden beri sıfır olmasıdır. Ama elimizdeki tarihçe 2024-01-05'te
başlıyor ve ilk keşif koşusu her adayı `startDate=01-01-2024` ile yoklamıştı —
yani 2024-01-05, YOKLAMANIN KENDİ ALT SINIRI olabilir, serinin başı değil.
Tablo 5'in yirmi iki serisinin HEPSİNİN o tarihe yapışması, kırpılmış bir
tarihçenin imzasıdır; tablo 2 ve 4'ün 2024-06-28'de başlaması ise pencerenin
İÇİNDE, yani ölçülmüş.

İkisi tıpatıp aynı görünür ve aralarındaki fark hükmü tersine çevirir: seri
gerçekten 2024'te başlıyorsa sıfır yapısaldır; 2019'da başlayıp bir dönem
sıfırdan farklı yayımlandıysa elimizdeki sıfır, yayımı DURMUŞ bir bacaktır —
yani hattın elemeye çalıştığı hâlin ta kendisi.

Bu koşu tek soru soruyor: çok daha erken bir başlangıç istendiğinde EVDS ne
döndürüyor? Depoya hiçbir şey yazmaz; çıktı logdadır.
"""
from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__)))
import pandas as pd  # noqa: E402
import veri  # noqa: E402  (hattın kendi istemcisi — ikinci bir istemci yazılmaz)

ERKEN = "01-01-2005"          # kaynağın verebileceğinden kesinlikle daha eski

# Tablo başına birkaç temsilci: hepsini sormak istemci bütçesini yakar ve
# soru zaten TABLO düzeyinde — bir tablonun serileri aynı yayımdan gelir.
ADAY = [
    ("hpbitablo5 · toplam",        "TP.HPBITABLO5.1"),
    ("hpbitablo5 · gerçek",        "TP.HPBITABLO5.2"),
    ("hpbitablo5 · gerçek·dolar",  "TP.HPBITABLO5.3"),
    ("hpbitablo5 · gerçek·maden",  "TP.HPBITABLO5.6"),
    ("hpbitablo5 · PE gerçek",     "TP.HPBITABLO5.13"),
    ("hpbitablo5 · PE gerçek·dolar",  "TP.HPBITABLO5.14"),
    ("hpbitablo5 · PE gerçek·euro",   "TP.HPBITABLO5.15"),
    ("hpbitablo5 · PE gerçek·diğer",  "TP.HPBITABLO5.16"),
    ("hpbitablo5 · PE gerçek·maden",  "TP.HPBITABLO5.17"),
    ("hpbitablo5 · PE tüzel·diğer",   "TP.HPBITABLO5.21"),
    ("hpbitablo2 · toplam YP",     "TP.HPBITABLO2.10"),
    ("hpbitablo4 · toplam",        "TP.HPBITABLO4.1"),
]


def main() -> int:
    print(f"ERKEN BAŞLANGIÇ SORUSU — startDate={ERKEN}\n" + "=" * 78)
    for ad, kod in ADAY:
        try:
            # Hattın KENDİ çekicisi kullanılır; ikinci bir istemci yazmak,
            # keşfin ölçtüğü şeyin üretimdekinden farklı olması demektir.
            df = veri._demet_cek([kod], pd.Timestamp(ERKEN), pd.Timestamp.today(),
                                 parca_gun=6300, bicim_ad="gun")
        except Exception as ex:                        # noqa: BLE001
            print(f"{ad:32} {kod:22} HATA {type(ex).__name__}: {ex}")
            continue
        if df is None or df.empty:
            print(f"{ad:32} {kod:22} BOŞ")
            continue
        s = df.iloc[:, 0].dropna()
        if not len(s):
            print(f"{ad:32} {kod:22} BOŞ (hepsi eksik)")
            continue
        nz = s[s != 0]
        print(f"{ad:32} {kod:22} n={len(s):5} "
              f"ilk={s.index.min().date()} son={s.index.max().date()} "
              f"sıfırdışı={len(nz):5} "
              f"ilk_sıfırdışı={nz.index.min().date() if len(nz) else '—'}")
    print("=" * 78)
    print("HÜKÜM: bir serinin ilk gözlemi 2024-01-05'te DEĞİL daha eskiyse,")
    print("elimizdeki tarihçe KIRPIK demektir ve yapısal sıfır hükmü kurulamaz.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
