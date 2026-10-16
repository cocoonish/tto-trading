#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Takvimdeki her olayın SAATİNİ 1 dakikalık fiyattan ayrıca sınar.

Resmi metin saati söyler; fiyat onu ayrıca doğrular. Bir veri yayımı ya da faiz kararı
duyurulduğu dakikada fiyatın dakikalık aralığı birkaç kat büyür. Sınama, olay
saatinin −20/+20 dakikalık penceresinde dakikalık mid aralığının (yüksek − düşük)
en büyük olduğu dakikayı bulur: o dakika olay dakikası ya da sonraki iki dakikadan
biriyse olay o paritede "doğrulandı" sayılır. Aynı ölçü bir saat önce ve sonra
(yaz saati hatası), yarım saat önce ve sonra (ECB 13:45 ↔ 14:15 değişimi) de
hesaplanır: resmi saatten daha iyi oturan bir aday saat varsa kayda yazılır.

Basın toplantıları bu sınamaya girmez: başlangıçlarında tek dakikalık bir sıçrama
yoktur (konuşma yavaş yayılır) ve karar dakikasının oynaklığı pencereyi doldurur.
Onlar için yalnız bilgi verilir: toplantının ilk 15 dakikasındaki aralığın, önceki
15 dakikaya oranı.

Hüküm olay başına: değerlendirilebilen paritelerin çoğunluğunda doğrulandıysa olay
analize girer; değilse `takvim.py` onu dışarıda bırakır ve sebebi sayfada sayılır.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

import ayar as ay
import takvim as tk
import veri as vr

BURASI = Path(__file__).resolve().parent
CIKTI = BURASI / "veri" / "takvim" / "sinama.json"
PENCERE_DK = 20
KABUL_DK = (0, 2)
BASIN = {"FOMC_basin", "ECB_basin"}


def _aralik(d: vr.Dakika, bas: int, son: int) -> tuple[np.ndarray, np.ndarray]:
    i, j = np.searchsorted(d.t, [bas, son])
    return d.t[i:j], (d.mh[i:j] - d.ml[i:j]) / d.pip


def tepe(d: vr.Dakika, t0: int) -> dict | None:
    t, a = _aralik(d, t0 - PENCERE_DK * 60, t0 + (PENCERE_DK + 1) * 60)
    if len(t) < 25:
        return None
    k = int(np.argmax(a))
    on = a[t < t0 - 120]
    taban = float(np.median(on)) if len(on) >= 5 else float("nan")
    return {"tepe_dk": int((t[k] - t0) // 60), "tepe_pip": float(a[k]),
            "oran": float(a[k] / taban) if taban and np.isfinite(taban) and taban > 0 else float("nan")}


def aday_saatler(d: vr.Dakika, t0: int) -> dict:
    """Resmi saatin ±30 ve ±60 dakika ötesinde aynı ölçü: olay dakikası ±2 içinde en büyük aralığın,
    o adayın öncesindeki medyana oranı."""
    out = {}
    for kay in (-60, -30, 0, 30, 60):
        ta = t0 + kay * 60
        t, a = _aralik(d, ta - 30 * 60, ta + 3 * 60)
        if len(t) < 20:
            continue
        on = a[t < ta - 120]
        pen = a[(t >= ta) & (t <= ta + 120)]
        if len(on) >= 5 and len(pen) and np.median(on) > 0:
            out[str(kay)] = float(pen.max() / np.median(on))
    return out


def basin_bilgisi(d: vr.Dakika, t0: int) -> dict | None:
    t, a = _aralik(d, t0 - 15 * 60, t0 + 15 * 60)
    once, sonra = a[t < t0], a[t >= t0]
    if len(once) < 10 or len(sonra) < 10 or once.mean() <= 0:
        return None
    return {"ilk15_once15_orani": float(sonra.mean() / once.mean())}


def main() -> int:
    a = ay.oku()
    olay = tk.tumu(dogrulanmis=False)
    veriler = {}
    for cift in a.ciftler:
        try:
            veriler[cift] = vr.oku(cift, a)
        except FileNotFoundError:
            print(f"{cift}: arşiv yok, sınamaya girmez")
    satir = []
    for _, o in olay.iterrows():
        t0 = int(o["utc_sn"])
        kayit = {"olay": o["olay"], "tarih": o["tarih"], "yerel_saat": o["yerel_saat"], "bolge": o["bolge"],
                 "parite": {}}
        for cift in o["ciftler"].split():
            d = veriler.get(cift)
            if d is None:
                continue
            if o["olay"] in BASIN:
                b = basin_bilgisi(d, t0)
                if b:
                    kayit["parite"][cift] = b
                continue
            tp = tepe(d, t0)
            if tp is None:
                kayit["parite"][cift] = {"durum": "veri_yok"}
                continue
            tp["durum"] = "dogrulandi" if KABUL_DK[0] <= tp["tepe_dk"] <= KABUL_DK[1] else "tutmadi"
            tp["aday"] = aday_saatler(d, t0)
            kayit["parite"][cift] = tp
        if o["olay"] in BASIN:
            kayit["hukum"] = "basin_bilgi"
        else:
            dur = [v["durum"] for v in kayit["parite"].values() if v.get("durum") in ("dogrulandi", "tutmadi")]
            if not dur:
                kayit["hukum"] = "degerlendirilemedi"
            else:
                kayit["hukum"] = "dogrulandi" if dur.count("dogrulandi") * 2 > len(dur) else "tutmadi"
        satir.append(kayit)
    ozet: dict = {}
    for k in satir:
        oz = ozet.setdefault(k["olay"], {})
        oz[k["hukum"]] = oz.get(k["hukum"], 0) + 1
    tutmayan = [f"{k['olay']} {k['tarih']} {k['yerel_saat']} {k['bolge']}: "
                + ", ".join(f"{c} tepe {v.get('tepe_dk')} dk" for c, v in k["parite"].items() if "tepe_dk" in v)
                for k in satir if k["hukum"] == "tutmadi"]
    CIKTI.write_text(json.dumps({"kural": {"pencere_dk": PENCERE_DK, "kabul_dk": list(KABUL_DK)},
                                 "ozet": ozet, "tutmayan": tutmayan, "olay": satir},
                                ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    for o, v in ozet.items():
        print(f"{o:12s} {v}")
    for s in tutmayan:
        print("  tutmadı:", s)
    return 0


if __name__ == "__main__":
    sys.exit(main())
