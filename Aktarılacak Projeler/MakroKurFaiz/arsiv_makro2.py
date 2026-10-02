#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""MAKRO DERSİ — ikinci bulut geçişi: ilk geçişin bıraktığı boşluklar.

Neden ikinci geçiş (02.10.2026, ilk geçişin rapor.json'u): (1) EVDS'te seri
sayısı tavanı (900) Piyasa Katılımcıları Anketi'nin beş grubunda doldu —
uluslararası yatırım pozisyonu, kalan vadeye göre dış borç ve dış ticaret
endeksleri HİÇ indirilmedi. Bu geçiş seri kodlarını tahmin etmez: ilk geçişin
indirdiği `serieList` yanıtlarından okur ve yalnız gereken kodları ister.
(2) BLS arşiv sayfaları 403 verdi (bot süzgeci); yayım tarihi listeleri aynı
sayfaların Internet Archive kopyasından denenir — kopya yalnız TARİH listesi
için kullanılır, hiçbir sayı oradan okunmaz.

Ham yanıtlar `veri/ham/` altına aynı biçimde yazılır; künye ve rapor var
olanla birleşir.
"""
from __future__ import annotations

import gzip
import json
import re
import sys
import time

import arsiv_makro as am

SERILIST = am.HAM / "evds" / "serielist"
HEDEF_GRUP = {
    "bie_uypucay": None,          # bütün kalemler (net, varlık, yükümlülük ve alt kalemler)
    "bie_kalvadbg": None,         # kalan vadeye göre kısa vadeli dış borç, borçlu bazında
    "bie_kalanvade": None,        # kalan vadeye göre kısa vadeli dış borç, alacaklı/araç bazında
    "bie_dtihfb10": ["D01"], "bie_dtitfb10": ["D01", "D07"],
    "bie_dtihmb10": ["D01"], "bie_dtitmb10": ["D01", "D07"],
}


def _kodlar(grup: str, suzgec) -> list[str]:
    p = SERILIST / f"{grup}.json.gz"
    sl = json.loads(gzip.decompress(p.read_bytes()))
    kod = [s["SERIE_CODE"] for s in sl if s.get("SERIE_CODE")]
    if suzgec:
        kod = [k for k in kod if any(f".{x}." in k for x in suzgec)]
    return kod


@am.kaynak("EVDS hedefli")
def evds2() -> dict:
    bitis = am.SIMDI.strftime("%d-%m-%Y")
    sonuc = {}
    for grup, suz in HEDEF_GRUP.items():
        kodlar = _kodlar(grup, suz)
        sonuc[grup] = {"kod": len(kodlar), "demet": 0}
        for i in range(0, len(kodlar), 6):
            if am.kalan() < 240:
                break
            demet = kodlar[i:i + 6]
            yol = f"series={'-'.join(demet)}&startDate=01-01-1990&endDate={bitis}&type=json"
            try:
                d, gv = am._evds(yol, sn=60)
            except RuntimeError as e:
                sonuc[grup].setdefault("hata", []).append(f"{i}: {e}"[:160])
                continue
            am.yaz(f"evds/seri2/{grup}_{i // 6:03d}.json.gz", gv, f"{am.EVDS}/{yol}", d, not_=",".join(demet))
            sonuc[grup]["demet"] += 1
    return sonuc


WAYBACK = "https://web.archive.org/web/{ts}id_/{url}"


@am.kaynak("BLS (Internet Archive)")
def bls_arsiv() -> dict:
    sonuc = {}
    for ad in ("empsit", "cpi"):
        hedef = f"https://www.bls.gov/bls/news-release/{ad}.htm"
        sonuc[ad] = {}
        for ts in ("2026", "20260901", "2025"):
            u = WAYBACK.format(ts=ts, url=hedef)
            try:
                d, gv = am.al(u, sn=60, deneme=2)
            except RuntimeError as e:
                sonuc[ad][ts] = f"hata {e}"[:120]
                continue
            n = len(re.findall(rb"archives/" + ad.encode() + rb"_\d{8}", gv))
            sonuc[ad][ts] = {"durum": d, "bayt": len(gv), "arsiv_baglanti": n}
            if d == 200 and n > 50:
                am.yaz(f"bls/{ad}_wayback_{ts}.htm.gz", gv, u, d)
                break
    return sonuc


def main() -> int:
    am.HAM.mkdir(parents=True, exist_ok=True)
    for f in (evds2, bls_arsiv):
        f()
    kp = am.HAM / "kunye_bulut.json"
    eski = json.loads(kp.read_text(encoding="utf-8")) if kp.exists() else {}
    eski.update(am.KUNYE)
    kp.write_text(json.dumps(dict(sorted(eski.items())), ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    rp = am.HAM / "rapor.json"
    rapor = json.loads(rp.read_text(encoding="utf-8")) if rp.exists() else {}
    rapor[am.SIMDI.strftime("%Y-%m-%dT%H%M") + "_ikinci"] = am.RAPOR
    rp.write_text(json.dumps(rapor, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    print("\n══ ÖZET")
    for ad, r in am.RAPOR.items():
        print(f"  {ad:24s} {r.get('durum')}  {r.get('sure_sn', '')} sn  {json.dumps(r, ensure_ascii=False)[:400]}")
    print(f"  toplam {round(time.monotonic() - am.T0)} sn · {len(am.KUNYE)} ham dosya")
    return 0


if __name__ == "__main__":
    sys.exit(main())
