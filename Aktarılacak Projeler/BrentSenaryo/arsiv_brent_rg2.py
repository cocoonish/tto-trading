#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""BRENT 125–150 SENARYOSU — yedinci arşiv geçişi: iki ÖTV kararının PDF'i, ADRESİYLE.

Altıncı geçiş (`arsiv_brent_rg.py`) 38 günün fihristini yokladı ve Resmî Gazete sunucusu o koşuda
BÜTÜN isteklere zaman aşımı verdi (12.10.2026 14:54–15:12; ilk istekten itibaren, yani hız sınırı
değil bağlantı). Karar adresleri ise beşinci geçişin indirdiği fihristlerde zaten duruyor ve
`windows-1254` ile çözülünce okunuyor:

  01.10.2026 fihristi → "20261001-3-3.pdf" · Bazı Mallara Uygulanan ÖTV Tutarlarının Yeniden
                         Belirlenmesi Hakkında Karar (Karar Sayısı: 11822)
  13.08.2026 fihristi → "20260813-0.pdf"   · aynı başlık (Karar Sayısı: 11606)

Adresler TAHMİN edilmedi, fihristten çözüldü; bu geçiş yalnız onları ister (iki istek, uzun zaman
aşımı, üç deneme). Künye `kunye_rg.json`, rapor `rapor_rg.json` (var olan kayıtlar korunur).
"""
from __future__ import annotations

import sys
import time

import arsiv_brent as ab

KARARLAR = [
    ("https://www.resmigazete.gov.tr/eskiler/2026/10/20261001-3-3.pdf", "11822 — 01.10.2026"),
    ("https://www.resmigazete.gov.tr/eskiler/2026/08/20260813-0.pdf", "11606 — 13.08.2026"),
]


@ab.kaynak("Resmî Gazete ÖTV kararları (fihristten çözülmüş adres)")
def kararlar() -> dict:
    sonuc = {}
    for url, ad in KARARLAR:
        for deneme in range(3):
            try:
                d, gv = ab.al(url, sn=90, deneme=1, baslik={"Accept": "application/pdf,*/*;q=0.8",
                                                           "Referer": "https://www.resmigazete.gov.tr/"})
            except RuntimeError as e:
                sonuc[url] = f"hata (deneme {deneme + 1}) {e}"[:200]
                print(f"   ! {ad}: {sonuc[url]}", flush=True)
                time.sleep(10 * (deneme + 1))
                continue
            if d == 200 and gv[:5] == b"%PDF-":
                yol = f"resmigazete/karar_{url.rsplit('/', 1)[-1].rsplit('.', 1)[0]}.pdf.gz"
                ab.yaz(yol, gv, url, d, not_=f"ÖTV kararı {ad}")
                sonuc[url] = {"durum": d, "bayt": len(gv), "dosya": yol}
            else:
                sonuc[url] = {"durum": d, "bayt": len(gv), "not": "PDF değil"}
            print(f"   {d} {len(gv):>8} {ad}", flush=True)
            break
    return sonuc


def main() -> int:
    ab.HAM.mkdir(parents=True, exist_ok=True)
    kararlar()
    ab.kaydet("rg")
    return 0 if ab.KUNYE else 1


if __name__ == "__main__":
    sys.exit(main())
