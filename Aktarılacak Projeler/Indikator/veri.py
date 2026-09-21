#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""İki panelli indikatörün OHLC ARŞİVİ — tek yükleyici.

Arşiv `veri/<ad>-<aralik>.csv.gz` dosyalarında durur (t epoch sn UTC,
o,h,l,c,v); bulut keşif koşusundan (`bulten/kesif_indikator_veri.py`)
ayrıştırılıp buraya yazılır ve `veri/kunye.json` her serinin kaynağını,
koşu numarasını, bar sayısını, kapsamını ve sha256'sını taşır. Yayımlanan
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
sys.path.insert(0, str(DEPO / "site" / "public" / "indikatorler"))
from brooks_referans import Seri  # noqa: E402

# Tick: kaynağın ilan ettiği fiyat adımı (TradingView `syminfo.mintick`
# karşılığı). Yahoo ilan etmez; burada enstrümanın piyasa konvansiyonu
# yazılıdır, brooks_referans.tick_tahmini yalnız yedektir.
TICK = {"eurusd": 0.00001, "gbpusd": 0.00001, "usdjpy": 0.001, "usdchf": 0.00001,
        "audusd": 0.00001, "usdtry": 0.0001, "altin": 0.1, "btcusd": 1.0,
        "dxy": 0.001, "sp500": 0.25, "bist100": 0.01, "wti": 0.01}
PIP = {"eurusd": 0.0001, "gbpusd": 0.0001, "usdjpy": 0.01, "usdchf": 0.0001,
       "audusd": 0.0001, "usdtry": 0.0001}


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


def enstruman(ad: str) -> str:
    return ad.rsplit("-", 1)[0]


def aralik(ad: str) -> str:
    return ad.rsplit("-", 1)[1]


if __name__ == "__main__":
    for ad in seriler():
        s = oku(ad)
        print(f"{ad:16s} {len(s):7d} bar")
