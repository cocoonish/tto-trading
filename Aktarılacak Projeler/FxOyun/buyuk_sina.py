#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Büyük mum planının sınaması: 2018–2023 (planın yazıldığı dönem) ve 2024 → (planın hiç görmediği dönem).

Plan veri/buyuk_plan.json'dan okunur (buyuk_secim.py, ön kayıt kuralıyla, 2024 görülmeden yazdı); bu betik planı
DEĞİŞTİRMEZ. Başlarken ön kaydın [tanim] ve [maliyet] sabitlerini kodla kıyaslar; ayrışırsa koşmaz. Her işlem ve
referans girişi iki dönemde aynı kodla (buyuk_sim.simule) koşar. Hüküm yalnız 2024 → için, ön kaydın [hukum]
kuralıyla (işlem günü düzeyinde bootstrap) verilir. Gözlemin betimleyici ölçüleri de iki dönemde yan yana ölçülür.

Çıktı: veri/buyuk_sina.json (özetler, günlük R dizileri) ve veri/_yerel/buyuk_sina_islemler.parquet (git dışı).
"""
from __future__ import annotations

import hashlib
import json
import sys
import tomllib
from pathlib import Path

import numpy as np
import pandas as pd

import buyuk_mum as bm
import buyuk_sim as bs
from buyuk_gelistir import haber_sn

import ayar as ay  # noqa: E402
import veri as vr  # noqa: E402

BURASI = Path(__file__).resolve().parent
VERI = BURASI / "veri"
ON_YOL = BURASI / "onkayit_buyuk.toml"
ON = tomllib.loads(ON_YOL.read_text(encoding="utf-8"))
PLAN_YOL = VERI / "buyuk_plan.json"
PLAN = json.loads(PLAN_YOL.read_text(encoding="utf-8"))
DIS_BAS = int(pd.Timestamp(ON["donem"]["dis"][0]).timestamp())


def sabit_denetimi() -> None:
    t, m = ON["tanim"], ON["maliyet"]
    beklenen = {
        "dilimler": (t["dilimler"], bm.DILIMLER), "atr_n": (t["atr_n"], bm.ATR_N), "esik": (t["esik"], bm.ESIK),
        "kume_once": (t["kume_once"], bm.KUME_ONCE), "kararsiz_govde": (t["kararsiz_govde"], bm.KARARSIZ_GOVDE),
        "izle_mum": (t["izle_mum"], bm.IZLE), "doluluk": (t["doluluk"], bm.DOLULUK),
        "devir": (tuple(t["devir"]), tuple(bm.DEVIR)),
        "acilis_bosluk": (t["acilis_bosluk_saat"] * 3600, bm.ACILIS_BOSLUK_SN),
        "acilis_pay": (t["acilis_pay_dk"] * 60, bm.ACILIS_PAY_SN),
        "kayma": (m["kayma_pip"], bs.KAYMA_PIP), "haber_kayma": (m["haber_kayma_pip"], bs.HABER_KAYMA_PIP),
        "en_az_risk": (m["en_az_risk_pip"], bs.EN_AZ_RISK_PIP), "bekle": (m["bekle_mum"], bs.BEKLE),
    }
    ayri = {k: v for k, v in beklenen.items() if v[0] != v[1]}
    if ayri:
        raise SystemExit(f"ön kayıt ile kod ayrışıyor: {ayri}")
    if PLAN["onkayit_ozu"] != hashlib.sha256(ON_YOL.read_bytes()).hexdigest():
        raise SystemExit("plan başka bir ön kayıttan yazılmış")


def donem(bt: int) -> str:
    return "dis" if bt >= DIS_BAS else "ic"


def kimlik(rol: str, x: dict) -> str:
    return f"{rol}:{x['tf']}:{x['giris']}:{x['suzgec'] or '-'}={x['deger'] or '-'}"


def gun_bootstrap(gun: np.ndarray, r: np.ndarray, rng: np.random.Generator, tekrar: int):
    """İşlem günü düzeyinde yeniden örnekleme: günler yerine konarak çekilir, ortalama = Σ R / işlem sayısı."""
    if len(r) < 2:
        return None, None
    _, k = np.unique(gun, return_inverse=True)
    toplam = np.bincount(k, weights=r)
    sayi = np.bincount(k).astype(float)
    D = len(toplam)
    sec = rng.integers(0, D, size=(tekrar, D))
    ort = toplam[sec].sum(axis=1) / sayi[sec].sum(axis=1)
    return float(np.quantile(ort, 0.025)), float(np.quantile(ort, 0.975))


def ozet(g: pd.DataFrame, rng: np.random.Generator | None = None) -> dict:
    r = g["R"].to_numpy(float)
    out = {"n": int(len(r)), "gun_n": int(g["gun"].nunique()) if len(g) else 0}
    if not len(r):
        return out
    b = g["brut_R"].dropna().to_numpy(float)
    out.update(kazanma=float((r > 0).mean()), ort_R=float(r.mean()), toplam_R=float(r.sum()),
               brut_R=float(b.mean()) if len(b) else None, brut_n=int(len(b)),
               risk_pip_med=float(g["risk_pip"].median()))
    if rng is not None and len(r) >= 2:
        out["alt"], out["ust"] = gun_bootstrap(g["gun"].to_numpy(), r, rng, ON["hukum"]["bootstrap"])
    return out


def hukum(o: dict) -> str:
    h = ON["hukum"]
    if o["n"] < h["en_az_islem"]:
        return "olculemedi"
    if o.get("alt", -1) > 0:
        return "calisiyor"
    return "zayif" if o["ort_R"] > 0 else "calismiyor"


def main() -> int:
    sabit_denetimi()
    a = ay.oku()
    bacaklar = [("islem", x) for x in PLAN["islem"]] + [("referans", x) for x in PLAN["referans"]]
    girisler = {kimlik(r, x): (r, x, bs.coz(x["giris"])) for r, x in bacaklar}
    islemler, olaylar = [], []
    for cift in a.ciftler:
        d = vr.oku(cift, a)
        do = bs.Orta(d)
        hs = haber_sn(cift)
        for tf in bm.DILIMLER:
            ev, _ = bm.olaylar(d, tf, cift)
            for e in ev.to_dict("records"):
                dn = donem(e["bt"])
                if dn == "ic" and e["bt"] + (bm.IZLE + 1) * tf * 60 > DIS_BAS:
                    continue                                     # penceresi dönem sınırını aşan olay
                if e["yon"] == 0:
                    continue
                g, y = bm.olc(d, e)
                olaylar.append({"cift": cift, "tf": tf, "gun": e["gun"], "donem": dn,
                                **{k: g[k] for k in ("sim_1.0", "geri_0.5", "net_24")},
                                "ayna_geri_0.5": y["geri_0.5"]})
                for k, (rol, x, gi) in girisler.items():
                    if x["tf"] != tf or (x["suzgec"] and e[x["suzgec"]] != x["deger"]):
                        continue
                    r = bs.simule(d, e, gi, hs)
                    if r is None:
                        continue
                    b = bs.simule(do, e, gi, hs, kayma_pip=0.0, haber_kayma_pip=0.0)
                    islemler.append({"bacak": k, "rol": rol, "cift": cift, "tf": tf, "bt": e["bt"], "gun": e["gun"],
                                     "donem": dn, **r, "brut_R": None if b is None else b["R"]})
            print(f"  {cift} {tf} dk: {len(islemler)} işlem", flush=True)
        del d, do
    df = pd.DataFrame(islemler)
    rng = np.random.default_rng(ON["hukum"]["tohum"])
    sonuc = []
    for k, (rol, x, gi) in girisler.items():
        g = df[df["bacak"] == k]
        satir = {"rol": rol, "bacak": k, "tf": x["tf"], "giris": x["giris"], "suzgec": x["suzgec"],
                 "deger": x["deger"], "okuma": x.get("okuma")}
        for dn in ("ic", "dis"):
            gd = g[g["donem"] == dn]
            satir[dn] = ozet(gd, rng if dn == "dis" else None)
            satir[dn]["cift"] = {c: ozet(gg) for c, gg in gd.groupby("cift")}
            satir[dn]["yil"] = {str(yl): ozet(gg) for yl, gg in gd.groupby(pd.to_datetime(gd["bt"], unit="s").dt.year)}
            gunluk = gd.groupby("gun")["R"].sum().sort_index()
            satir[dn]["gunluk"] = [[str(i), round(float(v), 4)] for i, v in gunluk.items()]
        satir["hukum"] = hukum(satir["dis"])
        sonuc.append(satir)
    ol = pd.DataFrame(olaylar)
    davranis = []
    for tf in bm.DILIMLER:
        for dn in ("ic", "dis"):
            g = ol[(ol["tf"] == tf) & (ol["donem"] == dn)]
            r = {"tf": tf, "donem": dn, "n": int(len(g))}
            if not len(g):
                davranis.append(r)
                continue
            for m in ON["davranis"]["olculer"]:
                v = g[m].astype(float)
                ok = v.notna().to_numpy()
                r[m] = float(v.mean())
                r[f"{m}_alt"], r[f"{m}_ust"] = gun_bootstrap(g["gun"].to_numpy()[ok], v.to_numpy()[ok], rng,
                                                              ON["hukum"]["bootstrap"])
            r["ayna_geri_0.5"] = float(g["ayna_geri_0.5"].astype(float).mean())
            fark = (g["geri_0.5"].astype(float) - g["ayna_geri_0.5"].astype(float)).to_numpy()
            r["geri_0.5_fark_alt"], r["geri_0.5_fark_ust"] = gun_bootstrap(g["gun"].to_numpy(), fark, rng,
                                                                          ON["hukum"]["bootstrap"])
            davranis.append(r)
    out = {"plan_ozu": hashlib.sha256(PLAN_YOL.read_bytes()).hexdigest(),
           "onkayit_ozu": hashlib.sha256(ON_YOL.read_bytes()).hexdigest(),
           "kod_ozu": {p: hashlib.sha256((BURASI / p).read_bytes()).hexdigest()
                       for p in ("buyuk_mum.py", "buyuk_sim.py", "buyuk_sina.py", "sinif.py")},
           "veri_bitis": a.bitis.isoformat(), "bacak": sonuc, "davranis": davranis}
    (VERI / "buyuk_sina.json").write_text(json.dumps(out, ensure_ascii=False, separators=(",", ":")) + "\n",
                                          encoding="utf-8")
    (VERI / "_yerel").mkdir(exist_ok=True)
    df.to_parquet(VERI / "_yerel" / "buyuk_sina_islemler.parquet", index=False)
    for s in sonuc:
        i, o = s["ic"], s["dis"]
        print(f"  {s['rol']:8} {s['tf']:>2} {s['giris']:24} {s['suzgec'] or '-'}={s['deger'] or '-':8} "
              f"iç n {i['n']:6} kaz {i.get('kazanma', 0):.1%} R {i.get('ort_R', 0):+.3f} | "
              f"dış n {o['n']:6} kaz {o.get('kazanma', 0):.1%} R {o.get('ort_R', 0):+.3f} "
              f"[{o.get('alt', float('nan')):+.3f}, {o.get('ust', float('nan')):+.3f}] brüt {o.get('brut_R') or 0:+.3f} "
              f"{s['hukum']}")
    for r in davranis:
        if not r["n"]:
            continue
        print(f"  davranış {r['tf']:>2} {r['donem']}: n {r['n']} ±1A devam {r['sim_1.0']:.3f} · yarıya dönüş "
              f"{r['geri_0.5']:.3f} (ayna {r['ayna_geri_0.5']:.3f}) · net24 {r['net_24']:+.3f} A")
    return 0


if __name__ == "__main__":
    sys.exit(main())
