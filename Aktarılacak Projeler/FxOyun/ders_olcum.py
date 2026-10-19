#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Oyun planı derslerinin ölçüm dosyası → veri/ders.json (figürler ve ders metni YALNIZ buradan okur).

Girdiler: gozlem.json (2018–2023 davranışı, trend ayrımıyla), sina.json (planın iki dönemdeki sonucu ve davranış),
plan.json (ön kayıtlı bacaklar) ve dakika verisi (ortalama patikalar, örnek günler, fiksingde ay sonu ayrımı).
Ölçüm dosyası her girdinin ve her kod dosyasının sha256 özünü taşır; kapı (dogrula.py) özleri yeniden hesaplar.
"""
from __future__ import annotations

import gzip
import hashlib
import json
import sys
from datetime import date
from pathlib import Path

import numpy as np
import pandas as pd

import gozlem as gz
import sinif as sf
from sina import donem as donem_bul

import ayar as ay  # noqa: E402
import veri as vr  # noqa: E402
import zaman as z  # noqa: E402

BURASI = Path(__file__).resolve().parent
VERI = BURASI / "veri"
ADIM = 5                                   # patika örnekleme aralığı (dk)

def _patika_dk(pencere: int) -> np.ndarray:
    """İlk mumun kapanışından itibaren dakika noktaları: 0, 5, 10, … ve pencerenin son dakikası."""
    return np.r_[np.arange(0, pencere, ADIM), pencere - 1]


ORNEK_CIFT, ORNEK_AN, ORNEK_SON = "EURUSD", "londra_acilis", "2023-12-01"   # örnek gün: bu tarihten önceki SON uygun gün
#                                                                          (Aralık'ın tatil haftaları ince işlem görür)
AILE_AD = {"acilis": "Seans açılışları", "fiksing": "Fiksingler", "veri": "ABD verileri", "mb": "Merkez bankası kararları"}
BASAMAK = {"EURUSD": 5}                   # fiyat = nokta / 10^basamak (örnek gün yalnız EUR/USD)
ORNEKLER = ["guclu", "reddedilen", "normal", "kucuk"]
METRIK = ("orta", "devam", "donus", "orta_uc", "kapanis")


def oz(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def havuz(rows: list[dict]) -> dict:
    """Satırları yönlü olay sayısıyla ağırlıklandırarak birleştirir."""
    n = sum(r.get("n_yonlu", 0) for r in rows)
    out = {"n": n}
    for m in METRIK:
        out[m] = sum(r[m] * r["n_yonlu"] for r in rows if m in r) / n if n else None
    return out


def tsi_tablosu() -> list[dict]:
    yaz, kis = date(2026, 7, 15), date(2026, 1, 15)
    takv = pd.read_csv(sf.FXG / "veri" / "takvim" / "olaylar.csv", dtype=str)
    out = []
    for an in sf.ANLAR:
        saat = an.saat
        if an.olay:
            saat = takv[takv["olay"] == an.olay]["yerel_saat"].iloc[-1]     # bugünkü saat (ECB 21.07.2022'den beri 14:15)
        out.append({"an": an.kimlik, "ad": an.ad, "aile": an.aile, "bolge": z.BOLGE_ADI[an.bolge], "yerel": saat,
                    "tsi_yaz": z.tsi_saat(z.yerel_an(yaz, saat, an.bolge)),
                    "tsi_kis": z.tsi_saat(z.yerel_an(kis, saat, an.bolge)), "tf": an.tf, "pencere": an.pencere})
    return out


def main() -> int:
    G = json.loads((VERI / "gozlem.json").read_text(encoding="utf-8"))
    S = json.loads((VERI / "sina.json").read_text(encoding="utf-8"))
    P = json.loads((VERI / "plan.json").read_text(encoding="utf-8"))
    # ── davranış: an düzeyi (sina.json) ve aile düzeyi (havuz)
    dav = {}
    for r in S["davranis"]:
        if "orta" in r:
            dav.setdefault(r["donem"], {}).setdefault(r["an"], {})[r["sinif"]] = r
    aile_dav = {}
    for dn, ans in dav.items():
        for an in sf.ANLAR:
            for s in ("guclu", "normal", "reddedilen"):
                rows = [ans[a.kimlik][s] for a in sf.ANLAR if a.aile == an.aile and s in ans.get(a.kimlik, {})]
                aile_dav.setdefault(dn, {}).setdefault(an.aile, {})[s] = havuz(rows)
    # ── trend ayrımı (yalnız 2018–2023, gözlem dosyasından)
    trend = {}
    for aile in AILE_AD:
        for s in ("guclu", "normal", "reddedilen"):
            for u in ("trendle", "karsi", "yatay"):
                rows = [r for r in G["sinif"] if sf.AN[r["an"]].aile == aile and r["sinif"] == s and r["uyum"] == u
                        and "orta" in r]
                trend.setdefault(aile, {}).setdefault(s, {})[u] = havuz(rows)
    # ── küçük mum: kırılım
    kucuk = {}
    for r in S["davranis"]:
        if r["sinif"] == "kucuk":
            kucuk.setdefault(r["donem"], {})[r["an"]] = {k: r[k] for k in ("n", "kirilim_1R") if k in r}
    # ── dakika verisinden: patikalar, örnek günler, fiksingde ay sonu
    a = ay.oku()
    patika: dict = {}
    ornek: dict = {}
    fiks: dict = {}
    for cift in a.ciftler:
        d = vr.oku(cift, a)
        for an in sf.ANLAR:
            ev = sf.olaylar(d, an, cift)
            PATIKA_DK = _patika_dk(an.pencere)
            for e in ev.to_dict("records"):
                dn = donem_bul(e["t0"])
                R = e["h"] - e["l"]
                if an.aile == "fiksing":
                    o = gz.sonuc(d, e)
                    if "orta" in o:
                        k = (an.kimlik, dn, "ay_sonu" if e["ay_sonu"] else "diger", e["sinif"])
                        fiks.setdefault(k, []).append(o)
                if e["yon"] == 0 or R <= 0:
                    continue
                # dakika verisinde boşluk olabilir: noktalar SAATTEN aranır (o dakikada ya da hemen öncesinde son fiyat)
                idx = np.searchsorted(d.t, d.t[e["j0"]] + PATIKA_DK[1:] * 60, side="right") - 1
                if idx.min() >= e["j0"] and idx.max() < e["j1"]:
                    yol = np.r_[0.0, (d.mc[idx] - e["c"]) / R * e["yon"]]      # 0. nokta: ilk mumun kapanışı
                    patika.setdefault((an.kimlik, e["sinif"], dn), []).append(yol)
                if cift == ORNEK_CIFT and an.kimlik == ORNEK_AN and str(e["gun"]) < ORNEK_SON and gz.sonuc(d, e).get("orta"):
                    ornek[e["sinif"]] = (e, d)                            # sınıfın SON uygun günü kalır (orta noktaya dönen)
            if cift == ORNEK_CIFT and an.kimlik == ORNEK_AN:
                for e in ev[(ev["sinif"] == "kucuk")].to_dict("records"):
                    if str(e["gun"]) < ORNEK_SON:
                        ornek["kucuk"] = (e, d)
        print(f"  {cift} tamam", flush=True)
    pat = {}
    for (an, s, dn), yollar in sorted(patika.items()):
        m = np.vstack(yollar)
        pat.setdefault(an, {}).setdefault(s, {})[dn] = {"n": int(len(m)),
                                                          "dk": [int(x) for x in _patika_dk(sf.AN[an].pencere)],
                                                          "ortalama": [round(float(x), 4) for x in m.mean(0)],
                                                          "medyan": [round(float(x), 4) for x in np.median(m, 0)]}
    orn = {}
    for s, (e, d) in ornek.items():
        bas = e["t0"] - 30 * 60
        bit = e["t0"] + (sf.AN[ORNEK_AN].tf + sf.AN[ORNEK_AN].pencere) * 60
        i0, i1 = np.searchsorted(d.t, bas), np.searchsorted(d.t, bit)
        df = pd.DataFrame({"t": d.t[i0:i1], "o": d.mo[i0:i1], "h": d.mh[i0:i1], "l": d.ml[i0:i1], "c": d.mc[i0:i1]})
        df["k"] = (df["t"] - bas) // (ADIM * 60)
        m = df.groupby("k").agg(t=("t", "first"), o=("o", "first"), h=("h", "max"), l=("l", "min"), c=("c", "last"))
        orn[s] = {"gun": str(e["gun"]), "t0": int(e["t0"]), "tf": sf.AN[ORNEK_AN].tf, "pip": e["pip"],
                  "basamak": BASAMAK[ORNEK_CIFT],
                  "ilk": {k: float(e[k]) for k in "ohlc"}, "yon": int(e["yon"]), "uyum": e["uyum"],
                  "tsi": z.tsi_saat(pd.Timestamp(e["t0"], unit="s", tz="UTC").to_pydatetime()),
                  "mumlar": [[int(r.t), float(r.o), float(r.h), float(r.l), float(r.c)] for r in m.itertuples()]}
    fk = {}
    for (an, dn, grup, s), rows in sorted(fiks.items()):
        g = pd.DataFrame(rows)
        fk.setdefault(an, {}).setdefault(dn, {}).setdefault(grup, {})[s] = {
            "n": int(len(g)), **{m: float(g[m].mean()) for m in ("orta", "devam", "donus")}}
    # ── bacaklar ve 2024 → eğrileri
    isl = pd.read_csv(VERI / "sina_islemler.csv.gz")
    egri, dagilim = {}, {}
    for b in S["bacak"]:
        for dn in ("ic", "dis"):
            g = isl[(isl["bacak"] == b["bacak"]) & (isl["donem"] == dn)]
            if len(g):
                k, y = g[g["R"] > 0], g[g["R"] <= 0]
                dagilim.setdefault(b["bacak"], {})[dn] = {
                    "risk_pip_med": float(g["risk_pip"].median()),
                    "kazanc_ort": float(k["R"].mean()) if len(k) else None,
                    "kayip_ort": float(y["R"].mean()) if len(y) else None,
                    "neden": {n: int(x) for n, x in g["neden"].value_counts().items()}}
        if b["rol"] != "islem":
            continue
        g = isl[(isl["bacak"] == b["bacak"]) & (isl["donem"] == "dis")].sort_values("giris_dk")
        egri[b["bacak"]] = [[str(pd.Timestamp(t, unit="s").date()), round(float(x), 4)]
                            for t, x in zip(g["giris_dk"], g["R"].cumsum())]
    out = {
        "kunye": {"gozlem": oz(VERI / "gozlem.json"), "sina": oz(VERI / "sina.json"), "plan": oz(VERI / "plan.json"),
                  "onkayit": oz(BURASI / "onkayit_oyun.toml"),
                  "kod": {p: oz(BURASI / p) for p in ("sinif.py", "gozlem.py", "gelistir.py", "oyun_sim.py",
                                                       "secim.py", "sina.py", "ders_olcum.py")},
                  "veri_bitis": S["veri_bitis"], "ic": ["2018-01-01", "2023-12-31"], "dis_bas": "2024-01-01",
                  "olay_ic": G["olay"], "adim_dk": ADIM, "ciftler": list(a.ciftler)},
        "an": tsi_tablosu(), "davranis": dav, "aile_davranis": aile_dav, "trend": trend, "kucuk": kucuk,
        "patika": pat, "ornek": orn, "fiksing_ay_sonu": fk, "bacak": S["bacak"], "dagilim": dagilim, "plan": P, "egri": egri,
        "sabit": {"tipik_pencere": sf.TIPIK_PENCERE, "tipik_en_az": sf.TIPIK_EN_AZ, "haber_pencere": sf.HABER_PENCERE,
                  "haber_en_az": sf.HABER_EN_AZ, "guclu_aralik": sf.GUCLU_ARALIK, "guclu_govde": sf.GUCLU_GOVDE,
                  "red_govde": sf.RED_GOVDE, "red_fitil": sf.RED_FITIL, "red_aralik": sf.RED_ARALIK,
                  "kucuk_aralik": sf.KUCUK_ARALIK, "ema_n": sf.EMA_N, "ema_egim": sf.EMA_EGIM},
    }
    (VERI / "ders.json").write_text(json.dumps(out, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    print("✓ veri/ders.json")
    return 0


if __name__ == "__main__":
    sys.exit(main())
