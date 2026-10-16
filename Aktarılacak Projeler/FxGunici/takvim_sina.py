#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Takvimdeki her olayın SAATİNİ 1 dakikalık fiyattan ayrıca sınar.

Resmi metin saati söyler; fiyat onu ayrıca SINAR, ama yalnız ÇÜRÜTEBİLİR. Ölçü: olay dakikası ve sonraki iki
dakikanın en büyük dakikalık mid aralığının, olaydan önceki 30 → 3 dakikanın medyan aralığına oranı (sıçrama
oranı). Aynı oran bir saat önce ve sonra (yaz saati hatası) ve yarım saat önce ve sonra (ECB 13:45 ↔ 14:15
değişimi) da hesaplanır. Parite başına üç hâl:
  · doğrulandı — resmi saatte oran ≥ ESIK
  · çelişki    — bir aday saatte oran ≥ ESIK ve resmi saatin oranının en az iki katı (aday daha iyi oturuyor)
  · sessiz     — ikisi de değil: piyasa o dakikada kımıldamadı
Olay hükmü değerlendirilebilen paritelerden: çoğunlukta çelişki → "çelişki"; değilse en az bir parite
doğruladıysa "doğrulandı"; değilse "sessiz". HİÇBİR olay fiyat yüzünden dışarıda kalmaz (`takvim.celiskiler`
yalnız raporlar): resmi belge birincil kaynaktır, beklenen bir karar fiyatı oynatmayabilir ve tepkisiz ya da
çelişkili olayları atmak haber stratejilerinin örneklemini sonuca göre seçmek olurdu. İki örnek ölçüldü
(16.10.2026): 10.04.2020 TÜFE'si Paskalya cumasında, dakikalık aralıkların 0,1–4 pip olduğu bir piyasada
yayımlandı ve aday saatlerdeki gürültü "daha iyi" oturdu; 12.12.2019 ECB kararında aday saat basın
toplantısının içine düşüyor.

ESİK ölçüldü (16.10.2026, EUR/USD): olay dışı günlerde aynı saatte (aynı haftanın günü, rastgele 136 gün)
ECB'nin 14:15 CET'inde oran ≥ 3 olan gün %1,5; ABD saatlerinde (08:30 ve 14:00 ET) olay dışı günlerde de
başka yayımlar olduğu için oran yüksek çıkabiliyor — o yüzden ölçü çürütmek için kullanılır, seçmek için değil.

Basın toplantıları bu sınamaya girmez: başlangıçlarında tek dakikalık bir sıçrama yoktur (konuşma yavaş
yayılır) ve karar dakikasının oynaklığı pencereyi doldurur. Onlar için yalnız bilgi verilir: toplantının ilk
15 dakikasındaki aralığın, önceki 15 dakikaya oranı.
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
ESIK = 3.0
BASIN = {"FOMC_basin", "ECB_basin"}


def _aralik(d: vr.Dakika, bas: int, son: int) -> tuple[np.ndarray, np.ndarray]:
    i, j = np.searchsorted(d.t, [bas, son])
    return d.t[i:j], (d.mh[i:j] - d.ml[i:j]) / d.pip


def oran(d: vr.Dakika, t0: int) -> float:
    """Sıçrama oranı: [t0, t0+2 dk] en büyük dakikalık aralık / [t0−30, t0−3 dk] medyan aralık."""
    t, a = _aralik(d, t0 - 30 * 60, t0 + 3 * 60)
    on = a[t < t0 - 2 * 60]
    pen = a[(t >= t0) & (t <= t0 + 2 * 60)]
    if len(on) < 15 or len(pen) < 2:
        return float("nan")
    m = float(np.median(on))
    return float(pen.max() / m) if m > 0 else float("nan")


ADAY_DK = (-60, -30, 30, 60)


def parite_hukmu(d: vr.Dakika, t0: int) -> dict:
    r0 = oran(d, t0)
    if not np.isfinite(r0):
        return {"durum": "veri_yok"}
    aday = {str(k): oran(d, t0 + k * 60) for k in ADAY_DK}
    aday = {k: round(v, 2) for k, v in aday.items() if np.isfinite(v)}
    en_iyi = max(aday.items(), key=lambda kv: kv[1]) if aday else (None, float("nan"))
    if r0 >= ESIK:
        durum = "dogrulandi"
    elif en_iyi[0] is not None and en_iyi[1] >= ESIK and en_iyi[1] >= 2 * r0:
        durum = "celiski"
    else:
        durum = "sessiz"
    return {"durum": durum, "oran": round(r0, 2), "aday": aday,
            "en_iyi_aday_dk": int(en_iyi[0]) if en_iyi[0] is not None else None}


def basin_bilgisi(d: vr.Dakika, t0: int) -> dict | None:
    t, a = _aralik(d, t0 - 15 * 60, t0 + 15 * 60)
    once, sonra = a[t < t0], a[t >= t0]
    if len(once) < 10 or len(sonra) < 10 or once.mean() <= 0:
        return None
    return {"ilk15_once15_orani": float(sonra.mean() / once.mean())}


def main() -> int:
    a = ay.oku()
    olay = tk.tumu()
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
            kayit["parite"][cift] = parite_hukmu(d, t0)
        if o["olay"] in BASIN:
            kayit["hukum"] = "basin_bilgi"
        else:
            dur = [v["durum"] for v in kayit["parite"].values() if v.get("durum") in ("dogrulandi", "celiski", "sessiz")]
            if not dur:
                kayit["hukum"] = "degerlendirilemedi"
            elif dur.count("celiski") * 2 > len(dur):
                kayit["hukum"] = "celiski"
            elif "dogrulandi" in dur:
                kayit["hukum"] = "dogrulandi"
            else:
                kayit["hukum"] = "sessiz"
        satir.append(kayit)
    ozet: dict = {}
    for k in satir:
        oz = ozet.setdefault(k["olay"], {})
        oz[k["hukum"]] = oz.get(k["hukum"], 0) + 1
    celiski = [f"{k['olay']} {k['tarih']} {k['yerel_saat']} {k['bolge']}: "
                + ", ".join(f"{c} oran {v.get('oran')} · en iyi aday {v.get('en_iyi_aday_dk')} dk "
                            f"({(v.get('aday') or {}).get(str(v.get('en_iyi_aday_dk')))})"
                            for c, v in k["parite"].items() if v.get("durum") == "celiski")
                for k in satir if k["hukum"] == "celiski"]
    CIKTI.write_text(json.dumps({"kural": {"esik": ESIK, "aday_dk": list(ADAY_DK), "taban_dk": [-30, -3],
                                          "olay_dk": [0, 2]},
                                 "ozet": ozet, "celiski": celiski, "olay": satir},
                                ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    for o, v in ozet.items():
        print(f"{o:12s} {v}")
    for s in celiski:
        print("  çelişki:", s)
    return 0


if __name__ == "__main__":
    sys.exit(main())
