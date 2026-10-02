#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""MAKRO DERSİ — bölüm parçalarını tek ders metninde birleştirir.

Ders ~24 bin kelimedir ve bölüm bölüm yazılır: her bölümün metni `metin/<ad>.mdx`,
sayılarının kaynağı `veri/sayilar/<ad>.json`dadır (`python3 dogrula.py --parca <ad>`
bir parçayı tek başına sınar). Bu betik ön bilgiyi, içe aktarmaları ve parçaları
sırayla yazar; ders metni ELLE düzenlenmez, parça düzenlenip betik yeniden koşulur.

  python3 birlestir.py            (yazar)
  python3 birlestir.py --denetle  (yazılı dosya parçalarla aynı mı; değilse 1)
"""
from __future__ import annotations

import sys
from pathlib import Path

BURASI = Path(__file__).resolve().parent
KOK = BURASI.parents[1]
MDX = KOK / "site/src/content/arastirma/makro-kur-ve-faiz.mdx"
PARCALAR = ["giris"] + [f"b{i:02d}" for i in range(1, 14)]

ON_BILGI = """---
title: 'Makrodan Kura ve Faize: Gelişmiş ve Gelişmekte Olan Ekonomilerde Bütçe, Büyüme, Enflasyon, Reel Kur ve Dış Denge'
description: "İki saatlik ders: bir makro haberin faize ve kura hangi terimden ulaştığı (politika patikası, vade primi, risk primi; kurun çıpası, reel faiz farkı ve risk primi), aynı haberin gelişmiş ekonomide parayı güçlendirip gelişmekte olan ekonomide neden zayıflatabildiği ve rejimin veriyle nasıl teşhis edildiği. Veri günü mekaniği ve plasebo kapısı; büyüme, istihdam ve politika sürprizi; enflasyonun iki ters işareti; bütçe açığının gelişmiş ekonomide faiz kanalı ve politika bileşimi, gelişmekte olan ekonomide risk primi, borç aritmetiği ve mali baskınlık; reel efektif kur ve dönüş hızı; dış ticaret ve cari denge; finansman, rezerv ve dış varlık pozisyonu; ticaret hadleri ve emtia; taşıma, UIP, akım ve küresel faktör; ülke primi; ve veri günü oyun kitabı. ABD, euro alanı, gelişmekte olan ülkeler ve Türkiye verisiyle ölçülmüş yirmi bir figür, dört bağlı hesap aracı ve çözümlü alıştırmalar."
pubDate: 2026-10-02
tags: ['makro', 'kur', 'butce', 'buyume', 'enflasyon', 'reel-kur', 'cari-denge', 'tasima', 'em', 'ders']
durum: 'aktif'
kaynak: 'ABD Hazinesi par getiri eğrisi ve NY Fed ACM vade primi · Bundesbank ve ECB getirileri · CNBC New York kapanışı G10 kurları · Yahoo Finance USD/TRY, EM kurları, DXY ve VIX · TCMB EVDS (DİBS gösterge eğrisi, TLREF, AOFM, politika faizi, PKA, ödemeler dengesi, UYP, kalan vadeye göre dış borç, rezerv, REDK, dış ticaret endeksleri) · TÜİK (TÜFE, GSYH ve yayım takvimi) · HMB bütçe ve borç istatistikleri · BIS reel efektif kur ve politika faizleri · Eurostat ve Dünya Bankası · Dünya Bankası Pink Sheet emtia fiyatları · kaynak listesindeki makaleler'
ozet: "Bir makro haber geldiğinde faizde ve kurda hangi terimin oynadığını bulmayı öğretir: aynı bütçe, büyüme ya da enflasyon haberi gelişmiş ekonomide parayı neden güçlendirir, gelişmekte olan ekonomide neden zayıflatabilir; reel kur, cari denge, rezerv, emtia ve taşıma bu resme nasıl girer ve rejim veriyle nasıl teşhis edilir."
seviye: 'ileri'
onkosul:
  - risk-ve-hedge
  - faiz-egrisi-ve-konvansiyonlar
---

import GrafikEmbed from '../../components/GrafikEmbed.astro';
import MakroTaylorHesaplayici from '../../components/MakroTaylorHesaplayici.astro';
import MakroBorcHesaplayici from '../../components/MakroBorcHesaplayici.astro';
import MakroRedkHesaplayici from '../../components/MakroRedkHesaplayici.astro';
import MakroKurBloklari from '../../components/MakroKurBloklari.astro';
"""


def kur() -> str:
    eksik = [p for p in PARCALAR if not (BURASI / "metin" / f"{p}.mdx").exists()]
    if eksik:
        raise SystemExit(f"eksik parça: {eksik}")
    govde = "\n\n".join((BURASI / "metin" / f"{p}.mdx").read_text(encoding="utf-8").strip() for p in PARCALAR)
    return ON_BILGI + "\n" + govde + "\n"


def main(argv: list[str]) -> int:
    metin = kur()
    if argv[:1] == ["--denetle"]:
        if not MDX.exists() or MDX.read_text(encoding="utf-8") != metin:
            print("✗ ders metni parçalarla aynı değil — python3 birlestir.py koşulmalı")
            return 1
        print("✓ ders metni parçalarla aynı")
        return 0
    MDX.write_text(metin, encoding="utf-8")
    print(f"── {MDX.relative_to(KOK)} yazıldı · {len(metin.split())} sözcük")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
