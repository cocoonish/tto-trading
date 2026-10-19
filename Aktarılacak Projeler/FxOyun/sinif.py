#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""FX gün içi oyun planı — anlar ve sınıflar (gözlem ve sınama AYNI kodu kullanır).

Bir AN, fiyatın davranışının değiştiği bilinen bir saattir: seans açılışı, fiksing, veri ya da merkez bankası
kararı. Her anın bir İLK MUMU vardır (açılışlarda ve haberlerde andan sonraki ilk mum, fiksinglerde fiksinge
kadar süren mum) ve o mum iki şeyle sınıflanır:

- MUMUN KENDİSİ — aralığı o anın geçmişteki tipik ilk mumuna göre büyük mü, gövdesi dolu mu, fitili uzun mu.
  "Tipik" yalnız GEÇMİŞTEN ölçülür: aynı parite ve aynı anın önceki 60 ilk mumunun medyan aralığı (en az 20);
  haber anlarında önceki 24 olayın (en az 8).
- GENEL TREND — günlük kapanışların 20 günlük üstel ortalaması (EMA20): bir önceki günün kapanışı ortalamanın
  üstünde ve ortalama beş günde yükselmişse yukarı, tersi aşağı, öbür hâller yatay. Bu da yalnız geçmişten.

Hiçbir sınıf, mum kapandıktan sonraki fiyatı kullanmaz; sınıflama an kapandığı dakikada bilinir.
Bütün fiyatlar orta fiyattır (bid ile ask'ın ortası); sınama dolumu bid/ask'tan yapar.
"""
from __future__ import annotations

import sys
from dataclasses import dataclass
from pathlib import Path

import numpy as np
import pandas as pd

BURASI = Path(__file__).resolve().parent
FXG = BURASI.parent / "FxGunici"
if str(FXG) not in sys.path:
    sys.path.insert(0, str(FXG))
import takvim  # noqa: E402
import veri as vr  # noqa: E402
import zaman as z  # noqa: E402


@dataclass(frozen=True)
class An:
    kimlik: str
    ad: str
    aile: str            # acilis · fiksing · veri · mb
    bolge: object
    saat: str            # yerel saat; fiksingde fiksing ANI (ilk mum ondan önce biter)
    tf: int              # ilk mumun dakikası
    pencere: int         # ilk mumdan sonra izlenen süre (dk)
    olay: str = ""       # takvim olayı (haber anları)


ANLAR = [
    An("tokyo_acilis", "Tokyo açılışı", "acilis", z.TOKYO, "09:00", 15, 180),
    An("londra_acilis", "Londra açılışı", "acilis", z.LONDRA, "08:00", 15, 180),
    An("ny_acilis", "New York açılışı", "acilis", z.NEWYORK, "09:30", 15, 120),
    An("tokyo_fiks", "Tokyo fiksingi", "fiksing", z.TOKYO, "09:55", 30, 60),
    An("wmr", "Londra fiksingi (WM/R)", "fiksing", z.LONDRA, "16:00", 30, 60),
    An("nfp", "Tarım dışı istihdam", "veri", z.NEWYORK, "08:30", 5, 120, "NFP"),
    An("cpi", "ABD TÜFE", "veri", z.NEWYORK, "08:30", 5, 120, "CPI"),
    An("fomc", "FOMC kararı", "mb", z.NEWYORK, "14:00", 5, 120, "FOMC_karar"),
    An("ecb", "ECB kararı", "mb", z.FRANKFURT, "", 5, 120, "ECB_karar"),
    An("boe", "BoE kararı", "mb", z.LONDRA, "12:00", 5, 120, "BoE_karar"),
]
AN = {a.kimlik: a for a in ANLAR}

TIPIK_PENCERE, TIPIK_EN_AZ = 60, 20          # her gün olan anlar
HABER_PENCERE, HABER_EN_AZ = 24, 8           # ayda bir ya da daha seyrek olan haber anları
GUCLU_ARALIK, GUCLU_GOVDE = 1.25, 0.60      # aralık ≥ 1,25 × tipik ve gövde ≥ aralığın %60'ı
RED_GOVDE, RED_FITIL, RED_ARALIK = 0.35, 0.50, 0.75   # gövde ≤ %35, bir fitil ≥ %50, aralık ≥ 0,75 × tipik
KUCUK_ARALIK = 0.60                          # aralık < 0,6 × tipik
DOLULUK = 0.80                               # mumun ve pencerenin dakikalarının en az %80'i kotasyonlu
EMA_N, EMA_EGIM = 20, 5

SINIFLAR = ["guclu", "reddedilen", "normal", "kucuk"]
SINIF_AD = {"guclu": "güçlü", "reddedilen": "reddedilen (uzun fitil)", "normal": "normal", "kucuk": "küçük"}
UYUM_AD = {"trendle": "trend yönünde", "karsi": "trende karşı", "yatay": "trend yatay"}


def gunluk_trend(d: vr.Dakika) -> pd.DataFrame:
    """İşlem günü başına: o günün kapanışı, EMA20 ve trend sınıfı. Bir olay gününe ÖNCEKİ günün satırı uygulanır."""
    gun = pd.Series(d.gun)
    son = np.flatnonzero(np.r_[gun.values[1:] != gun.values[:-1], True])
    df = pd.DataFrame({"gun": d.gun[son], "kapanis": d.mc[son]})
    df = df[pd.DatetimeIndex(df["gun"]).dayofweek < 5].reset_index(drop=True)
    df["ema"] = df["kapanis"].ewm(alpha=2 / (EMA_N + 1), adjust=False).mean()
    egim = df["ema"] - df["ema"].shift(EMA_EGIM)
    yon = np.where((df["kapanis"] > df["ema"]) & (egim > 0), 1, np.where((df["kapanis"] < df["ema"]) & (egim < 0), -1, 0))
    df["trend"] = np.where(np.arange(len(df)) < EMA_N + EMA_EGIM, np.nan, yon)
    return df


def an_saniyeleri(an: An, cift: str, gunler: np.ndarray) -> np.ndarray:
    """Anın UTC epoch saniyeleri (her biri bir işlem gününe ait)."""
    if an.olay:
        df = takvim.olaylar_oku(cift)
        df = df[df["olay"] == an.olay]
        return np.sort(df["utc_sn"].to_numpy(np.int64))
    return vr.yerel_an_sn(gunler, an.saat, an.bolge)


def mum(d: vr.Dakika, bas: int, tf: int):
    """[bas, bas+tf) dakikalarının mumu ve kapanış dizini; yetersiz kotasyonda None."""
    i0, i1 = np.searchsorted(d.t, bas), np.searchsorted(d.t, bas + tf * 60)
    if i1 - i0 < DOLULUK * tf or i0 >= len(d.t):
        return None
    return d.mo[i0], d.mh[i0:i1].max(), d.ml[i0:i1].min(), d.mc[i1 - 1], i0, i1


def sinifla(o, h, l, c, tipik: float) -> tuple[str, int]:
    """(sınıf, yön). Yön: güçlü ve normal mumda gövdenin yönü; reddedilen mumda REDDİN yönü (üst fitil uzunsa
    aşağı, alt fitil uzunsa yukarı); küçük mumda 0."""
    R = h - l
    if not tipik or R <= 0:
        return "kucuk", 0
    B = abs(c - o)
    ust, alt = h - max(o, c), min(o, c) - l
    if R < KUCUK_ARALIK * tipik:
        return "kucuk", 0
    if R >= GUCLU_ARALIK * tipik and B >= GUCLU_GOVDE * R:
        return "guclu", int(np.sign(c - o))
    if B <= RED_GOVDE * R and R >= RED_ARALIK * tipik and max(ust, alt) >= RED_FITIL * R:
        return "reddedilen", -1 if ust > alt else 1
    return "normal", int(np.sign(c - o))


def uyum(yon: int, trend) -> str:
    if trend is None or np.isnan(trend) or trend == 0:
        return "yatay"
    if yon == 0:
        return "yatay"
    return "trendle" if yon == trend else "karsi"


def olaylar(d: vr.Dakika, an: An, cift: str) -> pd.DataFrame:
    """Anın her gerçekleşmesi: ilk mum, sınıfı, trend ve izleme penceresinin dakika dizinleri."""
    gunler = np.unique(d.gun)
    gunler = gunler[pd.DatetimeIndex(gunler).dayofweek < 5]
    sn = an_saniyeleri(an, cift, gunler)
    tr = gunluk_trend(d)
    tr_gun = tr["gun"].to_numpy()
    satir, araliklar = [], []
    for t0 in sn:
        bas = int(t0) - (an.tf * 60 if an.aile == "fiksing" else 0)    # fiksingde ilk mum fiksinge kadar sürer
        m = mum(d, bas, an.tf)
        if m is None:
            continue
        o, h, l, c, i0, i1 = m
        izle_bas = int(t0) if an.aile == "fiksing" else bas + an.tf * 60
        j0, j1 = np.searchsorted(d.t, izle_bas), np.searchsorted(d.t, izle_bas + an.pencere * 60)
        if j1 - j0 < DOLULUK * an.pencere:
            continue
        gun = d.gun[min(i0, len(d.gun) - 1)]
        k = np.searchsorted(tr_gun, gun) - 1                         # bir önceki işlem günü
        trend = float(tr["trend"].iloc[k]) if k >= 0 else np.nan
        gunluk_an = an.aile in ("acilis", "fiksing")
        onceki = araliklar[-(TIPIK_PENCERE if gunluk_an else HABER_PENCERE):]
        tipik = float(np.median(onceki)) if len(onceki) >= (TIPIK_EN_AZ if gunluk_an else HABER_EN_AZ) else np.nan
        araliklar.append(h - l)
        if np.isnan(tipik):
            continue
        s, y = sinifla(o, h, l, c, tipik)
        satir.append({"cift": cift, "an": an.kimlik, "t0": int(t0), "gun": str(gun), "o": o, "h": h, "l": l, "c": c,
                      "tipik": tipik, "sinif": s, "yon": y, "trend": trend, "uyum": uyum(y, trend),
                      "ay_sonu": bool(z.londra_ay_sonu(pd.Timestamp(gun).date())),
                      "j0": int(j0), "j1": int(j1), "pip": d.pip})
    return pd.DataFrame(satir)
