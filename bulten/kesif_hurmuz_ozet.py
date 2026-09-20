#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""HÜRMÜZ — yalnız HÜKÜM SATIRLARI ve figürün beslemesi.

kesif_hurmuz.py bütün aylık tabloyu basıyor (yedi darboğaz × ~90 ay);
koşu kaydı okunabilir ama uzun. Bu betik aynı ölçüyü yapar, yalnız
kıyas satırlarını ve son 60 günü basar, ayrıca figür için günlük seriyi
JSON olarak döker.

TABAN SEÇİMİ ölçüden geliyor: enerji fiyatlarındaki rejim kırılması
02.03.2026'da ölçüldü (Brent aylık ortalaması 66 → 95, distilat crack
41 → 73). Taban o günden ÖNCESİ.
"""
from __future__ import annotations

import json
import statistics as ist
import sys
from collections import defaultdict
from datetime import date, datetime, timedelta, timezone

import requests

B = {"User-Agent": "Mozilla/5.0 (compatible; tto-arastirma/1.0)"}
KAT = ("https://services9.arcgis.com/weJ1QsnbMYJlCHdG/arcgis/rest/services/"
       "Daily_Chokepoints_Data/FeatureServer/0")
KIRILMA = "2026-03-02"


def cek(nerede: str) -> list[dict]:
    out, ofs = [], 0
    while True:
        r = requests.get(KAT + "/query", timeout=60, headers=B, params={
            "where": f"portname='{nerede}'", "outFields": "*", "f": "json",
            "orderByFields": "date ASC", "resultOffset": ofs,
            "resultRecordCount": 1000})
        js = r.json()
        ozl = js.get("features", [])
        out += [f["attributes"] for f in ozl]
        if not ozl or not js.get("exceededTransferLimit"):
            break
        ofs += len(ozl)
    return out


def gun(a):
    t = a.get("date")
    if isinstance(t, (int, float)):
        return datetime.fromtimestamp(t / 1000, timezone.utc).strftime("%Y-%m-%d")
    return str(t)[:10]


def main() -> int:
    r = requests.get(KAT + "/query", timeout=45, headers=B, params={
        "where": "1=1", "outFields": "portname", "returnDistinctValues": "true",
        "f": "json", "resultRecordCount": 100})
    adlar = sorted({f["attributes"]["portname"] for f in r.json()["features"]})
    print("darboğazlar:", " · ".join(adlar), "\n")

    print(f"{'darboğaz':<26} {'n_total taban→son':>28} {'n_tanker taban→son':>28}")
    print("-" * 86)
    defter = {}
    for ad in adlar:
        try:
            k = cek(ad)
        except Exception as ex:                                  # noqa: BLE001
            print(f"{ad:<26} düştü {ex!r}"); continue
        if not k:
            continue
        seri = sorted(((gun(a), a) for a in k), key=lambda z: z[0])
        tb = [a for t, a in seri if t < KIRILMA]
        sn = [a for t, a in seri if t >= "2026-08-20"]
        if not tb or not sn:
            print(f"{ad:<26} taban/son penceresi boş (n={len(seri)})"); continue
        sat = []
        for alan in ("n_total", "n_tanker"):
            a0 = ist.mean([float(x[alan]) for x in tb if x.get(alan) is not None])
            a1 = ist.mean([float(x[alan]) for x in sn if x.get(alan) is not None])
            sat.append(f"{a0:8.1f} → {a1:7.1f} ({a1/a0*100-100:+6.1f}%)")
        print(f"{ad:<26} {sat[0]:>28} {sat[1]:>28}")
        defter[ad] = {"bas": seri[0][0], "son": seri[-1][0], "n": len(seri)}
        if "Hormuz" in ad:
            hormuz = seri

    print()
    print("=" * 78)
    print("HÜRMÜZ — aylık (2025-09'dan) ve son 60 gün")
    print("=" * 78)
    ay = defaultdict(lambda: defaultdict(list))
    for t, a in hormuz:
        for alan in ("n_total", "n_tanker", "capacity_tanker", "capacity"):
            v = a.get(alan)
            if v is not None:
                ay[t[:7]][alan].append(float(v))
    print(f"  {'ay':<9} {'n_total':>9} {'n_tanker':>9} {'kap_tanker':>13} {'kapasite':>13}")
    for k in sorted(ay):
        if k < "2025-09":
            continue
        d = ay[k]
        print(f"  {k:<9} {ist.mean(d['n_total']):9.2f} {ist.mean(d['n_tanker']):9.2f} "
              f"{ist.mean(d['capacity_tanker']):13,.0f} {ist.mean(d['capacity']):13,.0f}")
    print("\n  --- son 60 gün (n_total · n_tanker · kapasite) ---")
    for t, a in hormuz[-60:]:
        print(f"    {t}  {a.get('n_total'):>4}  {a.get('n_tanker'):>4}  "
              f"{a.get('capacity'):>12,}")

    # Kapsam: sağ uç eksik olabilir ve bu "trafik çöktü" ile aynı görünür.
    bugun = date.today()
    gunler = {t for t, _ in hormuz}
    son30 = sum(1 for i in range(30)
                if (bugun - timedelta(days=i)).strftime("%Y-%m-%d") in gunler)
    print(f"\n  KAPSAM: son kayıt {hormuz[-1][0]} "
          f"({(bugun - date.fromisoformat(hormuz[-1][0])).days} gün önce) · "
          f"son 30 takvim gününün {son30}'unda kayıt var · toplam {len(hormuz)} gün "
          f"({hormuz[0][0]}→)")
    print("\nDEFTER:", json.dumps(defter, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
