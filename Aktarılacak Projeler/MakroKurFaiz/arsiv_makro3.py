#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""MAKRO DERSİ — üçüncü bulut geçişi: BLS yayım tarihi listeleri, yavaş tempoda.

İkinci geçişte Internet Archive üç denemenin üçünde 429 (istek sınırı) verdi;
429 kaynağın ne döndürdüğü hakkında bir şey söylemez, yalnız hızımızı söyler.
Bu geçiş önce anlık görüntü dizinini (CDX) sorar, sonra en yeni 200'lü
kopyayı ister; istekler arasında bekler ve 429'da artan aralıkla yeniden
dener. BLS'nin kendi sunucusu otomatik erişimi reddettiği için (erişim
politikası) oraya istek atılmaz.
"""
from __future__ import annotations

import json
import re
import sys
import time

import arsiv_makro as am

CDX = ("https://web.archive.org/cdx/search/cdx?url=bls.gov/bls/news-release/{ad}.htm"
       "&output=json&filter=statuscode:200&fl=timestamp,original&limit=-8")


def _al(u: str, sn: int = 90) -> tuple[int, bytes]:
    for bekle in (0, 30, 75, 150):
        if bekle:
            time.sleep(bekle)
        try:
            d, gv = am.al(u, sn=sn, deneme=1)
        except RuntimeError as e:
            if "429" in str(e):
                continue
            raise
        if d != 429:
            return d, gv
    return 429, b""


@am.kaynak("BLS (Internet Archive, CDX)")
def bls_cdx() -> dict:
    sonuc = {}
    for ad in ("empsit", "cpi"):
        time.sleep(10)
        d, gv = _al(CDX.format(ad=ad))
        sonuc[ad] = {"cdx_durum": d}
        if d != 200:
            continue
        try:
            satir = json.loads(gv)[1:]
        except ValueError:
            sonuc[ad]["cdx"] = "json değil"
            continue
        sonuc[ad]["kopya_sayisi"] = len(satir)
        for ts, orij in reversed(satir):
            time.sleep(10)
            u = f"https://web.archive.org/web/{ts}id_/{orij}"
            d2, g2 = _al(u)
            n = len(re.findall(rb"archives/" + ad.encode() + rb"_\d{8}", g2))
            sonuc[ad][ts] = {"durum": d2, "bayt": len(g2), "arsiv_baglanti": n}
            if d2 == 200 and n > 50:
                am.yaz(f"bls/{ad}_wayback_{ts}.htm.gz", g2, u, d2)
                break
    return sonuc


def main() -> int:
    am.HAM.mkdir(parents=True, exist_ok=True)
    bls_cdx()
    kp = am.HAM / "kunye_bulut.json"
    eski = json.loads(kp.read_text(encoding="utf-8")) if kp.exists() else {}
    eski.update(am.KUNYE)
    kp.write_text(json.dumps(dict(sorted(eski.items())), ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    rp = am.HAM / "rapor.json"
    rapor = json.loads(rp.read_text(encoding="utf-8")) if rp.exists() else {}
    rapor[am.SIMDI.strftime("%Y-%m-%dT%H%M") + "_ucuncu"] = am.RAPOR
    rp.write_text(json.dumps(rapor, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    print(json.dumps(am.RAPOR, ensure_ascii=False, indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())
