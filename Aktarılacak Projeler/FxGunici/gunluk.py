#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""FX işlem günü tablosu ve stratejilerin ortak bağlamı.

Bir işlem günü (etiket D) önceki takvim günü 17:00 ET'den D 17:00 ET'ye uzanır.
Bu tablo, her gün için:
  · seans anları (UTC epoch sn): Londra 00:00 / 07:00 / 08:00 / 14:00 / 16:00,
    New York 08:00 / 09:30 / 12:00 / 14:00 / 16:00 / 16:55, günün başı ve sonu;
  · mid O/H/L/C, kapsam (kotasyonlu dakika / 1440), tatil bayrağı (TAKVİMDEN:
    hafta içine düşen 25 Aralık ve 1 Ocak, ve örneklemin iki ucunda tam kapsanmayan
    gün — günün sonundaki veri kapsamından değil, çünkü günün ortasındaki bir karar
    anında günün kapsamı henüz bilinmez);
  · ÖNCEKİ İŞLEM günlerinden bilinenler (zincir tatili atlar; `onceki_zincir`):
    ATR(14, Wilder), ATR'nin son 252 işlem günündeki yüzdeliği, önceki işlem
    gününün aralığı ve yönü, NR4/NR7, önceki işlem günü H/L/C/O;
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
    tatil: np.ndarray               # takvim: 25.12 / 01.01 (hafta içi) ya da örneklem kenarındaki eksik gün
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


#: Döviz piyasasının kapalı olduğu, önceden bilinen günler (ay, gün). Arşivde kapsamı %50'nin altında kalan
#: günlerin hepsi bunlardır ya da örneklemin kenarıdır (ölçüldü: dört paritede aynı küme).
TATIL_TAKVIM = ((12, 25), (1, 1))


def onceki_zincir(h: np.ndarray, l: np.ndarray, c: np.ndarray, o: np.ndarray, tatil: np.ndarray):
    """"Önceki FX işlem günü"nden bilinenler; zincir TATİL GÜNLERİNİ ATLAR.

    Ön kayıt "önceki FX işlem günü"nden (PDH/PDL, pivot, başarısız PDH/PDL) ve "önceki 14 FX işlem gününün
    ATR'si"nden söz eder; tatil (takvimden, K8) işlem günü değildir. Tatil satırı tablodan çıkmaz (o gün işlem
    açılmaz, işaretlenir), ama ertesi günün önceki günü tatilin ince kotasyonu değil, tatilden önceki son işlem
    günüdür. Bir gün için her değer o günden ÖNCEKİ tatil olmayan günlerden kurulur, yani bugünü hiç içermez:
      onceki_h/l/c/o  tatil olmayan son günün H/L/C/O'su
      atr             tatil olmayan günlerin gerçek aralığından (bir önceki tatil olmayan günün kapanışıyla) Wilder
                      ATR(14); tatil olmayan son güne kadar
      atr_yuzdelik    o ATR'nin, tatil olmayan son 252 günün aynı ölçüsü içindeki yüzdeliği (en az 60 gün)
      nr4 / nr7       tatil olmayan son gün, tatil olmayan son 4 / 7 günün en dar aralıklısı mı
    Tatil takvimden önceden bilindiği için zincir ileriye bakmaz."""
    n = len(h)
    idx = np.flatnonzero(~np.asarray(tatil, dtype=bool))
    # p[k]: k'den önceki tatil olmayan son satırın idx içindeki sırası (yoksa −1)
    p = np.searchsorted(idx, np.arange(n), side="left") - 1
    var = p >= 0
    son = np.where(var, idx[np.clip(p, 0, None)], 0)
    def onc(x):
        return np.where(var, x[son], np.nan)
    hs, ls, cs = h[idx], l[idx], c[idx]
    tr = np.empty(len(idx))
    if len(idx):
        tr[0] = hs[0] - ls[0]
        tr[1:] = np.maximum.reduce([hs[1:] - ls[1:], np.abs(hs[1:] - cs[:-1]), np.abs(ls[1:] - cs[:-1])])
    atr_alt = _wilder(tr, 14)                        # alt dizide: o günün kendisi dahil
    atr = np.where(var, atr_alt[np.clip(p, 0, None)] if len(idx) else np.nan, np.nan)
    # Yüzdelik: tatil olmayan günlerin "o günün başındaki ATR"si (atr_alt bir kaydırılmış) dizisinde.
    bas = np.concatenate([[np.nan], atr_alt[:-1]]) if len(idx) else np.array([])
    atr_y = np.full(n, np.nan)
    for k in range(n):
        if not var[k] or np.isnan(atr[k]):
            continue
        q = p[k] + 1                                  # bu günün ATR'si alt dizide q'ncu günün başındakidir
        g = bas[max(0, q - 252):q]
        g = g[~np.isnan(g)]
        if len(g) >= 60:
            atr_y[k] = (g < atr[k]).mean()
    aralik = hs - ls
    def nr(m):
        out = np.zeros(n, dtype=bool)
        for k in range(n):
            q = p[k]
            if q + 1 >= m:
                pen = aralik[q + 1 - m:q + 1]
                out[k] = aralik[q] <= pen.min() + 1e-9
        return out
    return onc(h), onc(l), onc(c), onc(o), atr, atr_y, nr(4), nr(7)


def gunluk_kur(d: Dakika, orneklem: tuple | None = None) -> Gunluk:
    """`orneklem`: (başlangıç, bitiş) UTC takvim günleri (iki uç dahil); bu pencerenin içinde baştan sona
    kapsanmayan işlem günü (ilk günün 17:00 ET başı pencereden önce, son günün sonu pencereden sonra) tatil
    sayılır — pencerenin kenarı bir ayardır, fiyat verisinden okunmaz."""
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
    an = {}
    for ad, (saat, bolge) in SEANSLAR.items():
        an[ad] = yerel_an_sn(gun, saat, bolge)
    gun_basi = yerel_an_sn(gun, "17:00", z.NEWYORK, onceki_gun=True)
    tarihler = pd.DatetimeIndex(gun.astype("datetime64[ns]"))
    tatil = np.array([(t.month, t.day) in TATIL_TAKVIM for t in tarihler], dtype=bool)
    if orneklem is not None:
        bas, bit = orneklem
        bas_sn = int(pd.Timestamp(bas, tz="UTC").timestamp())
        bit_sn = int(pd.Timestamp(bit, tz="UTC").timestamp()) + 86400      # bitiş günü dahil
        gun_sonu_sn = yerel_an_sn(gun, "17:00", z.NEWYORK)
        tatil |= (gun_basi < bas_sn) | (gun_sonu_sn > bit_sn)
    onc_h, onc_l, onc_c, onc_o, atr, atr_y, nr4, nr7 = onceki_zincir(h, l, c, o, tatil)
    # Ay sonu = ayın SON LONDRA İŞ GÜNÜ (ön kayıt [fiks]): hafta içi ve İngiltere resmî tatili değil.
    # Ayın son hafta içi günü bir Londra tatiline düşerse (2018-03 ve 2024-03 Paskalya cuması,
    # 2020-08 ve 2026-08 ağustos tatili, 2021-05 mayıs tatili) ay sonu bir önceki iş günüdür.
    # Takvim kural olduğu için pencerenin son günü de sorulabilir (veri yoksa bile kural bilinir).
    ay_sonu = np.array([z.londra_ay_sonu(t.date()) for t in tarihler], dtype=bool)
    dst_rejim = np.array([z.dst_rejimi(t.date()) for t in tarihler], dtype=object)
    dst_hafta = np.array([z.dst_gecis_haftasi(t.date()) for t in tarihler])
    sinir_i = np.searchsorted(d.t, an["ny_1655"], side="left")
    g = Gunluk(gun, i0, i1, o, h, l, c, kapsam, tatil, an, atr, atr_y,
               onc_h, onc_l, onc_c, onc_o, nr4, nr7, ay_sonu, dst_rejim, dst_hafta, hg,
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


def _gun_basinda_bilinen(olaylar: pd.DataFrame, t0: np.ndarray, j: np.ndarray, gun_basi: np.ndarray) -> np.ndarray:
    """Olay, işlem gününün başında takvimden bilinir mi: planlanmış olay her zaman; önceden duyurulmayan olay
    (takvim.olaganustu) yalnız anı günün başında ya da öncesindeyse. j < 0 (tablo dışı gün) için sonuç önemsizdir."""
    import takvim
    bas = np.full(len(j), np.iinfo(np.int64).max, dtype=np.int64)
    ic = j >= 0
    bas[ic] = gun_basi[j[ic]]
    return ~takvim.olaganustu(olaylar) | (t0 <= bas)


def baglam_kur(d: Dakika, olaylar: pd.DataFrame | None = None, pencere_dk=(-2, 15),
               orneklem: tuple | None = None) -> Baglam:
    g = gunluk_kur(d, orneklem)
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
        # "Büyük olay günü" bir koşul değişkenidir: günün ilk sinyalinden önce bilinmelidir. Önceden duyurulmayan bir
        # karar ancak olduğu anda bilinir ve günü yalnız FX gününün başında (önceki gün 17:00 New York) çoktan
        # olmuşsa işaretler. Haber penceresi (maliyet) bu ayrımı yapmaz: o dakikalar olay anının kendisidir.
        bilinen = _gun_basinda_bilinen(olaylar, t0, j, g.gun_basi)
        haber_gun[j[(j >= 0) & bilinen]] = True
    return Baglam(d, g, {}, {}, haber, haber_gun, olaylar if olaylar is not None else pd.DataFrame())
