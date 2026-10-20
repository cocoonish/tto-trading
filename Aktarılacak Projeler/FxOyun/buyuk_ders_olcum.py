#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Büyük mum derslerinin ölçüm dosyası → veri/buyuk_ders.json (figürler ve ders metni YALNIZ buradan okur).

Girdiler: buyuk_gozlem.json (2018–2023 gözlemi, dışlama sayımları), buyuk_gelistir.json (2018–2023 giriş ızgarası),
buyuk_plan.json (ön kayıtlı seçim), buyuk_sina.json (planın iki dönemdeki sonucu) ve dakika verisi. Dakika verisinden
BETİMLEME için yeniden ölçülenler: her iki dönemde süzgeç × değer davranışı, mumdan sonraki ortalama yol, giriş
ızgarasının 2024 → sonucu (seçimde kullanılmadı; seçim 2018–2023'tendir) ve örnek mumlar. Aralıklar işlem günü
düzeyinde bootstrapla (ön kaydın tohumu). Dosya her girdinin ve kodun sha256 özünü taşır; kapı özleri yeniden hesaplar.
"""
from __future__ import annotations

import hashlib
import json
import sys
import tomllib
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

import numpy as np
import pandas as pd

import buyuk_gelistir as bg
import buyuk_mum as bm
import buyuk_sim as bs
from buyuk_sina import gun_bootstrap

import ayar as ay  # noqa: E402
import veri as vr  # noqa: E402

BURASI = Path(__file__).resolve().parent
VERI = BURASI / "veri"
ON = tomllib.loads((BURASI / "onkayit_buyuk.toml").read_text(encoding="utf-8"))
DIS_BAS = int(pd.Timestamp(ON["donem"]["dis"][0]).timestamp())
TEKRAR, TOHUM = ON["hukum"]["bootstrap"], ON["hukum"]["tohum"]
ORNEK_CIFT, ORNEK_SON, ORNEK_KOVA = "EURUSD", "2023-12-01", "3-4"     # örnek mum: bu tarihten önceki SON uygun olay
ORNEK_ONCE, ORNEK_SONRA = 30, bm.IZLE                                 # örnek grafikte mumdan önce/sonra mum sayısı
KOD = ("buyuk_mum.py", "buyuk_sim.py", "buyuk_gozlem.py", "buyuk_gelistir.py", "buyuk_secim.py", "buyuk_sina.py",
       "buyuk_ders_olcum.py", "sinif.py")
OLCU = ["sim_0.5", "sim_1.0", "sim_2.0", "geri_0.25", "geri_0.5", "geri_0.62", "geri_1.0", "geri_50_uc", "uc_asma",
        "uc_asma_05A"]


def oz(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def olay_isci(cift: str) -> dict:
    a = ay.oku()
    d = vr.oku(cift, a)
    satir, yollar, ornek = [], {}, {}
    for tf in bm.DILIMLER:
        ev, _ = bm.olaylar(d, tf, cift)
        Y = []
        for e in ev.to_dict("records"):
            dn = "dis" if e["bt"] >= DIS_BAS else "ic"
            if dn == "ic" and e["bt"] + (bm.IZLE + 1) * tf * 60 > DIS_BAS:
                continue
            if e["yon"] == 0:
                continue
            g, y = bm.olc(d, e)
            mk = bm.makas(d, e)
            satir.append({"cift": cift, "tf": tf, "gun": e["gun"], "donem": dn, "bt": e["bt"],
                          **{f: e[f] for f in bm.SUZGECLER}, **g, **{f"ayna_{k}": v for k, v in y.items()}, **mk,
                          "A_pip": e["A"] / e["pip"], "R_pip": (e["h"] - e["l"]) / e["pip"]})
            cl = d.mc[e["j0"]:e["j1"]]
            idx = np.minimum(np.arange(1, bm.IZLE + 1) * tf, len(cl)) - 1
            Y.append(np.r_[0.0, e["yon"] * (cl[idx] - e["c"]) / e["A"]])
        yollar[tf] = np.array(Y)
        if cift == ORNEK_CIFT:
            son = int(pd.Timestamp(ORNEK_SON, tz="UTC").timestamp())
            aday = ev[(ev["bt"] < son) & (ev["kova"] == ORNEK_KOVA) & (ev["yon"] != 0) & (ev["kapanis"] == "uc")
                      & (ev["haber"] == "haber_yok")]
            if len(aday):
                e = aday.iloc[-1].to_dict()
                m = vr.mumla(d, tf)
                i = int(np.searchsorted(m.bt, e["bt"]))
                A = bm.atr(m)
                pen = slice(max(0, i - ORNEK_ONCE), min(len(m.bt), i + ORNEK_SONRA + 1))
                ornek[tf] = {"bt": int(e["bt"]), "gun": e["gun"], "kat": float(e["kat"]), "yon": int(e["yon"]),
                             "h": float(e["h"]), "l": float(e["l"]), "c": float(e["c"]), "A": float(e["A"]),
                             "mumlar": [[int(m.bt[k]), float(m.o[k]), float(m.h[k]), float(m.l[k]), float(m.c[k]),
                                         float(A[k - 1]) if k else None] for k in range(pen.start, pen.stop)]}
    return {"satir": satir, "yol": yollar, "ornek": ornek}


def _ort_aralik(g: pd.DataFrame, m: str, rng) -> dict:
    v = g[m].astype(float).to_numpy()
    ok = ~np.isnan(v)
    alt, ust = gun_bootstrap(g["gun"].to_numpy()[ok], v[ok], rng, TEKRAR)
    return {"ort": float(v[ok].mean()) if ok.any() else None, "alt": alt, "ust": ust, "n": int(ok.sum())}


def davranis(g: pd.DataFrame, rng, tam: bool = True) -> dict:
    r = {"n": int(len(g)), "gun_n": int(g["gun"].nunique())}
    if not len(g):
        return r
    for m in OLCU:
        r[m] = float(g[m].astype(float).mean())
        r[f"ayna_{m}"] = float(g[f"ayna_{m}"].astype(float).mean())
    r["net_24"] = _ort_aralik(g, "net_24", rng)
    fark = g.assign(_f=g["geri_0.5"].astype(float) - g["ayna_geri_0.5"].astype(float))
    r["geri_0.5_fark"] = _ort_aralik(fark, "_f", rng)
    r["sim_1.0_ci"] = _ort_aralik(g, "sim_1.0", rng)
    if tam:
        for H in bm.UFUKLAR:
            r[f"net_{H}_ort"] = float(g[f"net_{H}"].mean())
        r["mfe_med"], r["mae_med"] = float(g["mfe"].median()), float(g["mae"].median())
        r["geri_0.5_dk_med"] = float(g.loc[g["geri_0.5"].astype(bool), "geri_0.5_dk"].median())
        for k in ["mum"] + [str(x) for x in bm.MAKAS_SONRA]:
            o = g[f"makas_{k}"] / g["makas_once"]
            r[f"makas_{k}_kat_ort"] = float(o.mean())
            r[f"makas_{k}_iki_kat"] = float((o >= 2).mean())
            r[f"makas_{k}_pip_med"] = float(g[f"makas_{k}"].median())
        r["makas_once_pip_med"] = float(g["makas_once"].median())
        r["A_pip_med"], r["R_pip_med"] = float(g["A_pip"].median()), float(g["R_pip"].median())
    return r


def main() -> int:
    a = ay.oku()
    with ProcessPoolExecutor(max_workers=min(4, len(a.ciftler))) as ex:
        parca = list(ex.map(olay_isci, a.ciftler))
        izgara = list(ex.map(bg.kos_cift, a.ciftler, [a.bitis] * len(a.ciftler), [None] * len(a.ciftler)))
    df = pd.DataFrame([s for p in parca for s in p["satir"]])
    rng = np.random.default_rng(TOHUM)
    out = {"kunye": {}, "olay": {}, "davranis": {}, "suzgec": {}, "kova_haber": {}, "yol": {}, "izgara": {},
           "ters_secim": {}, "ornek": {}}
    for tf in bm.DILIMLER:
        k = str(tf)
        out["olay"][k], out["davranis"][k], out["suzgec"][k], out["yol"][k] = {}, {}, {}, {}
        for dn in ("ic", "dis"):
            g = df[(df["tf"] == tf) & (df["donem"] == dn)]
            out["olay"][k][dn] = {"n": int(len(g)), "kova": {v: int((g["kova"] == v).sum()) for v in bm.SUZGECLER["kova"]}}
            out["davranis"][k][dn] = davranis(g, rng)
        for f, vals in bm.SUZGECLER.items():
            out["suzgec"][k][f] = {v: {dn: davranis(df[(df["tf"] == tf) & (df["donem"] == dn) & (df[f] == v)], rng, False)
                                       for dn in ("ic", "dis")} for v in vals}
        # mumdan sonraki ortalama yol (A), dönem ayrı
        Y = np.vstack([p["yol"][tf] for p in parca if len(p["yol"][tf])])
        bt = df[df["tf"] == tf]["bt"].to_numpy()
        gun = df[df["tf"] == tf]["gun"].to_numpy()
        assert len(Y) == len(bt)
        for dn, m in (("ic", bt < DIS_BAS), ("dis", bt >= DIS_BAS)):
            yy, gg = Y[m], gun[m]
            nokta = []
            for h in range(bm.IZLE + 1):
                alt, ust = (gun_bootstrap(gg, yy[:, h], rng, TEKRAR) if h else (0.0, 0.0))
                nokta.append({"mum": h, "ort": float(yy[:, h].mean()), "alt": alt, "ust": ust})
            out["yol"][k][dn] = nokta
    # giriş ızgarası: 2018–2023 buyuk_gelistir.json'dan, 2024 → yeniden ölçüm (betimleme)
    iz = pd.concat(izgara, ignore_index=True)
    iz = iz[iz["bt"] >= DIS_BAS]
    for c in ["cift", "gun", "giris", "neden"] + bg.SUZ:
        iz[c] = iz[c].astype("category")
    G = json.loads((VERI / "buyuk_gelistir.json").read_text(encoding="utf-8"))
    for tf in bm.DILIMLER:
        k = str(tf)
        out["izgara"][k] = {"ic": [r for r in G["hucre"] if r["tf"] == tf]}
        out["izgara"][k]["dis"] = [{"tf": tf, "giris": gi, **bg.ozet(g)}
                                   for gi, g in iz[iz["tf"] == tf].groupby("giris", observed=True)]
    out["ters_secim"] = {"ic": G["ters_secim"], "dis": bg.ters_secim(iz)}
    for p in parca:
        out["ornek"].update({str(tf): o for tf, o in p["ornek"].items()})
    Gz = json.loads((VERI / "buyuk_gozlem.json").read_text(encoding="utf-8"))
    out["sayim_ic"] = {str(tf): {x: sum(v[x] for kk, v in Gz["sayim"].items() if kk.endswith(f"_{tf}"))
                                 for x in ("buyuk", "kume", "yeniden_acilis", "devir", "eksik", "olay")}
                       for tf in bm.DILIMLER}
    out["kararsiz_ic"] = Gz["kararsiz"]
    out["plan"] = json.loads((VERI / "buyuk_plan.json").read_text(encoding="utf-8"))
    S = json.loads((VERI / "buyuk_sina.json").read_text(encoding="utf-8"))
    out["bacak"], out["sina_davranis"] = S["bacak"], S["davranis"]
    out["kunye"] = {
        "ciftler": a.ciftler, "veri_bitis": a.bitis.isoformat(), "donem": ON["donem"],
        "girdi": {p: oz(VERI / p) for p in ("buyuk_gozlem.json", "buyuk_gelistir.json", "buyuk_plan.json",
                                             "buyuk_sina.json")},
        "onkayit": oz(BURASI / "onkayit_buyuk.toml"), "kod": {p: oz(BURASI / p) for p in KOD},
        "sabit": {"atr_n": bm.ATR_N, "esik": bm.ESIK, "kume_once": bm.KUME_ONCE, "izle": bm.IZLE,
                  "kararsiz_govde": bm.KARARSIZ_GOVDE, "bekle": bs.BEKLE, "limit_ote_a": bs.LIMIT_OTE_A,
                  "kosu_mum": bm.KOSU_MUM, "kosu_esik": bm.KOSU_ESIK, "ardisik_mum": bm.ARDISIK_MUM,
                  "kayma_pip": bs.KAYMA_PIP, "haber_kayma_pip": bs.HABER_KAYMA_PIP, "en_az_risk_pip": bs.EN_AZ_RISK_PIP,
                  "giris_sayisi": len(bs.hepsi()), "makas_once_dk": bm.MAKAS_ONCE_DK},
    }
    (VERI / "buyuk_ders.json").write_text(json.dumps(out, ensure_ascii=False, separators=(",", ":")) + "\n",
                                          encoding="utf-8")
    print(f"✓ veri/buyuk_ders.json ({len(df)} olay)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
