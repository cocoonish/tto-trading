#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Büyük mum — tanım, süzgeçler ve mumdan sonraki yolun ölçüleri (gözlem ve sınama AYNI kodu kullanır).

BÜYÜK MUM: 5, 15 ya da 60 dakikalık bir mumun aralığı (yüksek − düşük), aynı dilimin bir ÖNCEKİ muma kadar ölçülen
ATR(14)'ünün en az 2 katı. ATR, gerçek aralığın (önceki kapanışla boşluk dahil) Wilder ortalamasıdır (α = 1/14;
TradingView `ta.atr` ile aynı); önceki mum bitişik değilse (hafta sonu, tatil) gerçek aralık mumun kendi aralığıdır.
Büyüklük kovası: 2–3 · 3–4 · 4–5 · 5+ ATR. Yön kapanış − açılış; gövdesi aralığın %20'sinden küçük mum "kararsız"dır
ve yön ölçülerine girmez.

Dışarıda kalanlar (sayılır, raporlanır):
- kümenin devamı: önceki 3 mumdan biri de büyükse mum sayılmaz — yalnız kümenin İLK büyük mumu olaydır;
- yeniden açılış: 6 saatten uzun bir boşluktan (hafta sonu, tatil) sonraki ilk 60 dakikada başlayan mum —
  ilk kotasyonlar seyrek ve geniş, aralık fiyatın değil kotasyonun hareketidir;
- devir: New York 16:50–17:10 ile kesişen mum — FX gününün devrinde makas sıçrar ve orta fiyatın aralığını şişirir;
- eksik: mumun ya da izleme penceresinin dakikalarının %80'inden azı kotasyonlu.

Mumdan sonraki yol, mumun kapanışından başlar ve 24 mum boyunca izlenir (5 dk'da 2 saat, 15 dk'da 6 saat,
1 saatte 24 saat). Birimler: A = olayın ATR'si, R = mumun aralığı. Yön y, mumun yönüdür.

Hiçbir süzgeç mum kapandıktan sonraki fiyatı kullanmaz; hepsi mumun kapandığı dakikada bilinir.
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

import sinif as sf

import takvim  # noqa: E402  (sinif FxGunici'yi yola ekler)
import veri as vr  # noqa: E402
import zaman as z  # noqa: E402

DILIMLER = [5, 15, 60]
ATR_N = 14
ESIK = 2.0
KOVALAR = [(2.0, 3.0, "2-3"), (3.0, 4.0, "3-4"), (4.0, 5.0, "4-5"), (5.0, np.inf, "5+")]
KUME_ONCE = 3                     # önceki 3 mumda büyük mum varsa kümenin devamı
KARARSIZ_GOVDE = 0.20
ACILIS_BOSLUK_SN, ACILIS_PAY_SN = 6 * 3600, 3600
DEVIR = ("16:50", "17:10")        # New York
DOLULUK = 0.80
IZLE = 24                         # mum
UFUKLAR = [1, 3, 6, 12, 24]       # mum
SIMETRIK = [0.5, 1.0, 2.0]        # A: kapanıştan ±k·A; hangisi önce
GERI = [0.25, 0.50, 0.62, 1.00]   # mumun ucundan geri çekilme, R cinsinden (1,00 = mumun öbür ucu)
KOSU_MUM, KOSU_ESIK = 12, 2.0     # önceki 12 mumun net hareketi, A cinsinden
ARDISIK_MUM = 24                  # önceki 4–24 mumda büyük mum
GUNLUK_ATR_N, GUNLUK_YUZDELIK_N = 20, 250
MAKAS_ONCE_DK = 60
MAKAS_SONRA = [1, 5, 15, 30]      # dk, mum kapanışından sonra

SUZGECLER = {
    "kova": ["2-3", "3-4", "4-5", "5+"],
    "kapanis": ["uc", "orta", "geri"],
    "seans": ["asya", "londra", "ortusme", "ny"],
    "haber": ["haber", "haber_yok"],
    "trend": ["trendle", "karsi", "yatay"],
    "kosu": ["ayni", "ters", "sakin"],
    "gun_ucu": ["evet", "hayir"],
    "oynaklik": ["dusuk", "orta", "yuksek"],
    "ardisik": ["evet", "hayir"],
}
SUZGEC_AD = {
    "kova": "Büyüklük (ATR katı)", "kapanis": "Kapanışın yeri", "seans": "Seans", "haber": "Takvimdeki büyük haber",
    "trend": "Günlük trend (EMA20)", "kosu": "Mumdan önceki koşu", "gun_ucu": "Günün yeni ucu",
    "oynaklik": "Günlük oynaklık", "ardisik": "Yakın geçmişte başka büyük mum",
}
DEGER_AD = {
    "uc": "uca yakın (≥ %75)", "orta": "ortada (%50–75)", "geri": "geri verilmiş (< %50)",
    "asya": "Asya", "londra": "Londra", "ortusme": "Londra–New York örtüşmesi", "ny": "New York öğleden sonra",
    "haber": "var", "haber_yok": "yok", "trendle": "trend yönünde", "karsi": "trende karşı", "yatay": "trend yatay",
    "ayni": "aynı yönde koşudan sonra", "ters": "ters koşudan sonra", "sakin": "sakin geçmişten",
    "evet": "evet", "hayir": "hayır", "dusuk": "düşük", "yuksek": "yüksek",
    "2-3": "2–3 ATR", "3-4": "3–4 ATR", "4-5": "4–5 ATR", "5+": "5+ ATR",
}


def atr(m: vr.Mumlar) -> np.ndarray:
    """Her mumun KENDİSİ DAHİL Wilder ATR(14)'ü; olay için bir önceki mumun değeri kullanılır."""
    onceki = np.r_[np.nan, m.c[:-1]]
    bitisik = np.r_[False, np.diff(m.bt) == m.tf * 60]
    tr = np.where(bitisik, np.maximum(m.h, onceki) - np.minimum(m.l, onceki), m.h - m.l)
    out = np.full(len(tr), np.nan)
    if len(tr) < ATR_N:
        return out
    a = tr[:ATR_N].mean()
    out[ATR_N - 1] = a
    for i in range(ATR_N, len(tr)):
        a += (tr[i] - a) / ATR_N
        out[i] = a
    return out


def _seans(bt: np.ndarray) -> np.ndarray:
    ts = pd.to_datetime(bt, unit="s", utc=True)
    lon = ts.tz_convert(z.LONDRA)
    ny = ts.tz_convert(z.NEWYORK)
    lon_dk = lon.hour * 60 + lon.minute
    ny_dk = ny.hour * 60 + ny.minute
    return np.where((lon_dk >= 7 * 60) & (ny_dk < 8 * 60), "londra",
           np.where((ny_dk >= 8 * 60) & (lon_dk < 16 * 60 + 30), "ortusme",
           np.where((lon_dk >= 16 * 60 + 30) & (ny_dk < 17 * 60), "ny", "asya")))


def _devir(bt: np.ndarray, tf: int) -> np.ndarray:
    ts = pd.to_datetime(bt, unit="s", utc=True).tz_convert(z.NEWYORK)
    bas = ts.hour * 60 + ts.minute
    son = bas + tf
    a = int(DEVIR[0][:2]) * 60 + int(DEVIR[0][3:])
    b = int(DEVIR[1][:2]) * 60 + int(DEVIR[1][3:])
    return (bas < b) & (son > a)


def _gunluk_oynaklik(d: vr.Dakika) -> pd.Series:
    """İşlem günü → o günden ÖNCEKİ 20 günün ortalama günlük aralığının, önceki 250 güne göre yüzdelik sırası."""
    gun = pd.Series(d.gun)
    df = pd.DataFrame({"gun": d.gun, "h": d.mh, "l": d.ml}).groupby("gun").agg(h=("h", "max"), l=("l", "min"))
    df = df[pd.DatetimeIndex(df.index).dayofweek < 5]
    ort = (df["h"] - df["l"]).rolling(GUNLUK_ATR_N).mean().shift(1)
    sira = ort.rolling(GUNLUK_YUZDELIK_N, min_periods=60).apply(lambda x: (x[:-1] <= x[-1]).mean(), raw=True)
    del gun
    return sira


def _kova(k: float) -> str:
    for a, b, ad in KOVALAR:
        if a <= k < b:
            return ad
    return ""


def olaylar(d: vr.Dakika, tf: int, cift: str) -> tuple[pd.DataFrame, dict]:
    """Bir paritenin bir dilimindeki büyük mumlar ve süzgeç değerleri. Dönüş: (olaylar, dışarıda kalanların sayımı)."""
    m = vr.mumla(d, tf)
    A = atr(m)
    A_once = np.r_[np.nan, A[:-1]]
    kat = (m.h - m.l) / A_once
    buyuk = kat >= ESIK
    tam = m.n >= DOLULUK * tf
    bosluk = np.r_[np.inf, np.diff(m.bt)]
    # yeniden açılış: 6 saatten uzun boşluktan sonraki ilk 60 dk
    acilis_an = np.where(bosluk > ACILIS_BOSLUK_SN, m.bt, np.nan)
    acilis_an = pd.Series(acilis_an).ffill().to_numpy()
    yeniden = (m.bt - acilis_an) < ACILIS_PAY_SN
    devir = _devir(m.bt, tf)
    kume = np.zeros(len(m.bt), dtype=bool)
    for k in range(1, KUME_ONCE + 1):
        kume[k:] |= buyuk[:-k]
    ardisik = np.zeros(len(m.bt), dtype=bool)
    for k in range(KUME_ONCE + 1, ARDISIK_MUM + 1):
        ardisik[k:] |= buyuk[:-k]
    seans = _seans(m.bt)
    tr = sf.gunluk_trend(d)
    tr_gun = tr["gun"].to_numpy()
    oyn = _gunluk_oynaklik(d)
    oyn_gun = oyn.index.to_numpy().astype("datetime64[D]")
    hab = takvim.olaylar_oku(cift)
    hab_sn = np.sort(hab["utc_sn"].to_numpy(np.int64)) if len(hab) else np.array([], np.int64)
    # gün içi önceki mumların uçları
    gun_s = pd.Series(m.gun)
    gun_h = pd.Series(m.h).groupby(gun_s).cummax().groupby(gun_s).shift(1).to_numpy()
    gun_l = pd.Series(m.l).groupby(gun_s).cummin().groupby(gun_s).shift(1).to_numpy()
    sayim = {"buyuk": 0, "kume": 0, "yeniden_acilis": 0, "devir": 0, "eksik": 0, "olay": 0}
    satir = []
    adim = tf * 60
    for i in np.flatnonzero(buyuk & ~np.isnan(A_once)):
        sayim["buyuk"] += 1
        if kume[i]:
            sayim["kume"] += 1
            continue
        if yeniden[i]:
            sayim["yeniden_acilis"] += 1
            continue
        if devir[i]:
            sayim["devir"] += 1
            continue
        izle_bas = int(m.bt[i] + adim)
        j0 = int(np.searchsorted(d.t, izle_bas))
        j1 = int(np.searchsorted(d.t, izle_bas + IZLE * adim))
        if not tam[i] or j1 - j0 < DOLULUK * IZLE * tf:
            sayim["eksik"] += 1
            continue
        o, h, l, c, a = m.o[i], m.h[i], m.l[i], m.c[i], A_once[i]
        R = h - l
        B = c - o
        y = 0 if abs(B) < KARARSIZ_GOVDE * R else int(np.sign(B))
        kc = ((c - l) / R if y >= 0 else (h - c) / R)
        kapanis = "uc" if kc >= 0.75 else ("orta" if kc >= 0.5 else "geri")
        gun = m.gun[i]
        k = np.searchsorted(tr_gun, gun) - 1
        trend = float(tr["trend"].iloc[k]) if k >= 0 else np.nan
        ko = np.searchsorted(oyn_gun, gun)
        sira = float(oyn.iloc[ko]) if ko < len(oyn) and oyn_gun[ko] == gun else np.nan
        oynaklik = "" if np.isnan(sira) else ("dusuk" if sira < 1 / 3 else ("yuksek" if sira >= 2 / 3 else "orta"))
        if i >= KOSU_MUM + 1 and y != 0 and m.bt[i] - m.bt[i - KOSU_MUM - 1] == (KOSU_MUM + 1) * adim:
            net = y * (m.c[i - 1] - m.c[i - 1 - KOSU_MUM]) / a
            kosu = "ayni" if net >= KOSU_ESIK else ("ters" if net <= -KOSU_ESIK else "sakin")
        else:
            kosu = ""
        if np.isnan(gun_h[i]) or y == 0:
            gun_ucu = ""
        else:
            gun_ucu = "evet" if (h > gun_h[i] if y > 0 else l < gun_l[i]) else "hayir"
        hk = np.searchsorted(hab_sn, m.bt[i] - 120)
        haber = "haber" if hk < len(hab_sn) and hab_sn[hk] < m.bt[i] + adim else "haber_yok"
        satir.append({
            "cift": cift, "tf": tf, "bt": int(m.bt[i]), "gun": str(gun), "o": o, "h": h, "l": l, "c": c, "A": a,
            "kat": float(kat[i]), "kova": _kova(kat[i]), "yon": y, "kc": float(kc), "kapanis": kapanis,
            "seans": str(seans[i]), "haber": haber, "trend": trend, "trend_uyum": sf.uyum(y, trend),
            "kosu": kosu, "gun_ucu": gun_ucu, "oynaklik": oynaklik, "ardisik": "evet" if ardisik[i] else "hayir",
            "i_son": int(m.i1[i]), "j0": j0, "j1": j1, "pip": d.pip,
        })
    sayim["olay"] = len(satir)
    df = pd.DataFrame(satir)
    if len(df):
        df = df.rename(columns={"trend_uyum": "trend", "trend": "trend_yon"})
    return df, sayim


# ───────────────────────────────────────────────────────────── yolun ölçüleri

def _ilk(m: np.ndarray) -> int:
    return int(np.argmax(m)) if m.any() else 10 ** 9


def yol(hi: np.ndarray, lo: np.ndarray, cl: np.ndarray, e: dict, tf: int) -> dict:
    """Mumdan sonraki yolun ölçüleri (orta fiyat). `hi, lo, cl` izleme penceresinin dakikaları."""
    c, A, R, y = e["c"], e["A"], e["h"] - e["l"], e["yon"]
    uc, ters = (e["h"], e["l"]) if y > 0 else (e["l"], e["h"])
    out = {}
    # yönlü bakış: yukarı = mumun yönü
    if y > 0:
        ileri, geri = hi - c, c - lo
    else:
        ileri, geri = c - lo, hi - c
    for k in SIMETRIK:
        a, b = _ilk(ileri >= k * A), _ilk(geri >= k * A)
        out[f"sim_{k}"] = 1.0 if a < b else (0.0 if b < a else np.nan)    # aynı dakika ya da hiçbiri: ölçülemez
    for f in GERI:
        sev = uc - y * f * R
        dok = (lo <= sev) if y > 0 else (hi >= sev)
        t = _ilk(dok)
        out[f"geri_{f}"] = t < 10 ** 9
        out[f"geri_{f}_dk"] = (t + 1) if t < 10 ** 9 else np.nan
    # yarıya dönüp yeniden uca
    t50 = _ilk((lo <= uc - y * 0.5 * R) if y > 0 else (hi >= uc - y * 0.5 * R))
    if t50 < 10 ** 9:
        ucu = (hi[t50 + 1:] >= uc) if y > 0 else (lo[t50 + 1:] <= uc)
        kirar = (lo[t50:] <= ters) if y > 0 else (hi[t50:] >= ters)
        a, b = _ilk(ucu), _ilk(kirar)
        out["geri_50_uc"] = (a + 1) < b if a < 10 ** 9 else False
    else:
        out["geri_50_uc"] = False
    asma = (hi > uc) if y > 0 else (lo < uc)
    out["uc_asma"] = bool(asma.any())
    out["uc_asma_05A"] = bool(((hi >= uc + 0.5 * A) if y > 0 else (lo <= uc - 0.5 * A)).any())
    out["mfe"] = float(ileri.max() / A)
    out["mae"] = float(geri.max() / A)
    for H in UFUKLAR:
        n = min(len(cl), H * tf) - 1
        out[f"net_{H}"] = float(y * (cl[n] - c) / A)
    return out


def olc(d: vr.Dakika, e: dict) -> tuple[dict, dict]:
    """(gerçek yol, kapanışa göre AYNALANMIŞ yol: p' = 2c − p). Ayna, yön bilgisi yokken mum geometrisinin
    kendiliğinden ürettiği oranı verir; gerçek − ayna farkı mumun yön bilgisidir."""
    j0, j1, c = e["j0"], e["j1"], e["c"]
    hi, lo, cl = d.mh[j0:j1], d.ml[j0:j1], d.mc[j0:j1]
    return yol(hi, lo, cl, e, e["tf"]), yol(2 * c - lo, 2 * c - hi, 2 * c - cl, e, e["tf"])


def makas(d: vr.Dakika, e: dict) -> dict:
    """Makas (pip): mumdan önceki 60 dakikanın medyanı, mumun son dakikasının kapanışı ve kapanıştan sonraki
    dakikaların açılışı."""
    i_son = e["i_son"]
    bas = int(np.searchsorted(d.t, e["bt"] - MAKAS_ONCE_DK * 60))
    i0 = int(np.searchsorted(d.t, e["bt"]))
    once = np.median((d.ac - d.bc)[bas:i0]) / d.pip if i0 > bas else np.nan
    out = {"makas_once": float(once), "makas_mum": float((d.ac[i_son] - d.bc[i_son]) / d.pip)}
    for k in MAKAS_SONRA:
        j = int(np.searchsorted(d.t, e["bt"] + e["tf"] * 60 + (k - 1) * 60))
        out[f"makas_{k}"] = float((d.ao[j] - d.bo[j]) / d.pip) if j < len(d.t) else np.nan
    return out


if __name__ == "__main__":
    sys.exit("modül; gözlem için buyuk_gozlem.py")
