# -*- coding: utf-8 -*-
"""KEŞİF — El Niño'nun küresel kanadı için veri kaynağı ÖLÇÜMÜ.

Bu betik hiçbir şey yazmaz; yalnız FRED'in hangi serileri GERÇEKTEN sunduğunu,
hangi tarihte başladığını ve son değerini ölçer. Seri kodu uydurulup hatta
girmesin diye kurulan keşif iş akışıyla koşar (bkz. .github/workflows/kesif.yml).

Neden FRED: FAO'nun gıda fiyat endeksi CSV'si her ay adı değişen bir dosyada
duruyor (kırılgan). FRED tek bir genel uçtan (anahtarsız CSV) hem IMF birincil
emtia fiyatlarını hem ABD TÜFE'sini hem politika faizini veriyor — tek host,
sabit kod. Emtia serileri 1980'de başlıyorsa Türkiye'de ölçülemeyen şey
(yeterli sayıda güçlü epizot) küresel tarafta ÖLÇÜLEBİLİR hale gelir.
"""
from __future__ import annotations

import io
import sys
import urllib.request

import pandas as pd

UC = "https://fred.stlouisfed.org/graph/fredgraph.csv?id={}"
UA = ("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/148.0.0.0 Safari/537.36")

ADAYLAR = [
    # ── IMF birincil emtia fiyat endeksleri (aylık, USD)
    ("PFOODINDEXM",     "IMF gıda fiyat endeksi"),
    ("PALLFNFINDEXM",   "IMF tüm emtia endeksi"),
    ("PNFUELINDEXM",    "IMF yakıt dışı emtia endeksi"),
    ("PNRGINDEXM",      "IMF enerji endeksi"),
    ("PRAWMINDEXM",     "IMF tarımsal hammadde endeksi"),
    ("PBEVEINDEXM",     "IMF içecek endeksi"),
    # ── ENSO'nun doğrudan vurduğu ürünler
    ("PWHEAMTUSDM",     "buğday"),
    ("PMAIZMTUSDM",     "mısır"),
    ("PRICENPQUSDM",    "pirinç"),
    ("PSOYBUSDM",       "soya fasulyesi"),
    ("PPOILUSDM",       "palm yağı"),
    ("PSUGAISAUSDM",    "şeker (ISA)"),
    ("PCOFFOTMUSDM",    "kahve (robusta/other mild)"),
    ("PCOCOUSDM",       "kakao"),
    ("PLAMBUSDM",       "kuzu"),
    ("PORANGUSDM",      "portakal"),
    ("PBANSOPUSDM",     "muz"),
    # ── ABD: enflasyon, gıda, politika faizi, tahvil
    ("CPIAUCSL",        "ABD TÜFE (mevsimsellikten arındırılmış)"),
    ("CPIAUCNS",        "ABD TÜFE (ham)"),
    ("CPIUFDSL",        "ABD TÜFE gıda"),
    ("CPIUFDNS",        "ABD TÜFE gıda (ham)"),
    ("CUSR0000SAF11",   "ABD TÜFE evde tüketilen gıda"),
    ("CPILFESL",        "ABD çekirdek TÜFE"),
    ("FEDFUNDS",        "Fed etkin politika faizi (aylık)"),
    ("DGS10",           "ABD 10 yıllık tahvil (günlük)"),
    ("DFII10",          "ABD 10 yıllık reel (TIPS, günlük)"),
    ("T10YIE",          "ABD 10 yıllık başabaş enflasyon"),
    ("DTWEXBGS",        "Geniş dolar endeksi"),
    # ── dünya geneli
    ("FPCPITOTLZGWLD",  "Dünya TÜFE enflasyonu (yıllık, Dünya Bankası)"),
]


def cek(kod: str) -> pd.Series | None:
    req = urllib.request.Request(UC.format(kod), headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=60) as r:
        ham = r.read().decode("utf-8", errors="replace")
    df = pd.read_csv(io.StringIO(ham))
    if df.shape[1] < 2:
        return None
    tar = pd.to_datetime(df.iloc[:, 0], errors="coerce")
    deg = pd.to_numeric(df.iloc[:, 1].replace(".", None), errors="coerce")
    s = pd.Series(deg.to_numpy(), index=pd.Index(tar)).dropna()
    return s if len(s) else None


def main() -> int:
    istenen = [a for a in sys.argv[1:] if a.strip()]
    liste = [(k, ad) for k, ad in ADAYLAR if not istenen or k in istenen]
    print(f"── FRED keşfi · {len(liste)} aday seri\n")
    print(f"{'KOD':<18}{'DURUM':<8}{'BAŞ':<10}{'SON':<10}{'N':>7}  {'SON DEĞER':>12}  AÇIKLAMA")
    print("-" * 118)
    olan, olmayan = [], []
    for kod, ad in liste:
        try:
            s = cek(kod)
        except Exception as ex:
            olmayan.append((kod, ad, str(ex)[:60]))
            print(f"{kod:<18}{'DÜŞTÜ':<8}{'-':<10}{'-':<10}{'-':>7}  {'-':>12}  {ad}  [{str(ex)[:40]}]")
            continue
        if s is None:
            olmayan.append((kod, ad, "boş"))
            print(f"{kod:<18}{'BOŞ':<8}{'-':<10}{'-':<10}{'-':>7}  {'-':>12}  {ad}")
            continue
        olan.append(kod)
        print(f"{kod:<18}{'VAR':<8}{s.index.min():%Y-%m}   {s.index.max():%Y-%m}   "
              f"{len(s):>5}  {s.iloc[-1]:>12,.2f}  {ad}")

    print("\n── ÖZET")
    print(f"   çalışan: {len(olan)}/{len(liste)}")
    if olmayan:
        print("   ÇALIŞMAYAN (hatta girmemeli):")
        for kod, ad, sebep in olmayan:
            print(f"     {kod:<18} {ad}  — {sebep}")
    print("\n   HATTA GİRECEK KODLAR: " + " ".join(olan))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
