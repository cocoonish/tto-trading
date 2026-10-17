#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Giriş anında BİLİNEBİLEN koşul değişkenleri (işlem başına).

Kural: her değişken sinyal mumunun kapanış anında (`sinyal_t`) bilinen bilgiden
kurulur. Gün düzeyindeki ATR, yüzdelik, NR4/NR7 ve önceki gün bilgisi BUGÜNÜ
içermez (gunluk.py). Asya aralığı ve gece hareketi ancak Londra 08:00'den sonra
bilinir; daha erken sinyalde boş kalır. 60 dakikalık trend, sinyal anından ÖNCE
kapanmış son 60 dakikalık mumun kapanışının EMA50'ye göre yeri; işlem yönüyle
karşılaştırılır. Haber günü takvimden bilinir: planlanmış olay o gün daha sonra
olsa da sabah bellidir; önceden duyurulmayan bir karar günü yalnız FX gününün
başında çoktan olmuşsa işaretler (gunluk.baglam_kur).
"""
from __future__ import annotations

import numpy as np
import pandas as pd

import zaman as z
from gunluk import Baglam

GUN_ADI = np.array(["Pzt", "Sal", "Çar", "Per", "Cum", "Cmt", "Paz"], dtype=object)


def _ema50_60(b: Baglam):
    if "ema50_60" not in b.ek:
        m = b.mumlar(60, 0)
        b.ek["ema50_60"] = (m, pd.Series(m.c).ewm(span=50, adjust=False).mean().to_numpy())
    return b.ek["ema50_60"]


def ozellikler(b: Baglam, isl: pd.DataFrame) -> pd.DataFrame:
    g = b.g
    k = isl["gun_k"].to_numpy(np.int64)
    ts = isl["sinyal_t"].to_numpy(np.int64)
    yon = isl["yon"].to_numpy(np.int64)
    atr = g.atr[k]
    lon = g.an["lon_0800"][k]
    sonra = ts >= lon
    with np.errstate(invalid="ignore", divide="ignore"):
        f = pd.DataFrame(index=isl.index)
        f["range_atr"] = isl["yapi"].to_numpy(np.float64) / atr
        f["asya_atr"] = np.where(sonra, (g.asya_h["08:00"] - g.asya_l["08:00"])[k] / atr, np.nan)
        f["onceki_gun_range_atr"] = (g.onceki_h - g.onceki_l)[k] / atr
        oy = np.sign(g.onceki_c - g.onceki_o)[k] * yon
        f["onceki_gun_yon"] = np.where(oy > 0, "aynı yön", np.where(oy < 0, "ters yön", None))
        f["nr4"] = np.where(g.nr4[k], "NR4", "değil")
        f["nr7"] = np.where(g.nr7[k], "NR7", "değil")
        f["acilis_farki_atr"] = np.where(sonra, (g.lon_acilis - g.onceki_c)[k] / atr * yon, np.nan)
        f["oynaklik_yuzdelik"] = g.atr_yuzdelik[k]
    m60, ema = _ema50_60(b)
    j = np.searchsorted(m60.bt + 3600, ts, side="right") - 1
    ok = j >= 50
    jj = np.clip(j, 0, len(m60) - 1)
    t60 = np.sign(m60.c[jj] - ema[jj]) * yon
    f["trend60"] = np.where(ok & (t60 > 0), "trend yönünde", np.where(ok & (t60 < 0), "trend tersine", None))
    f["hafta_gunu"] = GUN_ADI[g.hafta_gunu[k]]
    f["haber_gunu"] = np.where(b.haber_gun[k], "haber günü", "değil")
    f["ay_sonu"] = np.where(g.ay_sonu[k], "ay sonu", "değil")
    f["dst_gecis_haftasi"] = np.where(g.dst_hafta[k], "geçiş haftası", "değil")
    ara = np.isin(g.dst_rejim[k], ["abd_yaz_avrupa_kis", "avrupa_kis_abd_yaz"])
    f["dst_ara_donem"] = np.where(ara, "ara dönem", "değil")
    f["r"] = isl["r"].to_numpy()
    f["pnl_pip"] = isl["pnl_pip"].to_numpy()
    return f


def giris_saati_tsi(isl: pd.DataFrame) -> np.ndarray:
    t = pd.to_datetime(isl["giris_t"].to_numpy(np.int64), unit="s", utc=True).tz_convert(z.ISTANBUL)
    return t.hour.to_numpy()
