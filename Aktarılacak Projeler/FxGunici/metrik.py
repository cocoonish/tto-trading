#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Backtest metrikleri — tek tanım.

Bütün oranlar ALINAN işlemlerden (motorun `durum == 0`) kurulur; alınmayan
emirler (pozisyon açık, geçersiz risk) ayrıca sayılır.

  isabet        net pip > 0 olan işlemlerin payı
  beklenti      işlem başına ortalama net sonuç (pip ve R)
  PF            kazançların toplamı / kayıpların toplamının mutlak değeri; pip (`pf`) ve R (`pf_r`) ayrı —
                ikisi aynı işlemlerden farklı ağırlıkla kurulur ve 1'in iki yanına düşebilir
  Sharpe        GÜNLÜK R serisinin ortalaması / standart sapması × √252; işlemsiz
                işlem günleri 0 sayılır (seri, dönemin bütün tatil dışı işlem günleri)
  azami düşüş   günlük birikimli R eğrisinin tepeden en derin düşüşü (R)
  MAE / MFE     işlem boyunca emir tarafında en kötü / en iyi gezinme (R, medyan)
  başabaş       beklentiyi sıfırlayan EK gidiş-dönüş maliyeti (pip); temel senaryonun
                (gerçek makas + kayma) üstüne. Negatifse strateji temel maliyette bile kaybeder.
  %95 aralık    ortalama R'nin (ve ayrıca ortalama net pipin) bootstrap (işlem yeniden örneklemesi) aralığı;
                `kume_sutun` verilirse KÜME bootstrap'i: aynı kümenin (ör. aynı günün dört paritedeki) bütün
                işlemleri birlikte seçilir — işlemler kümede ilintiliyse işlem başına aralık fazla dar çıkar
"""
from __future__ import annotations

import math

import numpy as np
import pandas as pd

YIL_GUN = 252.0
#: Bootstrap aralığının asgari işlem (ve küme bootstrap'inde küme) sayısı; altında aralık kurulmaz.
ASGARI_BOOTSTRAP = 10


def alinan(isl: pd.DataFrame) -> pd.DataFrame:
    if isl is None or len(isl) == 0:
        return pd.DataFrame(columns=["r", "pnl_pip", "gun"])
    return isl[isl["durum"] == 0]


def gunluk_r(isl: pd.DataFrame, gunler: np.ndarray) -> np.ndarray:
    """Dönemin işlem günlerinde günlük toplam R (işlemsiz gün 0)."""
    a = alinan(isl)
    s = pd.Series(0.0, index=pd.Index(gunler))
    if len(a):
        t = a.groupby("gun")["r"].sum()
        t = t[t.index.isin(s.index)]
        s.loc[t.index] = t.to_numpy()
    return s.to_numpy()


def sharpe(gunluk: np.ndarray) -> float:
    if len(gunluk) < 20:
        return float("nan")
    sd = gunluk.std(ddof=1)
    return float(gunluk.mean() / sd * math.sqrt(YIL_GUN)) if sd > 0 else float("nan")


def azami_dusus(gunluk: np.ndarray) -> float:
    if len(gunluk) == 0:
        return float("nan")
    e = np.cumsum(gunluk)
    tepe = np.maximum.accumulate(np.concatenate([[0.0], e]))[1:]
    return float((tepe - e).max())


def bootstrap_ort(x: np.ndarray, tekrar: int = 2000, tohum: int = 7) -> tuple[float, float]:
    x = np.asarray(x, dtype=np.float64)
    if len(x) < ASGARI_BOOTSTRAP:
        return (float("nan"), float("nan"))
    r = np.random.default_rng(tohum)
    n = len(x)
    ort = np.empty(tekrar)
    for i in range(0, tekrar, 250):
        k = min(250, tekrar - i)
        ix = r.integers(0, n, size=(k, n))
        ort[i:i + k] = x[ix].mean(axis=1)
    return (float(np.percentile(ort, 2.5)), float(np.percentile(ort, 97.5)))


def bootstrap_kume_ort(x: np.ndarray, kume: np.ndarray, tekrar: int = 2000, tohum: int = 7) -> tuple[float, float]:
    """Ortalamanın küme bootstrap'iyle %95 aralığı: kümeler yerine konarak seçilir, ortalama Σx / Σn (oran
    tahmincisi). En az 10 işlem ve 10 küme ister."""
    x = np.asarray(x, dtype=np.float64)
    if len(x) < ASGARI_BOOTSTRAP:
        return (float("nan"), float("nan"))
    _, ters = np.unique(np.asarray(kume), return_inverse=True)
    toplam = np.bincount(ters, weights=x)
    sayi = np.bincount(ters).astype(np.float64)
    K = len(toplam)
    if K < ASGARI_BOOTSTRAP:
        return (float("nan"), float("nan"))
    r = np.random.default_rng(tohum)
    ort = np.empty(tekrar)
    for i in range(0, tekrar, 250):
        k = min(250, tekrar - i)
        ix = r.integers(0, K, size=(k, K))
        ort[i:i + k] = toplam[ix].sum(axis=1) / sayi[ix].sum(axis=1)
    return (float(np.percentile(ort, 2.5)), float(np.percentile(ort, 97.5)))


def ozet(isl: pd.DataFrame, gunler: np.ndarray, bootstrap: bool = True, kume_sutun: str | None = None) -> dict:
    """Bir işlem kümesinin bütün metrikleri."""
    a = alinan(isl)
    n = int(len(a))
    gr = gunluk_r(isl, gunler)
    out = {
        "n": n,
        "n_gun": int(len(gunler)),
        "alinmayan": int((isl["durum"] != 0).sum()) if isl is not None and len(isl) else 0,
        "pozisyon_acik": int((isl["durum"] == 1).sum()) if isl is not None and len(isl) else 0,
        "belirsiz": int(a["belirsiz"].sum()) if n else 0,
    }
    if n == 0:
        out.update({k: float("nan") for k in ("isabet", "beklenti_r", "beklenti_pip", "brut_r", "brut_pip",
                                              "ort_kazanc_r", "ort_kayip_r", "ort_kazanc_pip", "ort_kayip_pip",
                                              "pf", "pf_r", "sharpe", "azami_dusus_r", "sure_dk", "mae_r", "mfe_r",
                                              "risk_pip", "basabas_pip", "ga_alt", "ga_ust", "ga_brut_alt",
                                              "ga_brut_ust", "ga_pip_alt", "ga_pip_ust", "toplam_r")})
        return out
    r, pp = a["r"].to_numpy(), a["pnl_pip"].to_numpy()
    kaz, kay = pp > 0, pp <= 0
    pf_pay = pp[kaz].sum()
    pf_payda = -pp[kay].sum()
    out.update({
        "isabet": float(kaz.mean()),
        "beklenti_r": float(r.mean()),
        "beklenti_pip": float(pp.mean()),
        "brut_r": float(a["r_brut"].mean()),
        "brut_pip": float(a["brut_pip"].mean()),
        "ort_kazanc_r": float(r[kaz].mean()) if kaz.any() else float("nan"),
        "ort_kayip_r": float(r[kay].mean()) if kay.any() else float("nan"),
        "ort_kazanc_pip": float(pp[kaz].mean()) if kaz.any() else float("nan"),
        "ort_kayip_pip": float(pp[kay].mean()) if kay.any() else float("nan"),
        "pf": float(pf_pay / pf_payda) if pf_payda > 0 else float("nan"),
        "pf_r": float(r[r > 0].sum() / -r[r <= 0].sum()) if (r <= 0).any() and r[r <= 0].sum() < 0 else float("nan"),
        "sharpe": sharpe(gr),
        "azami_dusus_r": azami_dusus(gr),
        "toplam_r": float(r.sum()),
        "sure_dk": float(a["sure_dk"].mean()),
        "mae_r": float(a["mae_r"].median()),
        "mfe_r": float(a["mfe_r"].median()),
        "risk_pip": float(a["R_pip"].median()),
        # Ek gidiş-dönüş maliyeti c pip, işlem başına net pipi c kadar düşürür:
        # beklenti_pip − c = 0 → c* = beklenti_pip.
        "basabas_pip": float(pp.mean()),
    })
    if bootstrap:
        if kume_sutun is None:
            bs = bootstrap_ort
        else:
            kume = a[kume_sutun].to_numpy()
            bs = lambda x: bootstrap_kume_ort(x, kume)  # noqa: E731
        out["ga_alt"], out["ga_ust"] = bs(r)
        out["ga_brut_alt"], out["ga_brut_ust"] = bs(a["r_brut"].to_numpy())
        # Pip ortalamasının aralığı da: R ortalaması her işlemi riskine göre büyüklükler, pip ortalaması aynı
        # büyüklükle işlem yapanın sonucudur; ikisinin işareti ayrıştığında okur ikisinin de belirsizliğini görmeli.
        out["ga_pip_alt"], out["ga_pip_ust"] = bs(pp)
        out["ga_kume"] = kume_sutun
    return out


def yil_toplamlari(isl: pd.DataFrame, gunler: np.ndarray) -> dict:
    """Yürüyen pencere için yıl başına günlük-R toplamları: n_gun, Σr, Σr², n_islem."""
    gr = gunluk_r(isl, gunler)
    yil = pd.DatetimeIndex(gunler.astype("datetime64[ns]")).year
    a = alinan(isl)
    ny = pd.DatetimeIndex(a["gun"].to_numpy().astype("datetime64[ns]")).year if len(a) else np.array([])
    out = {}
    for y in np.unique(yil):
        m = yil == y
        out[int(y)] = (int(m.sum()), float(gr[m].sum()), float((gr[m] ** 2).sum()), int((ny == y).sum()))
    return out


def sharpe_toplamdan(toplamlar: list[tuple]) -> tuple[float, int]:
    n = sum(t[0] for t in toplamlar)
    if n < 20:
        return float("nan"), 0
    s1 = sum(t[1] for t in toplamlar)
    s2 = sum(t[2] for t in toplamlar)
    ort = s1 / n
    var = (s2 - n * ort * ort) / (n - 1)
    islem = sum(t[3] for t in toplamlar)
    return (float(ort / math.sqrt(var) * math.sqrt(YIL_GUN)) if var > 0 else float("nan")), islem
