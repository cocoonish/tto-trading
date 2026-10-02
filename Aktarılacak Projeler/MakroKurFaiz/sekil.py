#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""MAKRODAN KURA VE FAİZE — figürlerin kaydı. Sayıların tamamı `veri/olcum.json`dan gelir.

Ders yayımlandığı günün metnidir; figürler de o günün ölçümünü dondurur ve
statik yola yazılır (`site/public/arastirma/makro-kur-ve-faiz/`). Her figür
kendi tarih aralığını kendi alt başlığında taşır ve çizildiği ölçüm dosyasının
sha256 özünü bir meta etiketinde (`tto-olcum-ozu`) taşır; ölçüm dosyası değişip
figür yeniden çizilmezse doğrulayıcı düşer. Figür kodu bölüm başına
`sekil_bNN.py`dedir; ortak yardımcılar `sekil_ortak.py`.

  python3 sekil.py [01 02 …]          (numara verilmezse hepsi)
  python3 site/tools/plotly_stil.py site/public/arastirma/makro-kur-ve-faiz/*.html
"""
from __future__ import annotations

import json
import sys

import sekil_b07
import sekil_b09
from sekil_ortak import OLCUM, go

SEKILLER = {
    "12": sekil_b07.s12_redk,
    "16": sekil_b09.s16_kur_baskisi,
}


def main(argv: list[str]) -> int:
    if go is None:
        print("plotly yok: figürler çizilemez (kapı yolu bundan etkilenmez)")
        return 1
    o = json.loads(OLCUM.read_text(encoding="utf-8"))
    for n in (argv or sorted(SEKILLER)):
        SEKILLER[n](o)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
