#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""FX işlem günü tablosu ve stratejilerin ortak bağlamı.

Bir işlem günü (etiket D) önceki takvim günü 17:00 ET'den D 17:00 ET'ye uzanır.
Bu tablo, her gün için:
  · seans anları (UTC epoch sn): Londra 00:00 / 07:00 / 08:00 / 14:00 / 16:00,
    New York 08:00 / 09:30 / 12:00 / 14:00 / 16:00 / 16:55, günün başı ve sonu;
  · mid O/H/L/C, kapsam (kotasyonlu dakika / 1440), tatil bayrağı;
  · ÖNCEKİ günlerden bilinenler: ATR(14, Wilder), ATR'nin son 252 gündeki
    yüzdeliği, önceki günün aralığı ve yönü, NR4/NR7, önceki gün H/L/C;
  · gün içinden, ilgili anda bilinenler: Asya aralığı (Londra 00:00 → 07:00 /
    08:00), Londra açılışı fiyatı ve gece hareketi.
Her alan "o anda bilinebilir mi" kuralına göre kurulur; ATR ve yüzdelik bugünü
HİÇ içermez.
"""
from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np
import pandas as pd

import zaman as z
from veri import Dakika, Mumlar, mumla, bar_son_dakika, yerel_an_sn


def _wilder(x: np.ndarray, n: int) -> np.ndarray:
    """Wilder ortalaması (RMA); ilk n−1 değer NaN."""
    out = np.full(len(x), np.nan)
    if len(x) < n:
        return out
    out[n - 1] = np.nanmean(x[:n])
    for i in range(n, len(x)):
        out[i] = out[i - 1] + (x[i] - out[i - 1]) / n
    return out


def _yuzdelik_izleyen(x: np.ndarray, pencere: int = 252) -> np.ndarray:
    """x[i]'nin x[i−pencere..i−1] içindeki yüzdeliği (0–1); geçmiş yetmezse NaN."""
    out = np.full(len(x), np.nan)
    for i in range(len(x)):
        if i < 60 or np.isnan(x[i]):
            continue
        g = x[max(0, i - pencere):i]
        g = g[~np.isnan(g)]
        if len(g) >= 60:
            out[i] = (g < x[i]).mean()
    return out


SEANSLAR = {
    "lon_0000": ("00:00", z.LONDRA), "lon_0700": ("07:00", z.LONDRA), "lon_0800": ("08:00", z.LONDRA),
    "lon_1000": ("10:00", z.LONDRA), "lon_1100": ("11:00", z.LONDRA), "lon_1200": ("12:00", z.LONDRA),
    "lon_1400": ("14:00", z.LONDRA), "lon_1600": ("16:00", z.LONDRA),
    "ny_0800": ("08:00", z.NEWYORK), "ny_0930": ("09:30", z.NEWYORK), "ny_1200": ("12:00", z.NEWYORK),
    "ny_1400": ("14:00", z.NEWYORK), "ny_1600": ("16:00", z.NEWYORK), "ny_1655": ("16:55", z.NEWYORK),
    "ny_1700": ("17:00", z.NEWYORK),
}


@dataclass
class Gunluk:
    gun: np.ndarray                 # datetime64[D] etiketler (hafta içi)
    i0: np.ndarray                  # günün ilk dakikası
    i1: np.ndarray                  # günün son dakikası (dahil)
    o: np.ndarray; h: np.ndarray; l: np.ndarray; c: np.ndarray
    kapsam: np.ndarray
    tatil: np.ndarray               # kapsam < 0,5
    an: dict                        # seans adı → epoch sn dizisi
    atr: np.ndarray                 # ÖNCEKİ günlerin ATR(14)'ü (bugünü içermez), nokta
    atr_yuzdelik: np.ndarray        # o ATR'nin son 252 gündeki yüzdeliği
    onceki_h: np.ndarray; onceki_l: np.ndarray; onceki_c: np.ndarray; onceki_o: np.ndarray
    nr4: np.ndarray; nr7: np.ndarray
    ay_sonu: np.ndarray
    dst_rejim: np.ndarray           # str
    dst_hafta: np.ndarray           # bool
    hafta_gunu: np.ndarray          # 0 = pazartesi
    gun_basi: np.ndarray            # epoch sn (önceki gün 17:00 ET)
    sinir: np.ndarray               # 16:55 ET dakikasının dizini (gün sonu çıkışı)
    asya_h: dict = field(default_factory=dict)   # aralık sonu ("07:00"/"08:00") → H dizisi
    asya_l: dict = field(default_factory=dict)
    lon_acilis: np.ndarray = None   # Londra 08:00'deki ilk dakikanın mid açılışı

    def __len__(self) -> int:
        return len(self.gun)

    def indeks(self, gunler: np.ndarray) -> np.ndarray:
        """Etiketlerin bu tablodaki sırası (yoksa −1)."""
        j = np.searchsorted(self.gun, gunler)
        j = np.clip(j, 0, len(self.gun) - 1)
        return np.where(self.gun[j] == gunler, j, -1)


def gunluk_kur(d: Dakika) -> Gunluk:
    etiket = d.gun
    sinir = np.flatnonzero(etiket[1:] != etiket[:-1]) + 1
    i0 = np.concatenate([[0], sinir])
    i1 = np.concatenate([sinir - 1, [len(etiket) - 1]])
    gun = etiket[i0]
    hg = (gun.astype("datetime64[D]").view("int64") - 4) % 7      # 1970-01-01 perşembe → 0 = pazartesi
    hafta_ici = hg < 5
    i0, i1, gun, hg = i0[hafta_ici], i1[hafta_ici], gun[hafta_ici], hg[hafta_ici]
    o = d.mo[i0]
    c = d.mc[i1]
    # H/L açık dilimlerle: hafta sonu etiketli dakikalar araya girebildiği için
    # reduceat'in "bir sonraki grubun başına kadar" kuralı burada yanlış olurdu.
    h = np.array([d.mh[a:b + 1].max() for a, b in zip(i0, i1)])
    l = np.array([d.ml[a:b + 1].min() for a, b in zip(i0, i1)])
    kapsam = (i1 - i0 + 1) / 1440.0
    tatil = kapsam < 0.5
    an = {}
    for ad, (saat, bolge) in SEANSLAR.items():
        an[ad] = yerel_an_sn(gun, saat, bolge)
    gun_basi = yerel_an_sn(gun, "17:00", z.NEWYORK, onceki_gun=True)
    # ATR: tatil günleri de kotasyon taşıyorsa hesaba girer; değer bugünü içermez (bir kaydırma).
    tr = np.empty(len(gun))
    tr[0] = h[0] - l[0]
    tr[1:] = np.maximum.reduce([h[1:] - l[1:], np.abs(h[1:] - c[:-1]), np.abs(l[1:] - c[:-1])])
    atr_bugun = _wilder(tr, 14)
    atr = np.concatenate([[np.nan], atr_bugun[:-1]])
    atr_y = _yuzdelik_izleyen(atr)
    onc = lambda x: np.concatenate([[np.nan], x[:-1]])  # noqa: E731
    aralik = h - l
    def nr(n):
        out = np.zeros(len(gun), dtype=bool)
        for i in range(n, len(gun)):
            pen = aralik[i - n:i]
            out[i] = aralik[i - 1] <= pen.min() + 1e-9
        return out
    tarihler = pd.DatetimeIndex(gun.astype("datetime64[ns]"))
    # Ay sonu = ayın SON LONDRA İŞ GÜNÜ (ön kayıt [fiks]): hafta içi ve İngiltere resmî tatili değil.
    # Ayın son hafta içi günü bir Londra tatiline düşerse (2018-03 ve 2024-03 Paskalya cuması,
    # 2020-08 ve 2026-08 ağustos tatili, 2021-05 mayıs tatili) ay sonu bir önceki iş günüdür.
    # Takvim kural olduğu için pencerenin son günü de sorulabilir (veri yoksa bile kural bilinir).
    ay_sonu = np.array([z.londra_ay_sonu(t.date()) for t in tarihler], dtype=bool)
    dst_rejim = np.array([z.dst_rejimi(t.date()) for t in tarihler], dtype=object)
    dst_hafta = np.array([z.dst_gecis_haftasi(t.date()) for t in tarihler])
    sinir_i = np.searchsorted(d.t, an["ny_1655"], side="left")
    g = Gunluk(gun, i0, i1, o, h, l, c, kapsam, tatil, an, atr, atr_y,
               onc(h), onc(l), onc(c), onc(o), nr(4), nr(7), ay_sonu, dst_rejim, dst_hafta, hg,
               gun_basi, sinir_i)
    for son in ("07:00", "08:00"):
        a = np.searchsorted(d.t, an["lon_0000"], side="left")
        b = np.searchsorted(d.t, an["lon_0700" if son == "07:00" else "lon_0800"], side="left")
        H = np.full(len(gun), np.nan)
        L = np.full(len(gun), np.nan)
        for k in range(len(gun)):
            if b[k] - a[k] >= 30:                       # en az 30 kotasyonlu dakika
                H[k] = d.mh[a[k]:b[k]].max()
                L[k] = d.ml[a[k]:b[k]].min()
        g.asya_h[son], g.asya_l[son] = H, L
    j = np.searchsorted(d.t, an["lon_0800"], side="left")
    j = np.clip(j, 0, len(d.t) - 1)
    g.lon_acilis = d.mo[j]
    return g


@dataclass
class Baglam:
    """Bir paritenin bütün stratejilere ortak girdisi."""
    d: Dakika
    g: Gunluk
    mum: dict                       # (tf, ofset) → Mumlar
    son: dict                       # (tf, ofset) → bar_son dakika dizisi
    haber: np.ndarray               # dakika başına haber penceresi bayrağı
    haber_gun: np.ndarray           # işlem günü başına: o gün takvimde büyük olay var mı
    olaylar: pd.DataFrame           # takvim (bu pariteye ilişkin)
    # Türetilmiş tabloların önbelleği (VWAP, EMA, olay çerçevesi). Nesnenin kendisinde
    # durur; id() anahtarlı modül önbelleği kimlik yeniden kullanılınca yanlış pariteyi verirdi.
    ek: dict = field(default_factory=dict, repr=False, compare=False)

    @staticmethod
    def _anahtar(tf: int, ofset: int) -> tuple[int, int]:
        # 5 ve 15 dakikada her seans saati (:00, :15, :30, :45) zaten sınırdadır.
        return (tf, 0) if tf < 60 else (tf, ofset % 60)

    def mumlar(self, tf: int, ofset: int = 0) -> Mumlar:
        anahtar = self._anahtar(tf, ofset)
        if anahtar not in self.mum:
            self.mum[anahtar] = mumla(self.d, anahtar[0], anahtar[1])
            self.son[anahtar] = bar_son_dakika(self.d, self.mum[anahtar])
        return self.mum[anahtar]

    def bar_son(self, tf: int, ofset: int = 0) -> np.ndarray:
        self.mumlar(tf, ofset)
        return self.son[self._anahtar(tf, ofset)]


def baglam_kur(d: Dakika, olaylar: pd.DataFrame | None = None, pencere_dk=(-2, 15)) -> Baglam:
    g = gunluk_kur(d)
    haber = np.zeros(len(d), dtype=np.bool_)
    haber_gun = np.zeros(len(g), dtype=bool)
    if olaylar is not None and len(olaylar):
        t0 = olaylar["utc_sn"].to_numpy(np.int64)
        a = np.searchsorted(d.t, t0 + pencere_dk[0] * 60, side="left")
        b = np.searchsorted(d.t, t0 + pencere_dk[1] * 60, side="left")
        for x, y in zip(a, b):
            haber[x:y] = True
        etiket = z.islem_gunu(pd.to_datetime(t0, unit="s", utc=True)).to_numpy().astype("datetime64[D]")
        j = g.indeks(etiket)
        haber_gun[j[j >= 0]] = True
    return Baglam(d, g, {}, {}, haber, haber_gun, olaylar if olaylar is not None else pd.DataFrame())
