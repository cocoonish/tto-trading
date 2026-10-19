#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Oyun planının sınaması: 2018–2023 (planın yazıldığı dönem) ve 2024 → (planın hiç görmediği dönem).

Plan veri/plan.json'dan okunur (secim.py, ön kayıt kuralıyla, 2024 görülmeden yazdı); bu betik planı DEĞİŞTİRMEZ.
Her işlem ve referans bacağı, iki dönemde aynı kodla (kosu.simule) koşar. Hüküm yalnız 2024 → için, ön kaydın
[hukum] kuralıyla verilir. Ayrıca gözlemin betimleyici ölçüleri (orta noktaya dönüş, devam, dönüş) iki dönemde
yan yana hesaplanır: plan bir davranışa dayanıyorsa önce o davranışın sürüp sürmediği sorulur.
"""
from __future__ import annotations

import hashlib
import json
import sys
import tomllib
from pathlib import Path

import numpy as np
import pandas as pd

import gozlem as gz
import oyun_sim as kosu
import sinif as sf

import ayar as ay  # noqa: E402
import veri as vr  # noqa: E402

BURASI = Path(__file__).resolve().parent
ON = tomllib.loads((BURASI / "onkayit_oyun.toml").read_text(encoding="utf-8"))
PLAN = json.loads((BURASI / "veri" / "plan.json").read_text(encoding="utf-8"))
DIS_BAS = pd.Timestamp(ON["donem"]["dis"][0]).timestamp()


def donem(t0: int) -> str:
    return "dis" if t0 >= DIS_BAS else "ic"


def bacak(b: dict) -> kosu.Bacak:
    return kosu.Bacak(b["tur"], b["hedef"], b["tampon"], b["bekle"])


def kimlik(rol: str, x: dict) -> str:
    b = x["bacak"]
    return f"{rol}:{x['aile']}:{x['sinif']}:{b['tur']}:{b['hedef']}:{b['tampon']}"


def ozet(r: np.ndarray, rng: np.random.Generator | None = None) -> dict:
    out = {"n": int(len(r))}
    if len(r) == 0:
        return out
    out.update(kazanma=float((r > 0).mean()), ort_R=float(r.mean()), toplam_R=float(r.sum()))
    if rng is not None and len(r) >= 2:
        h = ON["hukum"]
        ort = np.array([rng.choice(r, len(r)).mean() for _ in range(h["bootstrap"])])
        out["alt"], out["ust"] = float(np.quantile(ort, 0.025)), float(np.quantile(ort, 0.975))
    return out


def hukum(o: dict) -> str:
    h = ON["hukum"]
    if o["n"] < h["en_az_islem"]:
        return "olculemedi"
    if o.get("alt", -1) > 0:
        return "calisiyor"
    return "zayif" if o["ort_R"] > 0 else "calismiyor"


def main() -> int:
    a = ay.oku()
    bacaklar = [("islem", x) for x in PLAN["islem"]] + [("referans", x) for x in PLAN["referans"]]
    islemler, olaylar = [], []
    for cift in a.ciftler:
        d = vr.oku(cift, a)
        do = kosu.orta(d)
        for an in sf.ANLAR:
            ev = sf.olaylar(d, an, cift)
            if len(ev) == 0:
                continue
            for e in ev.to_dict("records"):
                e["donem"] = donem(e["t0"])
                o = gz.sonuc(d, e)
                olaylar.append({**{k: e[k] for k in ("cift", "an", "sinif", "uyum", "yon", "donem", "trend")}, **o})
                for rol, x in bacaklar:
                    if x["aile"] != an.aile or x["sinif"] != e["sinif"]:
                        continue
                    r = kosu.simule(d, e, bacak(x["bacak"]))
                    if r is not None:
                        r.update(rol=rol, bacak=kimlik(rol, x), aile=an.aile, donem=e["donem"],
                                 brut_R=kosu.brut(do, e, bacak(x["bacak"])))
                        islemler.append(r)
        print(f"  {cift}: {len(islemler)} işlem", flush=True)
    df = pd.DataFrame(islemler)
    rng = np.random.default_rng(ON["hukum"]["tohum"])
    sonuc = []
    for rol, x in bacaklar:
        k = kimlik(rol, x)
        g = df[df["bacak"] == k]
        satir = {"rol": rol, "bacak": k, "aile": x["aile"], "sinif": x["sinif"], **{f: x["bacak"][f] for f in x["bacak"]}}
        for dn in ("ic", "dis"):
            gd = g[g["donem"] == dn]
            satir[dn] = ozet(gd["R"].to_numpy(), rng if dn == "dis" else None)
            bb = gd["brut_R"].dropna()                      # orta fiyatta dolmayan emir brüt ortalamaya girmez
            satir[dn]["brut_R"] = float(bb.mean()) if len(bb) else None
            satir[dn]["brut_n"] = int(len(bb))
            satir[dn]["cift"] = {c: ozet(gg["R"].to_numpy()) for c, gg in gd.groupby("cift")}
            satir[dn]["yil"] = {str(y): ozet(gg["R"].to_numpy())
                                for y, gg in gd.groupby(pd.to_datetime(gd["t0"], unit="s").dt.year)}
        satir["hukum"] = hukum(satir["dis"])
        sonuc.append(satir)
    # davranış iki dönemde
    ol = pd.DataFrame(olaylar)
    davranis = []
    for dn in ("ic", "dis"):
        for r in gz.topla(ol[ol["donem"] == dn], ["an", "sinif"]):
            davranis.append({"donem": dn, **r})
    out = {"plan_ozu": hashlib.sha256((BURASI / "veri" / "plan.json").read_bytes()).hexdigest(),
           "onkayit_ozu": hashlib.sha256((BURASI / "onkayit_oyun.toml").read_bytes()).hexdigest(),
           "kod_ozu": {p: hashlib.sha256((BURASI / p).read_bytes()).hexdigest()
                       for p in ("sinif.py", "oyun_sim.py", "gozlem.py", "sina.py")},
           "veri_bitis": a.bitis.isoformat(), "bacak": sonuc, "davranis": davranis}
    (BURASI / "veri" / "sina.json").write_text(json.dumps(out, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    with __import__("gzip").open(BURASI / "veri" / "sina_islemler.csv.gz", "wt", encoding="utf-8") as f:
        df.to_csv(f, index=False)
    for s in sonuc:
        i, o = s["ic"], s["dis"]
        print(f"  {s['rol']:8} {s['aile']:8} {s['sinif']:11} {s['tur']}:{s['hedef']}:t{s['tampon']:<5} "
              f"iç n {i['n']:5} kaz {i.get('kazanma', 0):.1%} R {i.get('ort_R', 0):+.3f} | "
              f"dış n {o['n']:5} kaz {o.get('kazanma', 0):.1%} R {o.get('ort_R', 0):+.3f} "
              f"[{o.get('alt', float('nan')):+.3f}, {o.get('ust', float('nan')):+.3f}] {s['hukum']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
