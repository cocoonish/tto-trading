#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Ölçülmüş olasılıkları Pine'a YAZAR ve iki yönde SINAR.

`site/src/data/yapi_backtest.json` → `site/public/indikatorler/tto-yapi.pine`
içindeki `// OLASILIK-BAŞI … // OLASILIK-SON` bloğu. Elle yazılan sayı bir
sonraki ölçümde sessizce eskir; blok bu yüzden üretilir ve `duman.py` blok
ile JSON'un aynı sayıları taşıdığını sınar (`--denetle`). N < 30 olan hücre
−1 (ölçülmedi) yazılır: örneklem aritmetiği (SMC 15.4) 30'un altında ±9
puanı bile vermez.

    python3 pine_sabit.py            # yaz
    python3 pine_sabit.py --denetle  # Pine bloğu JSON'dan türetilenle aynı mı"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

KOK = Path(__file__).resolve().parent
DEPO = KOK.parents[1]
JSON = DEPO / "site" / "src" / "data" / "yapi_backtest.json"
PINE = DEPO / "site" / "public" / "indikatorler" / "tto-yapi.pine"
TF = ("5m", "15m", "1h", "4h", "1d")
ASGARI_N = 30

# Pine değişkeni → (olasılık anahtarı ya da özel)
ALANLAR = [
    ("olBosT1", "bos_t1"), ("olMssDevam", "mss_devam"), ("olSweep", "sweep_tepki"),
    ("olFvgTepki", "fvg_ce_tepki"), ("olObTepki", "ob_tepki"), ("olPrzT1", "prz_t1"),
]


def _oran(o: dict) -> float:
    return -1.0 if not o or o.get("oran") is None or o.get("n", 0) < ASGARI_N else round(o["oran"], 3)


def blok_uret(d: dict) -> str:
    satirlar = []
    for degisken, anahtar in ALANLAR:
        degerler = [_oran(d["olasilik"].get(tf, {}).get("toplam", {}).get(anahtar)) for tf in TF]
        satirlar.append(f"var {degisken:11s}= array.from(" + ", ".join(f"{v:.3f}" for v in degerler) + ")")
    # diverjans: tablo satırlarının N ağırlıklı toplam isabeti
    div = []
    for tf in TF:
        sat = d["diverjans"].get(tf, [])
        k = sum(int(round((r.get("oran") or 0) * r["n"])) for r in sat if r.get("n"))
        n = sum(r["n"] for r in sat if r.get("n"))
        div.append(-1.0 if n < ASGARI_N else round(k / n, 3))
    satirlar.append("var olDivIsabet = array.from(" + ", ".join(f"{v:.3f}" for v in div) + ")")
    nler = [sum(v["bar"] for a, v in d["kunye"]["seriler"].items() if a.endswith("-" + tf)) for tf in TF]
    satirlar.append("var olN         = array.from(" + ", ".join(str(n) for n in nler) + ")")
    satirlar.append(f"// ölçüm {d['kunye']['olcum_tarihi']} · bar sayısı zaman dilimine göre olN'de · N<{ASGARI_N} hücre −1")
    return "\n".join(satirlar)


def yaz() -> None:
    d = json.loads(JSON.read_text(encoding="utf-8"))
    metin = PINE.read_text(encoding="utf-8")
    yeni = "// OLASILIK-BAŞI\n" + blok_uret(d) + "\n// OLASILIK-SON"
    m = re.search(r"// OLASILIK-BAŞI\n.*?// OLASILIK-SON", metin, re.S)
    if not m:
        raise SystemExit("ENGEL · Pine'da OLASILIK bloğu işaretleri yok")
    PINE.write_text(metin[:m.start()] + yeni + metin[m.end():], encoding="utf-8")
    print("yazıldı:", PINE.name)


def denetle() -> list[str]:
    d = json.loads(JSON.read_text(encoding="utf-8"))
    metin = PINE.read_text(encoding="utf-8")
    m = re.search(r"// OLASILIK-BAŞI\n(.*?)// OLASILIK-SON", metin, re.S)
    if not m:
        return ["Pine'da OLASILIK bloğu yok"]
    beklenen = blok_uret(d).strip()
    mevcut = m.group(1).strip()
    if beklenen != mevcut:
        return ["Pine olasılık bloğu JSON'dan türetilenle AYNI DEĞİL — `pine_sabit.py` koşturulmalı"]
    return []


if __name__ == "__main__":
    if "--denetle" in sys.argv:
        h = denetle()
        print("\n".join(h) if h else "olasılık bloğu JSON ile aynı")
        sys.exit(1 if h else 0)
    yaz()
