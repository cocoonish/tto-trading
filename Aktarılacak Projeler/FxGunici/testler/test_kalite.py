# -*- coding: utf-8 -*-
"""Kalite denetiminin duman sınaması — sentetik arşiv, bilinen kusurlarla.

Arşive bilerek dört kusur konur ve denetimin her birini SAYDIĞI sınanır:
bir işlem gününde 30 dakikalık boşluk, bir negatif makas, bir sıçrama ve bir
tatil günü. Kusuru yakalayamayan bir denetim "temiz" der; o yüzden ölçüt
arızanın kendisine karşı koşturulur.
"""
from __future__ import annotations

import sys
from datetime import date
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import ayar as ay  # noqa: E402
import dukascopy as dk  # noqa: E402
import kalite as kl  # noqa: E402
import zaman as z  # noqa: E402


def sentetik(bas: date, bit: date, tohum: int = 5) -> pd.DataFrame:
    gunler, bas_sn = kl.beklenen_izgara(bas, bit)
    t = (bas_sn[:, None] + np.arange(1440)[None, :] * 60).ravel()
    r = np.random.default_rng(tohum)
    adim = r.integers(-6, 7, size=len(t))
    c = 110000 + np.cumsum(adim)
    o = np.concatenate([[110000], c[:-1]])
    h = np.maximum(o, c) + r.integers(0, 4, size=len(t))
    l = np.minimum(o, c) - r.integers(0, 4, size=len(t))
    df = pd.DataFrame({"t": t, "b_o": o, "b_h": h, "b_l": l, "b_c": c,
                       "d_o": 3, "d_h": 3, "d_l": 3, "d_c": 3,
                       "b_v": np.float32(2.0), "a_v": np.float32(2.0)})
    for s in ("b_o", "b_h", "b_l", "b_c", "d_o", "d_h", "d_l", "d_c"):
        df[s] = df[s].astype(np.int32)
    return df


def test_kalite_bilinen_kusurlari_sayar(tmp_path, monkeypatch):
    bas, bit = date(2024, 3, 4), date(2024, 3, 22)
    df = sentetik(bas, bit)
    # (1) 12.03.2024 işlem gününde 10:00 UTC'den 30 dakikalık boşluk
    b0 = int(pd.Timestamp("2024-03-12 10:00", tz="UTC").timestamp())
    df = df[~((df["t"] >= b0) & (df["t"] < b0 + 30 * 60))]
    # (2) 15.03.2024 işlem günü tamamen yok (tatil gibi)
    g0, g1 = z.islem_gunu_sinirlari(date(2024, 3, 15))
    df = df[~((df["t"] >= int(g0.timestamp())) & (df["t"] < int(g1.timestamp())))]
    # (3) bir negatif makas
    i = df.index[5000]
    df.loc[i, "d_c"] = -2
    # (4) bir sıçrama: kapanış +300 nokta, ertesi dakika geri
    j = df.index[7000]
    k = df.index.get_loc(j)
    df.loc[j, ["b_c", "b_h"]] = df.loc[j, "b_c"] + 300
    df.loc[df.index[k + 1], "b_o"] = df.loc[j, "b_c"]
    df.loc[df.index[k + 1], "b_h"] = max(df.loc[df.index[k + 1], "b_h"], df.loc[j, "b_c"])
    duka = tmp_path / "dukascopy"
    dk.yaz(df.reset_index(drop=True), duka / "EURUSD" / "2024.parquet")
    monkeypatch.setattr(ay, "DUKA", duka)
    a = ay.oku()
    a = a.__class__(**{**a.__dict__, "baslangic": bas, "bitis": bit, "ciftler": ("EURUSD",)})
    s = kl.denetle("EURUSD", a)
    k_ = s["kapsam"]
    assert k_["bosluk_kovalari"]["15-59"] >= 1
    assert any(b["uzunluk_dk"] == 30 for b in k_["en_uzun_bosluklar"])
    assert ["2024-03-15", 0.0] in [list(x) for x in k_["tatil_gunleri"]]
    assert s["makas"]["negatif_kapanis"] == 1
    assert s["sicrama"]["aday"] >= 1
    assert s["capraz"] == {"durum": "saatlik dosya yok"}
