#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""On bir strateji ailesinin SİNYAL kuralları (kurallar: onkayit.toml).

Her fonksiyon `(sinyal tablosu, ofset)` döner; ofset, mumların çıpasıdır (60
dakikada New York 09:30 için 30). Sinyal tablosunun sözleşmesi
`strat_ortak.py` başlığında. Kurallar yalnız mum KAPANIŞLARINI ve o ana kadar
bilinen seviyeleri kullanır; giriş daima sonraki mumun açılışıdır (ortak katman
sınar).
"""
from __future__ import annotations

import numpy as np
import pandas as pd
from numba import njit

from gunluk import Baglam
from strat_ortak import atr_mum, gun_mum_araligi, ilk_dogru, wilder
from veri import mum_dizini

LON = {"10:00": "lon_1000", "11:00": "lon_1100", "12:00": "lon_1200", "14:00": "lon_1400"}
NY = {"12:00": "ny_1200", "14:00": "ny_1400", "16:00": "ny_1600", "16:55": "ny_1655"}
SUTUN = ["gun_k", "s", "yon", "stop", "yapi", "ust", "alt"]

def mum_gunu(b: Baglam, m) -> np.ndarray:
    """Her mumun işlem günü sırası (Gunluk'ta yoksa −1). Mum nesnesinde önbellekli (mum tek bağlama aittir)."""
    if "gun_k" not in m.ek:
        m.ek["gun_k"] = b.g.indeks(m.gun)
    return m.ek["gun_k"]


def _tablo(satir, sutun=SUTUN, **ek) -> pd.DataFrame:
    df = pd.DataFrame(satir, columns=sutun)
    for k, v in ek.items():
        df[k] = v
    return df


def _aralik_kirilimi(b, m, tf, ust, alt, a_sn, b_sn, stop_yeri, gunler):
    """Ortak çekirdek: her gün [a, b) penceresinde aralığın DIŞINDA kapanan ilk mum."""
    j0, j1 = gun_mum_araligi(m, a_sn, b_sn, tf)
    satir = []
    for k in gunler:
        H, L = ust[k], alt[k]
        if not (np.isfinite(H) and np.isfinite(L)) or H <= L:
            continue
        c = m.c[j0[k]:j1[k]]
        i = ilk_dogru((c > H) | (c < L))
        if i < 0:
            continue
        s = j0[k] + i
        yon = 1 if c[i] > H else -1
        stop = (L if yon == 1 else H) if stop_yeri == "karsi_uc" else (H + L) / 2.0
        satir.append((k, s, yon, stop, H - L, H, L))
    return _tablo(satir)


# ───────────────────────────────────────────── 1 · London ORB
def orb(b: Baglam, tf: int, son_giris_londra: str, stop_yeri: str):
    m = b.mumlar(tf, 0)
    g = b.g
    t0 = g.an["lon_0800"]
    r = mum_dizini(m, t0)
    ust = np.full(len(g), np.nan)
    alt = np.full(len(g), np.nan)
    ok = (~g.tatil) & (r >= 0)
    ri = r[ok]
    dolu = m.n[ri] >= max(1, tf // 2)
    kk = np.flatnonzero(ok)[dolu]
    ust[kk], alt[kk] = m.h[r[kk]], m.l[r[kk]]
    sin = _aralik_kirilimi(b, m, tf, ust, alt, t0 + tf * 60, g.an[LON[son_giris_londra]], stop_yeri, kk)
    return sin, 0


# ───────────────────────────────────────────── 2 · Asya aralığı
def asya(b: Baglam, tf: int, aralik_sonu_londra: str, stop_yeri: str, son_giris_londra: str):
    m = b.mumlar(tf, 0)
    g = b.g
    ust, alt = g.asya_h[aralik_sonu_londra], g.asya_l[aralik_sonu_londra]
    kk = np.flatnonzero((~g.tatil) & np.isfinite(ust))
    sin = _aralik_kirilimi(b, m, tf, ust, alt, g.an["lon_0800"], g.an[LON[son_giris_londra]], stop_yeri, kk)
    return sin, 0


# ───────────────────────────────────────────── 3 · NY Initial Balance
def nyib(b: Baglam, tf: int, baslangic_et: str, ib_pencere: str, stop_yeri: str, son_giris_et: str):
    ofset = 30 if baslangic_et == "09:30" else 0
    m = b.mumlar(tf, ofset)
    g, d = b.g, b.d
    ts = g.an["ny_0930" if baslangic_et == "09:30" else "ny_0800"]
    W = tf if ib_pencere == "tf" else 60
    a = np.searchsorted(d.t, ts, side="left")
    e = np.searchsorted(d.t, ts + W * 60, side="left")
    ust = np.full(len(g), np.nan)
    alt = np.full(len(g), np.nan)
    for k in range(len(g)):
        if g.tatil[k] or e[k] - a[k] < max(1, W // 2):
            continue
        ust[k], alt[k] = d.mh[a[k]:e[k]].max(), d.ml[a[k]:e[k]].min()
    kk = np.flatnonzero(np.isfinite(ust))
    sin = _aralik_kirilimi(b, m, tf, ust, alt, ts + W * 60, g.an[NY[son_giris_et]], stop_yeri, kk)
    return sin, ofset


# ───────────────────────────────────────────── 4 · Inside bar
def icmum(b: Baglam, tf: int, referans: str, gecerlilik: int, seans: str):
    m = b.mumlar(tf, 0)
    g = b.g
    bk = mum_gunu(b, m)
    h, l, c = m.h, m.l, m.c
    ic = np.zeros(len(m), dtype=bool)
    ic[1:] = (h[1:] < h[:-1]) & (l[1:] > l[:-1]) & (bk[1:] == bk[:-1]) & (bk[1:] >= 0)
    lo = g.an["lon_0800"] if seans == "londra_ny" else g.gun_basi
    hi = g.an["ny_1200"] if seans == "londra_ny" else g.an["ny_1600"]
    satir, gorulen = [], set()
    for i in np.flatnonzero(ic):
        k = bk[i]
        if g.tatil[k] or m.bt[i - 1] < lo[k]:
            continue
        rh, rl = (h[i], l[i]) if referans == "ic" else (h[i - 1], l[i - 1])
        yon = 0
        for off in range(1, gecerlilik + 1):
            s = i + off
            if s >= len(m) or bk[s] != k or m.bt[s] + tf * 60 > hi[k]:
                break
            if c[s] > rh:
                yon = 1
                break
            if c[s] < rl:
                yon = -1
                break
        if yon == 0 or s in gorulen:
            continue
        gorulen.add(s)
        satir.append((k, s, yon, rl if yon == 1 else rh, rh - rl, rh, rl))
    return _tablo(satir), 0


# ───────────────────────────────────────────── 5 · BB/KC sıkışması
def sikisma(b: Baglam, tf: int, sure: int, yon: str, stop_yeri: str):
    m = b.mumlar(tf, 0)
    g = b.g
    bk = mum_gunu(b, m)
    c = pd.Series(m.c)
    sma = c.rolling(20).mean().to_numpy()
    sd = c.rolling(20).std(ddof=0).to_numpy()
    ema = c.ewm(span=20, adjust=False).mean().to_numpy()
    onceki = np.concatenate([[m.c[0]], m.c[:-1]])
    tr = np.maximum.reduce([m.h - m.l, np.abs(m.h - onceki), np.abs(m.l - onceki)])
    atr20 = wilder(tr.astype(np.float64), 20)
    sq = (sma + 2 * sd < ema + 1.5 * atr20) & (sma - 2 * sd > ema - 1.5 * atr20)
    sq = np.nan_to_num(sq, nan=False).astype(bool)
    d_ = np.diff(np.concatenate([[0], sq.astype(np.int8), [0]]))
    basl, son = np.flatnonzero(d_ == 1), np.flatnonzero(d_ == -1)      # son: ilk sıkışmasız mum
    hi = g.an["ny_1600"]
    satir = []
    for a, r in zip(basl, son):
        if r - a < sure or r >= len(m):
            continue
        H, L = m.h[a:r].max(), m.l[a:r].min()
        s, yn = -1, 0
        if yon == "kutu":
            for q in range(r, min(r + 5, len(m))):
                if m.c[q] > H:
                    s, yn = q, 1
                    break
                if m.c[q] < L:
                    s, yn = q, -1
                    break
        else:
            if m.c[r] > sma[r]:
                s, yn = r, 1
            elif m.c[r] < sma[r]:
                s, yn = r, -1
        if s < 0:
            continue
        k = bk[s]
        if k < 0 or g.tatil[k] or m.bt[s] + tf * 60 > hi[k]:
            continue
        stop = (L if yn == 1 else H) if stop_yeri == "karsi_uc" else (H + L) / 2.0
        if (m.c[s] - stop) * yn <= 0:
            continue
        satir.append((k, s, yn, stop, H - L, H, L))
    return _tablo(satir), 0


# ───────────────────────────────────────────── 6 · PDH/PDL
def pdhl(b: Baglam, tf: int, baslangic: str, stop_kurali: str):
    m = b.mumlar(tf, 0)
    g = b.g
    atr = atr_mum(m, 14)
    lo = g.gun_basi if baslangic == "gun_basi" else g.an["lon_0800"]
    j0, j1 = gun_mum_araligi(m, lo, g.an["ny_1400"], tf)
    satir = []
    for k in np.flatnonzero(~g.tatil):
        H, L = g.onceki_h[k], g.onceki_l[k]
        if not np.isfinite(H) or j0[k] < 1 or j1[k] <= j0[k]:
            continue
        c = m.c[j0[k]:j1[k]]
        p = m.c[j0[k] - 1:j1[k] - 1]
        i = ilk_dogru(((c > H) & (p <= H)) | ((c < L) & (p >= L)))
        if i < 0:
            continue
        s = j0[k] + i
        yon = 1 if c[i] > H else -1
        if stop_kurali == "sinyal_mumu":
            stop = m.l[s] if yon == 1 else m.h[s]
        else:
            stop = (H - 0.5 * atr[s]) if yon == 1 else (L + 0.5 * atr[s])
        satir.append((k, s, yon, stop, H - L, H, L))
    return _tablo(satir), 0


# ───────────────────────────────────────────── 7 · Başarısız kırılım
def sahte(b: Baglam, tf: int, seviye: str, pencere: int):
    m = b.mumlar(tf, 0)
    g = b.g
    if seviye == "orb":
        r = mum_dizini(m, g.an["lon_0800"])
        ust = np.where(r >= 0, m.h[np.clip(r, 0, len(m) - 1)], np.nan)
        alt = np.where(r >= 0, m.l[np.clip(r, 0, len(m) - 1)], np.nan)
        a_sn, b_sn = g.an["lon_0800"] + tf * 60, g.an["lon_1400"]
    elif seviye == "asya":
        ust, alt = g.asya_h["08:00"], g.asya_l["08:00"]
        a_sn, b_sn = g.an["lon_0800"], g.an["lon_1400"]
    else:
        ust, alt = g.onceki_h, g.onceki_l
        a_sn, b_sn = g.an["lon_0800"], g.an["ny_1400"]
    j0, j1 = gun_mum_araligi(m, a_sn, b_sn, tf)
    satir = []
    for k in np.flatnonzero(~g.tatil):
        H, L = ust[k], alt[k]
        if not (np.isfinite(H) and np.isfinite(L)) or j0[k] < 1:
            continue
        bulundu = False
        for j in range(j0[k], j1[k]):
            p = m.c[j - 1]
            if m.c[j] > H and p <= H:
                for q in range(j + 1, min(j + 1 + pencere, j1[k])):
                    if m.c[q] < H:
                        satir.append((k, q, -1, m.h[j:q + 1].max(), H - L, H, L))
                        bulundu = True
                        break
            elif m.c[j] < L and p >= L:
                for q in range(j + 1, min(j + 1 + pencere, j1[k])):
                    if m.c[q] > L:
                        satir.append((k, q, 1, m.l[j:q + 1].min(), H - L, H, L))
                        bulundu = True
                        break
            if bulundu:
                break
    return _tablo(satir), 0


# ───────────────────────────────────────────── 8 · VWAP
def vwap_dakika(b: Baglam, capa: str):
    """Çapadan beri dakika dakika VWAP ve hacim ağırlıklı σ; çapa öncesi NaN."""
    anahtar = ("vwap", capa)
    if anahtar in b.ek:
        return b.ek[anahtar]
    d, g = b.d, b.g
    t_capa = g.gun_basi if capa == "fx_gunu" else g.an["lon_0800"]
    a = np.searchsorted(d.t, t_capa, side="left")
    e = g.i1 + 1
    seg = np.full(len(d), -1, dtype=np.int64)
    for k in range(len(g)):
        if e[k] > a[k]:
            seg[a[k]:e[k]] = k
    tp = (d.mh + d.ml + d.mc) / 3.0
    v = np.where(d.v > 0, d.v, 0.0)
    df = pd.DataFrame({"seg": seg, "pv": tp * v, "p2v": tp * tp * v, "v": v})
    gr = df[df["seg"] >= 0].groupby("seg")
    cpv, cp2v, cv = (gr[x].cumsum() for x in ("pv", "p2v", "v"))
    vw = np.full(len(d), np.nan)
    sg = np.full(len(d), np.nan)
    ix = cpv.index.to_numpy()
    with np.errstate(invalid="ignore", divide="ignore"):
        ort = cpv.to_numpy() / cv.to_numpy()
        var = cp2v.to_numpy() / cv.to_numpy() - ort * ort
    vw[ix] = ort
    sg[ix] = np.sqrt(np.maximum(var, 0.0))
    b.ek[anahtar] = (vw, sg, t_capa)
    return b.ek[anahtar]


@njit(cache=True)
def _vwap_donus_tara(c, h, l, vw, sg, bk, ok, k):
    n = len(c)
    out_s = np.empty(n, np.int64); out_y = np.empty(n, np.int8)
    out_st = np.empty(n); out_lv = np.empty(n)
    m = 0
    durum = 0
    uc = 0.0
    for j in range(n):
        if j == 0 or bk[j] != bk[j - 1]:
            durum = 0
        if not ok[j] or np.isnan(vw[j]) or not (sg[j] > 0.0):
            durum = 0
            continue
        ust = vw[j] + k * sg[j]
        alt = vw[j] - k * sg[j]
        if durum == 0:
            if c[j] > ust:
                durum = 1; uc = h[j]
            elif c[j] < alt:
                durum = -1; uc = l[j]
        elif durum == 1:
            if h[j] > uc:
                uc = h[j]
            if c[j] <= ust:
                out_s[m] = j; out_y[m] = -1; out_st[m] = uc; out_lv[m] = vw[j]; m += 1
                durum = 0
        else:
            if l[j] < uc:
                uc = l[j]
            if c[j] >= alt:
                out_s[m] = j; out_y[m] = 1; out_st[m] = uc; out_lv[m] = vw[j]; m += 1
                durum = 0
    return out_s[:m], out_y[:m], out_st[:m], out_lv[:m]


@njit(cache=True)
def _vwap_cekilme_tara(c, h, l, vw, bk, ok, n_trend):
    n = len(c)
    out_s = np.empty(n, np.int64); out_y = np.empty(n, np.int8); out_st = np.empty(n)
    m = 0
    yuk = 0
    dus = 0
    for j in range(n):
        if j == 0 or bk[j] != bk[j - 1] or not ok[j] or np.isnan(vw[j]):
            yuk = 0; dus = 0
            if not ok[j] or np.isnan(vw[j]):
                continue
        if yuk >= n_trend and l[j] <= vw[j] and c[j] > vw[j]:
            out_s[m] = j; out_y[m] = 1; out_st[m] = l[j]; m += 1
        elif dus >= n_trend and h[j] >= vw[j] and c[j] < vw[j]:
            out_s[m] = j; out_y[m] = -1; out_st[m] = h[j]; m += 1
        yuk = yuk + 1 if c[j] > vw[j] else 0
        dus = dus + 1 if c[j] < vw[j] else 0
    return out_s[:m], out_y[:m], out_st[:m]


def _vwap_mum(b: Baglam, tf: int, capa: str):
    m = b.mumlar(tf, 0)
    g = b.g
    bk = mum_gunu(b, m)
    vw, sg, t_capa = vwap_dakika(b, capa)
    vwb, sgb = vw[m.i1], sg[m.i1]
    kk = np.clip(bk, 0, len(g) - 1)
    ok = (bk >= 0) & (m.bt >= t_capa[kk] + 3600) & (m.bt + tf * 60 <= g.an["ny_1600"][kk]) & (~g.tatil[kk])
    return m, bk, vwb, sgb, ok


def vwap_donus(b: Baglam, tf: int, capa: str, k: float):
    m, bk, vwb, sgb, ok = _vwap_mum(b, tf, capa)
    s, y, st, lv = _vwap_donus_tara(m.c, m.h, m.l, vwb, sgb, bk, ok, float(k))
    df = pd.DataFrame({"gun_k": bk[s], "s": s, "yon": y.astype(np.int64), "stop": st,
                       "yapi": np.abs(m.c[s] - st), "ust": vwb[s] + k * sgb[s], "alt": vwb[s] - k * sgb[s],
                       "seviye": lv})
    return df, 0


def vwap_cekilme(b: Baglam, tf: int, capa: str, n: int):
    m, bk, vwb, sgb, ok = _vwap_mum(b, tf, capa)
    s, y, st = _vwap_cekilme_tara(m.c, m.h, m.l, vwb, bk, ok, int(n))
    df = pd.DataFrame({"gun_k": bk[s], "s": s, "yon": y.astype(np.int64), "stop": st,
                       "yapi": np.abs(m.c[s] - st), "ust": vwb[s], "alt": vwb[s]})
    return df, 0


# ───────────────────────────────────────────── 9 · Floor pivot
def pivot(b: Baglam, tf: int, seviye: str, tur: str):
    m = b.mumlar(tf, 0)
    g = b.g
    P = (g.onceki_h + g.onceki_l + g.onceki_c) / 3.0
    R1, S1 = 2 * P - g.onceki_l, 2 * P - g.onceki_h
    j0, j1 = gun_mum_araligi(m, g.an["lon_0800"], g.an["ny_1400"], tf)
    h, l, c = m.h, m.l, m.c
    satir = []
    for k in np.flatnonzero((~g.tatil) & np.isfinite(P)):
        if j0[k] < 1:
            continue
        adaylar = [("P", P[k])] if seviye == "P" else [("R1", R1[k]), ("S1", S1[k])]
        for ad, lv in adaylar:
            for j in range(j0[k], j1[k]):
                p = c[j - 1]
                if tur == "donus":
                    if ad == "R1" and h[j] >= lv and c[j] < lv and p < lv:
                        satir.append((k, j, -1, h[j], abs(c[j] - h[j]), R1[k], P[k], P[k])); break
                    if ad == "S1" and l[j] <= lv and c[j] > lv and p > lv:
                        satir.append((k, j, 1, l[j], abs(c[j] - l[j]), P[k], S1[k], P[k])); break
                    if ad == "P" and l[j] <= lv and c[j] > lv and p > lv:
                        satir.append((k, j, 1, l[j], abs(c[j] - l[j]), R1[k], P[k], R1[k])); break
                    if ad == "P" and h[j] >= lv and c[j] < lv and p < lv:
                        satir.append((k, j, -1, h[j], abs(c[j] - h[j]), P[k], S1[k], S1[k])); break
                else:
                    if ad in ("R1", "P") and c[j] > lv and p <= lv:
                        satir.append((k, j, 1, l[j], abs(c[j] - l[j]), lv, lv, np.nan)); break
                    if ad in ("S1", "P") and c[j] < lv and p >= lv:
                        satir.append((k, j, -1, h[j], abs(c[j] - h[j]), lv, lv, np.nan)); break
    return _tablo(satir, SUTUN + ["seviye"]), 0


# ───────────────────────────────────────────── 10 · WM/R fiksingi
def fiks(b: Baglam, tf: int, tur: str, gecikme_mum: int, tutma_mum: int):
    m = b.mumlar(tf, 0)
    g, d = b.g, b.d
    atr = atr_mum(m, 14)
    F = g.an["lon_1600"]
    adim = tf * 60
    if tur == "momentum":
        sig = mum_dizini(m, F - 2 * adim)
        ent = mum_dizini(m, F - adim)
        cik_t = F
        isaret = 1
    else:
        sig = mum_dizini(m, F - adim)
        ent = mum_dizini(m, F + gecikme_mum * adim)
        cik_t = F + (gecikme_mum + tutma_mum) * adim
        isaret = -1
    cik = np.searchsorted(d.t, cik_t, side="left")
    satir = []
    for k in np.flatnonzero(~g.tatil):
        s, e = sig[k], ent[k]
        if s < 0 or e < 0 or e <= s:
            continue
        # Ön kayıt: "R birimi girişteki ATR(14, tf); 'sert'/'kapanis' stop 1·ATR". Girişteki ATR girişten önce
        # kapanan son mumundur (gecikmesiz girişte sinyal mumu) ve stop GİRİŞTEN 1·ATR uzaktadır. Tablo stop
        # SEVİYESİ taşımaz, yalnız riski: motor stop'u yürütülen girişten (kayma ve makas dahil) 1·ATR uzağa koyar,
        # yani R üç stop türünde de tam ATR'dir. Seviye sinyal kapanışından ölçülseydi, girişi bir mum geciken
        # dönüşte fiyat o mumda stop'a yaklaşabilir ve planlanan risk birkaç pipe inerdi.
        a = atr[e - 1]
        if not np.isfinite(a) or a <= 0:
            continue
        hareket = m.c[s] - m.o[s]
        if hareket == 0:
            continue
        yon = isaret * (1 if hareket > 0 else -1)
        gi = int(m.i0[e])
        satir.append((k, s, yon, np.nan, abs(hareket), m.h[s], m.l[s], a,
                      gi, int(cik[k]), bool(g.ay_sonu[k])))
    return _tablo(satir, SUTUN + ["risk", "giris_i", "cikis_i", "ay_sonu"]), 0


# ───────────────────────────────────────────── 11 · Gün içi momentum
def momentum(b: Baglam, tf: int, cikis_et: str):
    m = b.mumlar(tf, 0)
    g, d = b.g, b.d
    m60 = b.mumlar(60, 0)
    atr60 = atr_mum(m60, 14)
    sig = mum_dizini(m, g.an["lon_0800"])
    gir = np.searchsorted(d.t, g.an["ny_1200"], side="left")
    cik = np.searchsorted(d.t, g.an[NY[cikis_et]], side="left")
    j60 = np.searchsorted(m60.bt + 3600, g.an["ny_1200"], side="right") - 1
    satir = []
    for k in np.flatnonzero(~g.tatil):
        s = sig[k]
        if s < 0 or m.n[s] < max(1, tf // 2) or j60[k] < 0 or not np.isfinite(atr60[j60[k]]):
            continue
        if gir[k] >= len(d.t) or d.t[gir[k]] >= g.an["ny_1400"][k] or cik[k] <= gir[k]:
            continue
        hareket = m.c[s] - m.o[s]
        if hareket == 0:
            continue
        yon = 1 if hareket > 0 else -1
        r = atr60[j60[k]]
        # Stop seviyesi yok, yalnız risk: 'sert'/'kapanis' varyantında motor stop'u yürütülen girişten 1·ATR uzağa
        # koyar (fiksingle aynı kural; R üç stop türünde de tam ATR).
        satir.append((k, s, yon, np.nan, abs(hareket), m.h[s], m.l[s], r,
                      int(gir[k]), int(cik[k]), hareket))
    return _tablo(satir, SUTUN + ["risk", "giris_i", "cikis_i", "ilk_hareket"]), 0


AILE = {
    "orb": orb, "asya": asya, "nyib": nyib, "icmum": icmum, "sikisma": sikisma, "pdhl": pdhl,
    "sahte": sahte, "vwap_donus": vwap_donus, "vwap_cekilme": vwap_cekilme, "pivot": pivot,
    "fiks": fiks, "momentum": momentum,
}
# Çıkış parametreleri (sinyal fonksiyonuna gitmez, motora gider)
CIKIS = ("stop_turu", "hedef")
