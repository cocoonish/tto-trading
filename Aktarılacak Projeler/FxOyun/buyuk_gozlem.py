#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Büyük mum gözlemi — YALNIZ 2018–2023 (giriş planı bu dosyanın çıktısından yazılır, 2024 → sınanır).

Veri ayar dosyasının bitiş tarihi 31.12.2023'e çekilerek yüklenir: arşiv okuyucusu bütün yıl dosyalarının özünü
sınar ve satırları okur, yükleyici 2024 ve sonrasını İLK adımda keser — o fiyatlar hiçbir hesaba girmez; her paritenin
son dakikası ayrıca o tarihe karşı sınanır (assert). Tanım ve ölçüler `buyuk_mum.py`de.

Çıktı: veri/buyuk_gozlem.json (dilim × süzgeç × değer özetleri) ve veri/_yerel/buyuk_olaylar.csv.gz (olay başına
süzgeçler, gerçek ve ayna yol ölçüleri, makas; git dışı, aynı komutla yeniden üretilir).
"""
from __future__ import annotations

import dataclasses
import gzip
import json
import sys
from datetime import date
from pathlib import Path

import numpy as np
import pandas as pd

import buyuk_mum as bm

import ayar as ay  # noqa: E402
import veri as vr  # noqa: E402

BURASI = Path(__file__).resolve().parent
CIKTI = BURASI / "veri"
IC_BITIS = date(2023, 12, 31)
SINIR = pd.Timestamp("2024-01-01").value // 10 ** 9

ORAN = ([f"sim_{k}" for k in bm.SIMETRIK] + [f"geri_{f}" for f in bm.GERI]
        + ["geri_50_uc", "uc_asma", "uc_asma_05A"])
NET = [f"net_{H}" for H in bm.UFUKLAR]


def olaylari_kur(ciftler: list[str], a) -> tuple[pd.DataFrame, dict]:
    parca, sayim = [], {}
    for cift in ciftler:
        d = vr.oku(cift, a)
        assert int(d.t[-1]) < SINIR, "2024 sonrası veri gözleme girdi"
        for tf in bm.DILIMLER:
            ev, s = bm.olaylar(d, tf, cift)
            sayim[f"{cift}_{tf}"] = s
            if not len(ev):
                continue
            ev = ev[ev["bt"] + (bm.IZLE + 1) * tf * 60 <= SINIR].reset_index(drop=True)
            gercek, ayna, mk = [], [], []
            for e in ev.to_dict("records"):
                g, y = bm.olc(d, e)
                gercek.append(g)
                ayna.append({f"ayna_{k}": v for k, v in y.items()})
                mk.append(bm.makas(d, e))
            parca.append(pd.concat([ev, pd.DataFrame(gercek), pd.DataFrame(ayna), pd.DataFrame(mk)], axis=1))
            print(f"  {cift} {tf} dk: {len(ev)} olay (büyük {s['buyuk']}, küme {s['kume']}, "
                  f"yeniden açılış {s['yeniden_acilis']}, devir {s['devir']}, eksik {s['eksik']})", flush=True)
        del d
    return pd.concat(parca, ignore_index=True), sayim


def ozet(g: pd.DataFrame) -> dict:
    g = g[g["yon"] != 0]
    r = {"n": int(len(g)), "cift_n": {c: int(x) for c, x in g["cift"].value_counts().sort_index().items()},
         "gun_n": int(g["gun"].nunique())}
    if not len(g):
        return r
    for x in ORAN:
        v = g[x].astype(float)
        av = g[f"ayna_{x}"].astype(float)
        r[x] = float(v.mean())
        r[f"ayna_{x}"] = float(av.mean())
        r[f"{x}_n"] = int(v.notna().sum())
    for x in NET:
        r[f"{x}_ort"] = float(g[x].mean())
        r[f"{x}_med"] = float(g[x].median())
        r[f"{x}_se"] = float(g[x].std(ddof=1) / np.sqrt(len(g))) if len(g) > 1 else None
        r[f"{x}_pozitif"] = float((g[x] > 0).mean())
    r["mfe_med"], r["mae_med"] = float(g["mfe"].median()), float(g["mae"].median())
    r["geri_0.5_dk_med"] = float(g["geri_0.5_dk"].median()) if g["geri_0.5"].any() else None
    for k in ["mum"] + [str(x) for x in bm.MAKAS_SONRA]:
        oran = g[f"makas_{k}"] / g["makas_once"]
        r[f"makas_{k}_kat_med"] = float(oran.median())
        r[f"makas_{k}_kat_ort"] = float(oran.mean())
        r[f"makas_{k}_iki_kat"] = float((oran >= 2).mean())
        r[f"makas_{k}_pip_med"] = float(g[f"makas_{k}"].median())
    r["makas_once_pip_med"] = float(g["makas_once"].median())
    r["A_pip_med"] = float((g["A"] / g["pip"]).median())
    r["R_pip_med"] = float(((g["h"] - g["l"]) / g["pip"]).median())
    return r


def main() -> int:
    a = dataclasses.replace(ay.oku(), bitis=IC_BITIS)
    df, sayim = olaylari_kur(a.ciftler, a)
    CIKTI.mkdir(exist_ok=True)
    (CIKTI / "_yerel").mkdir(exist_ok=True)
    with gzip.open(CIKTI / "_yerel" / "buyuk_olaylar.csv.gz", "wt", encoding="utf-8") as f:   # git dışı (14 MB)
        df.to_csv(f, index=False)
    out = {"donem": ["2018-01-01", IC_BITIS.isoformat()], "olay": int(len(df)), "sayim": sayim,
           "kararsiz": {str(tf): int(((df["tf"] == tf) & (df["yon"] == 0)).sum()) for tf in bm.DILIMLER},
           "hepsi": {}, "suzgec": {}, "kova_suzgec": {}}
    for tf in bm.DILIMLER:
        g = df[df["tf"] == tf]
        out["hepsi"][str(tf)] = ozet(g)
        out["suzgec"][str(tf)] = {f: {v: ozet(g[g[f] == v]) for v in vals} for f, vals in bm.SUZGECLER.items()}
        out["kova_suzgec"][str(tf)] = {
            k: {f: {v: ozet(g[(g["kova"] == k) & (g[f] == v)]) for v in vals}
                for f, vals in bm.SUZGECLER.items() if f != "kova"}
            for k in bm.SUZGECLER["kova"]}
    (CIKTI / "buyuk_gozlem.json").write_text(json.dumps(out, ensure_ascii=False, separators=(",", ":")) + "\n", encoding="utf-8")
    print(f"✓ {len(df)} olay → veri/buyuk_gozlem.json")
    return 0


if __name__ == "__main__":
    sys.exit(main())
