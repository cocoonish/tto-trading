#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""İki panelli indikatörün OHLC ARŞİVİ — tek yükleyici.

Arşiv `veri/<ad>-<aralik>.csv.gz` dosyalarında durur (t epoch sn UTC,
o,h,l,c,v); bulut iş akışı (`.github/workflows/indikator-veri.yml` →
`indir.py`) onu dala commit eder ve `veri/kunye.json` her serinin kaynağını,
koşu künyesini, bar sayısını, kapsamını ve sha256'sını taşır. Yayımlanan
her backtest sayısı bu dosyalardan yeniden üretilebilir; ağa çıkmaz.

Tek sözleşme: dönen Seri KAPANMIŞ barlardır (indirme anında kapanmamış
son bar düşürülmüştür) ve zaman damgası barın AÇILIŞ anıdır (Yahoo
sözleşmesi)."""
from __future__ import annotations

import gzip
import hashlib
import json
import sys
from pathlib import Path

KOK = Path(__file__).resolve().parent
VERI = KOK / "veri"
DEPO = KOK.parents[1]
sys.dont_write_bytecode = True   # public altına __pycache__ bırakma: yayın kapısı düşer
sys.path.insert(0, str(DEPO / "site" / "public" / "indikatorler"))
from brooks_referans import Seri  # noqa: E402

# Tick: kaynağın ilan ettiği fiyat adımı (TradingView `syminfo.mintick`
# karşılığı). Yahoo ilan etmez; burada enstrümanın piyasa konvansiyonu
# yazılıdır, brooks_referans.tick_tahmini yalnız yedektir.
TICK = {"eurusd": 0.00001, "gbpusd": 0.00001, "usdjpy": 0.001, "usdchf": 0.00001,
        "audusd": 0.00001, "usdcad": 0.00001, "nzdusd": 0.00001, "eurgbp": 0.00001,
        "eurchf": 0.00001, "dxy": 0.001, "xu100": 0.01, "spx": 0.01, "ndx": 0.01,
        "wti": 0.01, "xau": 0.1}
PIP = {"eurusd": 0.0001, "gbpusd": 0.0001, "usdjpy": 0.01, "usdchf": 0.0001,
       "audusd": 0.0001, "usdcad": 0.0001, "nzdusd": 0.0001, "eurgbp": 0.0001,
       "eurchf": 0.0001}


def kunye() -> dict:
    return json.loads((VERI / "kunye.json").read_text(encoding="utf-8"))


def seriler() -> list[str]:
    return sorted(p.name[:-7] for p in VERI.glob("*.csv.gz"))


def oku(ad: str) -> Seri:
    """`ad` = "<enstrüman>-<aralık>" (ör. eurusd-1h). sha256 künyeyle sınanır."""
    yol = VERI / f"{ad}.csv.gz"
    ham = gzip.decompress(yol.read_bytes())
    k = kunye().get(ad)
    if k is None:
        raise SystemExit(f"ENGEL · {ad} künyede yok.")
    if hashlib.sha256(ham).hexdigest() != k["sha256"]:
        raise SystemExit(f"ENGEL · {ad} sha256 künyeyle tutmuyor.")
    satirlar = ham.decode().split("\n")
    assert satirlar[0] == "t,o,h,l,c,v", satirlar[0]
    o, h, l, c, z = [], [], [], [], []
    for s in satirlar[1:]:
        if not s:
            continue
        t, a, b, d, e, _ = s.split(",")
        z.append(int(t)); o.append(float(a)); h.append(float(b)); l.append(float(d)); c.append(float(e))
    if len(c) != k["bar"]:
        raise SystemExit(f"ENGEL · {ad}: {len(c)} bar, künye {k['bar']}.")
    return Seri(o, h, l, c, z)


def yeniden_ornekle(s: Seri, dakika: int) -> Seri:
    """Kapanmış barlardan daha uzun bar kurar (1 sa → 4 sa; FX'te 1 sa → günlük).

    Kova sınırı UTC gece yarısından sayılır (4 sa: 00·04·08·12·16·20). Bir
    kovanın barı, kovanın SON alt barı arşivde yoksa (hafta sonu, seans
    kapanışı) yine kapanmış sayılır — kova zamanı geçmiştir; yalnız arşivin
    SON kovası düşürülür, çünkü onun kalan alt barları henüz gelmemiş olabilir.
    Neden gerekli: Yahoo'nun FX GÜNLÜK barlarında gövde yok (gövde/menzil
    medyanı 0,02 — açılış kapanışa yapışık), yani bar anatomisi okunamaz;
    günlük FX bu yüzden saatlikten kurulur ve iki yıl geriye gider."""
    if s.zaman is None:
        raise ValueError("yeniden örnekleme zaman damgası ister")
    adim = dakika * 60
    kova, o, h, l, c, z = None, [], [], [], [], []
    for i, t in enumerate(s.zaman):
        k = (int(t) // adim) * adim
        if k != kova:
            kova = k
            o.append(s.o[i]); h.append(s.h[i]); l.append(s.l[i]); c.append(s.c[i]); z.append(k)
        else:
            h[-1] = max(h[-1], s.h[i]); l[-1] = min(l[-1], s.l[i]); c[-1] = s.c[i]
    return Seri(o[:-1], h[:-1], l[:-1], c[:-1], z[:-1])


def enstruman(ad: str) -> str:
    return ad.rsplit("-", 1)[0]


def aralik(ad: str) -> str:
    return ad.rsplit("-", 1)[1]


if __name__ == "__main__":
    for ad in seriler():
        s = oku(ad)
        print(f"{ad:16s} {len(s):7d} bar")
