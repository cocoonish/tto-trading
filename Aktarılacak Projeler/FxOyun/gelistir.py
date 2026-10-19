#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Plan geliştirme: aday bacakların 2018–2023 sonucu (maliyetli). YALNIZ örneklem içi.

Gözlem fiyatın ne yaptığını söyler; bu dosya o davranışa verilebilecek birkaç makul tepkinin (aday bacak)
2018–2023'te maliyet sonrası ne getirdiğini ölçer. Plan bu tablodan ve gözlemden yazılır, sonra 2024 ve
sonrasında AYNI kodla (kosu.simule) sınanır. Veri buraya da 31.12.2023'e kırpılarak yüklenir.
"""
from __future__ import annotations

import dataclasses
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

import oyun_sim as kosu
import sinif as sf
from gozlem import IC_BITIS

import ayar as ay  # noqa: E402
import veri as vr  # noqa: E402

BURASI = Path(__file__).resolve().parent

ADAY = {
    "yonlu": [kosu.Bacak("katil", "uc"), kosu.Bacak("katil", 1.0), kosu.Bacak("katil", 0.5),
              kosu.Bacak("devam", 1.0), kosu.Bacak("devam", 0.5),
              kosu.Bacak("katil", 1.0, tampon=0.5), kosu.Bacak("devam", 1.0, tampon=0.5)],
    "kucuk": [kosu.Bacak("kirilim", 1.0), kosu.Bacak("kirilim", 0.5),
              kosu.Bacak("kirilim", 1.0, tampon=0.5), kosu.Bacak("kirilim", 0.5, tampon=0.5),
              kosu.Bacak("kirilim", 1.0, tampon=1.0), kosu.Bacak("kirilim", 0.5, tampon=1.0)],
    "fiksing": [kosu.Bacak("fiks_ver", "orta"), kosu.Bacak("fiks_ver", 1.0), kosu.Bacak("fiks_ver", 0.5),
                kosu.Bacak("katil", "uc"), kosu.Bacak("fiks_ver", 1.0, tampon=0.5),
                kosu.Bacak("fiks_ver", "orta", tampon=0.5)],
}


def bacak_ad(b: kosu.Bacak) -> str:
    return f"{b.tur}:{b.hedef}" + (f":t{b.tampon:g}" if b.tampon != 0.1 else "")


def adaylar(an: sf.An, sinif: str) -> list[kosu.Bacak]:
    if sinif == "kucuk":
        return ADAY["kucuk"]
    return ADAY["fiksing"] if an.aile == "fiksing" else ADAY["yonlu"]


def ozet(g: pd.DataFrame) -> dict:
    r = g["R"].to_numpy()
    return {"n": int(len(r)), "kazanma": float((r > 0).mean()), "ort_R": float(r.mean()),
            "brut_R": float(g["brut_R"].mean()), "risk_pip_med": float(g["risk_pip"].median())}


def main() -> int:
    a = dataclasses.replace(ay.oku(), bitis=IC_BITIS)
    kayit = []
    for cift in a.ciftler:
        d = vr.oku(cift, a)
        assert pd.Timestamp(d.t[-1], unit="s") < pd.Timestamp("2024-01-01")
        for an in sf.ANLAR:
            ev = sf.olaylar(d, an, cift)
            if len(ev) == 0:
                continue
            for e in ev.to_dict("records"):
                for b in adaylar(an, e["sinif"]):
                    x = kosu.simule(d, e, b)
                    if x is not None:
                        x["bacak"] = bacak_ad(b)
                        x["aile"] = an.aile
                        kayit.append(x)
        print(f"  {cift}: {len(kayit)} işlem", flush=True)
    df = pd.DataFrame(kayit)
    out = []
    for anahtar in (["an", "sinif", "bacak"], ["aile", "sinif", "bacak"], ["an", "sinif", "uyum", "bacak"]):
        for k, g in df.groupby(anahtar):
            out.append({"anahtar": "+".join(anahtar), **dict(zip(anahtar, k)), **ozet(g)})
    (BURASI / "veri" / "gelistir.json").write_text(json.dumps({"donem": ["2018-01-01", IC_BITIS.isoformat()],
                                                             "kayma_pip": kosu.KAYMA_PIP, "satir": out},
                                                            ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    print(f"✓ {len(df)} aday işlem → veri/gelistir.json")
    return 0


if __name__ == "__main__":
    sys.exit(main())
