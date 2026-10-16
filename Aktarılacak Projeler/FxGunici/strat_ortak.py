#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Stratejilerin ortak katmanı: sinyal tablosu → motor emirleri → işlemler.

Bir strateji yalnız SİNYAL TABLOSU üretir (pandas DataFrame). Zorunlu sütunlar:
  gun_k       işlem gününün `Gunluk` içindeki sırası
  s           sinyal mumunun dizini (stratejinin kendi tf/ofset mumlarında)
  yon         +1 alış, −1 satış
  stop        stop seviyesi (nokta); stopsuz stratejide NaN
  yapi        yapının büyüklüğü (nokta): aralık genişliği, mum aralığı vb. —
              koşul analizinin "aralık/ATR" değişkeni
İsteğe bağlı: risk (stopsuz stratejinin R birimi), seviye (seviye hedefi), giris_i
(giriş dakikası; verilmezse sinyal mumundan sonraki mumun ilk dakikası), cikis_i
(zaman çıkışı dakikası; verilmezse gün sonu ya da 'zaman' hedefinde N mum sonra).

Giriş daima sinyal mumunun KAPANIŞINDAN sonradır; bu katman bunu sınar ve
bozulursa düşer (lookahead'in en basit biçimi tek satırla yakalanır).
"""
from __future__ import annotations

import numpy as np
import pandas as pd
from numba import njit

import motor as mt
from gunluk import Baglam

HEDEF_SEVIYE_ADLARI = {"vwap", "seviye", "oncesi", "karsi_uc", "itki_ucu"}


def emirler(b: Baglam, sin: pd.DataFrame, tf: int, ofset: int, stop_turu: str, hedef: str,
            zaman_mum: int = 12) -> tuple[np.ndarray, pd.DataFrame]:
    """Sinyal tablosundan motor emirleri; ayrıca işlemle birleşecek sinyal bilgisi."""
    m = b.mumlar(tf, ofset)
    g = b.g
    sin = sin.reset_index(drop=True).copy()
    if len(sin) == 0:
        return mt.bos_emir(0), sin
    s = sin["s"].to_numpy(np.int64)
    k = sin["gun_k"].to_numpy(np.int64)
    if "giris_i" in sin:
        giris = sin["giris_i"].to_numpy(np.int64)
    else:
        sonraki = s + 1
        gecerli = sonraki < len(m)
        giris = np.where(gecerli, m.i0[np.clip(sonraki, 0, len(m) - 1)], -1)
    # sinyal mumu kapanmadan giriş yok
    kapanis = m.bt[s] + tf * 60
    gt = np.where(giris >= 0, b.d.t[np.clip(giris, 0, len(b.d.t) - 1)], -1)
    if ((giris >= 0) & (gt < kapanis)).any():
        raise AssertionError("giriş, sinyal mumunun kapanışından önce — lookahead")
    gun_sonu = g.sinir[k]
    if "cikis_i" in sin:
        cikis = np.minimum(sin["cikis_i"].to_numpy(np.int64), gun_sonu)
    elif hedef == "zaman":
        j = s + 1 + zaman_mum
        zi = np.where(j < len(m), m.i0[np.clip(j, 0, len(m) - 1)], len(b.d.t) - 1)
        cikis = np.minimum(zi, gun_sonu)
    else:
        cikis = gun_sonu
    e = mt.bos_emir(len(sin))
    e["giris_i"] = np.where(giris < gun_sonu, giris, -1)      # gün sonundan sonra giriş yok
    e["yon"] = sin["yon"].to_numpy(np.int8)
    e["stop"] = sin["stop"].to_numpy(np.float64) if "stop" in sin else np.nan
    if "risk" in sin:
        e["risk"] = sin["risk"].to_numpy(np.float64)
    e["cikis_i"] = cikis
    e["stop_tur"] = {"sert": mt.STOP_SERT, "kapanis": mt.STOP_KAPANIS, "yok": mt.STOP_YOK}[stop_turu]
    if hedef in ("1R", "2R"):
        e["hedef_tur"] = mt.HEDEF_R
        e["hedef_k"] = 1.0 if hedef == "1R" else 2.0
    elif hedef in HEDEF_SEVIYE_ADLARI:
        e["hedef_tur"] = mt.HEDEF_SEVIYE
        e["hedef_seviye"] = sin["seviye"].to_numpy(np.float64)
    elif hedef in ("gun_sonu", "zaman", "yok"):
        e["hedef_tur"] = mt.HEDEF_YOK
    else:
        raise ValueError(f"bilinmeyen hedef: {hedef}")
    e["kimlik"] = np.arange(len(sin))
    sin["sinyal_t"] = kapanis
    return e, sin


def kos(b: Baglam, sin: pd.DataFrame, tf: int, ofset: int, stop_turu: str, hedef: str,
        kayma_pip: float, haber_kayma_pip: float, zaman_mum: int = 12) -> pd.DataFrame:
    """Sinyal tablosunu motorda koşturur; işlemleri sinyal bilgisiyle birleştirir."""
    e, sin = emirler(b, sin, tf, ofset, stop_turu, hedef, zaman_mum)
    if len(e) == 0:
        return pd.DataFrame()
    isl = mt.simule(b.d, e, b.bar_son(tf, ofset), b.haber, kayma_pip, haber_kayma_pip)
    isl = isl.sort_values("kimlik").reset_index(drop=True)
    sin = sin.reset_index(drop=True)
    birlesik = pd.concat([sin.drop(columns=[c for c in ("yon", "stop", "giris_i", "cikis_i") if c in sin]),
                          isl], axis=1)
    birlesik["gun"] = b.g.gun[birlesik["gun_k"].to_numpy(np.int64)]
    return birlesik


def gun_mum_araligi(m, a_sn: np.ndarray, b_sn: np.ndarray, tf: int) -> tuple[np.ndarray, np.ndarray]:
    """Her gün için [a, b) içinde BAŞLAYIP b'de ya da önce KAPANAN mumların dizin aralığı [j0, j1)."""
    j0 = np.searchsorted(m.bt, a_sn, side="left")
    j1 = np.searchsorted(m.bt, b_sn - tf * 60, side="right")
    return j0, np.maximum(j1, j0)


def ilk_dogru(maske: np.ndarray) -> int:
    i = int(np.argmax(maske)) if len(maske) else 0
    return i if len(maske) and maske[i] else -1


@njit(cache=True)
def wilder(x: np.ndarray, n: int) -> np.ndarray:
    out = np.full(len(x), np.nan)
    if len(x) >= n:
        out[n - 1] = x[:n].mean()
        a = 1.0 / n
        for i in range(n, len(x)):
            out[i] = out[i - 1] + a * (x[i] - out[i - 1])
    return out


def atr_mum(m, n: int = 14) -> np.ndarray:
    """Mum serisinin Wilder ATR'si (o mumun kapanışında bilinir). Mum nesnesinin kendisinde önbellekli."""
    anahtar = ("atr", n)
    if anahtar not in m.ek:
        h, l, c = m.h, m.l, m.c
        onceki = np.concatenate([[c[0]], c[:-1]])
        tr = np.maximum.reduce([h - l, np.abs(h - onceki), np.abs(l - onceki)])
        m.ek[anahtar] = wilder(tr.astype(np.float64), n)
    return m.ek[anahtar]
