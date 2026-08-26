#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""TÜFEX ve başabaş enflasyon — hesap katmanı.

Carry hattıyla aynı ilke: kendi veri kaynağına gitmez. Başabaş, reel getiri ve
risk primi serileri DIBS hattının, aylık TÜFE ise Enflasyon hattının depoya
yazdığı CSV'lerden okunur. Sayfadaki başabaş, DİBS sayfasındaki başabaşla aynı
seridir; olamayacağı bir mimari kurulmamıştır.

Üç katman:

  başabaş vs anket   Piyasanın fiyatladığı enflasyon (başabaş) ile anketin
                     AYNI UFKA eşlenmiş ortalaması. Fark = risk primi + likidite
                     primi; DIBS hattı bunu prim_* kolonlarında zaten üretir.
  reel getiri        TÜFEX reel eğrisinin tarihçesi.
  mevsimsellik       Aylık TÜFE'nin takvim deseni: ham eksi mevsimsellikten
                     arındırılmış fark, ay bazında ortalanır. Kısa vadeli
                     başabaş okumasının neden ayına göre düzeltilmesi
                     gerektiğinin ölçüsü.
"""
from __future__ import annotations

import json
from pathlib import Path

import pandas as pd

BURASI = Path(__file__).resolve().parent
KOK = BURASI.parent.parent
DIBS = KOK / "Aktarılacak Projeler" / "DIBS" / "data"
ENF = KOK / "Aktarılacak Projeler" / "Enflasyon" / "data"

VADELER = ("1y", "2y", "3y", "5y", "7y")
# Mevsimsel desen penceresi: son 10 yıl. Daha uzunu rejim değişimlerini
# (2003 bazlı seri, farklı sepetler) desene karıştırır.
MEVSIM_YIL = 10


def yukle() -> pd.DataFrame:
    m = pd.read_csv(DIBS / "metrik.csv", parse_dates=["tarih"]).set_index("tarih")
    kolonlar = ([f"be_{v}" for v in VADELER] + [f"r{v}" for v in VADELER]
                + [f"prim_{v}" for v in VADELER]
                + [f"pka_ort_{v}" for v in VADELER if f"pka_ort_{v}" in m.columns]
                + ["pka_12a", "pka_24a", "pka_5y", "n1y", "n2y"])
    return m[[c for c in kolonlar if c in m.columns]]


def mevsim_deseni() -> pd.DataFrame:
    """Ay bazında ortalama (ham − SA) aylık TÜFE farkı, son MEVSIM_YIL yıl.

    Pozitif fark o ayın mevsimsel olarak PAHALI olduğunu söyler (ham > SA):
    kısa TÜFEX carry'si o ayda görünürde yüksektir ama bu enflasyon haberi
    değil, takvimdir.
    """
    m = pd.read_csv(ENF / "metrik.csv", parse_dates=["tarih"])
    t = m[m["seri"] == "tufe"].set_index("tarih").sort_index()
    t = t[t.index >= t.index.max() - pd.DateOffset(years=MEVSIM_YIL)]
    t["fark"] = t["aylik_ham"] - t["aylik_sa"]
    d = t.groupby(t.index.month)["fark"].agg(["mean", "std", "count"])
    d.index.name = "ay"
    return d.round(3)


def hesapla():
    d = yukle()
    mevsim = mevsim_deseni()

    def son(kolon):
        s = d[kolon].dropna()
        return (None, "") if s.empty else (round(float(s.iloc[-1]), 2),
                                           f"{s.index[-1]:%d.%m.%Y}")

    ozet = {}
    for v in VADELER:
        for on, kolon in (("basabas", f"be_{v}"), ("reel", f"r{v}"),
                          ("prim", f"prim_{v}"), ("anket", f"pka_ort_{v}")):
            if kolon in d.columns:
                deger, tarih = son(kolon)
                if deger is not None:
                    ozet[f"{on}_{v}"] = deger
                    ozet[f"{on}_{v}_tarih"] = tarih
    ozet["_tarih"] = max((ozet[k] for k in ozet if k.endswith("_tarih")), default="")
    ozet["pka_12a"], _ = son("pka_12a")
    ozet["pka_24a"], _ = son("pka_24a")

    agu, eyl = mevsim.loc[8, "mean"], mevsim.loc[9, "mean"]
    ozet.update({
        "mevsim_yil": MEVSIM_YIL,
        "mevsim_agustos": round(float(agu), 2),
        "mevsim_ocak": round(float(mevsim.loc[1, "mean"]), 2),
        "mevsim_en_pahali_ay": int(mevsim["mean"].idxmax()),
        "mevsim_en_ucuz_ay": int(mevsim["mean"].idxmin()),
        "mevsim_aralik": round(float(mevsim["mean"].max() - mevsim["mean"].min()), 2),
    })
    return d, mevsim, ozet


if __name__ == "__main__":
    d, mevsim, ozet = hesapla()
    (BURASI / "ozet.json").write_text(
        json.dumps(ozet, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    print("veri tarihi:", ozet["_tarih"])
    print(f"{'vade':>5s} {'başabaş':>9s} {'anket':>7s} {'prim':>6s} {'reel':>6s}")
    for v in VADELER:
        print(f"{v:>5s} {str(ozet.get(f'basabas_{v}','—')):>9s} "
              f"{str(ozet.get(f'anket_{v}','—')):>7s} {str(ozet.get(f'prim_{v}','—')):>6s} "
              f"{str(ozet.get(f'reel_{v}','—')):>6s}")
    print("\nmevsimsel desen (ham − SA, son 10 yıl ort., puan):")
    print("  " + "  ".join(f"{ay}:{mevsim.loc[ay,'mean']:+.2f}" for ay in range(1, 13)))
