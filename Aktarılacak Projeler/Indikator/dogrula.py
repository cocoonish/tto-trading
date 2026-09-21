#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""TTO · Yapı ve Momentum — yayın kapısı (sayfa sınavı 26 bu dosyayı koşturur).

Üç kapıyı birden sorar ve biri düşerse yayın durur:
  · duman.kos()            — replikasyon, Pine paritesi, emir mekaniği (on bir madde)
  · pine_sabit.denetle()   — Pine'daki olasılık bloğu JSON'la aynı mı
  · sekil.mdx_sirasi_sina()— sayfadaki figürler üretilmiş ve sırada mı
Ağa çıkmaz, duvar saati okumaz; girdisi depodaki arşiv ve ölçüm dosyası."""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import duman        # noqa: E402
import pine_sabit   # noqa: E402
import sekil        # noqa: E402

if __name__ == "__main__":
    hata = duman.kos() + pine_sabit.denetle() + sekil.mdx_sirasi_sina()
    if hata:
        for h in hata:
            print(" ·", h)
        print(f"ENGEL · TTO Yapı ve Momentum doğrulaması: {len(hata)} kusur")
        sys.exit(1)
    print("TTO Yapı ve Momentum doğrulaması: duman on bir madde, olasılık bloğu ve figür sırası tamam")
