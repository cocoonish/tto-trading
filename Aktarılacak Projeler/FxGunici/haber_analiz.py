#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Haber analizleri: kırılım ↔ fade devam tablosu, FOMC karar ↔ basın, ortalama patikalar.

Parite başına (`haber_analizi`) ölçülür ve `cikti/sonuc/haber/<parite>.json`a yazılır;
devam tablosunun satırları `cikti/haber/devam/<parite>.parquet`e. Bütün paritelerin
devam satırları `devam_toplu` ile hücrelere toplanır (kural: onkayit.toml [haber_devam]).

GÖZLEM BİRİMİ OLAYDIR. Aynı ABD olayı dört paritede aynı dakikada ölçülür; dört
ölçüm bağımsız değildir (hepsi doların tepkisidir). Hücrede aynı olaya (olay tipi ×
tarih) düşen paritelerin ortalaması tek gözlem sayılır. Bunu yapmamak örneklemi
dörde katlar ve t'yi iki katına çıkarırdı.

ÖLÇÜ BİRİMİ günlük ATR'dir (net getiri / önceki 14 günün ATR'si, yüzde). Pip
paritelerden pariteye kıyaslanamaz; pip ortalaması bilgi olarak ayrıca yazılır.
"""
from __future__ import annotations

import json
import math
from pathlib import Path

import numpy as np
import pandas as pd
from scipy import stats

import strat_haber as sh
from gunluk import Baglam

BURASI = Path(__file__).resolve().parent
CIKTI = BURASI / "cikti"
HD = sh.ONKAYIT["haber_devam"]
UFUK = [int(x) for x in HD["ufuk_dk"]]
ASGARI = int(HD["asgari_olay"])
FDR_Q = float(HD["fdr_q"])
ANA_TF = int(HD["ana_tf"])
#: Olay sırası ön kayıttan ([haber] olaylar); takvimde ön kayıtta olmayan bir tip varsa (kullanıcının ek dosyası)
#: ondan sonra alfabetik gelir — ek bir olay tipi patikalara da girer.
OLAY_ONKAYIT = [str(x) for x in sh.ONKAYIT["haber"]["olaylar"]]


def olay_sirasi(tipler) -> list[str]:
    tipler = set(tipler)
    return [o for o in OLAY_ONKAYIT if o in tipler] + sorted(tipler - set(OLAY_ONKAYIT))


OLAY_SIRA = OLAY_ONKAYIT


def haber_analizi(b: Baglam, cift: str, zaman_dilimleri, kayma_pip: float, haber_kayma_pip: float,
                  dis_baslangic: str) -> dict:
    olaylar = b.olaylar if b.olaylar is not None else pd.DataFrame()
    out = {"cift": cift, "olay_sayisi": {}, "atlanan": {}, "patika": {}, "fomc": None}
    if len(olaylar) == 0:
        return out
    out["olay_sayisi"] = {str(k): int(v) for k, v in olaylar["olay"].value_counts().items()}
    parca = []
    for tf in zaman_dilimleri:
        cer = sh.cerceve(b, tf)
        out["atlanan"][str(tf)] = {"olculen": int(len(cer)), **b.ek.get(("haber_atlanan", tf), {})}
        out.setdefault("kova_dagilimi", {})[str(tf)] = {
            o: {k: int(v) for k, v in g["kova"].value_counts().items()} for o, g in cer.groupby("olay")}
        for ufuk in UFUK:
            dv = sh.devam(b, tf, ufuk, kayma_pip, haber_kayma_pip)
            kp = b.ek.get(("devam_kirpilan", tf, ufuk), {})
            if kp:
                out.setdefault("devam_kirpilan", {}).setdefault(str(tf), {})[str(ufuk)] = kp
            if len(dv):
                dv.insert(0, "ufuk", ufuk)
                dv.insert(0, "tf", tf)
                parca.append(dv)
    if parca:
        tum = pd.concat(parca, ignore_index=True)
        tum.insert(0, "cift", cift)
        tum["oos"] = tum["gun"] >= dis_baslangic
        yol = CIKTI / "haber" / "devam"
        yol.mkdir(parents=True, exist_ok=True)
        tum.to_parquet(yol / f"{cift}.parquet", index=False)
    for olay in olay_sirasi(olaylar["olay"]):
        out["patika"][olay] = sh.patika(b, olaylar, olay)
    df = sh.fomc(b, olaylar)
    if len(df):
        out["fomc"] = {"ozet": sh.fomc_ozet(df), "satir": df.round(6).to_dict(orient="records")}
    return out


# ───────────────────────────────────────────── bütün pariteler
def _hucre(g: pd.DataFrame, kume: bool) -> dict:
    """Bir hücrenin olay düzeyinde ortalaması ve kırılım/fade için tek yönlü t."""
    g = g.assign(kir=g["kirilim_pip"] / g["gun_atr_pip"] * 100.0, fad=g["fade_pip"] / g["gun_atr_pip"] * 100.0)
    if kume:
        g = g.groupby(["olay", "tarih"], as_index=False).agg(kir=("kir", "mean"), fad=("fad", "mean"),
                                                              oos=("oos", "first"),
                                                              kirilim_pip=("kirilim_pip", "mean"),
                                                              fade_pip=("fade_pip", "mean"))
    n = int(len(g))
    sonuc = {"n_olay": n}
    for ad in ("kir", "fad"):
        x = g[ad].to_numpy(float)
        ort = float(x.mean()) if n else float("nan")
        sd = float(x.std(ddof=1)) if n > 1 else float("nan")
        t = ort / (sd / math.sqrt(n)) if n > 1 and sd > 0 else float("nan")
        p = float(stats.t.sf(t, df=n - 1)) if np.isfinite(t) else float("nan")
        xo = g.loc[g["oos"].astype(bool), ad].to_numpy(float)
        sonuc[ad] = {"ort_atr_yuzde": ort, "t": t, "p_tek": p, "oos_n": int(len(xo)),
                     "oos_ort_atr_yuzde": float(xo.mean()) if len(xo) else float("nan")}
    sonuc["kir"]["ort_pip"] = float(g["kirilim_pip"].mean()) if n else float("nan")
    sonuc["fad"]["ort_pip"] = float(g["fade_pip"].mean()) if n else float("nan")
    return sonuc


def bh(p: np.ndarray) -> np.ndarray:
    """Benjamini–Hochberg q değerleri (NaN'ler dışarıda kalır)."""
    q = np.full(len(p), np.nan)
    ok = np.isfinite(p)
    pv = p[ok]
    m = len(pv)
    if m == 0:
        return q
    sira = np.argsort(pv)
    ham = pv[sira] * m / np.arange(1, m + 1)
    duz = np.minimum.accumulate(ham[::-1])[::-1]
    qq = np.empty(m)
    qq[sira] = np.minimum(duz, 1.0)
    q[ok] = qq
    return q


def devam_toplu() -> dict:
    dosyalar = sorted((CIKTI / "haber" / "devam").glob("*.parquet"))
    if not dosyalar:
        return {"hucre": [], "not": "devam satırı yok"}
    df = pd.concat([pd.read_parquet(d) for d in dosyalar], ignore_index=True)
    df = df[np.isfinite(df["gun_atr_pip"]) & (df["gun_atr_pip"] > 0)]
    hucre = []

    def ekle(boyut: str, deger: str, tf: int, ufuk: int, g: pd.DataFrame, kume: bool = True):
        if len(g) == 0:
            return
        hucre.append({"boyut": boyut, "deger": deger, "tf": tf, "ufuk": ufuk, **_hucre(g, kume)})

    for ufuk in UFUK:
        ana = df[(df["tf"] == ANA_TF) & (df["ufuk"] == ufuk)]
        for olay, g in ana.groupby("olay"):
            ekle("olay", olay, ANA_TF, ufuk, g)
        for cift, g in ana.groupby("cift"):
            ekle("cift", cift, ANA_TF, ufuk, g, kume=False)
        for kova, g in ana.groupby("kova"):
            ekle("kova", kova, ANA_TF, ufuk, g)
        for uyum, g in ana.groupby("trend_uyum"):
            ekle("trend_uyum", uyum, ANA_TF, ufuk, g)
        for (olay, kova), g in ana.groupby(["olay", "kova"]):
            ekle("olay_kova", f"{olay}|{kova}", ANA_TF, ufuk, g)
        for tf, g in df[df["ufuk"] == ufuk].groupby("tf"):
            ekle("tf", str(tf), int(tf), ufuk, g)
    p = np.array([h[s]["p_tek"] for h in hucre for s in ("kir", "fad")], dtype=float)
    q = bh(p)
    for i, h in enumerate(hucre):
        h["kir"]["q"], h["fad"]["q"] = float(q[2 * i]), float(q[2 * i + 1])
        hukum = "ayrışmıyor"
        if h["n_olay"] >= ASGARI:
            if np.isfinite(h["kir"]["q"]) and h["kir"]["q"] < FDR_Q and h["kir"]["ort_atr_yuzde"] > 0:
                hukum = "kırılım kazanır"
            elif np.isfinite(h["fad"]["q"]) and h["fad"]["q"] < FDR_Q and h["fad"]["ort_atr_yuzde"] > 0:
                hukum = "fade kazanır"
        else:
            hukum = "yetersiz örneklem"
        h["hukum"] = hukum
    sayim = {}
    for h in hucre:
        sayim[h["hukum"]] = sayim.get(h["hukum"], 0) + 1
    return {"kural": {"asgari_olay": ASGARI, "fdr_q": FDR_Q, "ana_tf": ANA_TF, "ufuk_dk": UFUK},
            "sinama_sayisi": int(np.isfinite(p).sum()), "hukum_sayimi": sayim, "hucre": hucre}


def yaz(yol: Path, veri) -> None:
    def temiz(x):
        if isinstance(x, float):
            return None if not math.isfinite(x) else round(x, 6)
        if isinstance(x, np.floating):
            return temiz(float(x))
        if isinstance(x, np.integer):
            return int(x)
        if isinstance(x, np.bool_):
            return bool(x)
        if isinstance(x, dict):
            return {str(k): temiz(v) for k, v in x.items()}
        if isinstance(x, (list, tuple)):
            return [temiz(v) for v in x]
        return x
    yol.parent.mkdir(parents=True, exist_ok=True)
    yol.write_text(json.dumps(temiz(veri), ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
