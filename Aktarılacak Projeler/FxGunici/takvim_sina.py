#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Takvimdeki her olayın SAATİNİ 1 dakikalık fiyattan ayrıca sınar.

Resmi metin saati söyler; fiyat onu ayrıca SINAR, ama yalnız ÇÜRÜTEBİLİR. Ölçü: olay dakikası ve sonraki iki
dakikanın en büyük dakikalık mid aralığının, olaydan önceki 30 → 3 dakikanın medyan aralığına oranı (sıçrama
oranı). Aynı oran bir saat önce ve sonra (yaz saati hatası) ve yarım saat önce ve sonra (ECB 13:45 ↔ 14:15
değişimi) da hesaplanır. Parite başına üç hâl:
  · doğrulandı — resmi saatte oran ≥ ESIK
  · çelişki    — bir aday saatte oran ≥ ESIK ve resmi saatin oranının en az iki katı (aday daha iyi oturuyor)
  · sessiz     — ikisi de değil: resmî dakikada ve ±1 saatlik adaylarda sıçrama yok (piyasanın günün başka bir
                 saatinde kımıldamış olabileceğini bu ölçü söylemez; aşağıdaki uzak tarama söyler)
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

UZAK TARAMA (16.10.2026, inceleme): ±1 saatlik adaylar beş saatlik bir kaymayı yapısal olarak göremez (2020'nin üç
BoE Para Politikası Raporu günü, saat kuraldan 12:00 yazılmışken fiyat 07:00'yi gösteriyordu). Bu yüzden ±6 saatlik
yarım saatlik bir tarama da yapılır ve resmî saatin oranını açıkça aşan uzak saat (≥ ESIK ve resmî oranın en az iki
katı) adıyla RAPORLANIR. Kural değildir, hüküm değişmez: aynı tarama denetimde on iki adayın onunda aynı günün başka
bir resmî yayımını buldu; o yüzden takvimin o saatteki öbür olayları yanına yazılır.

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
#: Uzak tarama: ±6 saat, yarım saat adımla (yakın adaylar ve resmî dakika hariç). Yalnız rapor.
UZAK_DK = tuple(k for k in range(-360, 361, 30) if k != 0 and k not in ADAY_DK)


def uzak_tarama(d: vr.Dakika, t0: int, r0: float) -> dict | None:
    """±6 saatlik taramanın en büyük oranı, resmî saatin oranını açıkça aşıyorsa (≥ ESIK ve ≥ 2 kat); değilse None."""
    en = None
    for k in UZAK_DK:
        v = oran(d, t0 + k * 60)
        if np.isfinite(v) and (en is None or v > en[1]):
            en = (k, v)
    if en and en[1] >= ESIK and (not np.isfinite(r0) or en[1] >= 2 * r0):
        return {"dk": int(en[0]), "oran": round(float(en[1]), 2)}
    return None


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
    out = {"durum": durum, "oran": round(r0, 2), "aday": aday,
           "en_iyi_aday_dk": int(en_iyi[0]) if en_iyi[0] is not None else None}
    u = uzak_tarama(d, t0, r0)
    if u:
        out["uzak"] = u
    return out


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
    # Uzak tarama raporu: paritelerin en az yarısında resmî saati açıkça aşan uzak saat; o saatteki öbür olaylar adıyla.
    zaman = olay[["olay", "tarih", "utc_sn"]].to_numpy()
    uzak = []
    for k, (_, o) in zip(satir, olay.iterrows()):
        par = {c: v["uzak"] for c, v in k["parite"].items() if isinstance(v, dict) and v.get("uzak")}
        degerli = [c for c, v in k["parite"].items() if isinstance(v, dict) and v.get("durum") in
                   ("dogrulandi", "celiski", "sessiz")]
        if not par or len(par) * 2 < len(degerli):
            continue
        dk = sorted({v["dk"] for v in par.values()})
        t0 = int(o["utc_sn"])
        baska = sorted({f"{x[0]} {x[1]}" for d_ in dk for x in zaman
                        if abs(int(x[2]) - (t0 + d_ * 60)) <= 180 and not (x[0] == o["olay"] and x[1] == o["tarih"])})
        uzak.append({"olay": k["olay"], "tarih": k["tarih"], "yerel_saat": k["yerel_saat"], "bolge": k["bolge"],
                     "parite": par, "dk": dk, "baska_olay": baska})
    celiski = [f"{k['olay']} {k['tarih']} {k['yerel_saat']} {k['bolge']}: "
                + ", ".join(f"{c} oran {v.get('oran')} · en iyi aday {v.get('en_iyi_aday_dk')} dk "
                            f"({(v.get('aday') or {}).get(str(v.get('en_iyi_aday_dk')))})"
                            for c, v in k["parite"].items() if v.get("durum") == "celiski")
                for k in satir if k["hukum"] == "celiski"]
    CIKTI.write_text(json.dumps({"kural": {"esik": ESIK, "aday_dk": list(ADAY_DK), "taban_dk": [-30, -3],
                                          "olay_dk": [0, 2], "uzak_dk": [min(UZAK_DK), max(UZAK_DK), 30]},
                                 "ozet": ozet, "celiski": celiski, "uzak": uzak, "olay": satir},
                                ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    for o, v in ozet.items():
        print(f"{o:12s} {v}")
    for s in celiski:
        print("  çelişki:", s)
    for u in uzak:
        print(f"  uzak saat (rapor): {u['olay']} {u['tarih']} {u['yerel_saat']} → {u['dk']} dk"
              + (f" · o saatte: {', '.join(u['baska_olay'])}" if u["baska_olay"] else ""))
    return 0


if __name__ == "__main__":
    sys.exit(main())
