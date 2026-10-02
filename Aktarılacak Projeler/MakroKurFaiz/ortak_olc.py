#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""MAKRODAN KURA VE FAİZE — ölçüm katmanının ORTAK araçları.

Bütün bölüm modülleri (`olcum_b*.py`) yalnız bu dosyanın okuyucularından ve
istatistik araçlarından geçer; aynı ölçü iki modülde iki ayrı kodla
kurulmasın (iki ayrı formül bir gün sessizce ayrışır).

OKUMA. `oku(ad)` arşiv dosyasını açar ve sıkıştırılmamış metnin sha256'sını
künyeyle kıyaslar; tutmazsa okumaz (arşiv elle değiştirilmiş ya da başka bir
çıpadan gelmiştir). Ham bulut arşivinin ayrıştırılmış hâli `veri/bulut/`
altındadır (`hazirla_bulut.py`) ve aynı kapıdan okunur.

USD/TRY (karar 09.09.2026 ve 02.10.2026): kurun konu olduğu her ölçü Yahoo
Finance'ten okunur. Saatlik barın ulaştığı yerde İstanbul 18:00 kapanışı
(`usdtry_ist18`), öncesinde günlük barın düzeltilmiş hâli: Yahoo'nun kapanmış
günlük döviz barında "Close" o günün BAŞINDAKİ fiyattır, değer bir önceki
hafta içi güne yazılır (`ortak/fx_kapanis.gunluk_duzelt`). Geçiş günü künyede
ölçülmüş olarak durur. TCMB gösterge kuru VALÖR tarihlidir (ertesi iş günü)
ve yalnız sağlamlık sınamasında, bir iş günü geri alınarak kullanılır.

İSTATİSTİK. Regresyonların hepsi Newey–West (Bartlett) standart hatasıyla
raporlanır; zaman serisi ilişkileri ayrıca ÖRNEKLEM DIŞI bir saf kıyasla
(rastgele yürüyüş ya da koşulsuz ortalama) sınanır, çünkü "örneklem içi uyum"
"yarın hangisini kullanayım" sorusunu cevaplamaz. Yarı ömür nokta değil
aralıktır (medyan-yansız kestirim, bootstrap).
"""
from __future__ import annotations

import gzip
import hashlib
import io
import json
import math
import sys
from functools import lru_cache
from pathlib import Path

import numpy as np
import pandas as pd

BURASI = Path(__file__).resolve().parent
VERI = BURASI / "veri"
BULUT = VERI / "bulut"
KOK = BURASI.parents[1]
sys.path.insert(0, str(KOK / "ortak"))
import fx_kapanis as _fx  # noqa: E402

CIPA_GUN = pd.Timestamp("2026-09-30")
CIPA_AY = pd.Period("2026-08", "M")
CIPA_CEYREK = pd.Period("2026Q2", "Q")


# ─────────────────────────────────────────────────────────────── okuma
@lru_cache(maxsize=None)
def _kunye(dizin: str) -> dict:
    p = Path(dizin) / "kunye.json"
    if not p.exists():
        return {}
    k = json.loads(p.read_text(encoding="utf-8"))
    return k.get("dosyalar", k)


def oku(ad: str, dizin: Path | None = None) -> pd.DataFrame:
    """Arşiv dosyası (`ad` uzantısız ya da .csv.gz'li); öz künyeyle sınanır."""
    dizin = dizin or (BULUT if (BULUT / _ad(ad)).exists() and not (VERI / _ad(ad)).exists() else VERI)
    dosya = _ad(ad)
    ham = gzip.decompress((dizin / dosya).read_bytes())
    k = _kunye(str(dizin)).get(dosya)
    if k is None:
        raise RuntimeError(f"{dosya}: künyede kaydı yok — arşiv dışı dosya okunmaz")
    oz = hashlib.sha256(ham).hexdigest()
    if oz != k.get("sha256"):
        raise RuntimeError(f"{dosya}: öz tutmuyor (künye {k.get('sha256', '')[:12]} · dosya {oz[:12]})")
    df = pd.read_csv(io.BytesIO(ham))
    ilk = df.columns[0]
    try:
        df[ilk] = pd.to_datetime(df[ilk])
        df = df.set_index(ilk).sort_index()
    except (ValueError, TypeError):
        df = df.set_index(ilk)
    return df


def _ad(ad: str) -> str:
    return ad if ad.endswith(".csv.gz") else f"{ad}.csv.gz"


def ozler() -> dict:
    """Ölçüm dosyasına yazılacak: okunan her arşiv dosyasının özü (dogrula.py sınar)."""
    out = {}
    for d in (VERI, BULUT):
        for ad, k in _kunye(str(d)).items():
            if isinstance(k, dict) and "sha256" in k:
                out[f"{d.name}/{ad}"] = k["sha256"]
    return dict(sorted(out.items()))


# ─────────────────────────────────────────────────────────────── kurlar
def usdtry() -> tuple[pd.Series, dict]:
    """USD/TRY günlük kapanış (Yahoo): saatlik bardan İstanbul 18:00, öncesi
    düzeltilmiş günlük bar. (seri, künye) döner."""
    df = oku("usdtry_yahoo_gunluk")
    ist = df["usdtry_ist18"].dropna()
    duz = _fx.gunluk_duzelt(df["usdtry_gunbasi"].dropna())
    gecis = ist.index.min()
    eski = duz[duz.index < gecis]
    s = pd.concat([eski, ist]).sort_index()
    s = s[~s.index.duplicated(keep="last")]
    s = s[s.index.dayofweek < 5]
    s.name = "usdtry"
    return s, {"kaynak": "Yahoo Finance USDTRY=X", "gecis": str(gecis.date()),
               "once": "günlük bar, değer bir önceki hafta içi güne (Londra gece yarısı kapanışı)",
               "sonra": "saatlik bardan İstanbul 18:00", "n": int(len(s)),
               "ilk": str(s.index.min().date()), "son": str(s.index.max().date())}


def usdtry_tcmb() -> pd.Series:
    """TCMB gösterge kuru, valör tarihi bir iş günü GERİ alınmış (sağlamlık)."""
    s = oku("usdtry_tcmb_gunluk")["usdtry_tcmb_valor"].dropna()
    s.index = s.index - pd.offsets.BDay(1)
    s = s[~s.index.duplicated(keep="last")]
    s = s[s.index <= CIPA_GUN]
    s.name = "usdtry_tcmb"
    return s


def em_kur(kod: str) -> pd.Series:
    """EM kuru (BRL, MXN, ZAR, INR; USD karşısında), Yahoo günlük barı düzeltilmiş."""
    s = oku("em_kur_yahoo_gunluk")[f"{kod.lower()}_gunbasi"].dropna()
    s = _fx.gunluk_duzelt(s)
    s.name = kod.lower()
    return s


# ─────────────────────────────────────────────────────────────── istatistik
def hac(y, X, gecikme: int | None = None, sabit: bool = True) -> dict:
    """OLS, Newey–West (Bartlett) HAC standart hatası. X tek dizi ya da matris.

    Döner: b (katsayılar, sabit ilk), se, t, r2, n, gecikme."""
    y = np.asarray(y, dtype=float)
    X = np.asarray(X, dtype=float)
    if X.ndim == 1:
        X = X[:, None]
    m = np.isfinite(y) & np.all(np.isfinite(X), axis=1)
    y, X = y[m], X[m]
    if sabit:
        X = np.column_stack([np.ones(len(y)), X])
    n, k = X.shape
    if n <= k + 2:
        return {"n": int(n), "yetersiz": True}
    if gecikme is None:
        gecikme = int(math.floor(4 * (n / 100) ** (2 / 9)))
    XtX_inv = np.linalg.inv(X.T @ X)
    b = XtX_inv @ X.T @ y
    e = y - X @ b
    S = (X * e[:, None]).T @ (X * e[:, None])
    for L in range(1, gecikme + 1):
        w = 1 - L / (gecikme + 1)
        G = (X[L:] * e[L:, None]).T @ (X[:-L] * e[:-L, None])
        S += w * (G + G.T)
    V = XtX_inv @ S @ XtX_inv
    se = np.sqrt(np.diag(V))
    r2 = 1 - (e @ e) / ((y - y.mean()) @ (y - y.mean())) if n > 1 else float("nan")
    return {"b": b.tolist(), "se": se.tolist(), "t": (b / se).tolist(), "r2": float(r2),
            "n": int(n), "gecikme": int(gecikme)}


def oos_kiyas(y: pd.Series, x: pd.Series, ilk_pencere: int, kiyas: str = "ortalama") -> dict:
    """Genişleyen pencerede y_t = a + b·x_t tahmini (x_t bilinen) ile saf kıyas
    (koşulsuz ortalama ya da sıfır = rastgele yürüyüşün değişimi) arasında
    örneklem dışı karesel hata. Oran < 1 modelin lehine; eşli farkın
    Diebold–Mariano t'si Newey–West ile."""
    d = pd.concat([y.rename("y"), x.rename("x")], axis=1).dropna()
    e_m, e_k = [], []
    for t in range(ilk_pencere, len(d)):
        egit = d.iloc[:t]
        X = np.column_stack([np.ones(len(egit)), egit["x"].values])
        b = np.linalg.lstsq(X, egit["y"].values, rcond=None)[0]
        tah = b[0] + b[1] * d["x"].iloc[t]
        kiy = egit["y"].mean() if kiyas == "ortalama" else 0.0
        e_m.append((d["y"].iloc[t] - tah) ** 2)
        e_k.append((d["y"].iloc[t] - kiy) ** 2)
    e_m, e_k = np.array(e_m), np.array(e_k)
    if not len(e_m):
        return {"n": 0}
    fark = e_m - e_k
    dm = hac(fark, np.zeros((len(fark), 0)), sabit=True) if len(fark) > 10 else {}
    return {"n": int(len(e_m)), "mse_oran": float(e_m.mean() / e_k.mean()) if e_k.mean() else None,
            "dm_t": (dm.get("t") or [None])[0], "kiyas": kiyas,
            "ilk": str(d.index[ilk_pencere].date()) if hasattr(d.index[ilk_pencere], "date") else str(d.index[ilk_pencere])}


def olay_profili(degisim: pd.Series, olaylar, pencere: int = 2) -> dict:
    """Olay günlerinin −k…+k iş günü kaymasında |Δ| ortalaması ve sıradan
    günlerin |Δ| ortalamasına oranı (plasebo profili). Tepe 0'da değilse
    tarih sözleşmesi kaymıştır; olay çalışması kurulmaz."""
    s = degisim.dropna()
    idx = s.index
    sira = {t: i for i, t in enumerate(idx)}
    poz = []
    for o in pd.DatetimeIndex(olaylar):
        j = idx.searchsorted(o)
        if j < len(idx) and idx[j] == o:
            poz.append(j)
    poz = np.array(poz, dtype=int)
    olay_kume = set()
    for p in poz:
        for k in range(-pencere, pencere + 1):
            olay_kume.add(p + k)
    sakin = np.array([i for i in range(len(s)) if i not in olay_kume])
    taban = float(np.nanmean(np.abs(s.values[sakin]))) if len(sakin) else float("nan")
    prof = {}
    for k in range(-pencere, pencere + 1):
        p = poz + k
        p = p[(p >= 0) & (p < len(s))]
        prof[k] = float(np.nanmean(np.abs(s.values[p]))) / taban if len(p) and taban else None
    tepe = max(prof, key=lambda k: prof[k] if prof[k] is not None else -1)
    return {"n_olay": int(len(poz)), "taban_abs": taban, "oran": {str(k): v for k, v in prof.items()},
            "tepe": int(tepe), "tepe_sifirda": bool(tepe == 0)}


def ar1(s: pd.Series) -> float:
    x = np.asarray(s.dropna(), dtype=float)
    x = x - x.mean()
    return float((x[1:] @ x[:-1]) / (x[:-1] @ x[:-1]))


def yari_omur(rho: float) -> float | None:
    if rho is None or not (0 < rho < 1):
        return None
    return float(math.log(0.5) / math.log(rho))


def ar1_medyan_yansiz(s: pd.Series, tohum: int = 20261002, deneme: int = 400,
                      izgara: np.ndarray | None = None) -> dict:
    """Andrews (1993) ruhunda medyan-yansız AR(1): ρ ızgarasında aynı uzunlukta
    yapay seri üretilir, OLS kestirimlerinin MEDYANI gözlenen ρ̂'ya eşit olan
    ρ seçilir. %90 aralığı aynı ızgaradan (5. ve 95. yüzdelik ters çevrilir).
    Üst uç 1'e dayanırsa yarı ömür üst sınırı SONSUZDUR ve öyle yazılır."""
    x = np.asarray(s.dropna(), dtype=float)
    n = len(x)
    rho_hat = ar1(pd.Series(x))
    rng = np.random.default_rng(tohum)
    izgara = izgara if izgara is not None else np.linspace(0.50, 1.0, 101)
    med, q05, q95 = [], [], []
    for r in izgara:
        # denemeler bir matrisin satırlarıdır: döngü yalnız zaman ekseninde
        e = rng.standard_normal((deneme, n))
        y = np.empty((deneme, n))
        y[:, 0] = e[:, 0] / math.sqrt(max(1 - r * r, 1e-6)) if r < 1 else e[:, 0]
        for i in range(1, n):
            y[:, i] = r * y[:, i - 1] + e[:, i]
        y = y - y.mean(axis=1, keepdims=True)
        tah = np.einsum("ij,ij->i", y[:, 1:], y[:, :-1]) / np.einsum("ij,ij->i", y[:, :-1], y[:, :-1])
        med.append(np.median(tah)); q05.append(np.quantile(tah, 0.05)); q95.append(np.quantile(tah, 0.95))
    med, q05, q95 = map(np.array, (med, q05, q95))

    def ters(egri: np.ndarray) -> float:
        # egri izgarada artan; rho_hat'ı veren ızgara noktası (doğrusal ara değer)
        if rho_hat <= egri[0]:
            return float(izgara[0])
        if rho_hat >= egri[-1]:
            return float(izgara[-1])
        j = int(np.searchsorted(egri, rho_hat))
        a, b = egri[j - 1], egri[j]
        return float(izgara[j - 1] + (rho_hat - a) / (b - a) * (izgara[j] - izgara[j - 1]))
    rho_mu = ters(med)
    alt = ters(q95)   # q95 eğrisini tutturan ρ alt sınır
    ust = ters(q05)
    return {"n": int(n), "rho_ols": rho_hat, "rho_mu": rho_mu, "rho_alt90": alt, "rho_ust90": ust,
            "yo_ols": yari_omur(rho_hat), "yo_mu": yari_omur(rho_mu), "yo_alt90": yari_omur(alt),
            "yo_ust90": yari_omur(ust) if ust < 0.9999 else None, "ust_sonsuz": bool(ust >= 0.9999)}


def yuvarla(x, h: int = 4):
    """olcum.json için: float'ları sabit hanede tutar (metin ondalığı ayrı)."""
    if isinstance(x, float):
        return None if not math.isfinite(x) else round(x, h)
    if isinstance(x, dict):
        return {str(k): yuvarla(v, h) for k, v in x.items()}
    if isinstance(x, (list, tuple)):
        return [yuvarla(v, h) for v in x]
    if isinstance(x, (np.floating,)):
        return yuvarla(float(x), h)
    if isinstance(x, (np.integer,)):
        return int(x)
    if isinstance(x, (pd.Timestamp,)):
        return str(x.date())
    return x
