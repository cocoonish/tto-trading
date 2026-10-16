#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Sağlamlık: deflated Sharpe, aynı saatlerde rastgele yön, walk-forward, koşul kovaları.

DEFLATED SHARPE (Bailey & López de Prado, 2014). N parametre kombinasyonu
denenip en iyisi seçildiyse, en iyinin Sharpe'ı şansla da yüksek çıkar.
Beklenen azami Sharpe (gerçek kenar sıfırken):
    SR₀ = √V · [(1 − γ)·Φ⁻¹(1 − 1/N) + γ·Φ⁻¹(1 − 1/(N·e))],  γ ≈ 0,5772
(V: denemelerin Sharpe'larının varyansı). Seçilen Sharpe'ın bunu aşma olasılığı
    DSR = Φ( (SR − SR₀)·√(T − 1) / √(1 − γ₃·SR + (γ₄ − 1)/4·SR²) )
(T gözlem; γ₃ çarpıklık, γ₄ basıklık; SR'ler yıllıklandırılmamış, günlük).
DSR ≥ 0,95 "seçim etkisinden arındırılınca da anlamlı" demektir.

RASTGELE YÖN. Stratejinin AYNI giriş dakikaları, aynı risk uzaklığı ve aynı
çıkış kuralıyla, yalnız YÖN yazı turayla seçilir; 1000 tekrarın ortalama R
dağılımında gerçek ortalamanın yüzdeliği. Zamanlamanın ve oynaklığın getirdiği
her şey iki tarafta da vardır; fark yalnız yönü seçmenin değeridir.
"""
from __future__ import annotations

import math

import numpy as np
import pandas as pd
from scipy import stats

import metrik as mk
import motor as mt
from gunluk import Baglam

EULER = 0.5772156649015329


def dsr(sr_secilen: float, sr_denemeler: np.ndarray, gunluk: np.ndarray) -> dict:
    """Günlük (yıllıklandırılmamış) Sharpe'larla deflated Sharpe."""
    sr_denemeler = np.asarray([x for x in sr_denemeler if np.isfinite(x)])
    N = len(sr_denemeler)
    T = len(gunluk)
    if N < 2 or T < 30 or not np.isfinite(sr_secilen):
        return {"dsr": float("nan"), "psr": float("nan"), "sr0": float("nan"), "n_deneme": N}
    V = float(np.var(sr_denemeler, ddof=1))
    sr0 = math.sqrt(V) * ((1 - EULER) * stats.norm.ppf(1 - 1.0 / N) + EULER * stats.norm.ppf(1 - 1.0 / (N * math.e)))
    g3 = float(stats.skew(gunluk))
    g4 = float(stats.kurtosis(gunluk, fisher=False))
    payda = math.sqrt(max(1e-12, 1 - g3 * sr_secilen + (g4 - 1) / 4.0 * sr_secilen ** 2))
    z_dsr = (sr_secilen - sr0) * math.sqrt(T - 1) / payda
    z_psr = sr_secilen * math.sqrt(T - 1) / payda
    return {"dsr": float(stats.norm.cdf(z_dsr)), "psr": float(stats.norm.cdf(z_psr)),
            "sr0_yillik": float(sr0 * math.sqrt(mk.YIL_GUN)), "n_deneme": N,
            "carpiklik": g3, "basiklik": g4}


def rastgele_yon(b: Baglam, isl: pd.DataFrame, tf: int, ofset: int | None, kayma_pip: float,
                 haber_kayma_pip: float, tekrar: int = 1000, tohum: int = 11) -> dict:
    """Aynı giriş dakikası, aynı R uzaklığı, ters yön → yazı tura karışımı.

    `ofset=None`: mum çıpası işlem başına (haber stratejileri); kapanış stop'unun
    sorulduğu mum sonu her işlemin kendi çıpasından okunur.
    """
    a = mk.alinan(isl).reset_index(drop=True)
    if len(a) < 20:
        return {"yuzdelik": float("nan"), "ort": float("nan"), "p95": float("nan")}
    d = b.d
    i = a["giris_i"].to_numpy(np.int64)
    yon_t = -a["yon"].to_numpy(np.int8)
    k = kayma_pip * d.pip
    hk = haber_kayma_pip * d.pip
    s0 = k + np.where(b.haber[i], hk, 0.0)
    dolum = np.where(yon_t == 1, d.ao[i] + s0, d.bo[i] - s0)
    R = a["R"].to_numpy(np.float64)
    e = mt.bos_emir(len(a))
    e["giris_i"] = i
    e["yon"] = yon_t
    st = a["stop_tur"].to_numpy(np.int8)
    e["stop_tur"] = st
    e["stop"] = np.where(st != mt.STOP_YOK, dolum - yon_t * R, np.nan)
    e["risk"] = R
    ht = a["hedef_tur"].to_numpy(np.int8)
    e["hedef_tur"] = ht
    e["hedef_k"] = a["hedef_k"].to_numpy(np.float64)
    uzak = np.abs(a["hedef"].to_numpy(np.float64) - a["giris_f"].to_numpy(np.float64))
    e["hedef_seviye"] = np.where(ht == mt.HEDEF_SEVIYE, dolum + yon_t * uzak, np.nan)
    e["cikis_i"] = a["plan_cikis_i"].to_numpy(np.int64)
    e["kimlik"] = np.arange(len(a))
    if ofset is None:
        ofs = a["ofset"].to_numpy(np.int64)
        parca = [mt.simule(d, e[ofs == o], b.bar_son(tf, int(o)), b.haber, kayma_pip, haber_kayma_pip,
                           tek_pozisyon=False) for o in np.unique(ofs)]
        ters = pd.concat(parca, ignore_index=True)
    else:
        ters = mt.simule(d, e, b.bar_son(tf, ofset), b.haber, kayma_pip, haber_kayma_pip, tek_pozisyon=False)
    ters = ters.sort_values("kimlik")
    r_ayni = a["r"].to_numpy()
    r_ters = ters["r"].to_numpy()
    gecerli = np.isfinite(r_ters)
    r_ayni, r_ters = r_ayni[gecerli], r_ters[gecerli]
    rng = np.random.default_rng(tohum)
    ort = np.empty(tekrar)
    for q in range(0, tekrar, 200):
        n = min(200, tekrar - q)
        secim = rng.random((n, len(r_ayni))) < 0.5
        ort[q:q + n] = np.where(secim, r_ayni, r_ters).mean(axis=1)
    gercek = float(r_ayni.mean())
    return {"yuzdelik": float((ort < gercek).mean() * 100), "ort": float(ort.mean()),
            "p05": float(np.percentile(ort, 5)), "p95": float(np.percentile(ort, 95)),
            "ters_ort": float(r_ters.mean()), "n": int(len(r_ayni))}


# ───────────────────────────────────────────── koşul kovaları
SUREKLI = {"range_atr", "asya_atr", "onceki_gun_range_atr", "acilis_farki_atr", "oynaklik_yuzdelik"}


def kova_analizi(f: pd.DataFrame, ic: np.ndarray, asgari: int = 30) -> list[dict]:
    """Her değişken için kova başına IS/OOS metrikleri ve IS seçimi → OOS sonucu.

    `f`: işlem başına özellik tablosu (sütun: değişkenler + r + pnl_pip).
    `ic`: örneklem içi maskesi. Sürekli değişkenlerin kova sınırları YALNIZ
    örneklem içinden (terciller) kurulur ve örneklem dışına taşınır.
    """
    sonuc = []
    r = f["r"].to_numpy()
    ic_ort = float(np.nanmean(r[ic])) if ic.any() else float("nan")
    for ad in [c for c in f.columns if c not in ("r", "pnl_pip", "is")]:
        x = f[ad]
        if x.isna().all():
            continue
        if ad in SUREKLI:
            q = np.nanpercentile(x[ic], [100 / 3, 200 / 3]) if (ic & x.notna().to_numpy()).sum() >= 30 else None
            if q is None or not np.isfinite(q).all() or q[0] == q[1]:
                continue
            kova = np.where(x.isna(), None, np.where(x < q[0], "alt", np.where(x < q[1], "orta", "üst")))
            sinir = [float(q[0]), float(q[1])]
        else:
            kova = x.astype(object).where(x.notna(), None).to_numpy()
            sinir = None
        kova = pd.Series(kova, index=f.index)
        satirlar = []
        # Eksik değer kova değildir: pandas `where(..., None)` nesne dizisinde None'u NaN'a
        # çevirebiliyor ve NaN kovası tablolara "nan" adıyla, sıfır işlemle giriyordu.
        for k in [v for v in pd.unique(kova) if v is not None and pd.notna(v)]:
            m = (kova == k).to_numpy()
            mi, md = m & ic, m & ~ic
            satirlar.append({
                "kova": str(k),
                "is_n": int(mi.sum()), "is_r": float(r[mi].mean()) if mi.any() else float("nan"),
                "is_isabet": float((f["pnl_pip"].to_numpy()[mi] > 0).mean()) if mi.any() else float("nan"),
                "oos_n": int(md.sum()), "oos_r": float(r[md].mean()) if md.any() else float("nan"),
                "oos_isabet": float((f["pnl_pip"].to_numpy()[md] > 0).mean()) if md.any() else float("nan"),
            })
        secilen = [s["kova"] for s in satirlar if s["is_n"] >= asgari and np.isfinite(s["is_r"]) and s["is_r"] > ic_ort]
        hukum = "secilmedi"
        oos_sec = oos_tum = oos_ters = float("nan")
        if secilen and len(secilen) < len(satirlar):
            ms = kova.isin(secilen).to_numpy()
            msd, mtd = ms & ~ic, (~ms) & ~ic & kova.notna().to_numpy()
            oos_sec = float(r[msd].mean()) if msd.any() else float("nan")
            oos_ters = float(r[mtd].mean()) if mtd.any() else float("nan")
            n_oos = int(msd.sum())
            hukum = "tuttu" if (n_oos >= 20 and np.isfinite(oos_sec) and oos_sec > 0
                                and np.isfinite(oos_ters) and oos_sec > oos_ters) else "tutmadi"
        sonuc.append({"degisken": ad, "sinir": sinir, "kovalar": satirlar, "secilen": secilen,
                      "hukum": hukum, "oos_secilen_r": oos_sec, "oos_tamamlayan_r": oos_ters})
    return sonuc
