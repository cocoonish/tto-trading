#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""HÜRMÜZ GEÇİŞLERİ — seviye değil TABANA GÖRE konum.

İlk keşif (kesif_jeo.py) PortWatch'ın açık olduğunu ölçtü ve son 25 günü
bastı: günlük toplam 2–8 gemi. O sayı TEK BAŞINA hiçbir şey söylemez —
"az" demek için normalin ne olduğu gerekir, ve bu veri kümesi bütün
trafiği değil PortWatch'ın izlediği gemileri sayıyor olabilir. Bu yüzden
burada üç şey birden ölçülüyor:

  1. HÜRMÜZ'ün kendi TARİHÇESİ (taban dönemi ile bugün).
  2. BAŞKA DARBOĞAZLAR aynı pencerede — düşüş Hürmüz'e özgü mü, yoksa
     veri kümesinin genelinde mi. Kontrol grubu olmadan bir düşüş ölçüm
     değil, yorumdur.
  3. TANKER bacağı ayrı: petrol sorusunun muhatabı o.

Ayrıca aylık emtia (Dünya Bankası Pink Sheet) ve GDELT yeniden deneniyor;
GDELT ilk koşuda zaman aşımına uğradı ve devre kesici açıldı — bir zaman
aşımı kaynağın ne döndürdüğü hakkında hiçbir şey söylemez.

Koşum:  veri.yml → kesif = bulten/kesif_hurmuz.py
"""
from __future__ import annotations

import json
import statistics as ist
import sys
from collections import defaultdict
from datetime import datetime, timezone

import requests

B = {"User-Agent": "Mozilla/5.0 (compatible; tto-arastirma/1.0)"}
KAT = ("https://services9.arcgis.com/weJ1QsnbMYJlCHdG/arcgis/rest/services/"
       "Daily_Chokepoints_Data/FeatureServer/0")


def cek(nerede: str, kac: int = 6000) -> list[dict]:
    """Bir darboğazın bütün günlük kayıtları (sayfalı)."""
    out, ofs = [], 0
    while True:
        r = requests.get(KAT + "/query", timeout=60, headers=B, params={
            "where": f"portname='{nerede}'", "outFields": "*", "f": "json",
            "orderByFields": "date ASC", "resultOffset": ofs,
            "resultRecordCount": 2000})
        js = r.json()
        ozl = js.get("features", [])
        out += [f["attributes"] for f in ozl]
        if len(ozl) < 2000 or len(out) >= kac:
            break
        ofs += 2000
    return out


def gun(a: dict) -> str:
    t = a.get("date")
    if isinstance(t, (int, float)):
        return datetime.fromtimestamp(t / 1000, timezone.utc).strftime("%Y-%m-%d")
    return str(t)[:10]


def darbogaz_listesi() -> list[str]:
    r = requests.get(KAT + "/query", timeout=45, headers=B, params={
        "where": "1=1", "outFields": "portname", "returnDistinctValues": "true",
        "f": "json", "resultRecordCount": 100})
    return sorted({f["attributes"]["portname"] for f in r.json().get("features", [])})


def ozetle(ad: str, kayit: list[dict]) -> dict | None:
    if not kayit:
        print(f"  {ad}: kayıt yok")
        return None
    seri = sorted(((gun(a), a) for a in kayit), key=lambda z: z[0])
    ay = defaultdict(lambda: defaultdict(list))
    for t, a in seri:
        for alan in ("n_total", "n_tanker", "n_cargo", "capacity"):
            v = a.get(alan)
            if v is not None:
                ay[t[:7]][alan].append(float(v))
    print(f"\n  ── {ad}  ({seri[0][0]} → {seri[-1][0]}, {len(seri)} gün)")
    print(f"     {'ay':<9} {'n_total':>9} {'n_tanker':>9} {'kapasite':>12}")
    for k in sorted(ay):
        d = ay[k]
        print(f"     {k:<9} {ist.mean(d['n_total']):9.2f} {ist.mean(d['n_tanker']):9.2f} "
              f"{ist.mean(d['capacity']):12,.0f}")
    # TABAN: savaş öncesi pencere (fiyat kırılması 02.03.2026'da ölçüldü)
    taban = [a for t, a in seri if t < "2026-03-01"]
    simdi = [a for t, a in seri if t >= "2026-08-20"]
    cik = {}
    for alan in ("n_total", "n_tanker", "capacity"):
        tb = [float(a[alan]) for a in taban if a.get(alan) is not None]
        sm = [float(a[alan]) for a in simdi if a.get(alan) is not None]
        if tb and sm:
            o_t, o_s = ist.mean(tb), ist.mean(sm)
            cik[alan] = (o_t, o_s, (o_s / o_t - 1) * 100 if o_t else float("nan"))
            print(f"     {alan:<11} taban(→02.2026) {o_t:8.2f}  son(20.08→) {o_s:8.2f}  "
                  f"{cik[alan][2]:+7.1f}%   n={len(tb)}/{len(sm)}")
    return cik


def hurmuz_ve_kontrol():
    print("=" * 78)
    print("1. DARBOĞAZ LİSTESİ")
    print("=" * 78)
    try:
        adlar = darbogaz_listesi()
        print("  " + " · ".join(adlar))
    except Exception as ex:                                      # noqa: BLE001
        print(f"  liste alınamadı: {ex!r}")
        adlar = ["Strait of Hormuz"]

    hedef = [a for a in adlar if any(s in a.lower() for s in
             ("hormuz", "suez", "mandeb", "malacca", "panama", "gibraltar",
              "bosphorus", "dover", "taiwan", "good hope"))]
    print(f"\n  ölçülecek: {hedef}")

    print()
    print("=" * 78)
    print("2. AYLIK GEÇİŞ — Hürmüz ve kontrol darboğazları")
    print("=" * 78)
    for ad in hedef:
        try:
            ozetle(ad, cek(ad))
        except Exception as ex:                                  # noqa: BLE001
            print(f"  {ad}: düştü {ex!r}")


def gdelt():
    print()
    print("=" * 78)
    print("3. GDELT — haber hacmi (ilk koşuda zaman aşımı; uzun süreyle yeniden)")
    print("=" * 78)
    for etiket, q in (("Hürmüz", '"strait of hormuz"'),
                      ("İran savaşı", '"iran war"'),
                      ("rafineri saldırısı", '"refinery strike" OR "refinery attack"'),
                      ("ateşkes", '"ceasefire"')):
        u = ("https://api.gdeltproject.org/api/v2/doc/doc?query="
             + requests.utils.quote(q) + "&mode=timelinevol&timespan=12m&format=json")
        try:
            r = requests.get(u, timeout=90, headers=B)
            seri = r.json()["timeline"][0]["data"]
            d = [p["value"] for p in seri]
            z = max(range(len(d)), key=lambda i: d[i])
            print(f"  {etiket:<20} n={len(seri)}  son {seri[-1]['date'][:8]} {d[-1]:.4f}"
                  f"  zirve {seri[z]['date'][:8]} {d[z]:.4f}  son/zirve {d[-1]/d[z]*100:.0f}%")
            k = max(1, len(seri)//30)
            print("      " + " ".join(f"{p['date'][4:8]}:{p['value']:.2f}" for p in seri[::k][-16:]))
        except Exception as ex:                                  # noqa: BLE001
            print(f"  {etiket:<20} düştü: {type(ex).__name__}")


def main() -> int:
    print(f"HÜRMÜZ KEŞFİ · {datetime.now(timezone.utc):%Y-%m-%d %H:%M} UTC\n")
    hurmuz_ve_kontrol()
    gdelt()
    print("\nBİTTİ")
    return 0


if __name__ == "__main__":
    sys.exit(main())
