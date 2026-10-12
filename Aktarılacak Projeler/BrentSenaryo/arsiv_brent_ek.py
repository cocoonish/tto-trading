#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""BRENT 125–150 SENARYOSU — ikinci arşiv geçişi: CNBC DIŞINDAKİ kaynaklar.

Yahoo (hisse ve fon kapanışları), EIA (Brent/WTI spot günlük, ABD pompa
fiyatları), EVDS (TÜFE enerji ve akaryakıt kalemleri), ABD Hazinesi (2025–2026
nominal ve reel eğri), Dünya Bankası Pink Sheet, NY Fed petrol fiyatı
dinamikleri raporu ve jeopolitik risk endeksi. Yardımcılar ve ilkeler
`arsiv_brent.py` başlığında; künye ve rapor bu betiğe özgü dosyaya yazılır
(`veri/ham/kunye_ek.json`, `rapor_ek.json`), çünkü iki geçiş ayrı koşar.
"""
from __future__ import annotations

import sys

import arsiv_brent as ab


def main() -> int:
    ab.HAM.mkdir(parents=True, exist_ok=True)
    for f in (ab.yahoo, ab.evds, ab.eia, ab.hazine, ab.pink, ab.nyfed, ab.gpr):
        f()
    ab.kaydet("ek")
    return 0 if ab.KUNYE else 1


if __name__ == "__main__":
    sys.exit(main())
