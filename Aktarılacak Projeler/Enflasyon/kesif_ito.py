# -*- coding: utf-8 -*-
"""İTO (İstanbul Ticaret Odası) endeksleri — EVDS keşif koşusu.

NEDEN: Hattımızdaki `ito_ist` (TP.FG.IST1.23) Ocak 2024'te başlıyor ve
İTO–TÜFE karşılaştırması 30 aylık bir örnekleme sıkışıyor. İki ihtimal var ve
ikisi de ölçülmeden bilinemez:
  (a) Seri gerçekten 2024'te başlıyor (yeni baz yılına geçiş).
  (b) Aynı grupta ESKİ bazlı, daha uzun bir kardeş seri duruyor ve biz onu
      hiç sormadık.

KURUCU SIRA (CLAUDE.md — dış kaynak önce YOKLANIR): önce grup katalogları
yoklanır (her aday birkaç saniye), sonra AÇIK çıkan grubun serileri tek tek
ÖLÇÜLÜR (ilk/son gözlem, n, seviye), sonra hat kurulur. Bu betik yalnız
ölçer ve yazdırır; hiçbir üretim dosyasına dokunmaz.

Koşum (EVDS anahtarı gerekir):  python3 kesif_ito.py
"""
from __future__ import annotations

import json
import sys

import pandas as pd

import veri

# ÇIKTI TAMPONLANMAZ. İlk koşu 20 dakikalık iş bütçesini doldurdu ve TEK SATIR
# öğrenmeden bitti: Python stdout'u tty olmayan yere yazarken tamponluyor,
# GitHub log'una hiçbir şey düşmedi ve koşu iptal edildiğinde tampon da gitti.
# Uzun süren bir keşifte ilerlemenin GÖRÜNMESİ, keşfin kendisi kadar önemli —
# yoksa "hangi adımda takıldı" sorusu ancak yeni bir koşuyla cevaplanır.
print = __import__("functools").partial(print, flush=True)   # noqa: A001

# EVDS grup kodu adlandırması tek biçimli değil (bie_tukfiy2025, bie_oktug2025).
# İTO tarafında hangisinin geçtiğini BİLMİYORUZ; hepsi yoklanır ve açık çıkan
# kullanılır. Tahmin edip tek koda bağlanmak, kapalı çıktığında "seri yok"
# sonucunu üretirdi — oysa soru "hangi kapı açık".
GRUP_ADAYLARI = [
    "bie_fgist", "bie_fgist1", "bie_ito", "bie_itofiyat",
    "bie_fgistanbul", "bie_gecinme", "bie_ucretliler",
]

# Grup kataloğu hiç açılmazsa ikinci yol: kod uzayını doğrudan yoklamak.
# TP.FG.IST1.23 elimizdeki; kardeşleri aynı önekte olmalı.
# KOD UZAYI DAR TUTULUR. İlk sürüm 90 kod yokluyordu ve her ıskalanan kod
# istemcinin yeniden deneme bütçesini harcadığı için 20 dakika yetmedi. Keşfin
# işi kod uzayını taramak değil, SORUYU cevaplamak: "elimizdeki serinin daha
# uzun bir kardeşi var mı". Katalog açılırsa kodlar zaten oradan gelir; kapalı
# kalırsa bu kısa liste yeter.
KOD_ADAYLARI = [
    "TP.FG.IST1.23",                       # elimizdeki seri — kıyas noktası
    "TP.FG.IST1.01", "TP.FG.IST1.02", "TP.FG.IST1.03",
    "TP.FG.IST1.22", "TP.FG.IST1.24",
    "TP.FG.IST.01", "TP.FG.IST.23",
    "TP.FG.IST2.23",
]


def _olc(kod: str) -> dict:
    """Bir serinin KAPSAMINI ölç. 'Veri geldi' ile 'veri tam geldi' aynı şey
    değil: dönen serinin ilk/son ayı ve gözlem sayısı yazılır."""
    try:
        s = veri.evds_aylik(kod, bas="01-01-2000", yenile=True).dropna()
    except Exception as ex:
        return {"kod": kod, "durum": f"HATA: {type(ex).__name__}: {ex}"[:160]}
    if s.empty:
        return {"kod": kod, "durum": "boş"}
    return {
        "kod": kod, "durum": "VAR", "n": int(len(s)),
        "ilk": s.index[0].strftime("%Y-%m"), "son": s.index[-1].strftime("%Y-%m"),
        "ilk_deger": round(float(s.iloc[0]), 3),
        "son_deger": round(float(s.iloc[-1]), 3),
    }


def main() -> int:
    print("İTO keşif — EVDS")
    # SORU: TP.FG.IST1.23 elimizde Ocak 2024'te başlıyor. Bu serinin GERÇEK
    # başlangıcı mı, yoksa daha uzun bir kardeşi mi var? Cevap ya katalogdan
    # ya kapsam ölçümünden gelir.
    print("\n▶ 1. GRUP KATALOGLARI YOKLANIYOR")
    acik: list[tuple[str, pd.DataFrame]] = []
    for g in GRUP_ADAYLARI:
        try:
            kat = veri.seri_listesi(g, yenile=True)
            if kat.empty:
                print(f"  {g:20s} boş")
                continue
            acik.append((g, kat))
            print(f"  {g:20s} AÇIK — {len(kat)} seri")
        except Exception as ex:
            print(f"  {g:20s} kapalı ({type(ex).__name__}: {str(ex)[:70]})")

    for g, kat in acik:
        print(f"\n▶ 2. {g} kataloğu")
        kol = [c for c in ("SERIE_CODE", "SERIE_NAME", "SERIE_NAME_ENG",
                           "START_DATE", "END_DATE", "FREQUENCY_STR", "SEVIYE",
                           "UST_SERIE_CODE") if c in kat.columns]
        with pd.option_context("display.width", 240, "display.max_colwidth", 70,
                               "display.max_rows", 200):
            print(kat[kol].to_string() if kol else kat.head(50).to_string())

    print("\n▶ 3. KOD UZAYI YOKLANIYOR (kapsam ölçümü)")
    # Katalog açılsa bile kodlar tek tek ölçülür: katalogdaki START_DATE
    # yayımcının iddiası, ölçüm bizim gözlemimiz. İkisi ayrışabilir.
    kodlar = list(KOD_ADAYLARI)
    for _, kat in acik:
        if "SERIE_CODE" in kat.columns:
            kodlar = list(dict.fromkeys(list(kat["SERIE_CODE"]) + kodlar))
    bulunan = []
    for kod in kodlar:
        r = _olc(kod)
        if r["durum"] == "VAR":
            bulunan.append(r)
            print(f"  {kod:22s} n={r['n']:4d}  {r['ilk']} → {r['son']}  "
                  f"{r['ilk_deger']} → {r['son_deger']}")
        else:
            print(f"  {kod:22s} {r['durum']}")

    print("\n▶ 4. ÖZET — en uzun kapsamlı adaylar")
    for r in sorted(bulunan, key=lambda x: -x["n"])[:12]:
        print(f"  {r['kod']:22s} n={r['n']:4d}  {r['ilk']} → {r['son']}")
    if not bulunan:
        print("  HİÇBİRİ — kod uzayı yanlış ya da EVDS bu koşucudan erişilemiyor.")
        return 1
    print("\nJSON:")
    print(json.dumps(bulunan, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
