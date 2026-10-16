#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Arşivden işlem motorunun dizilerine: 1 dakikalık bid/ask/mid ve mumlar.

Birim: bütün fiyatlar NOKTA cinsinden (EURUSD 1 nokta = 0,00001; JPY'li
paritelerde 0,001); pip = 10 nokta. Motor tamsayı ya da yarım nokta (mid)
üzerinde çalışır, pipe yalnız raporda çevrilir — kayan nokta yuvarlaması bir
stop'u bir noktadan kaçırmasın.

Mumlar mid'den kurulur ve ÇIPALIDIR: bir mumun sınırı, `ofset_dk` kadar
kaydırılmış UTC ızgarasıdır. 5 ve 15 dakikada ofset 0 her seans saatini
(Londra 08:00, New York 08:30 ve 09:30) zaten sınıra oturtur; 60 dakikada New
York 08:30 / 09:30 için ofset 30, ECB için 15 ya da 45 gerekir. Bir strateji
mumlarını kendi olay saatine çıpalı ızgaradan alır.
"""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd

import ayar as ay
import dukascopy as dk
import zaman as z


@dataclass
class Dakika:
    cift: str
    pip: int                    # bir pipteki nokta (10)
    t: np.ndarray               # int64 epoch sn, dakikanın başı (UTC)
    bo: np.ndarray; bh: np.ndarray; bl: np.ndarray; bc: np.ndarray   # bid (nokta, float64)
    ao: np.ndarray; ah: np.ndarray; al: np.ndarray; ac: np.ndarray   # ask
    mo: np.ndarray; mh: np.ndarray; ml: np.ndarray; mc: np.ndarray   # mid
    v: np.ndarray               # Dukascopy hacmi (likidite; işlem hacmi DEĞİL)
    gun: np.ndarray             # FX işlem günü etiketi (datetime64[D])

    def __len__(self) -> int:
        return len(self.t)

    def dilim(self, son_t: int) -> "Dakika":
        """`son_t`'den ÖNCEKİ dakikalar (lookahead sınaması için kırpma)."""
        n = int(np.searchsorted(self.t, son_t, side="left"))
        return Dakika(self.cift, self.pip, *(getattr(self, a)[:n] for a in
                      ("t", "bo", "bh", "bl", "bc", "ao", "ah", "al", "ac", "mo", "mh", "ml", "mc", "v", "gun")))


def oku(cift: str, a: ay.Ayar | None = None) -> Dakika:
    a = a or ay.oku()
    ham = dk.oku_ham(ay.DUKA, cift)
    bas = int(pd.Timestamp(a.baslangic, tz="UTC").timestamp())
    bit = int((pd.Timestamp(a.bitis, tz="UTC") + pd.Timedelta(days=1)).timestamp())
    ham = ham[(ham["t"] >= bas) & (ham["t"] < bit)].reset_index(drop=True)
    t = ham["t"].to_numpy(np.int64)
    b = {x: ham[f"b_{x}"].to_numpy(np.float64) for x in "ohlc"}
    k = {x: b[x] + ham[f"d_{x}"].to_numpy(np.float64) for x in "ohlc"}
    m = {x: (b[x] + k[x]) / 2.0 for x in "ohlc"}
    # Mid'in yüksek/düşüğü, bid ve ask uçlarının ortalamasıdır (aynı anda oluşmamış
    # olabilirler); mid açılış/kapanış ile tutarsız kalmasın diye zarf olarak kurulur.
    m["h"] = np.maximum(m["h"], np.maximum(m["o"], m["c"]))
    m["l"] = np.minimum(m["l"], np.minimum(m["o"], m["c"]))
    gun = z.islem_gunu(pd.to_datetime(t, unit="s", utc=True)).to_numpy().astype("datetime64[D]")
    return Dakika(cift, a.nokta_pip(cift), t, b["o"], b["h"], b["l"], b["c"], k["o"], k["h"], k["l"], k["c"],
                  m["o"], m["h"], m["l"], m["c"], ham["b_v"].to_numpy(np.float64) + ham["a_v"].to_numpy(np.float64),
                  gun)


@dataclass
class Mumlar:
    tf: int                     # dakika
    ofset: int                  # dakika
    bt: np.ndarray              # mum başlangıcı (epoch sn)
    o: np.ndarray; h: np.ndarray; l: np.ndarray; c: np.ndarray       # mid
    n: np.ndarray               # mumdaki kotasyonlu dakika sayısı
    i0: np.ndarray; i1: np.ndarray  # ilk ve son dakikanın dizini (dahil)
    gun: np.ndarray             # FX işlem günü etiketi (mum başlangıcına göre)

    def __len__(self) -> int:
        return len(self.bt)

    @property
    def kapanis(self) -> np.ndarray:
        """Mumun nominal kapanış anı (sinyal bu anda bilinir)."""
        return self.bt + self.tf * 60


def mumla(d: Dakika, tf: int, ofset: int = 0) -> Mumlar:
    if 60 % tf and tf % 60:
        raise ValueError(f"desteklenmeyen tf: {tf}")
    if not 0 <= ofset < tf:
        ofset = ofset % tf
    adim = tf * 60
    kimlik = (d.t - ofset * 60) // adim
    sinir = np.flatnonzero(np.diff(kimlik)) + 1
    i0 = np.concatenate([[0], sinir]).astype(np.int64)
    i1 = np.concatenate([sinir - 1, [len(d.t) - 1]]).astype(np.int64)
    bt = kimlik[i0] * adim + ofset * 60
    o = d.mo[i0]
    c = d.mc[i1]
    h = np.maximum.reduceat(d.mh, i0)
    l = np.minimum.reduceat(d.ml, i0)
    gun = z.islem_gunu(pd.to_datetime(bt, unit="s", utc=True)).to_numpy().astype("datetime64[D]")
    return Mumlar(tf, ofset, bt.astype(np.int64), o, h, l, c, (i1 - i0 + 1).astype(np.int64), i0, i1, gun)


def bar_son_dakika(d: Dakika, m: Mumlar) -> np.ndarray:
    """Her dakika için: bir mumun SON dakikası mı (kapanış stop'u o dakikanın kapanışında sorulur)."""
    son = np.zeros(len(d.t), dtype=np.bool_)
    son[m.i1] = True
    return son


def yerel_an_sn(gunler: np.ndarray, saat: str, bolge, onceki_gun: bool = False) -> np.ndarray:
    """İşlem günü etiketleri için yerel duvar saatinin UTC epoch saniyesi.

    `onceki_gun=True`: saat, etiketten bir önceki takvim gününe aittir; FX
    gününün başlangıcı (önceki gün 17:00 ET) için kullanılır.
    """
    g = pd.DatetimeIndex(gunler.astype("datetime64[ns]"))
    if onceki_gun:
        g = g - pd.Timedelta(days=1)
    return z.yerel_utc(g, saat, bolge).as_unit("s").asi8


def ilk_dakika(d: Dakika, an_sn: np.ndarray) -> np.ndarray:
    """Her an için o andan itibaren ilk kotasyonlu dakikanın dizini (yoksa len)."""
    return np.searchsorted(d.t, an_sn, side="left")


def mum_dizini(m: Mumlar, an_sn: np.ndarray) -> np.ndarray:
    """Her an için o anda BAŞLAYAN mumun dizini; o anda başlayan mum yoksa −1."""
    j = np.searchsorted(m.bt, an_sn, side="left")
    j = np.minimum(j, len(m.bt) - 1)
    return np.where(m.bt[j] == an_sn, j, -1)
