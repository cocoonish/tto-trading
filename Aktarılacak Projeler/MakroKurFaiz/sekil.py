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

import sekil_b01
import sekil_b02
import sekil_b03
import sekil_b04
import sekil_b05
import sekil_b06
import sekil_b07
import sekil_b08
import sekil_b09
import sekil_b10
import sekil_b10_surucu
import sekil_b11
import sekil_b13
from sekil_ortak import OLCUM, go

SEKILLER = {
    "01": sekil_b01.s01_abd_korelasyon,
    "02": sekil_b02.s02_plasebo,
    "03": sekil_b03.s03_taylor_bandi,
    "04": sekil_b03.s04_faiz_farki_eurusd,
    "05": sekil_b04.s05_tufe_surprizi,
    "06": sekil_b04.s06_tr2021_abd2022,
    "07": sekil_b05.s07_dm_mali_kadran,
    "08": sekil_b05.s08_beklenti_disi_fark,
    "09": sekil_b06.s09_borc_ayrisimi,
    "10": sekil_b06.s10_pb_yildiz_fan,
    "11": sekil_b06.s11_cevre_farklari,
    "12": sekil_b07.s12_redk,
    "13": sekil_b08.s13_uc_denge,
    "14": sekil_b08.s14_j_egrisi,
    "15": sekil_b08.s15_redk_cari,
    "16": sekil_b09.s16_kur_baskisi,
    "17": sekil_b10.s17_emtia_paralari,
    "18": sekil_b10_surucu.s_surucu_harita,
    "19": sekil_b10_surucu.s_surucu_kayan,
    "20": sekil_b10_surucu.s_usdjpy,
    "21": sekil_b11.s18_fama_beta,
    "22": sekil_b11.s19_em_tasima_vix,
    "23": sekil_b11.s20_try_artik_akim,
    "24": sekil_b13.s21_matris,
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
