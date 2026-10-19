#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Gözlem: ilk mumdan sonra fiyat ne yaptı — YALNIZ 2018–2023.

Oyun planı bu dosyanın çıktısından yazılır ve 2024 ve sonrasında sınanır. Sınamanın anlamlı olması için plan
yazılırken 2024 sonrası veri hiçbir yoldan görülmemelidir; bu yüzden veri buraya ayar dosyasının bitiş tarihi
31.12.2023'e çekilerek yüklenir (2024 ve sonrasının dosyaları hiç açılmaz) ve her olay ayrıca o tarihe karşı
sınanır.

Her olay için ölçülen (birimi ilk mumun aralığı R; yön ilk mumun yönü — reddedilen mumda reddin yönü):
- devam      : fiyat, mumun öbür ucunu görmeden, kendi ucunu 0,5 R aştı
- donus      : fiyat, kendi ucunu 0,5 R aşmadan, mumun öbür ucunu kırdı
- orta       : pencerede mumun orta noktasına (yarısına) döndü
- orta_uc    : orta noktaya döndükten sonra, öbür uca gitmeden kendi ucuna ulaştı ("geri çekilip devam")
- kapanis    : pencerenin sonunda fiyat ilk mumun kapanışının mumun yönünde
- mfe, mae   : penceredeki en iyi ve en kötü hareket, mumun kapanışından, R cinsinden
Küçük mumda yön yoktur: hangi ucun önce kırıldığı ve kırılan tarafta 1 R ilerleyip ilerlemediği ölçülür.

Aynı dakikada iki seviye birden görülürse sıra bilinemez; o olay iki sonuçta da "olmadı" sayılır (kötümser).
"""
from __future__ import annotations

import dataclasses
import gzip
import json
import sys
from datetime import date
from pathlib import Path

import numpy as np
import pandas as pd

import sinif as sf

import ayar as ay  # noqa: E402  (sinif FxGunici'yi yola ekler)
import veri as vr  # noqa: E402

BURASI = Path(__file__).resolve().parent
CIKTI = BURASI / "veri"
IC_BITIS = date(2023, 12, 31)


def _ilk(maske: np.ndarray) -> int:
    return int(np.argmax(maske)) if maske.any() else 10 ** 9


def sonuc(d: vr.Dakika, e: dict) -> dict:
    hi, lo = d.mh[e["j0"]:e["j1"]], d.ml[e["j0"]:e["j1"]]
    h, l, c, R, s = e["h"], e["l"], e["c"], e["h"] - e["l"], e["yon"]
    son = d.mc[e["j1"] - 1]
    out = {}
    if s == 0:
        ust, alt = _ilk(hi > h), _ilk(lo < l)
        if ust == alt:
            out.update(kirilim=0, kirilim_1R=False)
            return out
        y = 1 if ust < alt else -1
        k = min(ust, alt)
        ilerle = _ilk(hi[k:] >= h + R) if y > 0 else _ilk(lo[k:] <= l - R)
        ters = _ilk(lo[k:] < l) if y > 0 else _ilk(hi[k:] > h)
        out.update(kirilim=y, kirilim_1R=ilerle < ters)
        return out
    uc, ters_uc = (h, l) if s > 0 else (l, h)
    orta = (h + l) / 2
    if s > 0:
        dev, dev1, uca, opp, mid = hi >= h + 0.5 * R, hi >= h + R, hi >= h, lo <= l, lo <= orta
        mfe, mae = (hi.max() - c) / R, (c - lo.min()) / R
    else:
        dev, dev1, uca, opp, mid = lo <= l - 0.5 * R, lo <= l - R, lo <= l, hi >= h, hi >= orta
        mfe, mae = (c - lo.min()) / R, (hi.max() - c) / R
    t_dev, t_dev1, t_opp, t_mid = _ilk(dev), _ilk(dev1), _ilk(opp), _ilk(mid)
    orta_uc = False
    if t_mid < 10 ** 9:
        k = t_mid
        a, b = _ilk(uca[k + 1:]), _ilk(opp[k:])          # orta noktaya dokunduğu dakikada kendi ucu sayılmaz
        orta_uc = (a + 1) < b if a < 10 ** 9 else False
    out.update(devam=t_dev < t_opp, devam_1R=t_dev1 < t_opp, donus=t_opp < t_dev, orta=t_mid < 10 ** 9,
               orta_uc=orta_uc, kapanis=bool(s * (son - c) > 0), mfe=float(mfe), mae=float(mae),
               ilk_orta_dk=(t_mid + 1) if t_mid < 10 ** 9 else None)
    return out


def topla(df: pd.DataFrame, anahtar: list[str]) -> list[dict]:
    out = []
    for k, g in df.groupby(anahtar, dropna=False):
        k = k if isinstance(k, tuple) else (k,)
        r = dict(zip(anahtar, k))
        r["n"] = int(len(g))
        r["cift_n"] = {c: int(x) for c, x in g["cift"].value_counts().sort_index().items()}
        if (g["yon"] != 0).any():
            g = g[g["yon"] != 0]
            r["n_yonlu"] = int(len(g))
            for x in ("devam", "devam_1R", "donus", "orta", "orta_uc", "kapanis"):
                r[x] = float(g[x].mean())
            r["mfe_med"], r["mae_med"] = float(g["mfe"].median()), float(g["mae"].median())
            om = g["orta"].astype(bool)
            if om.any():
                r["ilk_orta_dk_med"] = float(g.loc[om, "ilk_orta_dk"].median())
        else:
            yon = g["kirilim"]
            r["kirilim_var"] = float((yon != 0).mean())
            r["kirilim_trendle"] = float(((yon != 0) & (yon == g["trend"])).sum() / max((yon != 0).sum(), 1))
            r["kirilim_1R"] = float(g["kirilim_1R"].mean())
        out.append(r)
    return out


def main() -> int:
    a = dataclasses.replace(ay.oku(), bitis=IC_BITIS)
    hepsi = []
    for cift in a.ciftler:
        d = vr.oku(cift, a)
        assert pd.Timestamp(d.t[-1], unit="s") < pd.Timestamp("2024-01-01"), "2024 sonrası veri gözleme girdi"
        for an in sf.ANLAR:
            ev = sf.olaylar(d, an, cift)
            if len(ev) == 0:
                continue
            ev = ev[pd.to_datetime(ev["t0"], unit="s") < pd.Timestamp("2024-01-01")]
            sonu = [sonuc(d, e) for e in ev.to_dict("records")]
            hepsi.append(pd.concat([ev.reset_index(drop=True), pd.DataFrame(sonu)], axis=1))
        print(f"  {cift}: {sum(len(x) for x in hepsi if x['cift'].iloc[0] == cift)} olay", flush=True)
    df = pd.concat(hepsi, ignore_index=True)
    CIKTI.mkdir(exist_ok=True)
    with gzip.open(CIKTI / "gozlem_olaylar.csv.gz", "wt", encoding="utf-8") as f:
        df.drop(columns=["j0", "j1"]).to_csv(f, index=False)
    ozet = {"donem": ["2018-01-01", IC_BITIS.isoformat()], "olay": int(len(df)),
            "an": {an.kimlik: {"ad": an.ad, "aile": an.aile, "tf": an.tf, "pencere": an.pencere} for an in sf.ANLAR},
            "sinif": topla(df, ["an", "sinif", "uyum"]),
            "sinif_yonsuz_trend": topla(df, ["an", "sinif"]),
            "fiksing_ay_sonu": topla(df[df["an"].isin(["wmr", "tokyo_fiks"])], ["an", "ay_sonu", "sinif"])}
    (CIKTI / "gozlem.json").write_text(json.dumps(ozet, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    print(f"✓ {len(df)} olay → veri/gozlem.json")
    return 0


if __name__ == "__main__":
    sys.exit(main())
