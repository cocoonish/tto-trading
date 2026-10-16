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


def test_damga_sinamasi_0830_et_zirvesini_yazin_ve_kisin_bulur():
    """08:30 ET dakikasına konan sıçrama yazın 12:30, kışın 13:30 UTC'de durur; ölçüt ikisinde de 0 demeli."""
    parcalar = []
    for gun in ("2024-01-05", "2024-07-05"):          # ayın ilk cumaları: kış ve yaz
        yerel = pd.date_range(f"{gun} 07:00", f"{gun} 10:00", freq="1min", tz=z.NEWYORK, inclusive="left")
        aralik = np.where((yerel.hour == 8) & (yerel.minute == 30), 0.0030, 0.0002)
        c = np.full(len(yerel), 1.10)
        parcalar.append(pd.DataFrame({"o": c, "h": c + aralik / 2, "l": c - aralik / 2, "c": c},
                                     index=yerel.tz_convert("UTC")))
    f = pd.concat(parcalar)
    s = kl.damga_sinamasi(f, 1e-4)
    assert s["kis"]["zirve_dk"] == 0 and s["yaz"]["zirve_dk"] == 0
    # Bir saat kaydırılmış damga (ör. yerel saat UTC sanılmış) zirveyi ±60 dakikaya taşır → ölçüt sıfır demez.
    kayik = f.copy()
    kayik.index = kayik.index + pd.Timedelta(minutes=10)
    s2 = kl.damga_sinamasi(kayik, 1e-4)
    assert s2["kis"]["zirve_dk"] == 10 and s2["yaz"]["zirve_dk"] == 10
