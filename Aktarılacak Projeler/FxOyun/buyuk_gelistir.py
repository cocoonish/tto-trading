#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Büyük mumdan sonra giriş biçimlerinin 2018–2023 sonucu (maliyetli ve maliyetsiz). YALNIZ örneklem içi.

Her büyük mum olayına (buyuk_mum.olaylar) giriş ızgarasının bütün hücreleri (buyuk_sim.hepsi: 2 yön × emir
biçimleri × 2 stop × 2 hedef) aynı kodla uygulanır. Veri 31.12.2023'e kırpılarak yüklenir.

Çıktı: veri/buyuk_gelistir.json — dilim × giriş hücresi için işlem sayısı, dolum oranı, kazanma oranı, net ve
maliyetsiz ortalama R; dilim × giriş × süzgeç değeri; limit emirlerin ters seçimi (emrin dolduğu ve dolmadığı
olaylarda aynı yönlü piyasa girişinin sonucu). İşlem düzeyindeki tam dosya git'e girmez (veri/_yerel/).
"""
from __future__ import annotations

import dataclasses
import json
import sys
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

import numpy as np
import pandas as pd

import buyuk_mum as bm
import buyuk_sim as bs
from buyuk_gozlem import IC_BITIS, SINIR

import ayar as ay  # noqa: E402
import takvim  # noqa: E402
import veri as vr  # noqa: E402

BURASI = Path(__file__).resolve().parent
VERI = BURASI / "veri"
YEREL = VERI / "_yerel"
SUZ = [f for f in bm.SUZGECLER]
YARILAR = {"y1": (2018, 2020), "y2": (2021, 2023)}       # örneklem içinin iki yarısı (seçimde kararlılık)


def haber_sn(cift: str) -> np.ndarray:
    h = takvim.olaylar_oku(cift)
    return np.sort(h["utc_sn"].to_numpy(np.int64)) if len(h) else np.array([], np.int64)


def kos_cift(cift: str, bitis=IC_BITIS, sinir=SINIR) -> pd.DataFrame:
    a = dataclasses.replace(ay.oku(), bitis=bitis)
    d = vr.oku(cift, a)
    if sinir is not None:
        assert int(d.t[-1]) < sinir, "2024 sonrası veri geliştirmeye girdi"
    do = bs.Orta(d)
    hs = haber_sn(cift)
    girisler = bs.hepsi()
    olaylar, kayit = [], []
    NEDEN = {"hedef": 0, "stop": 1, "zaman": 2}
    for tf in bm.DILIMLER:
        ev, _ = bm.olaylar(d, tf, cift)
        if sinir is not None and len(ev):
            ev = ev[ev["bt"] + (bm.IZLE + 1) * tf * 60 <= sinir].reset_index(drop=True)
        for e in ev.to_dict("records"):
            if e["yon"] == 0:
                continue
            k = len(olaylar)
            olaylar.append({"cift": cift, "tf": tf, "bt": e["bt"], "gun": e["gun"], **{f: e[f] for f in SUZ}})
            for gi, g in enumerate(girisler):
                uygun = bs.emir(d, e, g) is not None and g.stop * e["A"] >= bs.EN_AZ_RISK_PIP * e["pip"]
                x = bs.simule(d, e, g, hs) if uygun else None
                if x is None:
                    kayit.append((k, gi, uygun, False, np.nan, np.nan, -1, np.nan, -1))
                    continue
                b = bs.simule(do, e, g, hs, kayma_pip=0.0, haber_kayma_pip=0.0)
                kayit.append((k, gi, True, True, x["R"], np.nan if b is None else b["R"], NEDEN[x["neden"]],
                              x["risk_pip"], x["bekleme_dk"]))
        print(f"  {cift} {tf} dk: {len(ev)} olay", flush=True)
    ol = pd.DataFrame(olaylar)
    for c in ["cift", "gun"] + SUZ:
        ol[c] = ol[c].astype("category")
    ik = pd.DataFrame(kayit, columns=["olay", "gi", "uygun", "doldu", "R", "brut_R", "neden", "risk_pip",
                                      "bekleme_dk"])
    ik["giris"] = pd.Categorical.from_codes(ik["gi"], [g.ad for g in girisler])
    ik["neden"] = pd.Categorical.from_codes(ik["neden"].clip(lower=-1), ["hedef", "stop", "zaman"])
    return ol.iloc[ik["olay"].to_numpy()].reset_index(drop=True).join(ik.drop(columns=["olay", "gi"]))


def ozet(g: pd.DataFrame) -> dict:
    u = g[g["uygun"]]
    f = g[g["doldu"]]
    r = f["R"].to_numpy(float)
    out = {"olay": int(len(g)), "uygun": int(len(u)), "n": int(len(f)),
           "dolum": float(len(f) / len(u)) if len(u) else None}
    if len(f):
        b = f["brut_R"].dropna().to_numpy(float)
        out.update(kazanma=float((r > 0).mean()), ort_R=float(r.mean()), med_R=float(np.median(r)),
                   brut_R=float(b.mean()) if len(b) else None, brut_kazanma=float((b > 0).mean()) if len(b) else None,
                   maliyet_R=float(b.mean() - r[f["brut_R"].notna().to_numpy()].mean()) if len(b) else None,
                   risk_pip_med=float(f["risk_pip"].median()),
                   hedef=float((f["neden"] == "hedef").mean()), stop=float((f["neden"] == "stop").mean()),
                   gun_n=int(f["gun"].nunique()))
        yil = pd.to_datetime(f["bt"], unit="s").dt.year.to_numpy()
        for ad, (a, b) in YARILAR.items():
            m = (yil >= a) & (yil <= b)
            out[f"{ad}_n"] = int(m.sum())
            out[f"{ad}_R"] = float(r[m].mean()) if m.any() else None
    return out


def ters_secim(df: pd.DataFrame) -> list[dict]:
    """Limit emir doldu mu, dolmadı mı — aynı olayda aynı yönlü piyasa girişinin (aynı stop ve hedef) sonucu."""
    out = []
    anahtar = ["cift", "tf", "bt"]
    for g in bs.hepsi():
        if not g.emir.startswith("limit"):
            continue
        p = bs.Giris(g.yon, "piyasa", g.stop, g.hedef).ad
        lim = df[(df["giris"] == g.ad) & df["uygun"]][anahtar + ["doldu"]].astype({"cift": str})
        pia = df[(df["giris"] == p) & df["doldu"]][anahtar + ["R", "brut_R"]].astype({"cift": str})
        m = lim.merge(pia, on=anahtar)
        for tf in bm.DILIMLER:
            mt = m[m["tf"] == tf]
            dol, kac = mt[mt["doldu"]], mt[~mt["doldu"]]
            out.append({"tf": tf, "giris": g.ad, "piyasa": p, "dolan_n": int(len(dol)), "kacan_n": int(len(kac)),
                        "piyasa_R_dolan": float(dol["R"].mean()) if len(dol) else None,
                        "piyasa_R_kacan": float(kac["R"].mean()) if len(kac) else None,
                        "piyasa_kazanma_dolan": float((dol["R"] > 0).mean()) if len(dol) else None,
                        "piyasa_kazanma_kacan": float((kac["R"] > 0).mean()) if len(kac) else None,
                        "piyasa_brut_dolan": float(dol["brut_R"].mean()) if len(dol) else None,
                        "piyasa_brut_kacan": float(kac["brut_R"].mean()) if len(kac) else None})
    return out


def toplu(df: pd.DataFrame) -> dict:
    hucre, suzgec = [], []
    for (tf, gir), g in df.groupby(["tf", "giris"], observed=True):
        hucre.append({"tf": int(tf), "giris": gir, **ozet(g)})
        for f in SUZ:
            for v, gg in g.groupby(f, observed=True):
                if v == "" or (isinstance(v, float) and np.isnan(v)):
                    continue
                suzgec.append({"tf": int(tf), "giris": gir, "suzgec": f, "deger": v, **ozet(gg)})
    return {"hucre": hucre, "suzgec": suzgec, "ters_secim": ters_secim(df)}


def main() -> int:
    a = ay.oku()
    with ProcessPoolExecutor(max_workers=min(4, len(a.ciftler))) as ex:
        parca = list(ex.map(kos_cift, a.ciftler))
    df = pd.concat(parca, ignore_index=True)
    for c in ["cift", "gun", "giris", "neden"] + SUZ:
        df[c] = df[c].astype("category")
    YEREL.mkdir(parents=True, exist_ok=True)
    df.to_parquet(YEREL / "buyuk_gelistir_islemler.parquet", index=False)
    out = {"donem": ["2018-01-01", IC_BITIS.isoformat()], "giris_sayisi": len(bs.hepsi()),
           "kayma_pip": bs.KAYMA_PIP, "haber_kayma_pip": bs.HABER_KAYMA_PIP, "bekle_mum": bs.BEKLE, **toplu(df)}
    (VERI / "buyuk_gelistir.json").write_text(json.dumps(out, ensure_ascii=False, separators=(",", ":")) + "\n", encoding="utf-8")
    print(f"✓ {int(df['doldu'].sum())} işlem → veri/buyuk_gelistir.json")
    return 0


if __name__ == "__main__":
    sys.exit(main())
