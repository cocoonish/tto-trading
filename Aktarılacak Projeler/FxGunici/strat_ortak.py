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
    # gün sonundan sonra giriş yok; motor bunu "gun_sonu" diye sayar (−1: sonraki mum yok, "veri_yok")
    e["giris_i"] = np.where(giris < 0, -1, np.where(giris < gun_sonu, giris, mt.GIRIS_GUN_SONU))
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
        kayma_pip: float, haber_kayma_pip: float, zaman_mum: int = 12, tek_pozisyon: bool = True) -> pd.DataFrame:
    """Sinyal tablosunu motorda koşturur; işlemleri sinyal bilgisiyle birleştirir."""
    e, sin = emirler(b, sin, tf, ofset, stop_turu, hedef, zaman_mum)
    if len(e) == 0:
        return pd.DataFrame()
    isl = mt.simule(b.d, e, b.bar_son(tf, ofset), b.haber, kayma_pip, haber_kayma_pip, tek_pozisyon=tek_pozisyon)
    isl = isl.sort_values("kimlik").reset_index(drop=True)
    sin = sin.reset_index(drop=True)
    birlesik = pd.concat([sin.drop(columns=[c for c in ("yon", "stop", "giris_i", "cikis_i") if c in sin]),
                          isl], axis=1)
    birlesik["gun"] = b.g.gun[birlesik["gun_k"].to_numpy(np.int64)]
    return birlesik


#: Tek pozisyon kuralının bir işlem engellendiğinde boşalttığı sonuç alanları (motorun alınmayan emir satırı gibi).
_SONUC_ALANI = ("giris_f", "cikis_f", "R", "pnl", "brut", "mae", "mfe", "hedef", "pnl_pip", "brut_pip", "R_pip",
                "r", "r_brut", "mae_r", "mfe_r", "sure_dk")


def tek_pozisyon_uygula(isl: pd.DataFrame) -> pd.DataFrame:
    """Ayrı ayrı (tek pozisyon kuralı olmadan) koşturulmuş işlemlere, giriş dakikası sırasıyla motorun tek pozisyon
    kuralını uygular: bir pozisyon açıkken gelen emir alınmaz (durum 1). Motorla aynı serbestlik kuralı: çıkış
    dakikanın açılışında olduysa (zaman, kapanış stop'u, boşluk) aynı dakikada yeni giriş olabilir — giriş dakikasının
    kendisindeki boşluklu stop hariç. İşlemler
    birbirinden bağımsız simüle edildiği için sonuç, hepsinin tek bir motor çağrısında koşmasıyla aynıdır."""
    if len(isl) == 0:
        return isl
    out = isl.copy()
    gi = out["giris_i"].to_numpy(np.int64)
    sira = np.argsort(np.where(gi >= 0, gi, np.iinfo(np.int64).max), kind="stable")
    durum = out["durum"].to_numpy(np.int8).copy()
    ci = out["cikis_i"].to_numpy(np.int64)
    nd = out["neden"].to_numpy(np.int64)
    serbest = 0
    engel = np.zeros(len(out), dtype=bool)
    for k in sira:
        if durum[k] != 0:
            continue
        if gi[k] < serbest:
            engel[k] = True
            continue
        serbest = ci[k] if (nd[k] in (3, 4, 5, 6) and ci[k] > gi[k]) else ci[k] + 1
    if engel.any():
        out.loc[engel, "durum"] = 1
        for c in _SONUC_ALANI:
            if c in out:
                out.loc[engel, c] = np.nan
        for c, v in (("cikis_i", -1), ("cikis_t", -1), ("neden", 0)):
            if c in out:
                out.loc[engel, c] = v
        if "belirsiz" in out:
            out.loc[engel, "belirsiz"] = False
    return out


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
